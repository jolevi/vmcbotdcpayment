import discord
from discord.ui import View, Button
from discord.ext import commands
import function.mydb 
import function.obj_Topup

class DiscordBot:
    def __init__(self, ENV_DATA, intents=None, log=False):

        if intents is None:
            intents = discord.Intents.default()
            intents.messages = True
            intents.message_content = True

        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        # เก็บค่าตัวแปรลงใน bot
        self.bot.db = function.mydb.MSSQLDatabase(ENV_DATA)
        self.bot.ENV_DATA = ENV_DATA
        self.bot.log = log

        # ✅ เพิ่ม event on_ready
        self.bot.add_listener(self.on_ready)

        # ✅ เพิ่มคำสั่ง
        self.bot.add_command(create_topup)

    async def on_ready(self):
        """ใช้งานบอทดิสคอร์ด"""
        print(f'✅ Logged in as {self.bot.user}')
        self.bot.db.connect()

    async def close_bot(self):
        """ปิดใช้งานบอทดิสคอร์ด"""
        self.bot.db.close()

    def run(self):
        """ตรวจสอบ Env ก่อนใช้งานบอท"""
        if self.bot.ENV_DATA:
            self.bot.run(self.bot.ENV_DATA['TOKEN'])
        else:
            print("❌ ENV_DATA is missing!")

# ✅ แยกฟังก์ชันออกจากคลาส
@commands.command()
async def create_topup(ctx):
    """สร้างปุ่มให้ผู้ใช้เปิดห้องเติมเงิน"""
    allowed_roles = ["Admin", "Moderator"]
    if ctx.author.id != ctx.guild.owner_id and not any(role.name in allowed_roles for role in ctx.author.roles):
        return

    create_button = Button(label="💰 เติมเงิน", style=discord.ButtonStyle.green)

    async def create_button_callback(interaction):
        category = interaction.channel.category
        # ✅ ตรวจสอบว่าผู้ใช้มีห้องอยู่แล้ว
        if category:
            existing_channel = discord.utils.get(category.channels, name=f"topup-{interaction.user.name}")
            if existing_channel:
                embed = discord.Embed(
                    title="❌ คุณมีห้องเติมเงินอยู่แล้ว!",
                    description=f"🔹 ห้องของคุณ: {existing_channel.mention}\nกรุณาใช้ห้องเดิมเพื่อดำเนินการต่อ",
                    color=discord.Color.red()
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return  

        # ✅ ดึงค่าตัวแปรจาก `ctx.bot` ซึ่งเป็น instance ของ DiscordBot
        ENV_DATA = ctx.bot.ENV_DATA
        db = ctx.bot.db
        log = ctx.bot.log

        # ✅ เปิด Modal ให้ผู้ใช้กรอกไอดี
        modal = function.obj_Topup.TopupIDModal(ENV_DATA, db, log)
        await interaction.response.send_modal(modal)

    create_button.callback = create_button_callback
    view = View()
    view.add_item(create_button)

    # ✅ Embed แจ้งให้กดปุ่ม
    embed = discord.Embed(
        title="💰 เปิดห้องเติมเงิน",
        description="📌 กดปุ่มด้านล่างเพื่อเปิดห้องเติมเงินของคุณ",
        color=discord.Color.blue()
    )
    embed.set_footer(text="✅ คุณสามารถกรอกไอดีและเติมเงินได้ในห้องที่ถูกสร้าง")

    await ctx.send(embed=embed, view=view)
