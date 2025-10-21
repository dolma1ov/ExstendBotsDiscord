import asyncio
import os
from dotenv import load_dotenv
import discord
from telegram.ext import Application, MessageHandler, filters, ContextTypes
from telegram import Update

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
TARGET_CHANNEL_ID = int(os.getenv("TARGET_CHANNEL_ID", "1428649319011057689"))
HEADER_TO_REMOVE = os.getenv("HEADER_TO_REMOVE", "📋 Организация: события | Huxley_Exstendyan, ")
RP_BOT_ID = int(os.getenv("RP_BOT_ID", "7621046969"))

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


async def send_to_discord(text):
    target_channel = discord_client.get_channel(TARGET_CHANNEL_ID)
    if target_channel:
        await target_channel.send(f"@everyone\n{text}")


async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    if not message or not message.text:
        return

    if message.from_user.id != RP_BOT_ID:
        return

    content = message.text.strip()

    if content.startswith(HEADER_TO_REMOVE):
        body = content[len(HEADER_TO_REMOVE):].strip()
        if body.startswith('\n'):
            body = body[1:].strip()
    else:
        body = content

    if body:
        await send_to_discord(body)


def run_telegram_bot():
    telegram_app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    telegram_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message))
    telegram_app.run_polling()


async def main():
    discord_task = asyncio.create_task(discord_client.start(DISCORD_BOT_TOKEN))
    telegram_task = asyncio.create_task(
        asyncio.to_thread(run_telegram_bot)
    )

    done, pending = await asyncio.wait(
        {discord_task, telegram_task},
        return_when=asyncio.FIRST_COMPLETED
    )

    for task in pending:
        task.cancel()

    if pending:
        await asyncio.gather(*pending, return_exceptions=True)

    for task in done:
        if exc := task.exception():
            raise exc


if __name__ == '__main__':
    asyncio.run(main())
