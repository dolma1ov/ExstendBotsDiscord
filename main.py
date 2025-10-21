import os
import threading
import asyncio
from dotenv import load_dotenv

import discord
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram import Update

# Загрузка переменных окружения
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))
HEADER_TO_REMOVE = os.getenv("HEADER_TO_REMOVE")
RP_BOT_ID = int(os.getenv("RP_BOT_ID"))

# Настройка Telegram-приложения
telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or message.from_user.id != RP_BOT_ID or not message.text:
        return
    content = message.text.strip()
    if content.startswith(HEADER_TO_REMOVE):
        body = content[len(HEADER_TO_REMOVE):].lstrip("\n").strip()
    else:
        body = content
    if body:
        channel = discord_client.get_channel(TARGET_CHANNEL_ID)
        if channel:
            await channel.send(f"@everyone\n{body}")

telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message)
)

# Запуск Telegram-покупщика в главном потоке
def run_telegram():
    telegram_app.run_polling()

# Настройка Discord-клиента
intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    print(f"✅ Discord-бот {discord_client.user} готов!")

@discord_client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.content.startswith('!ping'):
        await message.channel.send('Pong! Это работает!')

# Основная асинхронная функция запуска Discord
async def run_discord():
    await discord_client.start(DISCORD_BOT_TOKEN)

if __name__ == '__main__':
    # 1. Стартуем Telegram-пуллинг в отдельном потоке
    threading.Thread(target=run_telegram, daemon=True).start()
    asyncio.run(run_discord())