import os
import asyncio
from dotenv import load_dotenv
from telethon import TelegramClient, events
import discord

load_dotenv()
API_ID = int(os.getenv('TG_API_ID'))
API_HASH = os.getenv('TG_API_HASH')
SESSION_FILE = os.getenv('TG_SESSION', 'session')
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))
ALLOWED_SENDER_IDS = [
    int(x.strip()) for x in os.getenv("ALLOWED_SENDER_IDS", "").split(",") if x.strip().isdigit()
]

intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)

@discord_client.event
async def on_ready():
    print(f"[INFO] Discord-бот {discord_client.user} готов!", flush=True)

tg_client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

@tg_client.on(events.NewMessage(incoming=True))
async def tg_handler(event):
    sender = await event.get_sender()
    sender_id = sender.id if sender else None
    msg_text = event.message.message
    chat_id = event.chat_id
    print(f"[LOG] TG: from id={sender_id} chat={chat_id} text={msg_text!r}", flush=True)

    # Если ALLOWED_SENDER_IDS задан — фильтруем по нему
    if ALLOWED_SENDER_IDS and sender_id not in ALLOWED_SENDER_IDS:
        print(f"[SKIP] Отправитель {sender_id} не разрешён!", flush=True)
        return

    if msg_text:
        channel = discord_client.get_channel(TARGET_CHANNEL_ID)
        if channel:
            await channel.send(f"@everyone\n{msg_text}")
            print(f"[DS_LOG] Переслано из TG в Discord: {msg_text!r}", flush=True)
        else:
            print("[ERR] Канал Discord не найден!", flush=True)

async def main():
    tg_task = asyncio.create_task(tg_client.start())
    ds_task = asyncio.create_task(discord_client.start(DISCORD_BOT_TOKEN))
    await asyncio.gather(tg_task, ds_task)

if __name__ == '__main__':
    asyncio.run(main())
