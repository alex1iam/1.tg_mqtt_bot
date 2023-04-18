import paho.mqtt.client as mqtt
import telegram

# Токен бота в телеграме
bot_token = '1234567890:AAqwertyuiopasdfghjklzxcvbnm'
# ID чата
chat_id = '0987654321'
# Создаем бота
bot = telegram.Bot(token=bot_token)
# Создаем клиента для MQTT
client = mqtt.Client()
# Подключаемся к брокеру
client.connect("localhost", 1883, 60)
# Подписываемся на топик
client.subscribe("zigbee2mqtt/8187. ВАННАЯ Датчик протечки/water_leak")

# Устанавливаем переменную для хранения предыдущего значения топика
prev_topic_value = None
mapp_topic_value = ""

# Обработчик подключения к MQTT
def on_connect(client, userdata, flags, rc):
    print("Connected with result code "+str(rc))

# Функция для получения сообщения из топика
def on_message(client, userdata, msg):
    global prev_topic_value
    global mapp_topic_value
    # Получаем текущее значение топика
    curr_topic_value = str(msg.payload.decode("utf-8"))
#    print(msg.topic+" "+str(msg.payload.decode("utf-8")))
#    print(curr_topic_value)
    # Делаем мапинг содержимого топика (для человекочитаемости)
    if curr_topic_value == 'true':
     mapp_topic_value = 'Обнаружена протечка'
    if  curr_topic_value == 'false':
     mapp_topic_value = 'Протечка не обнаружена'
    # Проверяем, что значение содержимого топика изменилось
    if prev_topic_value != curr_topic_value:
      # Отправляем сообщение в телеграмм
      bot.send_message(chat_id=chat_id, text=msg.topic+":: "+mapp_topic_value)
      # Также можно сделать подмену  названия топика на любую фразу:
#     bot.send_message(chat_id=chat_id, text="Сюда впихнуть что хочется вместо названия топика mqtt: "+mapp_topic_value)
      # Обновляем предыдущее значение топика
      prev_topic_value = curr_topic_value
#     print(msg.topic+" "+str(msg.payload.decode("utf-8")))

# Устанавливаем функцию для обработки сообщений
client.on_connect = on_connect
client.on_message = on_message

# Запускаем бесконечный цикл
client.loop_forever()
