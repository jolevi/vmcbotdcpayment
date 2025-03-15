import time
import pytz

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