import os
import asyncio
import requests
import re
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
TWITCH_USERNAMES = ["ilven69", "devv_o", "xanameee", "mihynchik_"]
TWITCH_NOTIFY_CHANNEL_ID = int(os.getenv("TWITCH_NOTIFY_CHANNEL_ID", TARGET_CHANNEL_ID))

stats = {
    "total": 0,
    "allowed": 0
}

war_stats = {
    "win_attack": 13,
    "lose_attack": 11,
    "win_def": 9,
    "lose_def": 14
}
stats_message_id = None

# Контекст для последнего боя
last_attack_type = None  # "atk" или "def"
last_battle_object = None  # Название склада/локации

intents = discord.Intents.default()
intents.message_content = True
discord_client = discord.Client(intents=intents)
tree = app_commands.CommandTree(discord_client)

# ----------------- EMBED HELPERS -----------------

def make_war_stats_embed():
    embed = discord.Embed(
        title="Статистика боёв",
        color=0x9146FF  # Twitch-фиолетовый для WAR_STATS_CHANNEL_ID
    )
    embed.add_field(name="Выигранных атак", value=war_stats['win_attack'], inline=True)
    embed.add_field(name="Проигранных атак", value=war_stats['lose_attack'], inline=True)
    embed.add_field(name="Выигранных защит", value=war_stats['win_def'], inline=True)
    embed.add_field(name="Проигранных защит", value=war_stats['lose_def'], inline=True)
    embed.set_footer(text="Статистика обновляется автоматически")
    embed.timestamp = datetime.now(UTC)
    return embed

def make_target_channel_embed(msg_text):
    embed = discord.Embed(
        title="📣 Входящее сообщение от Telegram",
        description=msg_text,
        color=0xFF0000  # Ярко красный для TARGET_CHANNEL_ID
    )
    embed.set_footer(text="Отслеживание важных событий")
    embed.timestamp = datetime.now(UTC)
    return embed

# -------------------------------------------------

@discord_client.event
async def on_ready():
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="📺🟣  Author: dolma1ovvv👾",
        start=datetime.now(UTC)
    )
    await discord_client.change_presence(activity=activity, status=discord.Status.online)
    await tree.sync()
    print(f"[INFO] Discord-бот {discord_client.user} готов!", flush=True)

async def send_or_update_stats_message(channel, text):
    global stats_message_id
    embed = make_war_stats_embed()
    if stats_message_id is None:
        msg = await channel.send(embed=embed)
        stats_message_id = msg.id
    else:
        try:
            msg = await channel.fetch_message(stats_message_id)
            await msg.edit(embed=embed)
        except Exception as e:
            print(f"[ERROR] Edit stats msg: {e}")
            msg = await channel.send(embed=embed)
            stats_message_id = msg.id

tg_client = TelegramClient(SESSION_FILE, API_ID, API_HASH)

@tg_client.on(events.NewMessage(incoming=True))
async def tg_handler(event):
    global last_attack_type, last_battle_object
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

        updated = False

        # Отслеживание фаз ВОЙНЫ:
        if "Ваша организация забила" in msg_text:
            last_attack_type = "atk"
            m = re.search(r'за ([^ ]+)[^,]* на [0-9:]+', msg_text)
            last_battle_object = m.group(1) if m else None

        elif "забили Вашей организации войну за" in msg_text:
            last_attack_type = "def"
            m = re.search(r'за ([^ ]+)[^,]* на [0-9:]+', msg_text)
            last_battle_object = m.group(1) if m else None

        elif ("Захватывает" in msg_text or "Удерживает" in msg_text or "Проигрывает в бою" in msg_text):
            if last_attack_type == "atk" and "Захватывает" in msg_text:
                war_stats["win_attack"] += 1
                updated = True
            elif last_attack_type == "atk" and "Проигрывает в бою" in msg_text:
                war_stats["lose_attack"] += 1
                updated = True
            elif last_attack_type == "def" and "Удерживает" in msg_text:
                war_stats["win_def"] += 1
                updated = True
            elif last_attack_type == "def" and "Проигрывает в бою" in msg_text:
                war_stats["lose_def"] += 1
                updated = True
            last_attack_type = None
            last_battle_object = None

        if updated:
            stats_channel = discord_client.get_channel(WAR_STATS_CHANNEL_ID)
            if stats_channel:
                await send_or_update_stats_message(stats_channel, None)

        if "забили Вашей организации войну за" not in msg_text:
            return
        if ALLOWED_SENDER_IDS and sender_id in ALLOWED_SENDER_IDS:
            stats["allowed"] += 1
            if msg_text:
                channel = discord_client.get_channel(TARGET_CHANNEL_ID)
                if channel:
                    embed = make_target_channel_embed(msg_text)
                    await channel.send(content="@everyone", embed=embed)
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
