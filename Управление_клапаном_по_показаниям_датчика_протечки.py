import paho.mqtt.client as mqtt
import configparser
import telegram
import time
from datetime import datetime

# === Чтение конфигураций ===
config = configparser.ConfigParser()
config.read('/opt/tg_mqtt_bot/settings.ini')

# Настройки из settings.ini
mqtt_broker = config['MQTT']['ip']
mqtt_port = int(config['MQTT']['port'])
bot_token = config['TELEGRAM']['bot_token']
chat_id = int(config['TELEGRAM']['chat_id'])
bot = telegram.Bot(token=bot_token)

# === Датчики протечки ===
leak_sensors = [
    "zigbee2mqtt/4d9a. КУХНЯ Датчик протечки/water_leak",
    "zigbee2mqtt/4db7. КУХНЯ Датчик протечки/water_leak",
    "zigbee2mqtt/4d61. ВАННАЯ Датчик протечки/water_leak",
    "zigbee2mqtt/3b74. ВАННАЯ Датчик протечки/water_leak"
]

# === Клапаны (базовые топики без /state и /set) ===
valves_base = [
    "zigbee2mqtt/37cf. ВАННАЯ Клапан холодной воды",
    "zigbee2mqtt/639b. ВАННАЯ Клапан горячей воды"
]

# Топики состояния и команд
valves = [f"{base}/state" for base in valves_base]
valve_commands = {base: f"{base}/set" for base in valves_base}

# Состояния клапанов и флаги уведомлений
valve_states = {topic: None for topic in valves}
forced_closed_sent = {topic: False for topic in valves}
all_valves_closed_notified = False
all_valves_open_notified = False

# Активные протечки
active_leaks = set()

# === Утилиты ===
def send_telegram(message):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        bot.sendMessage(chat_id=chat_id, text=f"{timestamp} — {message}")
    except Exception as e:
        print("Ошибка Telegram:", e)

def get_device_name_from_topic(topic):
    name = topic
    if name.startswith("zigbee2mqtt/"):
        name = name[len("zigbee2mqtt/"):]
    return name.rsplit("/", 1)[0]

# === Обновление состояния клапана ===
def update_valve_state(topic, state):
    global all_valves_closed_notified, all_valves_open_notified
    previous_state = valve_states[topic]
    valve_states[topic] = state

    device_name = get_device_name_from_topic(topic)

    # Уведомления о срабатывании
    if state == "off" and previous_state != "off":
        send_telegram(f"🔴 {device_name}: вода перекрыта")
        forced_closed_sent[topic] = False
    elif state == "on" and previous_state != "on":
        send_telegram(f"🟢 {device_name}: вода включена")
        if active_leaks and not forced_closed_sent[topic]:
            base_topic = get_device_name_from_topic(topic)
            cmd_topic = None
            for base, command in valve_commands.items():
                if base_topic in base:
                    cmd_topic = command
                    break
            if cmd_topic:
                client.publish(cmd_topic, "OFF")
                send_telegram(f"🚨 Протечка активна, принудительно перекрыт клапан: {base_topic}")
                forced_closed_sent[topic] = True

    # Проверка всех клапанов
    if all(s == "off" for s in valve_states.values() if s is not None):
        if not all_valves_closed_notified:
            send_telegram("🔒 Все клапаны перекрыты")
            all_valves_closed_notified = True
                        all_valves_open_notified = False
    elif all(s == "on" for s in valve_states.values() if s is not None):
        if not all_valves_open_notified:
            send_telegram("🔓 Все клапаны открыты")
            all_valves_open_notified = True
            all_valves_closed_notified = False
    else:
        all_valves_closed_notified = False
        all_valves_open_notified = False

# === Запрос текущего состояния клапанов при старте ===
def request_valves_state(client):
    for base in valves_base:
        get_topic = f"{base}/get"
        client.publish(get_topic, '{"state":""}')
        print(f"Запрошено состояние клапана: {get_device_name_from_topic(base)}")

# === MQTT callbacks ===
def on_connect(client, userdata, flags, rc):
    print("MQTT connected")
    for topic in leak_sensors + valves:
        client.subscribe(topic)
    time.sleep(1)
    request_valves_state(client)

def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode("utf-8").strip().lower()
    device_name = get_device_name_from_topic(topic)

    # --- Датчики протечки ---
    if topic in leak_sensors:
        if payload == "true":
            if device_name not in active_leaks:
                active_leaks.add(device_name)
                send_telegram(f"⚠️ Обнаружена протечка! ({device_name})")
                for base, cmd_topic in valve_commands.items():
                    client.publish(cmd_topic, "OFF")
                    send_telegram(f"🚨 Отправлена команда на перекрытие клапана: {get_device_name_from_topic(base)}")
        elif payload == "false":
            if device_name in active_leaks:
                active_leaks.remove(device_name)
                send_telegram(f"✅ Протечка устранена ({device_name})")

    # --- Клапаны ---
    elif topic in valves:
        if payload in ["off", "0"]:
            update_valve_state(topic, "off")
        elif payload in ["on", "1"]:
            update_valve_state(topic, "on")
        else:
            print(f"Неизвестное состояние клапана: {topic} = {payload}")

# === Ручное открытие всех клапанов ===
def open_all_valves(client):
    for base, cmd_topic in valve_commands.items():
        client.publish(cmd_topic, "ON")
        send_telegram(f"🔔 Отправлена команда на открытие клапана: {get_device_name_from_topic(base)}")

# === MQTT клиент ===
client = mqtt.Client()

def main():
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(mqtt_broker, mqtt_port, 60)
    client.loop_forever()

if __name__ == "__main__":
    main()
