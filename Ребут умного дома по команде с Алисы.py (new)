import paho.mqtt.client as mqtt
import telegram
import subprocess

# Токен бота и ID чата (лучше хранить в переменных окружения)
BOT_TOKEN = '1234567890:AZvfg'
CHAT_ID = '0987654321'

# Создаем бота
bot = telegram.Bot(token=BOT_TOKEN)

# Функция обработки сообщений из MQTT
def on_message(client, userdata, msg):
    curr_topic_value = msg.payload.decode("utf-8")

    if curr_topic_value == "off":
        print("Получена команда перезагрузки")
        
        # Отправляем сообщение в Telegram
        bot.sendMessage(chat_id=CHAT_ID, text="Отправлена команда перезагрузить умный дом")
        
        # Перезагружаем систему
        subprocess.run(["sudo", "reboot"])

# Создаем MQTT-клиента
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

# Настроим MQTT-события
client.on_message = on_message
client.connect("localhost", 1883, 60)
client.subscribe("zigbee2mqtt/command/reboot")

# Запускаем бесконечный цикл
client.loop_forever()
