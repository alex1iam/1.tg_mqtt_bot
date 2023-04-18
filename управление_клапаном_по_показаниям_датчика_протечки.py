import paho.mqtt.client as mqtt
import telegram


# Токен бота в телеграме
bot_token = '1234567890:Aqwertyuiop'
# ID чата
chat_id = '0987654321'
# Создаем бота
bot = telegram.Bot(token=bot_token)
# Создаем клиента для MQTT
client = mqtt.Client()
# Подключаемся к брокеру
client.connect("localhost", 1883, 60)
# Подписываемся на топик №1
client.subscribe("zigbee2mqtt/8187. ВАННАЯ Датчик протечки/water_leak")

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
    # Получаем текущее значение топика датчика протечки и присваиваем переменной
    curr_topic_value = str(msg.payload.decode("utf-8"))
#    print(msg.topic+" "+str(msg.payload.decode("utf-8")))
    # Проверяем значение топика и мапим его
    if curr_topic_value == "true":
     mapp_topic_value = 'Обнаружена протечка'
    # Сразу грузим топик клапана, чтобы перекрыть воду
     client.publish("zigbee2mqtt/639b. ВАННАЯ Клапан горячей воды/set", "ON")
    # и отправляем сообщение в телеграмм, что вода перекрыта.
    # Спам в телегу будет идти на каждый ивент от датчика протечки,
    # но так как заливает, то это как раз дополнительные напоминания
     bot.send_message(chat_id=chat_id, text=msg.topic+":: Отправлена команда перекрыть горячую воду")

    if curr_topic_value == 'false':
     mapp_topic_value = 'Протечка не обнаружена или устранена'
     # Грузим топик клапана, чтобы включить воду, но отдельно в телегу пока не сообщаем
#    # и отправляем сообщение в телеграмм, что вода открыта
#     bot.send_message(chat_id=chat_id, text=msg.topic+":: Отправлена команда открыть горячую воду")

   # Проверяем, что значение содержимого топика изменилось
    if prev_topic_value != curr_topic_value:
      # Отправляем сообщение в телеграмм о статусе протечки
      bot.send_message(chat_id=chat_id, text=msg.topic+":: "+mapp_topic_value)
      # проверяем, что протечка устранена и сообщаем в телеграм
      if curr_topic_value == 'false':
       bot.send_message(chat_id=chat_id, text=msg.topic+":: Отправлена команда открыть горячую воду")
       client.publish("zigbee2mqtt/639b. ВАННАЯ Клапан горячей воды/set", "OFF")
      # Также можно сделать подмену  названия топика на любую фразу:
#     bot.send_message(chat_id=chat_id, text="Сюда впихнуть что хочется вместо названия топика mqtt: "+mapp_topic_value)
      # Обновляем предыдущее значение топика
      prev_topic_value = curr_topic_value
#     print(msg.topic+" "+str(msg.payload.decode("utf-8")))


# Устанавливаем функцию для обработки сообщений
client.on_connect = on_connect
client.on_message = on_message


# Запускаем прослушивание сообщений
client.loop_forever()
