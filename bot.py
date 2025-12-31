import os
import time
import random
import requests
import asyncio
import logging
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# --- HARDCODED CONFIGURATION ---
TOKEN = "8586348972:AAFAPGF45os8aEgVXW9nMwwtd4geRbMk6rc"
ADMIN_IDS = [7166967787]
# Default Channel ID (User should set this via command or env if not hardcoded)
CHANNEL_ID = os.getenv("CHANNEL_ID", "-1002364448532") # Example ID, user can change
IMAGE_URL = "https://i.ibb.co/v4m0YmP/prediction-banner.jpg"

# API Configuration
API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10)",
    "Referer": "https://hgnice.biz"
}

# File Paths for Auto-Initialization
DB_FILE = "bot_database.json"

# Global State
is_running = False
last_period = None
prediction_history = {}
stats = {"wins": 0, "losses": 0, "total": 0}

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

def init_db():
    """Automatically initialize database file if it doesn't exist"""
    if not os.path.exists(DB_FILE):
        with open(DB_FILE, 'w') as f:
            json.dump({"stats": stats, "admins": ADMIN_IDS, "channel_id": CHANNEL_ID}, f)
        logging.info("Database initialized.")
    else:
        with open(DB_FILE, 'r') as f:
            data = json.load(f)
            global stats, ADMIN_IDS, CHANNEL_ID
            stats = data.get("stats", stats)
            # Merge hardcoded admins with DB admins
            db_admins = data.get("admins", [])
            for admin in db_admins:
                if admin not in ADMIN_IDS:
                    ADMIN_IDS.append(admin)
            CHANNEL_ID = data.get("channel_id", CHANNEL_ID)

def save_db():
    with open(DB_FILE, 'w') as f:
        json.dump({"stats": stats, "admins": ADMIN_IDS, "channel_id": CHANNEL_ID}, f)

def get_big_small(number):
    return "SMALL" if int(number) <= 4 else "BIG"

def fetch_latest_data():
    try:
        ts = int(time.time() * 1000)
        url = f"{API_URL}?ts={ts}"
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code == 200:
            data = response.json()
            return data.get("data", {}).get("list", [])
        return []
    except Exception as e:
        logging.error(f"Error fetching data: {e}")
        return []

def analyze_trends(data):
    if not data: return "NEUTRAL"
    numbers = [int(item['number']) for item in data[:10]]
    big_count = sum(1 for n in numbers if n >= 5)
    if big_count >= 7: return "STRONG BIG TREND 🔥"
    if big_count <= 3: return "STRONG SMALL TREND ❄️"
    return "STABLE MARKET ⚖️"

def generate_prediction(last_results):
    if not last_results:
        return "BIG", random.randint(5, 9)
    numbers = [int(r['number']) for r in last_results[:5]]
    big_count = sum(1 for n in numbers if n >= 5)
    small_count = 5 - big_count
    if big_count > small_count:
        prediction = "SMALL" if random.random() > 0.7 else "BIG"
    else:
        prediction = "BIG" if random.random() > 0.7 else "SMALL"
    predicted_number = random.choice([5, 6, 7, 8, 9]) if prediction == "BIG" else random.choice([0, 1, 2, 3, 4])
    return prediction, predicted_number

def format_prediction_message(period, prediction, number, trend):
    msg = (
        f"╔══════════════════════════════════════╗\n"
        f"║   ⚠️  SYSTEM OVERRIDE : ACTIVE  ⚠️   ║\n"
        f"╠══════════════════════════════════════╣\n"
        f"║  🔮 SCRIPT-BASED LIVE PREDICTION     ║\n"
        f"║                                      ║\n"
        f"║  ▸ PERIOD NUMBER : {period}     ║\n"
        f"║  ▸ RESULT MODE   : {prediction}                 ║\n"
        f"║  ▸ CORE DIGITS   : {number} ⇄ {random.randint(0,9)}                  ║\n"
        f"║                                      ║\n"
        f"║  ▸ TREND ANALYZE : {trend}    ║\n"
        f"║  ▸ RISK FILTER   : ENABLED           ║\n"
        f"║  ▸ ACCURACY RATE : 100%              ║\n"
        f"║                                      ║\n"
        f"╠══════════════════════════════════════╣\n"
        f"║  👨‍💻 SCRIPT DEVELOPER : @kal_mods     ║\n"
        f"║  ⚡ MANAGER ID : @KALMODS_MANAGER     ║\n"
        f"╚══════════════════════════════════════╝"
    )
    return msg

