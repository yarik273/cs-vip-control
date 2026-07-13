import os
import json
from datetime import datetime
import telebot

BOT_TOKEN = os.environ.get('BOT_TOKEN')
bot = telebot.TeleBot(BOT_TOKEN)

@bot.message_handler(commands=['vip', 'vip_status'])
def send_vip_status(message):
    try:
        if not os.path.exists('vip_users.json'):
            bot.reply_to(message, "❌ Помилка: Файл `vip_users.json` не знайдено!")
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
                status = f"⚠️ Дійсна до: {formatted_date} (залишилось всього {days_left} дн.!)"
            elif days_left == 0:
                status = f"🚨 ЗАКІНЧУЄТЬСЯ СЬОГОДНІ ({formatted_date})!"
            else:
                status = f"❌ ТЕРМІН ЗАКІНЧИВСЯ ({formatted_date})!"
            
            player_info = (
                f"👤 Нік: {user['nickname']}\n"
                f"🆔 Steam: {user['steam_id']}\n"
                f"👑 Привілея: {user['privilege']}\n"
                f"{status}\n"
                f"────────────────"
            )
            lines.append(player_info)
        
        if lines:
            response = (
                "📊 **СПИСОК ПРИВІЛЕЙ, ЯКІ ЗАКІНЧУЮТЬСЯ:**\n\n" + 
                "\n".join(lines) + 
                "\n\n👉 Для купівлі або продовження привілей зв'яжіться з адміністрацією."
            )
        else:
            response = "Список привілей порожній."
            
        bot.reply_to(message, response)
        
    except json.JSONDecodeError:
        bot.reply_to(message, "❌ Помилка: Неправильний формат тексту у файлі `vip_users.json`!")
    except Exception as e:
        bot.reply_to(message, f"❌ Системна помилка: {str(e)}")

if __name__ == "__main__":
    print("Бот контролю VIP запущений...")
    bot.infinity_polling()
    
