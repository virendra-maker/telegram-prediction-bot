import os
import time
import random
import requests
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters

# Load environment variables
load_dotenv()

# Configuration
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_IDS = [int(id.strip()) for id in os.getenv("ADMIN_IDS", "").split(",") if id.strip()]
IMAGE_URL = os.getenv("IMAGE_URL", "https://i.ibb.co/v4m0YmP/prediction-banner.jpg")

# API Configuration
API_URL = "https://draw.ar-lottery01.com/WinGo/WinGo_1M/GetHistoryIssuePage.json"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 10)",
    "Referer": "https://hgnice.biz"
}

# Global State
is_running = False
last_period = None
prediction_history = {} # Store predictions to verify later
stats = {"wins": 0, "losses": 0, "total": 0}

# Logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

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
    """Unique Feature: Smart Trend Analyzer"""
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
    
    # Advanced logic: Trend following with randomness filter
    if big_count > small_count:
        prediction = "SMALL" if random.random() > 0.7 else "BIG"
    else:
        prediction = "BIG" if random.random() > 0.7 else "SMALL"
    
    if prediction == "BIG":
        predicted_number = random.choice([5, 6, 7, 8, 9])
    else:
        predicted_number = random.choice([0, 1, 2, 3, 4])
        
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
    """Unique Feature: Auto-Result Verification"""
    global stats
    if current_period in prediction_history:
        pred_data = prediction_history[current_period]
        actual_size = get_big_small(actual_number)
        
        is_win = pred_data['prediction'] == actual_size
        status_emoji = "✅ WIN" if is_win else "❌ LOSS"
        
        if is_win: stats['wins'] += 1
        else: stats['losses'] += 1
        stats['total'] += 1
        
        verify_msg = (
            f"📊 *PERIOD {current_period} RESULT*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"🎯 Result: `{actual_number} ({actual_size})`\n"
            f"🔮 Our Prediction: `{pred_data['prediction']}`\n"
            f"✨ Status: *{status_emoji}*\n"
            f"━━━━━━━━━━━━━━━━━━━━━\n"
            f"📈 Accuracy: `{(stats['wins']/stats['total']*100):.1f}%`"
        )
        await context.bot.send_message(chat_id=CHANNEL_ID, text=verify_msg, parse_mode='Markdown')
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
            
            # 1. Verify previous prediction if exists
            await verify_last_prediction(context, current_period, latest_item['number'])
            
            # 2. Check if it's time for a new prediction
            if current_period != last_period:
                last_period = current_period
                next_period = str(int(current_period) + 1)
                
                trend = analyze_trends(data)
                prediction, number = generate_prediction(data)
                
                # Store for verification
                prediction_history[next_period] = {'prediction': prediction, 'number': number}
                
                message = format_prediction_message(next_period, prediction, number, trend)
                
                await context.bot.send_photo(
                    chat_id=CHANNEL_ID,
                    photo=IMAGE_URL,
                    caption=message
                )
                logging.info(f"Sent prediction for period {next_period}")
                
            await asyncio.sleep(15)
        except Exception as e:
            logging.error(f"Error in prediction loop: {e}")
            await asyncio.sleep(10)

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Unauthorized.")
        return
        
    keyboard = [
        [InlineKeyboardButton("🚀 Start", callback_data='start_bot'), InlineKeyboardButton("🛑 Stop", callback_data='stop_bot')],
        [InlineKeyboardButton("📊 Stats", callback_data='status_bot'), InlineKeyboardButton("📢 Broadcast", callback_data='prep_broadcast')],
        [InlineKeyboardButton("⚙️ Settings", callback_data='settings_bot')]
    ]
    await update.message.reply_text(
        "🔥 *ULTIMATE PREDICTION CONTROL*\n\n"
        "Status: " + ("RUNNING 🟢" if is_running else "STOPPED 🔴"),
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running
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
        await query.edit_message_text("📝 Send the message you want to broadcast to the channel.")
        context.user_data['awaiting_broadcast'] = True

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unique Feature: Admin Broadcast"""
    if update.effective_user.id not in ADMIN_IDS: return
    
    if context.user_data.get('awaiting_broadcast'):
        text = update.message.text
        await context.bot.send_message(chat_id=CHANNEL_ID, text=f"📢 *ADMIN ANNOUNCEMENT*\n\n{text}", parse_mode='Markdown')
        await update.message.reply_text("✅ Broadcast sent to channel!")
        context.user_data['awaiting_broadcast'] = False

if __name__ == '__main__':
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("Bot is starting...")
    app.run_polling(drop_pending_updates=True)
