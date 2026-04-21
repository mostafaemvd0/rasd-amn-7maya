import discord
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime
import re
import os
import json

# --- Setup Google Sheets ---
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

creds_json = os.environ.get("GOOGLE_CREDENTIALS")
creds_dict = json.loads(creds_json)
creds = Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
gc = gspread.authorize(creds)

SHEET_ID = os.environ.get("SHEET_ID")
sheet = gc.open_by_key(SHEET_ID).sheet1

# --- Discord Bot ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

THREAD_ID = int(os.environ.get("THREAD_ID"))

@client.event
async def on_ready():
    print(f"البوت شغال: {client.user}")

@client.event
async def on_message(message):
    if message.author.bot:
        return
    if message.channel.id != THREAD_ID:
        return

    lines = message.content.strip().split("\n")
    data = {}
    for line in lines:
        if ":" in line:
            key, val = line.split(":", 1)
            data[key.strip().lower()] = val.strip()

    required = ["اسم", "كود", "ايدي", "رتبة", "تاريخ"]
    missing = [r for r in required if r not in data]

    if missing:
        await message.reply(
            f"❌ ناقص: {', '.join(missing)}\n\n"
            "الصيغة الصح:\n"
            "```\nاسم: محمد\nكود: A123\nايدي: 123456789\nرتبة: عضو\nتاريخ: 2024-01-15\n```"
        )
        return

    discord_id = f"<@{data['ايدي']}>"
    row = [""] * 5
    row[0] = discord_id
    row[1] = data["رتبة"]
    row[2] = data["اسم"]
    row[3] = data["كود"]
    row[4] = data["تاريخ"]

    cell_list = sheet.col_values(1)
    next_row = max(64, len(cell_list) + 1)
    sheet.update([row], f'A{next_row}:E{next_row}')

    await message.reply(
        f"✅ تم التسجيل بنجاح!\n"
        f"👤 **{data['اسم']}** | {data['رتبة']}\n"
        f"🆔 {discord_id} | 📅 {data['تاريخ']}"
    )

client.run(os.environ.get("DISCORD_TOKEN"))
