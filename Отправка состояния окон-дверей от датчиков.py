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

# Создаем бота
bot = telegram.Bot(token=BOT_TOKEN)

# Список сенсоров: топик -> (название, текст_при_true, текст_при_false)
sensors = {
    "zigbee2mqtt/b20b. ЗАЛ Датчик открытия окна/contact":
        ("ЗАЛ. Датчик открытия окна", "Окно в зале закрыто", "Окно в зале открыто"),
    "zigbee2mqtt/9873. КУХНЯ Датчик открытия окна/contact":
        ("КУХНЯ. Датчик открытия окна", "Окно в кухне закрыто", "Окно в кухне открыто"),
    "zigbee2mqtt/8968. ПРИХОЖАЯ Датчик открытия двери/contact":
        ("ПРИХОЖАЯ. Датчик открытия двери", "Дверь закрыта", "Дверь открыта"),
}

# Сохраняем предыдущие значения для каждого сенсора
prev_values = {topic: None for topic in sensors.keys()}

# Обработчик подключения
def on_connect(client, userdata, flags, rc):
    print("Connected with result code " + str(rc))
    for topic in sensors.keys():
        client.subscribe(topic)
        print(f"Subscribed to {topic}")

# Обработчик сообщений
def on_message(client, userdata, msg):
    global prev_values
    curr_value = str(msg.payload.decode("utf-8")).lower()
    topic = msg.topic

    if topic not in sensors:
        return

    name, text_true, text_false = sensors[topic]

    if curr_value in ["true", "1"]:
        status_text = text_true
    elif curr_value in ["false", "0"]:
        status_text = text_false
    else:
        status_text = f"Неизвестное значение: {curr_value}"

    if prev_values[topic] != curr_value:
        message = f"{name}: {status_text}. Текущее время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        try:
            bot.sendMessage(chat_id=CHAT_ID, text=message)
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")
        print(message)
        prev_values[topic] = curr_value

# Создаем MQTT-клиента
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

# Подключаемся к брокеру
client.connect(IP, PORT, 60)

# Запускаем цикл
client.loop_forever()
