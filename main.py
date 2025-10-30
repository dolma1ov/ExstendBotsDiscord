import os
import asyncio
import requests
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
WAR_STATS_CHANNEL_ID = 1274645422542950411
ALLOWED_SENDER_IDS = [
    int(x.strip()) for x in os.getenv("ALLOWED_SENDER_IDS", "").split(",") if x.strip().isdigit()
]
BLACKLIST_CHAT_IDS = set()

TWITCH_CLIENT_ID = os.getenv("TWITCH_CLIENT_ID")
TWITCH_CLIENT_SECRET = os.getenv("TWITCH_CLIENT_SECRET")
TWITCH_USERNAME = os.getenv("TWITCH_USERNAME")
TWITCH_NOTIFY_CHANNEL_ID = int(os.getenv("TWITCH_NOTIFY_CHANNEL_ID", TARGET_CHANNEL_ID))

stats = {
    "total": 0,
    "allowed": 0
}

war_stats = {
    "win_attack": 0,
    "lose_attack": 0,
    "win_def": 0,
    "lose_def": 0
}
stats_message_id = None

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

async def send_or_update_stats_message(channel, text):
    global stats_message_id
    if stats_message_id is None:
        msg = await channel.send(text)
        stats_message_id = msg.id
    else:
        try:
            msg = await channel.fetch_message(stats_message_id)
            await msg.edit(content=text)
        except Exception as e:
            print(f"[ERROR] Edit stats msg: {e}")
            msg = await channel.send(text)
            stats_message_id = msg.id

tg_client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

@tg_client.on(events.NewMessage(incoming=True))
async def tg_handler(event):
    try:
        chat_id = event.chat_id
        if chat_id in BLACKLIST_CHAT_IDS:
            print(f"[SKIP] Blacklisted chat_id: {chat_id}")
            return
        try:
            sender = await event.get_sender()
            sender_id = sender.id if sender else None
        except Exception as e:
            print(f"[ERROR] get_sender failed: {e}")
            sender_id = None
        msg_text = getattr(event.message, "message", "")
        msg_text = msg_text.replace(
            "📋 Организация: события | Huxley_Exstendyan, сервер Burton", ""
        ).strip()
        stats["total"] += 1
        print(f"[LOG] TG: from id={sender_id} chat={chat_id} text={msg_text!r}", flush=True)
        if sender_id is None:
            return

        # Счётчик войн
        updated = False
        if "захватывает" in msg_text:
            war_stats["win_attack"] += 1
            updated = True
        elif "проигрывает в бою" in msg_text and "забила" not in msg_text:
            war_stats["lose_attack"] += 1
            updated = True
        elif "удерживает" in msg_text:
            war_stats["win_def"] += 1
            updated = True
        elif "проигрывает в бою" in msg_text and "забили Вашей организации войну за" in msg_text:
            war_stats["lose_def"] += 1
            updated = True

        if updated:
            stat_msg = (
                f"Выигранных атак - {war_stats['win_attack']}\n"
                f"Проигранных атак - {war_stats['lose_attack']}\n"
                f"Выигранных защит - {war_stats['win_def']}\n"
                f"Проигранных защит - {war_stats['lose_def']}"
            )
            stats_channel = discord_client.get_channel(WAR_STATS_CHANNEL_ID)
            if stats_channel:
                await send_or_update_stats_message(stats_channel, stat_msg)
        
        if "забили Вашей организации войну за" not in msg_text:
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
    except Exception as global_e:
        print(f"[CRITICAL ERROR] event handler exception: {global_e}")

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

def get_twitch_token():
    url = 'https://id.twitch.tv/oauth2/token'
    params = {
        'client_id': TWITCH_CLIENT_ID,
        'client_secret': TWITCH_CLIENT_SECRET,
        'grant_type': 'client_credentials'
    }
    r = requests.post(url, params)
    return r.json().get('access_token')

async def check_twitch_live(discord_client, sent_last=[]):
    if not TWITCH_CLIENT_ID or not TWITCH_CLIENT_SECRET or not TWITCH_USERNAME:
        return
    token = get_twitch_token()
    headers = {
        'Client-ID': TWITCH_CLIENT_ID,
        'Authorization': f'Bearer {token}'
    }
    url = f'https://api.twitch.tv/helix/streams?user_login={TWITCH_USERNAME}'
    r = requests.get(url, headers=headers)
    data = r.json().get('data', [])
    channel = discord_client.get_channel(TWITCH_NOTIFY_CHANNEL_ID)
    live_now = len(data) > 0
    if live_now and not sent_last:
        stream_title = data[0].get('title', 'Стрим Twitch')
        twitch_url = f"https://twitch.tv/{TWITCH_USERNAME}"
        msg = (
            "@everyone\n"
            f"{stream_title}\n"
            f"{twitch_url}\n"
        )   
        if channel:
            await channel.send(msg)
        sent_last.append('sent')
    elif not live_now and sent_last:
        sent_last.clear()

async def twitch_loop():
    sent_last = []
    while True:
        await check_twitch_live(discord_client, sent_last)
        await asyncio.sleep(120)

async def main():
    tg_task = asyncio.create_task(tg_client.start())
    ds_task = asyncio.create_task(discord_client.start(DISCORD_BOT_TOKEN))
    twitch_task = asyncio.create_task(twitch_loop())
    await asyncio.gather(tg_task, ds_task, twitch_task)

if __name__ == '__main__':
    asyncio.run(main())