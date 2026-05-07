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

# ╔══════════════════════════════════════════════════════════════════╗
# ║  SHEET_ID       = رابط جدول الرئيسي + الاداري (نفس الملف)      ║
# ║  AFFAIRS_SHEET_ID = رابط جدول شؤون ادارية (ملف تاني)           ║
# ║  SHEET_NAME_MAIN  = اسم تاب الجدول الرئيسي                      ║
# ║  SHEET_NAME_ADMIN = اسم تاب الجدول الاداري                      ║
# ║  SHEET_NAME_AFFAIRS = اسم تاب شؤون ادارية                       ║
# ╚══════════════════════════════════════════════════════════════════╝
SHEET_ID        = os.environ.get("SHEET_ID")           # ملف الرئيسي + الاداري
AFFAIRS_SHEET_ID = os.environ.get("AFFAIRS_SHEET_ID")  # ملف شؤون ادارية منفصل

workbook         = gc.open_by_key(SHEET_ID)
affairs_workbook = gc.open_by_key(AFFAIRS_SHEET_ID)

SHEET_NAMES = {
    "اساسي": os.environ.get("SHEET_NAME_MAIN",    "جدول رئيسي"),
    "اداري": os.environ.get("SHEET_NAME_ADMIN",   "جدول اداري"),
    "شؤون":  os.environ.get("SHEET_NAME_AFFAIRS", "شؤون ادارية"),
}

def get_sheet(key: str):
    if key == "شؤون":
        return affairs_workbook.worksheet(SHEET_NAMES[key])
    return workbook.worksheet(SHEET_NAMES[key])

# --- Discord Bot ---
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(client)

THREAD_ID        = int(os.environ.get("THREAD_ID"))
START_ROW        = int(os.environ.get("START_ROW", 64))
STATUS_COLUMN    = os.environ.get("STATUS_COLUMN", "T")
ALLOWED_ROLE_IDS = [int(x) for x in os.environ.get("ALLOWED_ROLE_IDS", "").split(",") if x.strip()]

# ╔══════════════════════════════════════════════╗
# ║         ✏️ أضيف حالة جديدة هنا بس           ║
# ╚══════════════════════════════════════════════╝
STATUS_LIST = [
    {"label": "توظيف",     "status": "توظيف",     "emoji": "📝", "style": discord.ButtonStyle.success},
    {"label": "فى الخدمة", "status": "فى الخدمة", "emoji": "✅", "style": discord.ButtonStyle.success},
    {"label": "فصل",       "status": "فصل",       "emoji": "🚫", "style": discord.ButtonStyle.danger},
    {"label": "ترقية",     "status": "ترقية",     "emoji": "⭐", "style": discord.ButtonStyle.primary},
]

# --- التحقق من الرول ---
def has_allowed_role(interaction: discord.Interaction) -> bool:
    role_ids = [role.id for role in interaction.user.roles]
    return any(r in role_ids for r in ALLOWED_ROLE_IDS)

# ══════════════════════════════════════════════════════════
#  Modal رصد موظف (رئيسي / اداري) — 5 حقول
# ══════════════════════════════════════════════════════════
class EmployeeModal(discord.ui.Modal):
    f_name = discord.ui.TextInput(label="الاسم",      placeholder="اكتب الاسم الكامل")
    f_code = discord.ui.TextInput(label="الكود",      placeholder="مثلاً: S-01")
    f_id   = discord.ui.TextInput(label="Discord ID", placeholder="مثلاً: 123456789012345678")
    f_rank = discord.ui.TextInput(label="الرتبة",     placeholder="مثلاً: جندي")
    f_row  = discord.ui.TextInput(label="رقم الصف",   placeholder="اتركه فاضي للأوتوماتيك", required=False)

    def __init__(self, sheet_key: str, sheet_label: str):
        super().__init__(title=f"رصد موظف — {sheet_label}")
        self.sheet_key   = sheet_key
        self.sheet_label = sheet_label

    async def on_submit(self, interaction: discord.Interaction):
        from datetime import datetime
        sheet      = get_sheet(self.sheet_key)
        discord_id = f"<@{self.f_id.value}>"
        today      = datetime.now().strftime("%Y-%m-%d")
        row        = [discord_id, self.f_rank.value, self.f_name.value, self.f_code.value, today]

        if self.f_row.value.strip():
            try:
                next_row = int(self.f_row.value.strip())
                if next_row < START_ROW:
                    await interaction.response.send_message(
                        f"❌ رقم الصف لازم يكون {START_ROW} أو أكبر!", ephemeral=True); return
            except ValueError:
                await interaction.response.send_message(
                    "❌ رقم الصف لازم يكون رقم صح!", ephemeral=True); return
        else:
            cell_list = sheet.col_values(1)
            filled    = [v for v in cell_list[START_ROW - 1:] if v != ""]
            next_row  = START_ROW + len(filled)

        sheet.update([row], f'A{next_row}:E{next_row}')
        await interaction.response.send_message(
            f"✅ تم الرصد في **{self.sheet_label}** — صف {next_row}!\n\n"
            f"👤 **{self.f_name.value}** | {self.f_rank.value}\n"
            f"🆔 {discord_id} | 📅 {today}",
            ephemeral=True
        )

