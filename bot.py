import discord
import gspread
from google.oauth2.service_account import Credentials
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

# --- Modal ---
class EmployeeModal(discord.ui.Modal, title="تسجيل موظف جديد"):
    f_name = discord.ui.TextInput(label="الاسم", placeholder="اكتب الاسم الكامل")
    f_code = discord.ui.TextInput(label="الكود", placeholder="مثلاً: S-01")
    f_id = discord.ui.TextInput(label="Discord ID", placeholder="مثلاً: 123456789012345678")
    f_rank = discord.ui.TextInput(label="الرتبة", placeholder="مثلاً: جندي")

    async def on_submit(self, interaction: discord.Interaction):
        from datetime import datetime
        discord_id = f"<@{self.f_id.value}>"
        today = datetime.now().strftime("%Y-%m-%d")
        row = [discord_id, self.f_rank.value, self.f_name.value, self.f_code.value, today]

        cell_list = sheet.col_values(1)
        filled = [v for v in cell_list[START_ROW-1:] if v != ""]
        next_row = START_ROW + len(filled)

        sheet.update([row], f'A{next_row}:E{next_row}')

        await interaction.response.send_message(
            f"✅ تم التسجيل بنجاح!\n"
            f"👤 **{self.f_name.value}** | {self.f_rank.value}\n"
            f"🆔 {discord_id} | 📅 {today}",
            ephemeral=True
        )

# --- Button ---
class RegisterButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 تسجيل موظف جديد", style=discord.ButtonStyle.primary, custom_id="register_btn")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(EmployeeModal())

# --- Commands ---
@tree.command(name="register", description="فتح ملف توظيف امن وحماية")
async def register(interaction: discord.Interaction):
    if interaction.channel_id != THREAD_ID:
        await interaction.response.send_message("❌ الأمر ده شغال في الثريد المخصص بس!", ephemeral=True)
        return
    await interaction.response.send_message("اضغط الزرار عشان تفتح الفورم:", view=RegisterButton())

@tree.command(name="setup", description="ارسال مسدج التوظيف")
async def setup(interaction: discord.Interaction):
    if interaction.channel_id != THREAD_ID:
        await interaction.response.send_message("❌ شغال في الثريد المخصص بس!", ephemeral=True)
        return
    await interaction.response.send_message("✅ تم!", ephemeral=True)
    await interaction.channel.send(
        "📋 **تسجيل موظف جديد**\nاضغط الزرار عشان تفتح الفورم:",
        view=RegisterButton()
    )

@client.event
async def on_ready():
    await tree.sync()
    client.add_view(RegisterButton())
    print(f"البوت شغال: {client.user}")
    print(f"Commands synced!")

client.run(os.environ.get("DISCORD_TOKEN"))
