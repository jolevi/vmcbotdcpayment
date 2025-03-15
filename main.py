from myserver import server_on
import discord
from discord.ui import View, Button, Modal, TextInput, Select
from discord import SelectOption
from datetime import datetime, timedelta
from discord.ext import commands
from io import BytesIO
import base64
import json
import os
import time
import pytz
import requests
import urllib3
import pyodbc

# ตั้งค่า env
ENV_DATA = {
    'TOKEN': os.getenv("TOKEN"),
    'TMP_API_ENDPOINT': os.getenv("TMP_API_ENDPOINT"),
    'TMP_API_USERNAME': os.getenv("TMP_API_USERNAME"),
    'TMP_API_PASSWORD': os.getenv("TMP_API_PASSWORD"),
    'TMP_API_CONID': os.getenv("TMP_API_CONID"),
    'TMP_BANK_ACCODE': os.getenv("TMP_BANK_ACCODE"),
    'TMP_BANK_ACCOUNT': os.getenv("TMP_BANK_ACCOUNT"),
    'TMP_PROMMPAY_NO': os.getenv("TMP_PROMMPAY_NO"),
    'TMP_PROMMPAY_TYPE': os.getenv("TMP_PROMMPAY_TYPE"),
    'TMP_PROMMPAY_NAME': os.getenv("TMP_PROMMPAY_NAME"),
    'TOPUP_MULTIPLY': os.getenv("TOPUP_MULTIPLY"),
    'MSSQL_DRIVER': os.getenv("MSSQL_DRIVER"),
    'MSSQL_SERVER': os.getenv("MSSQL_SERVER"),
    'MSSQL_USERNAME': os.getenv("MSSQL_USERNAME"),
    'MSSQL_PASSWORD': os.getenv("MSSQL_PASSWORD")
}

# ปิด InsecureRequestWarning ถ้าไม่ใช้การตรวจสอบ SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def verify_ip():
    urlip = url = "https://api.ipify.org?format=json"  # Only IPv4
    response = requests.get(urlip)

    if response.status_code == 200:
        ip_address = response.json().get("ip")
        print("Your Public IPv4 Address:", ip_address)

        url = f"https://oreocb.online/oreoAPI/vrfvmc.php?vmc=verymaocodein&mode=2&ip={ip_address}"

        response = requests.get(url)  # Use json=data for JSON payload

        print("Status Code:", response.status_code)
        print("Response Body:", response.text)

    else:
        print("Failed to get IP address:", response.status_code)

def connect_api(url):
    response = requests.get(url)

    if response.status_code == 200:
        return response
    else:
        print("Error:", response.status_code)
        return None
    
async def save_chat_logs(channel, user, path):
    """บันทึกข้อความในห้องลงไฟล์ text ก่อนปิดห้อง"""
    # ดึงข้อความย้อนหลังจากช่อง
    messages = [message async for message in channel.history(limit=1000)]  # ดึงข้อความย้อนหลัง (สูงสุด 1000 ข้อความ)

    # แปลงเวลาเป็น UTC+7
    for message in messages:
        # รับเวลาจาก message ในรูปแบบ UTC
        utc_time = message.created_at.replace(tzinfo=pytz.utc)  # คอนเวิร์ตเวลาเป็น UTC
        # แปลงเวลาจาก UTC เป็น UTC+7
        local_time = utc_time.astimezone(pytz.timezone('Asia/Bangkok'))

        # ใช้ตัวแปรแยกเพื่อเก็บเวลาในรูปแบบที่ต้องการ
        message_time = local_time.strftime('%Y-%m-%d %H:%M:%S')  # เก็บเวลาที่แปลงแล้ว

    messages.reverse()  # ให้เรียงจากข้อความเก่ามาก่อน

    log_filename = f"{path}{channel.name}_{int(time.time())}.txt"

    with open(log_filename, "w", encoding="utf-8") as log_file:
        log_file.write(f"Chat log from {channel.name} (closed by {user.name}):\n")
        log_file.write("=" * 50 + "\n")

        for msg in messages:
            # ใช้ message_time ที่เก็บเวลาที่แปลงแล้ว
            log_file.write(f"[{message_time}] {msg.author}: {msg.content}\n")
            
    print(f"✅ Chat logs saved to {log_filename}")

