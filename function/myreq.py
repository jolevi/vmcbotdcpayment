import requests
import urllib3

# ปิด InsecureRequestWarning ถ้าไม่ใช้การตรวจสอบ SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def connect_api(url):
    response = requests.get(url)

    if response.status_code == 200:
        return response
    else:
        print("Error:", response.status_code)
        return None