import pyodbc
import time

class MSSQLDatabase:
    def __init__(self, ENV_DATA):
        self.driver = ENV_DATA['MSSQL_DRIVER']
        self.server = ENV_DATA['MSSQL_SERVER']
        self.username = ENV_DATA['MSSQL_USERNAME']
        self.password = ENV_DATA['MSSQL_PASSWORD']
        self.conn_str = f"DRIVER={self.driver};SERVER={self.server};UID={self.username};PWD={self.password}"
        self.conn = None
        self.cursor = None

    def connect(self):
        """เชื่อมต่อกับฐานข้อมูล"""
        try:
            self.conn = pyodbc.connect(self.conn_str)
            self.cursor = self.conn.cursor()
            print("✅ Connected to MSSQL successfully!")
            return True
        except pyodbc.Error as e:
            print("❌ Connection Error:", e)
            return False
        
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