# ══════════════════════════════════════════════════════════
#  Modal رصد شؤون ادارية — حقلين فقط (ID + انتساب)
# ══════════════════════════════════════════════════════════
class AffairsModal(discord.ui.Modal, title="رصد شؤون ادارية"):
    f_id      = discord.ui.TextInput(label="Discord ID",  placeholder="مثلاً: 123456789012345678")
    f_entisab = discord.ui.TextInput(label="الانتساب",    placeholder="اكتب الانتساب")

    async def on_submit(self, interaction: discord.Interaction):
        sheet      = get_sheet("شؤون")
        discord_id = f"<@{self.f_id.value}>"

        # إيجاد أول صف فاضي ابتداءً من START_ROW
        col_a  = sheet.col_values(1)
        filled = [v for v in col_a[START_ROW - 1:] if v != ""]
        next_row = START_ROW + len(filled)

        # كتابة ID في عمود A والانتساب في عمود F
        sheet.update([[discord_id]],      f'A{next_row}')
        sheet.update([[self.f_entisab.value]], f'F{next_row}')

        await interaction.response.send_message(
            f"✅ تم الرصد في **{SHEET_NAMES['شؤون']}** — صف {next_row}!\n\n"
            f"🆔 {discord_id} | 📋 {self.f_entisab.value}",
            ephemeral=True
        )

# ══════════════════════════════════════════════════════════
#  Modal تحديث الحالة
# ══════════════════════════════════════════════════════════
class UpdateIDModal(discord.ui.Modal):
    def __init__(self, status: str, emoji: str, sheet_key: str, sheet_label: str):
        super().__init__(title=f"تحديث الحالة — {emoji} {status} ({sheet_label})")
        self.status      = status
        self.sheet_key   = sheet_key
        self.sheet_label = sheet_label

    f_id = discord.ui.TextInput(
        label="Discord ID",
        placeholder="مثلاً: 123456789012345678"
    )

    async def on_submit(self, interaction: discord.Interaction):
        sheet         = get_sheet(self.sheet_key)
        raw_id        = self.f_id.value.strip()
        mention_format = f"<@{raw_id}>"
        col_a         = sheet.col_values(1)
        target_row    = None

        for i, cell in enumerate(col_a[START_ROW - 1:], start=START_ROW):
            if cell.strip() == mention_format:
                target_row = i
                break

        if target_row is None:
            await interaction.response.send_message(
                f"❌ مش لاقي ID `{raw_id}` في **{self.sheet_label}**!", ephemeral=True)
            return

        sheet.update([[self.status]], f'{STATUS_COLUMN}{target_row}')
        await interaction.response.send_message(
            f"✅ تم تحديث حالة <@{raw_id}> إلى **{self.status}** في **{self.sheet_label}** — صف {target_row}!",
            ephemeral=True
        )

# ══════════════════════════════════════════════════════════
#  View: اختيار الشيت لتحديث الحالة
# ══════════════════════════════════════════════════════════
class SheetSelectForStatusView(discord.ui.View):
    """يظهر أزرار اختيار الشيت، بعدين يعرض أزرار الحالات"""

    SHEET_OPTIONS = [
        {"key": "اساسي",  "label": "جدول اساسيين", "emoji": "👥", "style": discord.ButtonStyle.primary},
        {"key": "اداري",  "label": "جدول اداريين", "emoji": "🏢", "style": discord.ButtonStyle.secondary},
    ]

    def __init__(self):
        super().__init__(timeout=60)
        for opt in self.SHEET_OPTIONS:
            btn = discord.ui.Button(
                label=f"{opt['emoji']} {opt['label']}",
                style=opt["style"],
                custom_id=f"sheetsel__{opt['key']}"
            )
            btn.callback = self._make_callback(opt["key"], opt["label"])
            self.add_item(btn)

    def _make_callback(self, sheet_key: str, sheet_label: str):
        async def callback(interaction: discord.Interaction):
            await interaction.response.send_message(
                f"اختار الحالة الجديدة للشيت **{sheet_label}**:",
                view=StatusButtonsView(sheet_key, sheet_label),
                ephemeral=True
            )
        return callback

