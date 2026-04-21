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
tree = discord.app_commands.CommandTree(client)

THREAD_ID = int(os.environ.get("THREAD_ID"))
START_ROW = int(os.environ.get("START_ROW", 64))

# --- Modal (الفورم) ---
class TوظيفModal(discord.ui.Modal, title="تسجيل موظف جديد"):
    اسم = discord.ui.TextInput(label="الاسم", placeholder="اكتب الاسم الكامل")
    كود = discord.ui.TextInput(label="الكود", placeholder="مثلاً: EMP001")
    ايدي = discord.ui.TextInput(label="Discord ID", placeholder="مثلاً: 123456789012345678")
    رتبة = discord.ui.TextInput(label="الرتبة", placeholder="مثلاً: مشرف")
    تاريخ = discord.ui.TextInput(label="تاريخ التعيين", placeholder="مثلاً: 2024-01-15")

    async def on_submit(self, interaction: discord.Interaction):
        discord_id = f"<@{self.ايدي.value}>"
        row = [discord_id, self.رتبة.value, self.اسم.value, self.كود.value, self.تاريخ.value]

        cell_list = sheet.col_values(1)
        filled = [v for v in cell_list[START_ROW-1:] if v != ""]
        next_row = START_ROW + len(filled)

        sheet.update([row], f'A{next_row}:E{next_row}')

        await interaction.response.send_message(
            f"✅ تم التسجيل بنجاح في صف {next_row}!\n"
            f"👤 **{self.اسم.value}** | {self.رتبة.value}\n"
            f"🆔 {discord_id} | 📅 {self.تاريخ.value}",
            ephemeral=True
        )

# --- زرار الفورم ---
class ToظيفButton(discord.ui.View):
    @discord.ui.button(label="📋 تسجيل موظف جديد", style=discord.ButtonStyle.primary)
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TوظيفModal())

# --- Command ---
@tree.command(name="register", description="فتح ملف توظيف امن وحماية")
async def register(interaction: discord.Interaction):
    if interaction.channel_id != THREAD_ID:
        await interaction.response.send_message("❌ الأمر ده شغال في الثريد المخصص بس!", ephemeral=True)
        return
    await interaction.response.send_message("اضغط الزرار عشان تفتح الفورم:", view=ToظيفButton())

@client.event
async def on_ready():
    await tree.sync()
    print(f"البوت شغال: {client.user}")

client.run(os.environ.get("DISCORD_TOKEN"))
