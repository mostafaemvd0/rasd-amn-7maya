# ══════════════════════════════════════════════════════════
#  ✅ View اختيار الانتساب — بتظهر بعد رصد اساسي/اداري
# ══════════════════════════════════════════════════════════
class EntisabView(discord.ui.View):
    def __init__(self, discord_id: str):
        super().__init__(timeout=60)
        self.discord_id = discord_id

        options = [
            {"label": "اساسي", "emoji": "👤", "style": discord.ButtonStyle.primary},
            {"label": "منتدب", "emoji": "🔄", "style": discord.ButtonStyle.secondary},
            {"label": "رقابي", "emoji": "🔍", "style": discord.ButtonStyle.success},
        ]
        for opt in options:
            btn = discord.ui.Button(label=f"{opt['emoji']} {opt['label']}", style=opt["style"])
            btn.callback = self._make_callback(opt["label"])
            self.add_item(btn)

    def _make_callback(self, entisab: str):
        async def callback(interaction: discord.Interaction):
            sheet      = get_sheet("شؤون")
            discord_id = f"<@{self.discord_id}>"
            col_a      = sheet.col_values(1)
            filled     = [v for v in col_a[START_ROW - 1:] if v != ""]
            next_row   = START_ROW + len(filled)

            # ✅ بيكتب ID في A والانتساب في E بس
            sheet.update([[discord_id]], f'A{next_row}')
            sheet.update([[entisab]],   f'E{next_row}')

            for item in self.children:
                item.disabled = True

            await interaction.response.edit_message(
                content=(
                    f"✅ تم الرصد في **{SHEET_NAMES['شؤون']}**!\n"
                    f"🆔 {discord_id} | 📋 **{entisab}** — صف {next_row}"
                ),
                view=self
            )
        return callback


# ══════════════════════════════════════════════════════════
#  ✅ EmployeeModal — بعد الرصد بيعرض أزرار الانتساب
# ══════════════════════════════════════════════════════════
class EmployeeModal(discord.ui.Modal):
    f_name = discord.ui.TextInput(label="الاسم",      placeholder="اكتب الاسم الكامل")
    f_code = discord.ui.TextInput(label="الكود",      placeholder="مثلاً: S-01")
    f_id   = discord.ui.TextInput(label="Discord ID", placeholder="مثلاً: 123456789012345678")
    f_rank = discord.ui.TextInput(label="الرتبة",     placeholder="مثلاً: جندي")
    f_row  = discord.ui.TextInput(label="رقم الصف",   placeholder="اتركه فاضي للأوتوماتيك", required=False)

    def __init__(self, sheet_key: str, sheet_label: str):
        super().__init__(title=f"رصد موظف — {sheet_label}"[:45])
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

        # ✅ رسالة النجاح + أزرار الانتساب
        await interaction.response.send_message(
            f"✅ تم الرصد في **{self.sheet_label}** — صف {next_row}!\n"
            f"👤 **{self.f_name.value}** | {self.f_rank.value}\n"
            f"🆔 {discord_id} | 📅 {today}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📋 اختار حالة الانتساب للقطاع:",
            view=EntisabView(self.f_id.value.strip()),
            ephemeral=True
        )


# ══════════════════════════════════════════════════════════
#  ✅ زرار شؤون ادارية — بقى فيه تحديث الحالة بس
# ══════════════════════════════════════════════════════════
class MainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="👥 رصد موظف اساسي", style=discord.ButtonStyle.primary,   custom_id="btn_main")
    async def open_main(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_allowed_role(interaction):
            await interaction.response.send_message("❌ مش عندك صلاحية!", ephemeral=True); return
        await interaction.response.send_modal(EmployeeModal("اساسي", SHEET_NAMES["اساسي"]))

    @discord.ui.button(label="🏢 رصد اداري", style=discord.ButtonStyle.secondary, custom_id="btn_admin")
    async def open_admin(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_allowed_role(interaction):
            await interaction.response.send_message("❌ مش عندك صلاحية!", ephemeral=True); return
        await interaction.response.send_modal(EmployeeModal("اداري", SHEET_NAMES["اداري"]))

    # ✅ زرار شؤون ادارية = تحديث الحالة بس
    @discord.ui.button(label="📁 شؤون ادارية — تحديث الحالة", style=discord.ButtonStyle.secondary, custom_id="btn_affairs")
    async def open_affairs(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_allowed_role(interaction):
            await interaction.response.send_message("❌ مش عندك صلاحية!", ephemeral=True); return
        await interaction.response.send_message(
            "اختار الشيت اللي عايز تحدث فيه الحالة:",
            view=SheetSelectForStatusView(),
            ephemeral=True
        )

    @discord.ui.button(label="🔄 تحديث حالة", style=discord.ButtonStyle.danger, custom_id="btn_update")
    async def open_update(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not has_allowed_role(interaction):
            await interaction.response.send_message("❌ مش عندك صلاحية!", ephemeral=True); return
        await interaction.response.send_message(
            "اختار الشيت اللي عايز تحدث فيه الحالة:",
            view=SheetSelectForStatusView(),
            ephemeral=True
        )
