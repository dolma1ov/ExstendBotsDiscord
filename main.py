import os
import asyncio
import logging
from dotenv import load_dotenv
import discord
from discord import app_commands
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram import Update
from datetime import datetime, UTC

def log_action(message):
    print(f"[LOG] {message}", flush=True)
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

telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("[DEBUG] Получено сообщение от Telegram!")
    message = update.message
    if not message:
        print("[DEBUG] Нет объекта message — не обрабатываем.")
        return
    print(f"[DEBUG] message.from_user.id = {getattr(message.from_user, 'id', None)} RP_BOT_ID = {RP_BOT_ID}")
    if message.from_user.id != RP_BOT_ID:
        print("[DEBUG] Не тот отправитель — игнорируем.")
        return
    if not message.text:
        print("[DEBUG] Сообщение не содержит текст — игнорируем.")
        return

    content = message.text.strip()
    print(f"[DEBUG] Исходный контент: {content!r}")
    if content.startswith(HEADER_TO_REMOVE):
        body = content[len(HEADER_TO_REMOVE):].lstrip("\n").strip()
        print("[DEBUG] HEADER_TO_REMOVE найден — тело:", body)
    else:
        body = content
        print("[DEBUG] HEADER_TO_REMOVE — нет, тело:", body)

    if body:
        print("[DEBUG] Пробуем получить канал Discord:", TARGET_CHANNEL_ID)
        channel = discord_client.get_channel(TARGET_CHANNEL_ID)
        if channel:
            print(f"[DEBUG] Канал Discord найден: {channel}. Пытаемся отправить сообщение…")
            await channel.send(f"@everyone\n{body}")
            log_action(f"Сообщение переслано из Telegram: {body}")
        else:
            print("[ERR] Канал Discord не найден!", flush=True)

telegram_app.add_handler(
    MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message)
)

intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)
tree = app_commands.CommandTree(discord_client)

@discord_client.event
async def on_ready():
    start_time = datetime.now(UTC)
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="📺🟣 Twitch: ilven69 👾",
        start=start_time
    )
    await discord_client.change_presence(activity=activity, status=discord.Status.online)
    await tree.sync()
    print(f"[INFO] Discord-бот {discord_client.user} готов!", flush=True)
    print(f"[INFO] Slash-команды синхронизированы!", flush=True)
    log_action("Discord-бот запущен и готов к работе!")

@tree.command(name="ping", description="Проверка работы бота")
async def ping(interaction: discord.Interaction):
    print(f"[LOG] ping от {interaction.user.id}", flush=True)
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
    print(f"[LOG] stats вызвал: {interaction.user.id}", flush=True)
    log_action(f"/stats запрошена: от {interaction.user} (id: {interaction.user.id})")
    await interaction.response.send_message(msg)

async def main():
    print('[LOG] Telegram initializing...', flush=True)
    await telegram_app.initialize()
    tg_task = asyncio.create_task(telegram_app.start())
    print('[LOG] Telegram запущен!', flush=True)
    await discord_client.start(DISCORD_BOT_TOKEN)
    print('[LOG] Discord запущен!', flush=True)
    await tg_task

if __name__ == '__main__':
    asyncio.run(main())
