import os
import asyncio
import logging
from dotenv import load_dotenv
import discord
from discord import app_commands
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram import Update
from datetime import datetime

logging.basicConfig(
    filename='bot.log',
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    encoding='utf-8'
)

def log_action(message):
    logging.info(message)

stats = {
    'ping_count': 0,
    'users': set()
}

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))
HEADER_TO_REMOVE = os.getenv("HEADER_TO_REMOVE")
RP_BOT_ID = int(os.getenv("RP_BOT_ID"))

# Создаем Telegram приложение
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
            log_action(f"Сообщение переслано из Telegram: {body}")

telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message)
)

intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)
tree = app_commands.CommandTree(discord_client)

@discord_client.event
async def on_ready():
    start_time = datetime.utcnow()
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="📺🟣 Twitch: ilven69 👾",
        start=start_time
    )
    await discord_client.change_presence(activity=activity, status=discord.Status.online)
    await tree.sync()
    print(f"Discord-бот {discord_client.user} готов!")
    print(f"Slash-команды синхронизированы!")
    log_action("Discord-бот запущен и готов к работе!")

@tree.command(name="ping", description="Проверка работы бота")
async def ping(interaction: discord.Interaction):
    if interaction.channel_id != TARGET_CHANNEL_ID:
        log_action(f"Попытка /ping не в том канале: от {interaction.user} (id: {interaction.user.id})")
        await interaction.response.send_message(
            "слышь иди нахуй", ephemeral=True
        )
        return
    stats['ping_count'] += 1
    stats['users'].add(interaction.user.id)
    log_action(f"/ping исполнена: от {interaction.user} (id: {interaction.user.id})")
    await interaction.response.send_message("понг блять, он работает не еби его")

@tree.command(name="stats", description="Статистика использования бота")
async def stats_command(interaction: discord.Interaction):
    msg = (
        f"Статистика использования:\n"
        f"- /ping вызван: {stats['ping_count']} раз\n"
        f"- Уникальных пользователей: {len(stats['users'])}\n"
    )
    log_action(f"/stats запрошена: от {interaction.user} (id: {interaction.user.id})")
    await interaction.response.send_message(msg)

async def main():
    # Запуск Telegram бота в отдельной задаче
    telegram_task = asyncio.create_task(telegram_app.run_polling())
    # Запуск Discord бота
    await discord_client.start(DISCORD_BOT_TOKEN)
    await telegram_task

if __name__ == '__main__':
    asyncio.run(main())