class MSSQLDatabase:
    def __init__(self, ENV_DATA):
        self.driver = ENV_DATA['MSSQL_DRIVER']
        self.server = ENV_DATA['MSSQL_SERVER']
        self.username = ENV_DATA['MSSQL_USERNAME']
        self.password = ENV_DATA['MSSQL_PASSWORD']
        self.conn_str = f"DRIVER={self.driver};SERVER={self.server};UID={self.username};PWD={self.password}"
        self.conn = None
        self.cursor = None
        self.myconnect = False

    def connect(self):
        """เชื่อมต่อกับฐานข้อมูล"""
        while not self.myconnect:
            try:
                self.conn = pyodbc.connect(self.conn_str)
                self.cursor = self.conn.cursor()
                print("✅ Connected to MSSQL successfully!")
                return True
            except pyodbc.Error as e:
                verify_ip()
                print("❌ Connection Error:", e)
                # return False
            time.sleep(.5)
        
    async def execute(self, query, params=()):
        """รันคำสั่ง SQL (INSERT, UPDATE, DELETE)"""
        if not self.cursor:
            print("❌ Error: No database connection")
            return False

        try:
            self.cursor.execute(query, params)
            self.conn.commit()
            print("✅ Query executed successfully")
            return True
        except pyodbc.Error as e:
            print("❌ Query Error:", e)
            self.conn.rollback()
            return False

    async def fetch_all_with_cache(self, query, params=()):
        """ดึงข้อมูลจากฐานข้อมูลแบบใช้แคช"""
        if not self.cursor:
            print("❌ Error: No database connection")
            return []

        current_time = time.time()

        # ตรวจสอบแคช
        if query not in self.cache:
            self.cache[query] = {}

        if params in self.cache[query]:
            cached_data = self.cache[query][params]
            if current_time - cached_data['timestamp'] < self.cache_expiry_time:
                print("✅ Returning data from cache")
                return cached_data['data']
            else:
                print("🔄 Cache expired, querying database...")

        # ถ้าไม่มีแคชหรือแคชหมดอายุ
        try:
            self.cursor.execute(query, params)
            columns = [column[0] for column in self.cursor.description]
            result = [dict(zip(columns, row)) for row in self.cursor.fetchall()]

            # เก็บข้อมูลลงแคช
            self.cache[query][params] = {'data': result, 'timestamp': current_time}
            print("✅ Data fetched from database and cached.")
            return result
        except pyodbc.Error as e:
            print("❌ Query Error:", e)
            return []
         
    async def fetch_all(self, query, params=()):
        """ดึงข้อมูลจากฐานข้อมูลโดยไม่มีแคช"""
        if not self.cursor:
            print("❌ Error: No database connection")
            return []

        try:
            self.cursor.execute(query, params)
            columns = [column[0] for column in self.cursor.description]
            return [dict(zip(columns, row)) for row in self.cursor.fetchall()]
        except pyodbc.Error as e:
            print("❌ Query Error:", e)
            return []
        
    async def fetch_one(self, query, params=()):
        """ดึงข้อมูล 1 row จาก MSSQL"""
        if not self.cursor:
            print("❌ Error: No database connection")
            return None

        try:
            self.cursor.execute(query, params)
            row = self.cursor.fetchone()
            if row:
                columns = [column[0] for column in self.cursor.description]
                return dict(zip(columns, row))
            return None
        except pyodbc.Error as e:
            print("❌ Query Error:", e)
            return None
        
    def close(self):
        """ปิดการเชื่อมต่อ"""
        try:
            if self.cursor:
                self.cursor.close()
            if self.conn:
                self.conn.close()
            print("🔌 Connection closed")
        except Exception as e:
            print("❌ Error while closing connection:", e)

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
                    await save_chat_logs(close_interaction.channel, interaction.user, 'log/topup/')

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
            getidpay_data = json.loads(connect_api(getidpay_url).text)

            if getidpay_data['status'] == 1:
                id_pay = getidpay_data['id_pay']
                getqr_url = f'{self.TMP_API_ENDPOINT}?username={self.TMP_API_USERNAME}&password={self.TMP_API_PASSWORD}&con_id={self.TMP_API_CONID}&id_pay={id_pay}'
                getqr_url += f'&type={self.TMP_PROMMPAY_TYPE}&promptpay_id={self.TMP_PROMMPAY_NO}&method=detail_pay'
                getqr_data = json.loads(connect_api(getqr_url).text)

                if getqr_data['status'] == 1:
                    if getqr_data['time_out'] < 0:
                        cancel_url = f'{self.TMP_API_ENDPOINT}?username={self.TMP_API_USERNAME}&password={self.TMP_API_PASSWORD}&con_id={self.TMP_API_CONID}'
                        cancel_url += f'&method=cancel&id_pay={id_pay}'
                        connect_api(cancel_url)
                        
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
                        confirm_data = json.loads(connect_api(confirm_url).text)

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

class DiscordBot:
    def __init__(self, ENV_DATA, intents=None, log=False):

        if intents is None:
            intents = discord.Intents.default()
            intents.messages = True
            intents.message_content = True

        self.bot = commands.Bot(command_prefix="!", intents=intents)
        
        # เก็บค่าตัวแปรลงใน bot
        self.bot.db = MSSQLDatabase(ENV_DATA)
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
        modal = TopupIDModal(ENV_DATA, db, log)
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

server_on()

bot = DiscordBot(ENV_DATA)
bot.run()  # เรียกใช้งานบอท
