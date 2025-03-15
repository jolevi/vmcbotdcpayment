import discord
from discord.ui import View, Button, Modal, TextInput, Select
from discord import SelectOption
from datetime import datetime, timedelta
from io import BytesIO
from PIL import Image
import base64
import json
import function.myfunction
import function.myreq

class TopupIDModal(Modal):
    def __init__(self, ENV_DATA, db, log=False):
        super().__init__(title="📌 กรอกข้อมูลไอดี")  # เรียก constructor ของ Modal

        self.db = db  # เก็บ object db ไว้ใน instance
        self.log = log

        self.TMP_API_ENDPOINT = ENV_DATA['TMP_API_ENDPOINT']
        self.TMP_API_USERNAME = ENV_DATA['TMP_API_USERNAME']
        self.TMP_API_PASSWORD = ENV_DATA['TMP_API_PASSWORD']
        self.TMP_API_CONID = ENV_DATA['TMP_API_CONID']
        self.TMP_BANK_ACCODE = ENV_DATA['TMP_BANK_ACCODE']
        self.TMP_BANK_ACCOUNT = ENV_DATA['TMP_BANK_ACCOUNT']
        self.TMP_PROMMPAY_NO = ENV_DATA['TMP_PROMMPAY_NO']
        self.TMP_PROMMPAY_TYPE = ENV_DATA['TMP_PROMMPAY_TYPE']
        self.TMP_PROMMPAY_NAME = ENV_DATA['TMP_PROMMPAY_NAME']
        self.TOPUP_MULTIPLY = ENV_DATA['TOPUP_MULTIPLY']

    id_input = TextInput(label="🔹 กรุณากรอกไอดีของคุณ", placeholder="ไอดีของคุณที่ใช้ในเกม")
        
    async def on_submit(self, interaction: discord.Interaction):
        user_id = self.id_input.value.strip()

        # 🔴 ตรวจสอบว่าค่าว่างหรือไม่
        if not user_id:
            embed = discord.Embed(
                title="❌ ข้อผิดพลาด",
                description="🔹 กรุณากรอกไอดีของคุณให้ถูกต้อง!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        query = "SELECT [UserNum] FROM [Account].[dbo].[cabal_auth_table] WHERE [ID] = ?"
        result = await self.db.fetch_one(query, (user_id,))

        if not result:
            embed = discord.Embed(
                title="❌ ข้อผิดพลาด",
                description="🔹 ไม่พบชื่อผู้ใช้นี้ในระบบ!",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return
        
        # ✅ ดำเนินการต่อเมื่อ user_id มีค่า
        guild = interaction.guild
        category = interaction.channel.category  

        if not category:
            category = await guild.create_category("Topup")

        # ✅ ตรวจสอบว่าผู้ใช้มีห้องอยู่แล้ว
        existing_channel = discord.utils.get(category.channels, name=f"topup-{interaction.user.name}")
        if existing_channel:
            embed = discord.Embed(
                title="❌ คุณมีห้องเติมเงินอยู่แล้ว!",
                description=f"🔹 ห้องของคุณ: {existing_channel.mention}\nกรุณาใช้ห้องเดิมเพื่อดำเนินการต่อ",
                color=discord.Color.red()
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        # ✅ สร้างห้องใหม่
        channel_name = f"topup-{interaction.user.name}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False, send_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True),  # Allow the bot to send messages
        }

        footer = "❗โปรดอย่าปิดห้องจนกว่าการเติมเงินจะเสร็จสิ้น!\n"
        footer += "⛔ ช่วงเวลา 00:00 - 02:00 เป็นช่วงที่ธนาคารปรับปรุงระบบในรอบวัน อาจทำให้ไม่สามารถตรวจสอบการโอนได้ ควรกดตรวจสอบเป็นระยะ"

        topup_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        # 🔴 ปุ่มปิดห้อง
        close_button = Button(label="ปิดห้อง", style=discord.ButtonStyle.red)

        async def close_button_callback(close_interaction):
            if "topup-" in close_interaction.channel.name:
                if self.log:
                    await function.myfunction.save_chat_logs(close_interaction.channel, interaction.user, 'log/topup/')

                await close_interaction.channel.delete()
            else:
                embed = discord.Embed(
                    title="❌ ไม่สามารถปิดห้องนี้ได้!",
                    description="🔹 กรุณาติดต่อแอดมิน",
                    color=discord.Color.red()
                )
                await close_interaction.response.send_message(embed=embed, ephemeral=True)

        # ตั้งค่า callback
        close_button.callback = close_button_callback

        # ✅ สร้าง Select สำหรับการเลือกจำนวนเงิน
        select = Select(
            placeholder="เลือกจำนวนเงินที่ต้องการเติม",
            options=[
                SelectOption(label="50 บาท", value="50"),
                SelectOption(label="150 บาท", value="150"),
                SelectOption(label="300 บาท", value="300"),
                SelectOption(label="500 บาท", value="500"),
                SelectOption(label="1000 บาท", value="1000"),
                SelectOption(label="1500 บาท", value="1500")
            ]
        )

        async def select_callback(select_interaction: discord.Interaction):
            selected_price = select.values[0]

            # ใช้ defer เพื่อแจ้งว่าเราจะตอบกลับในภายหลัง
            await select_interaction.response.defer()

            # ดึงข้อความทั้งหมดในช่อง
            messages = []
            async for message in topup_channel.history():
                messages.append(message)

            # ลบข้อความทั้งหมด ยกเว้นข้อความแรก
            messages.reverse()
            for message in messages[1:]:
                # print(message)
                await message.delete()
            # การเชื่อมต่อกับ API
            getidpay_url = f'{self.TMP_API_ENDPOINT}?username={self.TMP_API_USERNAME}&password={self.TMP_API_PASSWORD}&amount={selected_price}'
            getidpay_url += f'&ref1={user_id}&con_id={self.TMP_API_CONID}&method=create_pay'
            getidpay_data = json.loads(function.myreq.connect_api(getidpay_url).text)

            if getidpay_data['status'] == 1:
                id_pay = getidpay_data['id_pay']
                getqr_url = f'{self.TMP_API_ENDPOINT}?username={self.TMP_API_USERNAME}&password={self.TMP_API_PASSWORD}&con_id={self.TMP_API_CONID}&id_pay={id_pay}'
                getqr_url += f'&type={self.TMP_PROMMPAY_TYPE}&promptpay_id={self.TMP_PROMMPAY_NO}&method=detail_pay'
                getqr_data = json.loads(function.myreq.connect_api(getqr_url).text)

                if getqr_data['status'] == 1:
                    if getqr_data['time_out'] < 0:
                        cancel_url = f'{self.TMP_API_ENDPOINT}?username={self.TMP_API_USERNAME}&password={self.TMP_API_PASSWORD}&con_id={self.TMP_API_CONID}'
                        cancel_url += f'&method=cancel&id_pay={id_pay}'
                        function.myreq.connect_api(cancel_url)
                        
                        # ส่ง Embed แจ้งข้อผิดพลาด
                        embed = discord.Embed(
                            title="❌ เกิดข้อผิดพลาด!",
                            description=f"🔹 **คุณ {interaction.user.mention}**\n👻 ไอดีที่จะเติม: {user_id}\n💰 กรุณาเลือกจำนวนเงินที่ต้องการจะเติมอีกครั้ง",
                            color=discord.Color.red()
                        )
                        embed.set_footer(text=footer)
                        
                        await select_interaction.edit_original_response(embed=embed)

                        return

                    image_data = base64.b64decode(getqr_data['qr_image_base64'])
                    image_bytes = BytesIO(image_data)

                    amount = "{:.2f}".format(int(getqr_data['amount_check']) / 100)
                    time_out = getqr_data['time_out']

                    # สร้าง Embed พร้อม QR Code
                    CashTopup = int(selected_price) * int(self.TOPUP_MULTIPLY)

                    des = f"🔹 **คุณ {interaction.user.mention}**\n"
                    des += f"👻 ไอดีที่จะเติม: {user_id}\n"
                    des += f"💸 จำนวนเงินที่ต้องเติม: {amount} บาท\n"
                    des += f"🧈 แคสที่จะได้: {CashTopup} Cash\n"
                    des += f"🗡️ ชื่อบัญชี: {self.TMP_PROMMPAY_NAME}\n"
                    des += f"🏛️ เลขที่บัญชี: {self.TMP_PROMMPAY_NO}\n"

                    embed = discord.Embed(
                        title="✅ เลือกจำนวนเงินแล้ว!",
                        description=des,
                        color=discord.Color.green()
                    )
                    expired = datetime.now() + timedelta(seconds=time_out)

                    formatted_time = expired.strftime("%Y/%m/%d %H:%M:%S")
                    footer_time = f'📌 สแกน QR เพื่อจ่ายเงิน\n🕓 หมดอายุตอน: {formatted_time}\n'

                    embed.set_footer(text= (footer_time + footer) )

                    # ใส่รูปภาพใน Embed โดยใช้ discord.File
                    image_file = discord.File(image_bytes, filename="image.png")
                    embed.set_image(url="attachment://image.png")

                    # 🔴 ปุ่มปิดห้อง
                    confirm_button = Button(label="ตกลง", style=discord.ButtonStyle.primary)

                    async def confirm_button_callback(confirm_interaction):
                        # print("wait api confirm")
                        confirm_url = f'{self.TMP_API_ENDPOINT}?username={self.TMP_API_USERNAME}&password={self.TMP_API_PASSWORD}'
                        confirm_url += f'&con_id={self.TMP_API_CONID}&method=confirm&id_pay={getqr_data["id_pay"]}'
                        confirm_url += f'&accode={self.TMP_BANK_ACCODE}&account_no={self.TMP_BANK_ACCOUNT}&ip=45.154.24.43'
                        confirm_data = json.loads(function.myreq.connect_api(confirm_url).text)

                        # print("wait api check status")
                        if confirm_data['status'] != 1:
                            print("error")
                            embed = discord.Embed(
                                title="❌ เกิดข้อผิดพลาด!",
                                description=f"❗⚠️⁴⁰⁴{confirm_data['msg']}",
                                color=discord.Color.red()
                            )
                            embed.set_footer(text=footer)
                            await confirm_interaction.response.send_message(embed=embed, ephemeral=True)  # ✅ แก้ interaction ให้ถูกต้อง
                            return
                        
                        rw_set = 0

                        match int(selected_price):
                            case 50:
                                rw_set=1
                            case 150:
                                rw_set=2
                            case 300:
                                rw_set=3
                            case 500:
                                rw_set=4
                            case 1000:
                                rw_set=5
                            case 1500:
                                rw_set=6
                            case 2000:
                                rw_set=7
                            case _:
                                rw_set=0

                        # CashTopup
                        # int(self.TOPUP_MULTIPLY)

                        query_topup = """
                        DECLARE @ID varchar(50) = ?
                        ,@rw_set INT = ? -- True ID
                        ,@CashADD INT = ? -- Cash

                        -- ไม่ต้องแก้อะไร
                        DECLARE @UserNum int = 0
                                
                        -- คำนวณผลรวมของ Item_Unit และเก็บในตัวแปร
                        DECLARE @sumitem INT
                        SELECT @sumitem = SUM(Item_Unit)
                        FROM CabalLog.dbo.True_Log
                        WHERE True_ID = @rw_set;
                        SELECT @UserNum = UserNum From Account..cabal_auth_table WHERE ID = @ID

                        IF @UserNum != 0
                        BEGIN
                            UPDATE [CabalCash].[dbo].[CashAccount] SET [Cash] = [Cash] + @CashADD WHERE [UserNum] = @UserNum
                        
                            INSERT INTO CabalCash..CashLogNew (ID,CashADD,Reward)
                            VALUES (@ID,@CashADD,0)
                            INSERT INTO CabalCash..CashLogNewPP (ID,CashADD,Reward)
                            VALUES (@ID,@CashADD,0)

                            -- ตรวจสอบว่ามีค่าใน @sumitem หรือไม่
                            IF @sumitem > 0
                            BEGIN
                                -- การวนลูปเพื่อแทรกข้อมูล (หากต้องการแทรกหลายรายการ)
                                DECLARE @Item_ID INT, @Item_Option INT, @Item_Duration INT, @Item_Unit INT;

                                DECLARE data_cursor CURSOR FOR
                                SELECT Item_ID, Item_Option, Item_Duration, Item_Unit
                                FROM CabalLog.dbo.True_Log
                                WHERE True_ID = @rw_set;

                                OPEN data_cursor;
                                FETCH NEXT FROM data_cursor INTO @Item_ID, @Item_Option, @Item_Duration, @Item_Unit;

                                WHILE @@FETCH_STATUS = 0
                                BEGIN
                                    -- วนลูปตามจำนวน Item_Unit
                                    DECLARE @i INT = 1;
                                    WHILE @i <= @Item_Unit
                                    BEGIN
                                        -- ทำการแทรกข้อมูลใน up_addmycashitembyitem
                                        EXEC CabalCash.dbo.up_addmycashitembyitem 
                                            @UserNum,  -- ใช้ @UserNum ที่กำหนดไว้
                                            1, 
                                            1, 
                                            @Item_ID, 
                                            @Item_Option, 
                                            @Item_Duration, 
                                            'Promotion Topup With Discord';

                                        SET @i = @i + 1;  -- เพิ่มค่า @i เพื่อลูปต่อไป
                                    END

                                    FETCH NEXT FROM data_cursor INTO @Item_ID, @Item_Option, @Item_Duration, @Item_Unit;
                                END

                                CLOSE data_cursor;
                                DEALLOCATE data_cursor;
                            END
                        END

                        """

                        result_topup = await self.db.execute(query_topup, (user_id,rw_set,CashTopup,))

                        if result_topup != True:
                            if confirm_data['status'] != 1:
                                # print("db error")
                                embed = discord.Embed(
                                    title="❌ เกิดข้อผิดพลาด!",
                                    description=f"❗⚠️⁴⁰⁴ไม่สามารถเชื่อมต่อกับเซิฟเวอร์ได้กรุณาติดต่อแอดมิน",
                                    color=discord.Color.red()
                                )
                                embed.set_footer(text=footer)
                                await confirm_interaction.response.send_message(embed=embed, ephemeral=True)  # ✅ แก้ interaction ให้ถูกต้อง
                                return

                        # print("success")
                        success_des = f"🔹 **คุณ {interaction.user.mention}**\n"
                        success_des += f"👻 ไอดีที่จะเติม: {user_id}\n"
                        success_des += f"💸 จำนวนเงินที่เติม: {amount} บาท\n"
                        success_des += f"🧈 แคสที่ได้: {CashTopup} Cash\n"
                        success_des += f"🎁 ไอจากโปรโมชั่นจะถูกส่งเข้าไปใน Cash Inventory\n"
                        success_des += f"🌟 สามารถปิดห้องนี้ได้เลย\n"
                        embed = discord.Embed(
                            title="✅ เติมเงินสำเร็จ!",
                            description=success_des,
                            color=discord.Color.gold()
                        )
                        embed.set_footer(text=footer)
                        await confirm_interaction.response.send_message(embed=embed, ephemeral=True)  # ✅ ใช้ interaction ที่ถูกต้อง
                            
                    confirm_button.callback = confirm_button_callback

                    confirm_view = View()
                    confirm_view.add_item(confirm_button)

                    # ใช้ followup.send() ส่ง Embed และ QR Code
                    await select_interaction.followup.send(embed=embed, file=image_file, view=confirm_view)

        # ตั้งค่า callback ให้กับ Select
        select.callback = select_callback

        # ใส่ปุ่มลงใน View
        ticket_view = View()
        ticket_view.add_item(select)
        ticket_view.add_item(close_button)

        # ✅ Embed แจ้งในห้องใหม่
        embed = discord.Embed(
            title="✅ ห้องเติมเงินของคุณถูกสร้างแล้ว!",
            description=f"🔹 **คุณ {interaction.user.mention}**\n👻 ไอดีที่จะเติม: {user_id}\n💰 กรุณาเลือกจำนวนเงินที่ต้องการจะเติม",
            color=discord.Color.green()
        )
        embed.set_footer(text=footer)

        await topup_channel.send(embed=embed, view=ticket_view)

        # ✅ Embed แจ้งกลับไปยังผู้ใช้
        embed = discord.Embed(
            title="✅ ห้องเติมเงินของคุณถูกสร้าง!",
            description=f"🔹 ห้องของคุณ: {topup_channel.mention}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)
