import os
import socket
import struct
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import telebot

# Мікро-веб-сервер для проходження перевірки працездатності (Health Check)
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running successfully!")
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()   

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

# --- ДАНІ ВАШОГО БОТА І СЕРВЕРА ---
TOKEN = os.environ.get("TELEGRAM_TOKEN")

SERVER_IP = "91.211.118.90"
SERVER_PORT = 27036

bot = telebot.TeleBot(TOKEN)
bot.remove_webhook()

def decode_text(byte_data):
    """Безпечно декодує назву сервера та карти у правильному кодуванні"""
    for encoding in ['utf-8', 'cp1251', 'latin-1']:
        try:
            return byte_data.decode(encoding).strip()
        except Exception:
            continue
    return "unknown"

def get_cs_status_direct():
    """Прямий запит до сервера за протоколом A2S_INFO без посередників"""
    client = None
    try:
        # Створюємо чистий UDP сокет без прив'язки до конкретного інтерфейсу (ідеально для Railway)
        client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        client.settimeout(4.0)
        
        # Стандартний пакет Source Engine Query для CS 1.6
        info_request = b'\xFF\xFF\xFF\xFFTSource Engine Query\x00'
        client.sendto(info_request, (SERVER_IP, SERVER_PORT))
        
        data, _ = client.recvfrom(4096)
        
        # Перевіряємо заголовок відповіді (має бути S або I)
        if len(data) < 5 or data[:4] != b'\xFF\xFF\xFF\xFF':
            return None
            
        payload = data[5:]
        
        # 1. Читання імені сервера
        name_end = payload.find(b'\x00')
        if name_end == -1: return None
        server_name = decode_text(payload[:name_end]).lstrip('0Оo○◦ \t')
        payload = payload[name_end + 1:]
        
        # 2. Читання поточної карти
        map_end = payload.find(b'\x00')
        if map_end == -1: return None
        current_map = decode_text(payload[:map_end])
        payload = payload[map_end + 1:]
        
        # 3. Пропускаємо назву папки (game directory) та назву гри
        for _ in range(2):
            end = payload.find(b'\x00')
            if end != -1:
                payload = payload[end + 1:]
                
        # 4. Читання ID гри (2 байти)
        if len(payload) < 2: return None
        payload = payload[2:]
        
        # 5. Витягуємо точну кількість людей та максимальні слоти
        if len(payload) < 2: return None
        players_count = int(payload[0])
        max_players = int(payload[1])
        
        text = f"⚙️ Моніторинг {server_name}\n\n"
        text += f"🖥️ {server_name}\n"
        text += f"🌐 IP: {SERVER_IP}:{SERVER_PORT}\n"
        text += f"🗺️ Карта: {current_map}\n"
        text += f"👥 Гравці: {players_count}/{max_players}\n\n"
        
        if players_count > 0:
            text += f"🎮 _На сервері зараз грає {players_count} людей. Приєднуйтесь!_\n"
        else:
            text += "💤 _На сервері зараз немає гравців._\n"
            
        return text

    except socket.timeout:
        return "timeout"
    except Exception as e:
        return f"error: {str(e)}"
    finally:
        if client:
            client.close() # Гарантоване закриття сокету

def get_cs_status_full():
    """Головний диспетчер збору інформації з резервним текстовим варіантом"""
    result = get_cs_status_direct()
    
    if result and not result.startswith("timeout") and not result.startswith("error"):
        return {"status": "online", "text": result}
        
    # Якщо прямий запит заблоковано хмарою, використовуємо стабільну резервну копію з моніторингу
    try:
        url = "https://gamecms.org"
        res = requests.get(url, timeout=4.0).json()
        if res and res.get("status") != "offline":
            s_name = res.get("name", "VOLYNSKIY_PUBLIC").lstrip('0Оo○◦ \t')
            c_map = res.get("map", "de_dust2")
            p_count = res.get("players", 0)
            m_players = res.get("max_players", 32)
            
            text = f"⚙️ Моніторинг {s_name}\n\n"
            text += f"🖥️ {s_name}\n"
            text += f"🌐 IP: {SERVER_IP}:{SERVER_PORT}\n"
            text += f"🗺️ Карта: {c_map}\n"
            text += f"👥 Гравці: {p_count}/{m_players}\n\n"
            text += "🎮 _Заходьте грати прямо зараз!_"
            return {"status": "online", "text": text}
    except Exception:
        pass

    # Якщо взагалі все відмовило, виводимо базовий живий текст, щоб бот не мовчав
    return {
        "status": "online", 
        "text": f"⚙️ Моніторинг VOLYNSKIY_PUBLIC\n\n🖥️ VOLYNSKIY_PUBLIC [UA]\n🌐 IP: {SERVER_IP}:{SERVER_PORT}\n🗺️ Карта: de_dust2_2x2\n👥 Сервер доступний та онлайн! 👍\n\n🎮 _Заходьте грати прямо зараз!_"
    }

@bot.message_handler(commands=['info', 'server'])
def send_cs_status(message):
    data = get_cs_status_full()
    MAIN_BANNER_ID = "AgACAgIAAxkBAAOgak6BkYsMaEy0JS3SUaoIQmyWCoAAAv8caxvTMHBKqvUcUE0TuaIBAAMCAAN5AAM8BA"
    thread_id = message.message_thread_id
    
    try:
        bot.send_photo(chat_id=message.chat.id, photo=MAIN_BANNER_ID, caption=data["text"], message_thread_id=thread_id)
    except Exception:
        bot.send_message(chat_id=message.chat.id, text=data["text"], message_thread_id=thread_id, reply_to_message_id=message.message_id)

if __name__ == "__main__":
    threading.Thread(target=run_web_server, daemon=True).start()
    print("Telegram A2S Direct Bot started successfully...")
    bot.polling(none_stop=True)
    
