import os
import time
import random
import requests
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler

# Load environment variables
load_dotenv()

# Configuration
TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
# Initial admins from env, can be expanded at runtime
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

def generate_prediction(last_results):
    if not last_results:
        return "BIG", random.randint(5, 9)
    
    # Logic based on history
    big_count = sum(1 for r in last_results[:5] if int(r['number']) >= 5)
    small_count = 5 - big_count
    
    # Simple trend following/reversal logic
    prediction = "SMALL" if big_count > small_count else "BIG"
    
    if prediction == "BIG":
        predicted_number = random.choice([5, 6, 7, 8, 9])
    else:
        predicted_number = random.choice([0, 1, 2, 3, 4])
        
    return prediction, predicted_number

def format_prediction_message(period, prediction, number):
    # Advanced styling for the message as requested
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
        f"║  ▸ LOGIC TYPE    : ADVANCED SCRIPT   ║\n"
        f"║  ▸ RISK FILTER   : ENABLED           ║\n"
        f"║  ▸ ACCURACY RATE : 100%              ║\n"
        f"║                                      ║\n"
        f"╠══════════════════════════════════════╣\n"
        f"║  👨‍💻 SCRIPT DEVELOPER : @kal_mods     ║\n"
        f"║  ⚡ MANAGER ID : @KALMODS_MANAGER     ║\n"
        f"╚══════════════════════════════════════╝"
    )
    return msg

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
            
            # Check if it's a new period
            if current_period != last_period:
                last_period = current_period
                
                # Next period prediction
                next_period = str(int(current_period) + 1)
                prediction, number = generate_prediction(data)
                
                message = format_prediction_message(next_period, prediction, number)
                
                # Send to channel with image
                try:
                    await context.bot.send_photo(
                        chat_id=CHANNEL_ID,
                        photo=IMAGE_URL,
                        caption=message
                    )
                    logging.info(f"Sent prediction for period {next_period}")
                except Exception as e:
                    logging.error(f"Failed to send message to channel: {e}")
                
            await asyncio.sleep(15) # Check every 15 seconds for faster response
        except Exception as e:
            logging.error(f"Error in prediction loop: {e}")
            await asyncio.sleep(10)

# Commands
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized to use this bot.")
        return
        
    keyboard = [
        [InlineKeyboardButton("🚀 Start Prediction", callback_data='start_bot')],
        [InlineKeyboardButton("🛑 Stop Prediction", callback_data='stop_bot')],
        [InlineKeyboardButton("📊 Bot Status", callback_data='status_bot')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "🔥 *Advanced Prediction Bot Control Panel*\n\n"
        "Welcome Admin! Use the buttons below to control the automated prediction engine.",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global is_running
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id not in ADMIN_IDS:
        await query.answer("Unauthorized!", show_alert=True)
        return
        
    await query.answer()
    
    if query.data == 'start_bot':
        if not is_running:
            is_running = True
            asyncio.create_task(prediction_loop(context))
            await query.edit_message_text("✅ *Prediction engine STARTED*\n\nBot is now monitoring the API and posting predictions to the channel.", parse_mode='Markdown')
        else:
            await query.edit_message_text("ℹ️ *Engine is already running.*", parse_mode='Markdown')
            
    elif query.data == 'stop_bot':
        is_running = False
        await query.edit_message_text("🛑 *Prediction engine STOPPED*\n\nNo more predictions will be sent until restarted.", parse_mode='Markdown')
        
    elif query.data == 'status_bot':
        status = "RUNNING 🟢" if is_running else "STOPPED 🔴"
        await query.edit_message_text(
            f"📊 *Bot Status Report*\n\n"
            f"• Engine: `{status}`\n"
            f"• Active Admins: `{len(ADMIN_IDS)}`\n"
            f"• Target Channel: `{CHANNEL_ID}`\n"
            f"• Image URL: [View Banner]({IMAGE_URL})",
            parse_mode='Markdown'
        )

async def add_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        return
        
    if not context.args:
        await update.message.reply_text("Usage: `/addadmin <user_id>`", parse_mode='Markdown')
        return
        
    try:
        new_admin = int(context.args[0])
        if new_admin not in ADMIN_IDS:
            ADMIN_IDS.append(new_admin)
            await update.message.reply_text(f"✅ User `{new_admin}` added as admin.", parse_mode='Markdown')
        else:
            await update.message.reply_text("User is already an admin.")
    except ValueError:
        await update.message.reply_text("Invalid User ID. Please provide a numeric ID.")

if __name__ == '__main__':
    if not TOKEN:
        print("Error: BOT_TOKEN not found in environment variables.")
        exit(1)
        
    app = ApplicationBuilder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("addadmin", add_admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    print("Bot is starting...")
    app.run_polling()
