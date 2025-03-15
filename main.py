from myserver import server_on
from function.mydiscord import DiscordBot
import os

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

server_on()

bot = DiscordBot(ENV_DATA)
bot.run()  # เรียกใช้งานบอท