# Advanced Telegram Prediction Bot

An advanced Telegram bot designed for automated predictions with multi-admin support and channel integration.

## Features
- **Automated Predictions**: Real-time fetching and posting of predictions to a Telegram channel.
- **Multi-Admin Control**: Multiple admins can start/stop the bot and manage settings.
- **Advanced UI**: High-end visual style with boxes and emojis.
- **Railway Ready**: Pre-configured for easy deployment on Railway.app.

## Deployment on Railway

1. Fork or clone this repository to your GitHub.
2. Create a new project on [Railway.app](https://railway.app/).
3. Connect your GitHub repository.
4. Add the following Environment Variables:
   - `BOT_TOKEN`: Your Telegram Bot Token from @BotFather.
   - `CHANNEL_ID`: The ID of the Telegram channel where predictions will be posted (e.g., -100...).
   - `ADMIN_IDS`: Comma-separated list of Telegram User IDs who can control the bot.
   - `IMAGE_URL`: URL of the image to be sent with predictions.
5. Railway will automatically detect the `Procfile` and start the bot.

## Commands
- `/start`: Open the admin control panel.
- `/addadmin <user_id>`: Add a new admin (Admin only).

## Developer
Developed by Manus AI.
Original Script Logic: @kal_mods