# ══════════════════════════════════════════════════════════
#  View: أزرار الحالات (بعد اختيار الشيت)
# ══════════════════════════════════════════════════════════
class StatusButton(discord.ui.Button):
    def __init__(self, label: str, status: str, emoji: str, style, sheet_key: str, sheet_label: str):
        super().__init__(
            label=f"{emoji} {label}",
            style=style,
            custom_id=f"status__{status}__{sheet_key}"
        )
        self.status      = status
        self.emoji_str   = emoji
        self.sheet_key   = sheet_key
        self.sheet_label = sheet_label

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(
            UpdateIDModal(
                status=self.status,
                emoji=self.emoji_str,
                sheet_key=self.sheet_key,
                sheet_label=self.sheet_label
            )
        )

class StatusButtonsView(discord.ui.View):
    def __init__(self, sheet_key: str, sheet_label: str):
        super().__init__(timeout=60)
        for s in STATUS_LIST:
            self.add_item(StatusButton(
                s["label"], s["status"], s["emoji"], s["style"],
                sheet_key, sheet_label
            ))

# ══════════════════════════════════════════════════════════
#  الأزرار الرئيسية
# ══════════════════════════════════════════════════════════
class MainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    # ── رصد موظف اساسي ──────────────────────────────────
    @discord.ui.button(label="👥 رصد موظف اساسي",    style=discord.ButtonStyle.primary,   custom_id="btn_main")
    async def open_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_allowed_role(interaction):
            await interaction.response.send_message("❌ مش عندك صلاحية!", ephemeral=True); return
        await interaction.response.send_modal(EmployeeModal("اساسي", SHEET_NAMES["اساسي"]))

    # ── رصد اداري ────────────────────────────────────────
    @discord.ui.button(label="🏢 رصد اداري",          style=discord.ButtonStyle.secondary, custom_id="btn_admin")
    async def open_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_allowed_role(interaction):
            await interaction.response.send_message("❌ مش عندك صلاحية!", ephemeral=True); return
        await interaction.response.send_modal(EmployeeModal("اداري", SHEET_NAMES["اداري"]))

    # ── رصد شؤون ادارية ──────────────────────────────────
    @discord.ui.button(label="📁 رصد شؤون ادارية", style=discord.ButtonStyle.secondary, custom_id="btn_affairs")
    async def open_affairs(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_allowed_role(interaction):
            await interaction.response.send_message("❌ مش عندك صلاحية!", ephemeral=True); return
        await interaction.response.send_modal(AffairsModal())

    # ── تحديث الحالة ──────────────────────────────────────
    @discord.ui.button(label="🔄 تحديث حالة",         style=discord.ButtonStyle.danger,    custom_id="btn_update")
    async def open_update(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_allowed_role(interaction):
            await interaction.response.send_message("❌ مش عندك صلاحية!", ephemeral=True); return
        await interaction.response.send_message(
            "اختار الشيت اللي عايز تحدث فيه الحالة:",
            view=SheetSelectForStatusView(),
            ephemeral=True
        )

# ══════════════════════════════════════════════════════════
#  Commands
# ══════════════════════════════════════════════════════════
@tree.command(name="setup", description="ارسال مسدج الرصد الرئيسي")
async def setup(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("❌ مش عندك صلاحية!", ephemeral=True); return
    if interaction.channel_id != THREAD_ID:
        await interaction.response.send_message("❌ شغال في الثريد المخصص بس!", ephemeral=True); return
    await interaction.response.send_message("✅ تم!", ephemeral=True)
    await interaction.channel.send(
        "📋 **لوحة الرصد**\nاختار الجدول المناسب:",
        view=MainView()
    )

@tree.command(name="register", description="فتح لوحة الرصد")
async def register(interaction: discord.Interaction):
    if not has_allowed_role(interaction):
        await interaction.response.send_message("❌ مش عندك صلاحية!", ephemeral=True); return
    if interaction.channel_id != THREAD_ID:
        await interaction.response.send_message("❌ الأمر ده شغال في الثريد المخصص بس!", ephemeral=True); return
    await interaction.response.send_message(
        "📋 **لوحة الرصد**\nاختار الجدول المناسب:",
        view=MainView()
    )

# ══════════════════════════════════════════════════════════
@client.event
async def on_ready():
    await tree.sync()
    client.add_view(MainView())
    print(f"البوت شغال: {client.user}")

client.run(os.environ.get("DISCORD_TOKEN"))
