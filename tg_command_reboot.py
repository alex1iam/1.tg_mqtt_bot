import paho.mqtt.client as mqtt
import configparser
import subprocess
import telegram
import time
from datetime import datetime

# === Чтение конфигураций ===
config = configparser.ConfigParser()
config.read('/opt/tg_mqtt_bot/settings.ini')

# Настройки из settings.ini
IP = config['MQTT']['ip']
PORT = int(config['MQTT']['port'])
BOT_TOKEN = config['TELEGRAM']['bot_token']
CHAT_ID = int(config['TELEGRAM']['chat_id'])

# Темы MQTT
TOPIC_SYSTEM = "zigbee2mqtt/command/reboot/system"
TOPIC_Z2M = "zigbee2mqtt/command/reboot/z2m_service"

# Создаем экземпляр Telegram-бота (для старой версии библиотеки)
bot = telegram.Bot(token=BOT_TOKEN)

# === ФУНКЦИЯ: надёжный перезапуск Zigbee2MQTT ===
def restart_z2m_service():
    print("→ Остановка сервиса z2m.service...")
    subprocess.run(["sudo", "systemctl", "stop", "z2m.service"], check=True)

    # Ожидание завершения
    for i in range(10):  # 15 попыток по 2 сек = 30 секунд максимум
        status = subprocess.run(
            ["systemctl", "is-active", "z2m.service"],
            capture_output=True, text=True
        ).stdout.strip()

        if status == "inactive":
            print("→ Сервис успешно остановлен.")
            break
        else:
            print(f"⏳ Сервис ещё не остановлен (попытка {i+1}/10)...")
            time.sleep(2)
    else:
        raise RuntimeError("Сервис Zigbee2MQTT не остановился за 30 секунд!")

    print("→ Запуск сервиса z2m.service...")
    subprocess.run(["sudo", "systemctl", "start", "z2m.service"], check=True)
    print("→ Сервис Zigbee2MQTT успешно запущен.")

# === ФУНКЦИЯ ОБРАБОТКИ СООБЩЕНИЙ ===
def on_message(client, userdata, msg):
    curr_topic_value = msg.payload.decode("utf-8").strip().lower()
    topic = msg.topic
    print(f"[{datetime.now()}] Получено сообщение из топика '{topic}': '{curr_topic_value}'")

    try:
        if curr_topic_value == "off":
            # --- Перезагрузка системы ---
            if topic == TOPIC_SYSTEM:
                bot.sendMessage(chat_id=CHAT_ID, text="🔄 Получена команда перезагрузить систему")
                print("→ Выполняется reboot...")
                subprocess.run(["sudo", "reboot"], check=True)

            # --- Перезапуск Zigbee2MQTT ---
            elif topic == TOPIC_Z2M:
                bot.sendMessage(chat_id=CHAT_ID, text="♻️ Получена команда перезапуска Zigbee2MQTT (stop → wait → start)")
                restart_z2m_service()
                bot.sendMessage(chat_id=CHAT_ID, text="✅ Сервис Zigbee2MQTT успешно перезапущен")

            else:
                print(f"Неизвестный топик: {topic}")

        else:
            print(f"Неизвестная команда '{curr_topic_value}' в топике '{topic}'")

    except subprocess.CalledProcessError as e:
        error_msg = f"Ошибка при выполнении команды: {e}"
        print(error_msg)
        bot.sendMessage(chat_id=CHAT_ID, text=f"❌ {error_msg}")

    except Exception as e:
        error_msg = f"Ошибка: {e}"
        print(error_msg)
        bot.sendMessage(chat_id=CHAT_ID, text=f"⚠️ {error_msg}")

# === НАСТРОЙКА MQTT ===
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message

client.connect(IP, PORT, 60)
client.subscribe([(TOPIC_SYSTEM, 0), (TOPIC_Z2M, 0)])

print(f"[{datetime.now()}] Ожидание команд...")
print(f"→ {TOPIC_SYSTEM} — перезагрузка системы")
print(f"→ {TOPIC_Z2M} — перезапуск Zigbee2MQTT (stop → wait → start)")

client.loop_forever()
