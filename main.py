import os
import asyncio
import re
from datetime import datetime, UTC, timedelta
from time import time
from dotenv import load_dotenv
from telethon import TelegramClient, events
import discord
from discord.ext import commands
import pytz

load_dotenv()

API_ID = int(os.getenv("TG_API_ID"))
API_HASH = os.getenv("TG_API_HASH")
SESSION_FILE = os.getenv("TG_SESSION", "session")

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID"))
WAR_STATS_CHANNEL_ID = 1479807955372085299

ALLOWED_SENDER_IDS = [
    int(x.strip())
    for x in os.getenv("ALLOWED_SENDER_IDS", "").split(",")
    if x.strip().isdigit()
]

BLACKLIST_CHAT_IDS = set()

stats = {"total": 0, "allowed": 0}

war_stats = {"win_attack": 0, "lose_attack": 0, "win_def": 0, "lose_def": 0}
points = 3
stats_message_id = None

last_attack_type = None
last_battle_object = None

ALERT_COOLDOWN = 10
last_alert_ts = 0

intents = discord.Intents.default()
intents.message_content = True
discord_client = commands.Bot(command_prefix="!", intents=intents)

MENTIONS = discord.AllowedMentions(everyone=True)

msk_tz = pytz.timezone("Europe/Moscow")


def format_now_msk():
    now_utc = datetime.now(UTC)
    now_msk = now_utc.astimezone(msk_tz)
    return now_msk.strftime("%H:%M:%S")


def make_war_stats_embed():
    embed = discord.Embed(title="Winrate", color=0x9146FF)
    embed.add_field(name="ATT WIN", value=war_stats["win_attack"], inline=True)
    embed.add_field(name="ATT LOOSE", value=war_stats["lose_attack"], inline=True)
    embed.add_field(name="DEF WIN", value=war_stats["win_def"], inline=True)
    embed.add_field(name="DEF LOOSE", value=war_stats["lose_def"], inline=True)
    embed.add_field(name="POINTS", value=points, inline=False)
    embed.set_footer(text="само обновляется бляди")
    embed.timestamp = datetime.now(UTC)
    return embed


def make_target_channel_embed(msg_text: str):
    embed = discord.Embed(
        title="деф бляди",
        description=msg_text,
        color=0xFF0000,
    )
    embed.timestamp = datetime.now(UTC)
    return embed


@discord_client.event
async def on_ready():
    activity = discord.Activity(
        type=discord.ActivityType.watching,
        name="Author: dolma1ovvv",
        start=datetime.now(UTC),
    )
    await discord_client.change_presence(activity=activity, status=discord.Status.online)
    await discord_client.tree.sync()
    print(f"[INFO] Discord-бот {discord_client.user} готов!", flush=True)


async def get_text_channel(channel_id: int):
    ch = discord_client.get_channel(channel_id)
    if ch is not None:
        return ch
    try:
        return await discord_client.fetch_channel(channel_id)
    except Exception as e:
        print(f"[ERROR] fetch_channel({channel_id}) failed: {e}", flush=True)
        return None


async def send_or_update_stats_message(channel):
    global stats_message_id
    embed = make_war_stats_embed()

    if stats_message_id is None:
        msg = await channel.send(embed=embed)
        stats_message_id = msg.id
        return

    try:
        msg = await channel.fetch_message(stats_message_id)
        await msg.edit(embed=embed)
    except Exception as e:
        print(f"[ERROR] Edit stats msg: {e}", flush=True)
        msg = await channel.send(embed=embed)
        stats_message_id = msg.id

    await asyncio.sleep(0.2)


tg_client = TelegramClient(SESSION_FILE, API_ID, API_HASH)


