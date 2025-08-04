# โค้ดสำหรับไฟล์ list_voices.py

import os
from google.cloud import texttospeech

# ตั้งค่า Credentials ให้เหมือนกับไฟล์อื่น
CREDENTIALS_FILE = "teptubev1-52050d27583e.json"
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = CREDENTIALS_FILE

try:
    # สร้าง client
    client = texttospeech.TextToSpeechClient()

    # ดึงรายชื่อเสียงสำหรับภาษาไทย
    print("--- กำลังดึงรายชื่อเสียงภาษาไทย (th-TH) จาก Google Cloud ---")
    response = client.list_voices(language_code="th-TH")

    # แสดงผล
    print("\n✅ รายชื่อเสียงที่ใช้งานได้จริงในโปรเจกต์ของคุณ:")
    for voice in response.voices:
        gender = texttospeech.SsmlVoiceGender(voice.ssml_gender).name
        print(f'- Name: "{voice.name}", Gender: {gender}')

    print("\n👉 คัดลอกชื่อเสียง (ในเครื่องหมายคำพูด) ไปใช้ในไฟล์ preview_voices.py ของคุณได้เลย")

except Exception as e:
    print(f"!!! เกิดข้อผิดพลาด: {e}")