import os
import json
from datetime import datetime
import telebot
from flask import Flask
from threading import Thread

# Создаем микро-веб-сервер для Render
app = Flask('')

@app.route('/')
def home():
    return "Бот работает!"

def run_web_server():
    # Render автоматически дает порт в переменную PORT
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# Инициализируем бота Telegram
BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['vip', 'vip_status'])
def send_vip_status(message):
    try:
        if not os.path.exists('vip_users.json'):
            bot.reply_to(message, "❌ Ошибка: Файл `vip_users.json` не найден!")
            return

        with open('vip_users.json', 'r', encoding='utf-8') as f:
            users = json.load(f)
        
        today = datetime.now().date()
        lines = []
        
        for user in users:
            expire_date = datetime.strptime(user['expire_date'], "%Y-%m-%d").date()
            days_left = (expire_date - today).days
            formatted_date = expire_date.strftime("%d.%m.%Y")
            
            if days_left > 5:
                status = f"⏳ Дійсна до: {formatted_date} (залишилось {days_left} дн.)"
            elif 0 < days_left <= 5:
                status = f"⚠️ **Дійсна до: {formatted_date} (залишилось всього {days_left} дн.!)**"
            elif days_left == 0:
                status = f"🚨 **ЗАКІНЧУЄТЬСЯ СЬОГОДНІ ({formatted_date})!**"
            else:
                status = f"❌ **ТЕРМІН ЗАКІНЧИВСЯ ({formatted_date})!**"
            
            player_info = (
                f"👤 **Нік:** {user['nickname']}\n"
                f"🆔 **Steam:** `{user['steam_id']}`\n"
                f"👑 **Привілея:** {user['privilege']}\n"
                f"{status}\n"
                f"────────────────"
            )
            lines.append(player_info)
        
        if lines:
            response = "📊 **ПОВНИЙ СПИСОК ПРИВІЛЕЙ НА СЕРВЕРІ:**\n\n" + "\n".join(lines) + "\n\n👉 *Для купівлі або продовження привілей зв'яжіться з адміністрацією.*"
        else:
            response = "Список привілей порожній."
            
        bot.reply_to(message, response, parse_mode="Markdown")
        
    except json.JSONDecodeError:
        bot.reply_to(message, "❌ Ошибка: Неправильный формат текста в файле `vip_users.json`!")
    except Exception as e:
        bot.reply_to(message, f"❌ Системная ошибка: {str(e)}")

if __name__ == "__main__":
    print("Запуск веб-сервера для Render...")
    # Запускаем веб-сервер в отдельном потоке, чтобы он не мешал боту
    Thread(target=run_web_server).start()
    
    print("Бот контроля VIP запущен...")
    bot.infinity_polling()
    