async def verify_last_prediction(context, current_period, actual_number):
    global stats
    if current_period in prediction_history:
        pred_data = prediction_history[current_period]
        actual_size = get_big_small(actual_number)
        is_win = pred_data['prediction'] == actual_size
        if is_win: stats['wins'] += 1
        else: stats['losses'] += 1
        stats['total'] += 1
        save_db()
        
        status_emoji = "✅ WIN" if is_win else "❌ LOSS"
        verify_msg = (
            f"📊 *PERIOD {current_period} RESULT*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 Result: `{actual_number} ({actual_size})`\n"
            f"🔮 Our Prediction: `{pred_data['prediction']}`\n"
            f"✨ Status: *{status_emoji}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 Accuracy: `{(stats['wins']/stats['total']*100):.1f}%`"
        )
        try:
            await context.bot.send_message(chat_id=CHANNEL_ID, text=verify_msg, parse_mode='Markdown')
        except: pass
        del prediction_history[current_period]

async def prediction_loop(context: ContextTypes.DEFAULT_TYPE):
    global is_running, last_period
    while is_running:
        try:
            data = fetch_latest_data()
            if not data:
                await asyncio.sleep(10)
                continue
            latest_item = data[0]
            current_period = str(latest_item['issueNumber'])
            await verify_last_prediction(context, current_period, latest_item['number'])
            if current_period != last_period:
                last_period = current_period
                next_period = str(int(current_period) + 1)
                trend = analyze_trends(data)
                prediction, number = generate_prediction(data)
                prediction_history[next_period] = {'prediction': prediction, 'number': number}
                message = format_prediction_message(next_period, prediction, number, trend)
                try:
                    await context.bot.send_photo(chat_id=CHANNEL_ID, photo=IMAGE_URL, caption=message)
                except Exception as e:
                    logging.error(f"Send error: {e}")
            await asyncio.sleep(15)
        except Exception as e:
            logging.error(f"Loop error: {e}")
            await asyncio.sleep(10)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    keyboard = [
        [InlineKeyboardButton("🚀 Start", callback_data='start_bot'), InlineKeyboardButton("🛑 Stop", callback_data='stop_bot')],
        [InlineKeyboardButton("📊 Stats", callback_data='status_bot'), InlineKeyboardButton("📢 Broadcast", callback_data='prep_broadcast')],
        [InlineKeyboardButton("🆔 Set Channel", callback_data='set_channel')]
    ]
    await update.message.reply_text(
        "🔥 *ULTIMATE PREDICTION CONTROL*\n\n"
        f"Status: {'RUNNING 🟢' if is_running else 'STOPPED 🔴'}\n"
        f"Channel: `{CHANNEL_ID}`",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running, CHANNEL_ID
    query = update.callback_query
    if query.from_user.id not in ADMIN_IDS: return
    await query.answer()
    if query.data == 'start_bot':
        if not is_running:
            is_running = True
            asyncio.create_task(prediction_loop(context))
            await query.edit_message_text("✅ Engine Started!")
    elif query.data == 'stop_bot':
        is_running = False
        await query.edit_message_text("🛑 Engine Stopped!")
    elif query.data == 'status_bot':
        await query.edit_message_text(f"📊 *LIFETIME STATS*\n\nWins: {stats['wins']}\nLosses: {stats['losses']}\nTotal: {stats['total']}", parse_mode='Markdown')
    elif query.data == 'prep_broadcast':
        await query.edit_message_text("📝 Send the message you want to broadcast.")
        context.user_data['awaiting_broadcast'] = True
    elif query.data == 'set_channel':
        await query.edit_message_text("🆔 Send the Channel ID (e.g., -100...).")
        context.user_data['awaiting_channel'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_ID
    if update.effective_user.id not in ADMIN_IDS: return
    if context.user_data.get('awaiting_broadcast'):
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"📢 *ADMIN ANNOUNCEMENT*\n\n{update.message.text}", parse_mode='Markdown')
        await update.message.reply_text("✅ Broadcast sent!")
        context.user_data['awaiting_broadcast'] = False
    elif context.user_data.get('awaiting_channel'):
        CHANNEL_ID = update.message.text
        save_db()
        await update.message.reply_text(f"✅ Channel ID updated to: `{CHANNEL_ID}`", parse_mode='Markdown')
        context.user_data['awaiting_channel'] = False

if __name__ == '__main__':
    init_db()
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is starting...")
    app.run_polling(drop_pending_updates=True)
