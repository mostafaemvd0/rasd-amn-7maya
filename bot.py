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
STATUS_COLUMN = os.environ.get("STATUS_COLUMN", "T")
ALLOWED_ROLE_IDS = [int(x) for x in os.environ.get("ALLOWED_ROLE_IDS", "").split(",") if x.strip()]

# ╔══════════════════════════════════════════════╗
# ║         ✏️ أضيف حالة جديدة هنا بس           ║
# ║  label = الاسم اللي يظهر على الزرار          ║
# ║  status = القيمة اللي تتكتب في الشيت         ║
# ║  emoji  = الإيموجي                           ║
# ║  style  = success(أخضر) danger(أحمر)         ║
# ║           primary(أزرق) secondary(رمادي)     ║
# ╚══════════════════════════════════════════════╝
STATUS_LIST = [
    {"label": "توظيف",     "status": "توظيف",     "emoji": "📝", "style": discord.ButtonStyle.success},
    {"label": "فى الخدمة", "status": "فى الخدمة", "emoji": "✅", "style": discord.ButtonStyle.primary},
    {"label": "فصل",       "status": "فصل",       "emoji": "🚫", "style": discord.ButtonStyle.danger},
    {"label": "ترقية",     "status": "ترقية",     "emoji": "🟢", "style": discord.ButtonStyle.secondary},
    {"label": "تغيير أكواد",     "status": "تغيير أكواد",     "emoji": "⭐", "style": discord.ButtonStyle.secondary},
    {"label": "استقالة",     "status": "استقالة",     "emoji": "🚩", "style": discord.ButtonStyle.danger},
    {"label": "إجازة خارجية",     "status": "إجازة خارجية",     "emoji": "✈️", "style": discord.ButtonStyle.secondary},
]

# --- التحقق من الرول ---
def has_allowed_role(interaction: discord.Interaction) -> bool:
    role_ids = [role.id for role in interaction.user.roles]
    return any(r in role_ids for r in ALLOWED_ROLE_IDS)

# --- Modal التسجيل ---
class EmployeeModal(discord.ui.Modal, title="تسجيل موظف جديد"):
    f_name = discord.ui.TextInput(label="الاسم", placeholder="اكتب الاسم الكامل")
    f_code = discord.ui.TextInput(label="الكود", placeholder="مثلاً: S-01")
    f_id   = discord.ui.TextInput(label="Discord ID", placeholder="مثلاً: 123456789012345678")
    f_rank = discord.ui.TextInput(label="الرتبة", placeholder="مثلاً: جندي")
    f_row  = discord.ui.TextInput(label="رقم الصف", placeholder="اتركه فاضي للأوتوماتيك", required=False)

    async def on_submit(self, interaction: discord.Interaction):
        from datetime import datetime
        discord_id = f"<@{self.f_id.value}>"
        today = datetime.now().strftime("%Y-%m-%d")
        row = [discord_id, self.f_rank.value, self.f_name.value, self.f_code.value, today]

        if self.f_row.value.strip():
            try:
                next_row = int(self.f_row.value.strip())
                if next_row < START_ROW:
                    await interaction.response.send_message(
                        f"❌ رقم الصف لازم يكون {START_ROW} أو أكبر!", ephemeral=True)
                    return
            except ValueError:
                await interaction.response.send_message(
                    "❌ رقم الصف لازم يكون رقم صح!", ephemeral=True)
                return
        else:
            cell_list = sheet.col_values(1)
            filled = [v for v in cell_list[START_ROW-1:] if v != ""]
            next_row = START_ROW + len(filled)

        sheet.update([row], f'A{next_row}:E{next_row}')
        await interaction.response.send_message(
            f"✅ تم التسجيل بنجاح في صف {next_row}!\n\n"
            f"👤 **{self.f_name.value}** | {self.f_rank.value}\n\n"
            f"🆔 {discord_id} | 📅 {today}",
            ephemeral=True
        )

# --- Modal تحديث الحالة ---
class UpdateIDModal(discord.ui.Modal):
    def __init__(self, status: str, emoji: str):
        super().__init__(title=f"تحديث الحالة إلى {emoji} {status}")
        self.status = status

    f_id = discord.ui.TextInput(
        label="Discord ID",
        placeholder="مثلاً: 123456789012345678"
    )

    async def on_submit(self, interaction: discord.Interaction):
        raw_id = self.f_id.value.strip()
        mention_format = f"<@{raw_id}>"
        col_a = sheet.col_values(1)
        target_row = None

        for i, cell in enumerate(col_a[START_ROW - 1:], start=START_ROW):
            if cell.strip() == mention_format:
                target_row = i
                break

        if target_row is None:
            await interaction.response.send_message(
                f"❌ مش لاقي ID `{raw_id}` في الجدول!", ephemeral=True)
            return

        sheet.update([[self.status]], f'{STATUS_COLUMN}{target_row}')
        await interaction.response.send_message(
            f"✅ تم تحديث حالة <@{raw_id}> إلى **{self.status}** في صف {target_row}!",
            ephemeral=True
        )

# --- زرار الحالة (ديناميكي) ---
class StatusButton(discord.ui.Button):
    def __init__(self, label: str, status: str, emoji: str, style):
        super().__init__(label=f"{emoji} {label}", style=style, custom_id=f"status__{status}")
        self.status = status
        self.emoji_str = emoji

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(UpdateIDModal(status=self.status, emoji=self.emoji_str))

# --- View الحالات ---
class StatusButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
        for s in STATUS_LIST:
            self.add_item(StatusButton(s["label"], s["status"], s["emoji"], s["style"]))

# --- الأزرار الرئيسية ---
class RegisterButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📋 تسجيل موظف جديد", style=discord.ButtonStyle.primary, custom_id="register_btn")
    async def open_register(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_allowed_role(interaction):
            await interaction.response.send_message("❌ مش عندك صلاحية!", ephemeral=True)
            return
        await interaction.response.send_modal(EmployeeModal())

    @discord.ui.button(label="🔄 تحديث حالة", style=discord.ButtonStyle.secondary, custom_id="update_status_btn")
    async def open_status_menu(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_allowed_role(interaction):
            await interaction.response.send_message("❌ مش عندك صلاحية!", ephemeral=True)
            return
        await interaction.response.send_message(
            "اختار الحالة الجديدة:",
            view=StatusButtonsView(),
            ephemeral=True
        )

# --- Commands ---
@tree.command(name="register", description="فتح ملف توظيف")
async def register(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("❌ مش عندك صلاحية!", ephemeral=True)
        return
    if interaction.channel_id != THREAD_ID:
        await interaction.response.send_message("❌ الأمر ده شغال في الثريد المخصص بس!", ephemeral=True)
        return
    await interaction.response.send_message("اضغط الزرار عشان تفتح الفورم:", view=RegisterButton())

@tree.command(name="setup", description="ارسال مسدج التوظيف")
async def setup(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("❌ مش عندك صلاحية!", ephemeral=True)
        return
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

client.run(os.environ.get("DISCORD_TOKEN"))
