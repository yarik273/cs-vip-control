import os
import json
from datetime import datetime
import telebot
import threading
import http.server
import socketserver

# 1. Фейковий веб-сервер для обходу перевірки портів на Render
def run_fake_server():
    port = int(os.environ.get("PORT", 8080))
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *args: None 
    with socketserver.TCPServer(("", port), handler) as httpd:
        httpd.serve_forever()

threading.Thread(target=run_fake_server, daemon=True).start()

# 2. Ініціалізація бота та конфігурація прив'язки
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("Токен BOT_TOKEN не знайдено в змінних оточення!")

bot = telebot.TeleBot(BOT_TOKEN)

# НАЛАШТУВАННЯ ПРИВ'ЯЗКИ
ALLOWED_CHAT_USERNAME = "volynskiy_public"  # Юзернейм вашої групи
ALLOWED_THREAD_ID = 738                      # ID дозволеної гілки
MY_PERSONAL_ID = 5596041220                  # Ваш особистий Telegram ID

# 3. Обробка команди статусу VIP
@bot.message_handler(commands=['vip', 'vip_status'])
def send_vip_status(message):
    try:
        # ПЕРЕВІРКА ДОСТУПУ: Дозволяємо ЛС з вами АБО конкретну гілку у групі
        is_my_private_chat = (message.chat.type == 'private' and message.chat.id == MY_PERSONAL_ID)
        is_allowed_group_thread = (
            message.chat.username and 
            message.chat.username.lower() == ALLOWED_CHAT_USERNAME.lower() and 
            message.message_thread_id == ALLOWED_THREAD_ID
        )

        # Якщо це не ваш особистий чат і не дозволена гілка — повністю ігноруємо
        if not (is_my_private_chat or is_allowed_group_thread):
            return  

        if not os.path.exists('vip_users.json'):
            bot.reply_to(message, "❌ Помилка: Файл `vip_users.json` не знайдено!")
            return

        with open('vip_users.json', 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        today = datetime.now().date()
        
        # Заголовок повідомлення
        header = "📊 *СТАТУС VIP ПРИВІЛЕЙ:*\n\n"
        footer = "\n👉 Для купівлі або продовження привілей зв'яжіться з адміністрацією. @Marvel_Volynskiy_Public"
        
        chunks = []
        current_chunk = header
        
        if not users:
            bot.reply_to(message, "Список привілей порожній.")
            return

        for user in users:
            # Очищаємо дати від можливих випадкових пробілів на кінцях
            clean_date_str = user['expire_date'].strip()
            expire_date = datetime.strptime(clean_date_str, "%Y-%m-%d").date()
            days_left = (expire_date - today).days
            formatted_date = expire_date.strftime("%d.%m.%Y")
            
            if days_left > 5:
                status = f"⏳ Дійсна до: {formatted_date} (залишилось {days_left} дн.)"
            elif 0 < days_left <= 5:
                status = f"⚠️ Дійсна до: {formatted_date} (залишилось всього {days_left} дн.!)"
            elif days_left == 0:
                status = f"🚨 ЗАКІНЧУЄТЬСЯ СЬОГОДНІ ({formatted_date})!"
            else:
                status = f"❌ ТЕРМІН ЗАКІНЧИВСЯ ({formatted_date})!"
            
            # Екрануємо символи підкреслення окремо для кожного гравця, щоб Markdown не ламався
            clean_nickname = str(user['nickname']).replace("_", "\\_")
            clean_steam = str(user['steam_id']).replace("_", "\\_").strip()
            clean_privilege = str(user['privilege']).replace("_", "\\_")

            player_info = (
                f"👤 Нік: {clean_nickname}\n"
                f"🆔 Steam: `{clean_steam}`\n"
                f"👑 Привілея: {clean_privilege}\n"
                f"{status}\n"
                f"────────────────\n"
            )
            
            # Якщо додавання гравця перевищить безпечний ліміт (~3500 символів з урахуванням екранування)
            if len(current_chunk) + len(player_info) + len(footer) > 3500:
                chunks.append(current_chunk)
                current_chunk = ""  # Починаємо новий блок без заголовка
            
            current_chunk += player_info
        
        # Додаємо фінальний підпис до останнього блоку тексту
        current_chunk += footer
        chunks.append(current_chunk)
        
        # Надсилаємо всі частини по черзі
        for index, chunk in enumerate(chunks):
            if index == 0:
                bot.reply_to(message, chunk, parse_mode='Markdown')
            else:
                bot.send_message(message.chat.id, chunk, parse_mode='Markdown', message_thread_id=message.message_thread_id)
                
    except json.JSONDecodeError:
        bot.reply_to(message, "❌ Помилка: Неправильний формат тексту у файлі `vip_users.json`!")
    except Exception as e:
        bot.reply_to(message, f"❌ Системна помилка: {str(e)}")

# 4. Головний цикл запуску
if __name__ == "__main__":
    print("Бот контролю VIP запущений...")
    bot.infinity_polling()
    
