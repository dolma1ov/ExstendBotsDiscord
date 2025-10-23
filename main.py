import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
import discord
from discord import app_commands
from datetime import datetime, UTC

load_dotenv()
API_ID = int(os.getenv('TG_API_ID'))
API_HASH = os.getenv('TG_API_HASH')
SESSION_FILE = os.getenv('TG_SESSION', 'session')
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))
ALLOWED_SENDER_IDS = [
    int(x.strip()) for x in os.getenv("ALLOWED_SENDER_IDS", "").split(",") if x.strip().isdigit()
]

stats = {
    "total": 0,
    "allowed": 0
}

intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)
tree = app_commands.CommandTree(discord_client)

@discord_client.event
async def on_ready():
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="📺🟣 Twitch: ilven69 👾",
        start=datetime.now(UTC)
    )
    await discord_client.change_presence(activity=activity, status=discord.Status.online)
    await tree.sync()
    print(f"[INFO] Discord-бот {discord_client.user} готов!", flush=True)

tg_client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

@tg_client.on(events.NewMessage(incoming=True))
async def tg_handler(event):
    try:
        sender = await event.get_sender()
        sender_id = sender.id if sender else None
    except Exception as e:
        print(f"[ERROR] get_sender failed: {e}")
        sender_id = None

    msg_text = event.message.message
    chat_id = event.chat_id
    stats["total"] += 1

    print(f"[LOG] TG: from id={sender_id} chat={chat_id} text={msg_text!r}", flush=True)

    if sender_id is None:
        return

    if ALLOWED_SENDER_IDS and sender_id in ALLOWED_SENDER_IDS:
        stats["allowed"] += 1
        if msg_text:
            channel = discord_client.get_channel(TARGET_CHANNEL_ID)
            if channel:
                await channel.send(f"@everyone\n{msg_text}")
                print(f"[DS_LOG] Переслано из TG в Discord: {msg_text!r}", flush=True)
            else:
                print("[ERR] Канал Discord не найден!", flush=True)

@tree.command(name="ping", description="Проверка работы бота")
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message("понг блять, он работает не еби его", ephemeral=False)

@tree.command(name="stats", description="Статистика полученных сообщений")
async def stats_command(interaction: discord.Interaction):
    msg = (
        f"Всего сообщений обработано: {stats['total']}\n"
        f"Сообщений от нужного бота: {stats['allowed']}"
    )
    await interaction.response.send_message(msg, ephemeral=False)

async def main():
    tg_task = asyncio.create_task(tg_client.start())
    ds_task = asyncio.create_task(discord_client.start(DISCORD_BOT_TOKEN))
    await asyncio.gather(tg_task, ds_task)

if __name__ == '__main__':
    asyncio.run(main())