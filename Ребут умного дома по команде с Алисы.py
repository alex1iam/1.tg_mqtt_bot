import paho.mqtt.client as mqtt
import telegram
import subprocess
from datetime import datetime

# Токен бота в телеграме
bot_token = '1234567890:AAAAAAAAAAAAAAyTf6wTxY4'
# ID чата
chat_id = '0987654321'
# Создаем бота
bot = telegram.Bot(token=bot_token)
# Создаем клиента для MQTT
client = mqtt.Client()
# Подключаемся к брокеру
client.connect("localhost", 1883, 60)
# Подписываемся на топик №1
client.subscribe("zigbee2mqtt/command/reboot")

# Устанавливаем переменную для хранения предыдущего значения топика
prev_topic_value = None
mapp_topic_value = ""

# Обработчик подключения к MQTT
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

# Функция для работы с сообщениями топиков
def on_message(client, userdata, msg):
    global prev_topic_value
    global mapp_topic_value
    # Получаем текущее значение топика для команды и присваиваем переменной
    curr_topic_value = str(msg.payload.decode("utf-8"))
#    print(msg.topic+" "+str(msg.payload.decode("utf-8")))
    # Проверяем значение топика и мапим его
    if curr_topic_value == "off":
     mapp_topic_value = 'Поступила команда перезагрузки'
    # отправляем сообщение в телеграмм, что комп перазагружается.
#    bot.send_message(chat_id=chat_id, text=msg.topic+":: Отправлена команда перезагрузить компьютер")
     bot.send_message(chat_id=chat_id, text="Отправлена команда перезагрузить умный дом")
    # Сразу даем команду отправить комп на перезагрузку
     subprocess.run(["sudo", "reboot"])
     client.disconnect()



# Устанавливаем функцию для обработки сообщений
client.on_connect = on_connect
client.on_message = on_message


# Запускаем прослушивание сообщений
client.loop_forever()