@tg_client.on(events.NewMessage(incoming=True))
async def tg_handler(event):
    global last_attack_type, last_battle_object, last_alert_ts, points

    try:
        chat_id = event.chat_id
        if chat_id in BLACKLIST_CHAT_IDS:
            print(f"[SKIP] Blacklisted chat_id: {chat_id}", flush=True)
            return

        sender_id = event.sender_id
        msg_text = (getattr(event.message, "message", "") or "").strip()

        msg_text = msg_text.replace(
            "📋 Организация: события | Emo_Work, сервер Downtown", ""
        ).strip()

        stats["total"] += 1
        print(f"[LOG] TG: from id={sender_id} chat={chat_id} text={msg_text!r}", flush=True)

        if sender_id is None:
            return

        updated = False
        log_line = None

        if "Ваша организация забила" in msg_text:
            last_attack_type = "atk"
            m = re.search(r"за ([^ ]+)[^,]* на [0-9:]+", msg_text)
            last_battle_object = m.group(1) if m else None

        elif "забили Вашей организации войну за" in msg_text:
            last_attack_type = "def"
            m = re.search(r"за ([^ ]+)[^,]* на [0-9:]+", msg_text)
            last_battle_object = m.group(1) if m else None

        elif ("Захватывает" in msg_text or
              "Удерживает" in msg_text or
              "Проигрывает в бою" in msg_text):

            if last_attack_type == "atk" and "Захватывает" in msg_text:
                war_stats["win_attack"] += 1
                points += 1
                log_line = f"Атака выиграна в {format_now_msk()} (MSK)"
                updated = True

            elif last_attack_type == "atk" and "Проигрывает в бою" in msg_text:
                war_stats["lose_attack"] += 1
                log_line = f"Атака проиграна в {format_now_msk()} (MSK)"
                updated = True

            elif last_attack_type == "def" and "Удерживает" in msg_text:
                war_stats["win_def"] += 1
                log_line = f"Защита выиграна в {format_now_msk()} (MSK)"
                updated = True

            elif last_attack_type == "def" and "Проигрывает в бою" in msg_text:
                war_stats["lose_def"] += 1
                points -= 1
                log_line = f"Защита проиграна в {format_now_msk()} (MSK)"
                updated = True

            last_attack_type = None
            last_battle_object = None

        if updated:
            stats_channel = await get_text_channel(WAR_STATS_CHANNEL_ID)
            if stats_channel:
                if log_line:
                    await stats_channel.send(log_line)
                await send_or_update_stats_message(stats_channel)

        if "забили Вашей организации войну за" not in msg_text:
            return

        allowed = (not ALLOWED_SENDER_IDS) or (sender_id in ALLOWED_SENDER_IDS)
        print(
            f"[DEBUG] contains_trigger=True sender_allowed={allowed} allowed_list={ALLOWED_SENDER_IDS}",
            flush=True,
        )
        if not allowed:
            return

        stats["allowed"] += 1
        channel = await get_text_channel(TARGET_CHANNEL_ID)
        if channel and msg_text:
            embed = make_target_channel_embed(msg_text)

            now = time()
            if now - last_alert_ts < ALERT_COOLDOWN:
                print("[WARN] alert throttled to avoid spam", flush=True)
            else:
                last_alert_ts = now
                await channel.send(content="@everyone", embed=embed, allowed_mentions=MENTIONS)
                print(f"[DS_LOG] Переслано из TG в Discord: {msg_text!r}", flush=True)
        else:
            print("[ERR] Канал Discord не найден/нет доступа!", flush=True)

    except Exception as global_e:
        print(f"[CRITICAL ERROR] event handler exception: {global_e}", flush=True)


@discord_client.tree.command(name="ping", description="Проверка работы бота")
async def ping_command(interaction: discord.Interaction):
    await interaction.response.send_message(
        "понг блять, он работает не еби его", ephemeral=False
    )


@discord_client.tree.command(
    name="stats",
    description="Статистика войн (табличка win/lose + points)",
)
async def stats_command(interaction: discord.Interaction):
    embed = make_war_stats_embed()
    await interaction.response.send_message(embed=embed, ephemeral=False)


@discord_client.tree.command(
    name="test_forward", description="Тест: отправить сообщение в целевой канал"
)
async def test_forward(interaction: discord.Interaction):
    channel = await get_text_channel(TARGET_CHANNEL_ID)
    embed = make_target_channel_embed("TEST: пересылка работает (ручная проверка).")
    if channel:
        await channel.send(content="@everyone", embed=embed, allowed_mentions=MENTIONS)
        await interaction.response.send_message(
            "Ок, тестовое сообщение отправлено.", ephemeral=True
        )
    else:
        await interaction.response.send_message(
            "Канал не найден/нет доступа.", ephemeral=True
        )


async def main():
    try:
        tg_task = asyncio.create_task(tg_client.start())
        ds_task = asyncio.create_task(discord_client.start(DISCORD_BOT_TOKEN))
        await asyncio.gather(tg_task, ds_task)
    finally:
        await tg_client.disconnect()
        await discord_client.close()


if __name__ == "__main__":
    asyncio.run(main())