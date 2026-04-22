import paho.mqtt.client as mqtt
import configparser
import subprocess
import time
import threading
from datetime import datetime

# ======================
# CONFIG
# ======================
config = configparser.ConfigParser()
config.read('/opt/tg_mqtt_bot/settings.ini')

IP = config['MQTT']['ip']
PORT = int(config['MQTT']['port'])

BOT_TOKEN = config['TELEGRAM']['bot_token']
CHAT_ID = int(config['TELEGRAM']['chat_id'])

TOPIC_SYSTEM = "zigbee2mqtt/command/reboot/system"
TOPIC_Z2M = "zigbee2mqtt/command/reboot/z2m_service"

# ======================
# TELEGRAM (ленивая инициализация, не падает)
# ======================
telegram_available = True
bot = None

def init_telegram():
    """Инициализация Telegram бота (ленивая)"""
    global bot, telegram_available
    
    if bot is not None:
        return True
    
    try:
        import telegram
        bot = telegram.Bot(token=BOT_TOKEN)
        # Проверяем, что бот работает
        bot.get_me()
        telegram_available = True
        print("[TG] Bot initialized successfully")
        return True
    except Exception as e:
        telegram_available = False
        print(f"[TG] Telegram unavailable: {e}")
        return False

tg_queue = []
queue_lock = threading.Lock()
QUEUE_TTL = 60

def tg_worker():
    """Фоновый поток для отправки сообщений"""
    global bot, telegram_available
    
    while True:
        time.sleep(2)
        
        with queue_lock:
            now = time.time()
            tg_queue[:] = [(t, m) for (t, m) in tg_queue if now - t <= QUEUE_TTL]
            
            if not tg_queue:
                continue
            
            ts, msg = tg_queue.pop(0)
        
        # Пробуем инициализировать бота (если ещё нет)
        if bot is None:
            init_telegram()
        
        # Если телеграм недоступен — просто пропускаем отправку
        if not telegram_available or bot is None:
            print(f"[TG SKIP] Telegram not available, message: {msg}")
            continue
        
        try:
            bot.sendMessage(chat_id=CHAT_ID, text=msg)
            print("[TG SENT]", msg)
        except Exception as e:
            print(f"[TG ERROR] {e}")
            telegram_available = False
            bot = None  # Сбросим бота, чтобы переинициализировать позже
            # Не добавляем обратно в очередь, чтобы не зациклиться

def tg_send(msg):
    """Отправить сообщение (если получится)"""
    with queue_lock:
        tg_queue.append((time.time(), msg))

# ======================
# Z2M RESTART
# ======================
def restart_z2m_service():
    print(">>> STOP z2m.service")
    
    subprocess.run(["sudo", "systemctl", "stop", "z2m.service"])
    
    for i in range(15):
        status = subprocess.run(
            ["systemctl", "is-active", "z2m.service"],
            capture_output=True, text=True
        ).stdout.strip()
        
        print(f"STOP CHECK [{i}] =", status)
        
        if status == "inactive":
            break
        
        time.sleep(2)
    
    print(">>> START z2m.service")
    subprocess.run(["sudo", "systemctl", "start", "z2m.service"])
    
    final = subprocess.run(
        ["systemctl", "is-active", "z2m.service"],
        capture_output=True, text=True
    ).stdout.strip()
    
    print("FINAL STATUS =", final)

# ======================
# MQTT HANDLER
# ======================
def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode(errors="ignore").strip().lower()
    
    print("\n======================")
    print("MQTT RECEIVED")
    print("TOPIC  :", topic)
    print("PAYLOAD:", payload)
    print("======================\n")
    
    if payload != "off":
        print("IGNORE (not off)")
        return
    
    try:
        if topic == TOPIC_SYSTEM:
            print(">>> SYSTEM REBOOT TRIGGERED")
            tg_send("🔄 SYSTEM REBOOT")
            print(">>> EXEC reboot")
            subprocess.run(["sudo", "reboot"], check=True)
        
        elif topic == TOPIC_Z2M:
            print(">>> Z2M RESTART TRIGGERED")
            tg_send("♻️ Z2M restart")
            restart_z2m_service()
            tg_send("✅ Z2M restarted")
        
        else:
            print("UNKNOWN TOPIC")
    
    except Exception as e:
        print("ERROR:", e)
        tg_send(f"❌ ERROR: {e}")

def on_connect(client, userdata, flags, rc):
    print("MQTT CONNECT RC =", rc)
    client.subscribe([(TOPIC_SYSTEM, 0), (TOPIC_Z2M, 0)])
    print("SUBSCRIBED TO:")
    print(" -", TOPIC_SYSTEM)
    print(" -", TOPIC_Z2M)

def connect_mqtt():
    client = mqtt.Client()
    client.on_message = on_message
    client.on_connect = on_connect
    
    while True:
        try:
            client.connect(IP, PORT, 60)
            print("MQTT CONNECTED")
            return client
        except Exception as e:
            print("MQTT CONNECT FAILED:", e)
            time.sleep(5)

# ======================
# START
# ======================
threading.Thread(target=tg_worker, daemon=True).start()

print("SCRIPT STARTED")
print("[TG] Telegram will be initialized on first use")

client = connect_mqtt()
client.loop_forever()
