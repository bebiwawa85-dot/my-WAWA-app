import requests

# 1. กำหนด prompt ภาษาอังกฤษ (API นี้น่าจะรับแค่ ENG)
prompt = "a magical forest at night, glowing plants, cinematic lighting"

# 2. URL ของ API ที่คุณให้มา
url = "https://flux-image-generator.bebiwawa85.workers.dev/"

# 3. ส่ง request ไปยัง API
response = requests.post(url, json={"prompt": prompt})

# 4. ตรวจสอบว่าระบบส่งกลับภาพ (status 200)
if response.status_code == 200:
    with open("test_output.png", "wb") as f:
        f.write(response.content)
    print("✅ Image saved: test_output.png")
else:
    print(f"❌ Error: {response.status_code} - {response.text}")
