# -*- coding: utf-8 -*-
"""
WAWATUBE-DEMO : Faceless Video Content Generator
เครื่องมือสร้างคอนเทนต์วิดีโอครบวงจร ตั้งแต่คิดไอเดีย เขียนสคริปต์ จนถึงสร้างเสียงพากย์
- ใช้ OpenAI (GPT-4o) สำหรับการสร้างไอเดียและสคริปต์
- ใช้ Google Cloud Text-to-Speech สำหรับการสร้างเสียงพากย์
"""

# --- 1. IMPORTS ---
import os
import re
import io
import streamlit as st
import openai
from dotenv import load_dotenv
from google.cloud import texttospeech
from pydub import AudioSegment
# ตรวจสอบให้แน่ใจว่า final_video_generator.py อยู่ใน directory เดียวกันกับ app.py หรืออยู่ใน path ที่ Python สามารถ import ได้
from final_video_generator import generate_final_video
# หมายเหตุ: ในการใช้ pydub คุณอาจต้องติดตั้ง ffmpeg ในระบบของคุณด้วย
# 1. pip install pydub
# 2. ติดตั้ง ffmpeg (สำหรับ Windows: https://www.gyan.dev/ffmpeg/builds/)

st.set_page_config(page_title="WAWATUBE-DEMO - Video Content Generator", layout="wide")
# --- 2. CONSTANTS ---
VOICE_LIST = [
    # ชาย (MALE)
    ("ชาย 1 (Achird, ฟังสบาย/สุภาพ)", "th-TH-Chirp3-HD-Achird"),
    ("ชาย 2 (Fenrir, จริงจัง/เข้มแข็ง)", "th-TH-Chirp3-HD-Fenrir"),
    ("ชาย 3 (Orus, โมเดิร์น/กระฉับกระเฉง)", "th-TH-Chirp3-HD-Orus"),
    ("ชาย 4 (Zubenelgenubi, นุ่มลึก/อบอุ่น)", "th-TH-Chirp3-HD-Zubenelgenubi"),
    ("ชาย 5 (Umbriel, มั่นใจ/เสียงหนุ่ม)", "th-TH-Chirp3-HD-Umbriel"),

    # หญิง (FEMALE)
    ("หญิง 1 (Achernar, ฟังง่าย/เป็นธรรมชาติ)", "th-TH-Chirp3-HD-Achernar"),
    ("หญิง 2 (Laomedeia, อ่อนโยน/อบอุ่น)", "th-TH-Chirp3-HD-Laomedeia"),
    ("หญิง 3 (Leda, หวาน/นุ่มนวล)", "th-TH-Chirp3-HD-Leda"),
    ("หญิง 4 (Vindemiatrix, สุภาพ/เป็นทางการ)", "th-TH-Chirp3-HD-Vindemiatrix"),
    ("หญิง 5 (Zephyr, สดใส/กระฉับกระเฉง)", "th-TH-Chirp3-HD-Zephyr"),
]

# --- 2.1. VOICE STYLE MAP ---
VOICE_STYLE_MAP = {
    "เรื่องผีไทย & ตำนานลี้ลับ": "ลึกลับ/จริงจัง",
    "ประวัติศาสตร์": "จริงจัง/เป็นทางการ",
    "วิทยาศาสตร์รอบตัว": "ฉลาด/สดใส",
    "การพัฒนาตนเอง": "ให้กำลังใจ/อบอุ่น",
    "เทคโนโลยี AI": "โมเดิร์น/กระฉับกระเฉง",
    "การเงิน-การลงทุน": "จริงจัง",
    "สุขภาพ & ไลฟ์สไตล์": "อ่อนโยน/อบอุ่น",
    "ท่องเที่ยว & ประสบการณ์ชีวิต": "สดใส/เล่าเรื่อง",
    "บันเทิง-ซีรีส์/ดารา": "สนุก/บันเทิง",
    "ข่าว/โซเชียล/เทรนด์ฮิต": "กระชับ/เข้มข้น",
    "How-To / เคล็ดลับ / DIY": "สอน/เข้าใจง่าย",
    "ธรรมชาติ/สัตว์โลก": "ผ่อนคลาย/อบอุ่น"
}
def get_voice_style_by_topic(topic):
    return VOICE_STYLE_MAP.get(topic, "ปกติ")

# --- 3. CLIENT INITIALIZATION ---
def initialize_clients():
    """
    โหลดค่าจาก .env และสร้าง client สำหรับ OpenAI และ Google Cloud TTS
    คืนค่าเป็น (openai_client, gcp_tts_client)
    """
    load_dotenv()

    openai_client = None
    gcp_tts_client = None

    # ตั้งค่า OpenAI Client
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY is not set in .env file.")
        openai_client = openai.OpenAI(api_key=api_key)
        st.session_state.openai_client = openai_client # Store in session state
    except ValueError as e:
        st.error(f"เกิดข้อผิดพลาดในการตั้งค่า OpenAI: {e}")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดที่ไม่คาดคิดในการตั้งค่า OpenAI: {e}")

    # ตั้งค่า Google Cloud TTS Client
    try:
        credentials_path = "teptubev1-52050d27583e.json"
        if not os.path.exists(credentials_path):
             raise FileNotFoundError(f"ไม่พบไฟล์ credentials \'{credentials_path}\'")
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = credentials_path
        gcp_tts_client = texttospeech.TextToSpeechClient()
        st.session_state.gcp_tts_client = gcp_tts_client # Store in session state
    except FileNotFoundError as e:
        st.error(f"เกิดข้อผิดพลาดในการตั้งค่า Google Cloud TTS: {e}")
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดที่ไม่คาดคิดในการตั้งค่า Google Cloud TTS: {e}")

    return openai_client, gcp_tts_client


# --- 4. HELPER FUNCTIONS (Text Processing) ---
def clean_script_for_tts(text):
    """ทำความสะอาดสคริปต์ก่อนส่งไปสร้างเสียง (เวอร์ชันปรับปรุง)"""
    text = re.sub(r'\[.*?\]', '', text)
    text = re.sub(r"^(เสียงบรรยาย:|เปิดเรื่อง:)\s*", "", text, flags=re.MULTILINE)
    return text.strip()

def split_text_for_tts(text, max_sentence_len=25):
    import re
    # ตัดด้วย . ! ? หรือ ขึ้นบรรทัดใหม่
    sentences = re.split(r'([.!?]|[\n])', text)
    sentences = [
        (sentences[i] + sentences[i+1]).strip()
        for i in range(0, len(sentences)-1, 2)
    ]
    results = []
    for s in sentences:
        if len(s.split()) > max_sentence_len:
            chunks = re.split(r'(,|;|และ|แต่)', s)
            part = ''
            for c in chunks:
                if len((part + c).split()) > max_sentence_len:
                    results.append(part.strip())
                    part = c
                else:
                    part += c
            if part.strip():
                results.append(part.strip())
        else:
            results.append(s)
    return [x for x in results if x.strip()]

def split_script_for_image(script_text):
    # แบ่งสคริปต์ตาม 'ย่อหน้า' (แยกที่มีเว้นบรรทัดเปล่า)
    import re
    paras = re.split(r'\n\s*\n', script_text.strip())
    # ลบช่องว่าง, ลบย่อหน้าว่าง
    return [p.strip() for p in paras if p.strip()]

# --- 5. API FUNCTIONS (Interacting with OpenAI) ---
def gen_idea_list(client, topic):
    """สร้างรายการไอเดียจาก OpenAI (ปรับปรุง Prompt ให้สร้างชื่อคลิปที่น่าสนใจ)"""
    prompt = (
        f"ในฐานะนักสร้างคอนเทนต์ไวรัล, จงสร้าง \"ชื่อคลิป\" ที่สั้นและน่าสนใจสำหรับ Youtube/Tiktok จำนวน 5 ข้อ เกี่ยวกับหัวข้อ: '{topic}'\n\n"
        "กฎที่ต้องปฏิบัติตาม:\n"
        "1. **ต้องเป็นชื่อคลิปเท่านั้น:** ห้ามมีคำอธิบายหรือคำว่า 'สร้างวิดีโอเกี่ยวกับ...'\n"
        "2. **สั้นและกระตุ้นความสงสัย:** ไม่เกิน 15 คำ ทำให้คนเห็นแล้วต้องอยากรู้ต่อทันที\n"
        "3. **ใช้ภาษาที่น่าดึงดูด:** เช่น 'ความจริงของ...', 'สิ่งที่ไม่มีใครเคยบอกคุณเกี่ยวกับ...', 'ทำไม...ถึงผิด'\n"
        "4. **แสดงผลลัพธ์เป็นรายการที่มีหมายเลขกำกับเท่านั้น** (เช่น 1. ชื่อคลิป 2. ชื่อคลิป ...)"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=800,
            temperature=0.85,
        )
        ideas_text = response.choices[0].message.content.strip()
        ideas = re.findall(r'^\d+\.\s*(.*)', ideas_text, re.MULTILINE)
        if not ideas:
            ideas = re.findall(r'^\s*-\s*(.*)', ideas_text, re.MULTILINE)
        return [idea.strip().strip('"\'') for idea in ideas if idea.strip()]
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการสร้างไอเดีย: {e}")
        return []

def gen_script(client, topic, idea, length):
    """สร้างสคริปต์วิดีโอจาก OpenAI (ปรับปรุง Hook ให้ทรงพลังขึ้น)"""
    prompt = (
        f"ในฐานะนักเล่าเรื่องแนวลึกลับสำหรับ Youtube/Tiktok, จงเขียนสคริปต์สำหรับวิดีโอความยาวประมาณ {length} วินาที\n"
        f"หัวข้อหลัก: {topic}\n"
        f"ชื่อคลิป (สิ่งที่ต้องเล่า): {idea}\n\n"
        "กฎที่ต้องปฏิบัติตามอย่างเคร่งครัด:\n\n"
        "1. **การเปิดเรื่อง (Hook):** ต้องขึ้นต้นด้วยประโยคที่ทรงพลัง น่าตกใจ หรือขัดแย้งกับความเชื่อทันที **ห้าม**ทักทายหรือแนะนำตัวเด็ดขาด (เช่น 'สวัสดีครับ', 'วันนี้จะมาเล่า')\n"
        "2. **ภาษา:** ใช้ภาษาพูดที่เป็นธรรมชาติเหมือนเล่าให้เพื่อนฟัง ไม่ใช่ภาษาเขียน\n"
        "3. **โครงสร้าง:** ไม่ต้องมีหัวข้อ ไม่ต้องมีสัญลักษณ์ (*, -) ไม่ต้องมีคำบรรยายในวงเล็บ (เช่น (เสียงดัง))\n"
        "4. **การแบ่งย่อหน้า:** นี่คือส่วนที่สำคัญที่สุด! **ให้แบ่งเนื้อหาเป็นย่อหน้าสั้นๆ จำนวน 8-12 ย่อหน้า** โดยเว้นบรรทัดว่างระหว่างกัน แต่ละย่อหน้าจะถูกนำไปสร้างเป็นภาพ 1 ภาพ ดังนั้นต้องสั้นและสื่อถึงภาพที่ชัดเจน\n"
        "5. **การปิดท้าย:** สรุปให้กระชับและทิ้งคำถามปลายเปิดให้คนดูไปคิดต่อ\n\n"
        "--- เริ่มเขียนสคริปต์ด้านล่างนี้ ---"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1500,
            temperature=0.85,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการสร้างสคริปต์: {e}")
        return "เกิดข้อผิดพลาดในการสร้างสคริปต์"

# --- NEW FUNCTION FOR IMAGE PROMPT GENERATION ---
# (This function seems to be duplicated in final_video_generator, but kept here as it was in the original app.py)
def create_image_prompt_from_thai_text(openai_client, thai_text: str) -> str: # เปลี่ยน Optional[str] เป็น str
    """
    รับข้อความภาษาไทยจากสคริปต์ แล้วให้ AI สร้าง prompt ภาษาอังกฤษที่เหมาะสำหรับสร้างภาพ
    โดย AI จะต้องตีความเนื้อหาและสร้าง prompt ที่สื่อความหมายและเห็นภาพได้ชัดเจน
    หากไม่สามารถสร้าง prompt ได้ จะใช้ prompt สำรอง
    """
    if not thai_text:
        print("Error: No Thai text provided to create image prompt.")
        raise ValueError("No Thai text provided to create image prompt.") 

    prompt_for_ai = (
        f"Consider the following Thai text which describes a scene or concept for a video clip:\n\n"
        f"'{thai_text}'\n\n"
        f"Now, create a creative and visually descriptive English prompt suitable for an AI image generator (like Stable Diffusion). "
        f"The prompt should capture the essence of the Thai text, focusing on visual elements, atmosphere, and key details. "
        f"Do not just translate directly. Imagine the scene and describe it vividly. Aim for around 50-100 words.\n\n"
        f"English Image Prompt:"
    )
    
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt_for_ai}],
            max_tokens=150,
            temperature=0.7,
        )
        image_prompt = response.choices[0].message.content.strip()
        
        if image_prompt and len(image_prompt) > 10:
            return image_prompt
        else:
            print(f"Warning: Generated image prompt was too short or empty for Thai text: '{thai_text[:50]}...'. Using default prompt.")
            return "A generic beautiful scene, art by Studio Ghibli, vibrant colors, detailed illustration" # Default prompt
    except Exception as e:
        print(f"Error creating image prompt from Thai text: {e}. Using default prompt.")
        return "A generic beautiful scene, art by Studio Ghibli, vibrant colors, detailed illustration" # Default prompt

# --- NEW FUNCTION: GENERATE SEO CONTENT ---
def generate_seo_content(client, topic, title, script):
    """
    Generate SEO title, description, and keywords for different platforms.
    """
    prompt = (
        f"ในฐานะนักการตลาดคอนเทนต์และผู้เชี่ยวชาญด้าน SEO, โปรดสร้าง Title, Description, และ Keywords สำหรับวิดีโอสั้น (Short Video) ด้านล่างนี้:\n\n"
        f"หัวข้อ: {topic}\n"
        f"ชื่อคลิป: {title}\n"
        f"สคริปต์:\n{script}\n\n"
        "รูปแบบที่ต้องการ:\n\n"
        "--- YouTube SEO ---\n\n"
        "ชื่อคลิป (Title): [ชื่อคลิปที่น่าดึงดูดสำหรับวิดีโอสั้น, ไม่เกิน 60 ตัวอักษร, และใส่ Hashtags ที่เกี่ยวข้อง 3-5 อัน]\n"
        "คำอธิบาย (Description): [คำอธิบายสั้นๆ สำหรับ YouTube Shorts, ไม่เกิน 2-3 ประโยค]\n\n"
        "--- Facebook / TikTok Caption ---\n\n"
        "Facebook Caption: [ข้อความสั้นดึงดูดความสนใจ, กระชับ, และใส่ Hashtags ที่เกี่ยวข้อง 4-5 อัน]\n\n"
        "TikTok Caption: [ข้อความสั้นดึงดูดความสนใจ, กระชับ, ใช้ Hashtags ยอดนิยมที่เกี่ยวข้อง 4-5 อัน]\n"
    )
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1000,
            temperature=0.7,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"เกิดข้อผิดพลาดในการสร้าง SEO Content: {e}")
        return "เกิดข้อผิดพลาดในการสร้าง SEO Content"

# --- 6. CORE APPLICATION LOGIC (Audio Generation) ---
# --- 6. CORE APPLICATION LOGIC (Audio Generation) ---
def create_audio_from_script(gcp_client, script_text, voice_name):
    """
    สร้างไฟล์เสียงจากสคริปต์ (เวอร์ชันแก้ไข: ใช้ SSML เฉพาะเมื่อจำเป็น)
    """
    if not gcp_client:
        st.error("Google TTS client ไม่ได้ถูกตั้งค่าอย่างถูกต้อง")
        return None

    clean_script = clean_script_for_tts(script_text)
    if not clean_script:
        st.warning("ไม่มีข้อความที่สามารถสร้างเสียงได้หลังจากการทำความสะอาดสคริปต์")
        return None
    
    text_chunks = split_text_for_tts(clean_script)
    if not text_chunks:
        st.warning("ไม่สามารถแบ่งข้อความเป็นส่วนๆ ที่เหมาะสมได้")
        return None
        
    audio_chunks = []
    progress_bar = st.progress(0, text="กำลังสร้างเสียง...")

    # --- ส่วนที่แก้ไข ---
    # 1. สร้าง Dictionary สำหรับคำที่ต้องการแก้ไขการออกเสียง
    # ทำให้ง่ายต่อการเพิ่มคำอื่นๆ ในอนาคต
    pronunciation_fixes = {
        "หลอน": "ล๋อน"
        # สามารถเพิ่มคำอื่นๆ ที่มีปัญหาได้ที่นี่ เช่น "อนุญาต": "อะนุยาด"
    }
    # --------------------

    for i, chunk in enumerate(text_chunks):
        try:
            # --- ส่วนที่แก้ไข: เพิ่ม Logic ตรวจสอบก่อนส่ง ---
            use_ssml = False
            processed_text = chunk

            # ตรวจสอบว่ามีคำที่ต้องแก้ไขใน chunk นี้หรือไม่
            for word, alias in pronunciation_fixes.items():
                if word in processed_text:
                    processed_text = processed_text.replace(word, f'<sub alias="{alias}">{word}</sub>')
                    use_ssml = True # ถ้าเจอ ให้ตั้งค่าเป็น True

            # ถ้าต้องใช้ SSML (เพราะมีการแทนที่คำ)
            if use_ssml:
                ssml_payload = f"<speak>{processed_text}</speak>"
                synthesis_input = texttospeech.SynthesisInput(ssml=ssml_payload)
                debug_info = ssml_payload
            # ถ้าไม่ต้องใช้ SSML (เป็นประโยคปกติ)
            else:
                synthesis_input = texttospeech.SynthesisInput(text=chunk)
                debug_info = chunk
            # ----------------------------------------------------

            voice = texttospeech.VoiceSelectionParams(language_code="th-TH", name=voice_name)
            audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
            
            response = gcp_client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )
            audio_chunks.append(response.audio_content)
            progress_bar.progress((i + 1) / len(text_chunks), text=f"กำลังสร้างเสียงส่วนที่ {i+1}/{len(text_chunks)}")

        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการสร้างเสียงส่วนที่ {i+1}: {e}")
            st.info("ข้อความในส่วน (chunk) ที่ทำให้เกิดข้อผิดพลาด:")
            st.code(debug_info, language='text') # แสดงข้อมูลที่ส่งไปตอนเกิดปัญหา
            progress_bar.empty()
            return None

    progress_bar.empty()

    if not audio_chunks:
        return None

    # การรวมไฟล์เสียงยังคงเหมือนเดิม
    if len(audio_chunks) == 1:
        return audio_chunks[0]
    else:
        try:
            with st.spinner("กำลังรวมไฟล์เสียง..."):
                final_audio = AudioSegment.empty()
                for mp3_bytes in audio_chunks:
                    segment = AudioSegment.from_file(io.BytesIO(mp3_bytes), format="mp3")
                    final_audio += segment
                
                output_buffer = io.BytesIO()
                final_audio.export(output_buffer, format="mp3")
                return output_buffer.getvalue()
        except Exception as e:
            st.error(f"เกิดข้อผิดพลาดในการรวมไฟล์เสียง: {e}. โปรดตรวจสอบว่าคุณได้ติดตั้ง ffmpeg เรียบร้อยแล้ว")
            return None

# --- 7. STREAMLIT UI COMPONENTS ---
def render_left_column(openai_client):
    """แสดงผล UI ในคอลัมน์ด้านซ้าย (ขั้นตอนที่ 1 และ 2)"""
    st.subheader("ขั้นตอนที่ 1: เลือกหัวข้อและไอเดีย")
    topic_options = ["เรื่องผีไทย & ตำนานลี้ลับ", "ประวัติศาสตร์", "วิทยาศาสตร์รอบตัว", "การพัฒนาตนเอง", "เทคโนโลยี AI", "การเงิน-การลงทุน", "สุขภาพ & ไลฟ์สไตล์", "ท่องเที่ยว & ประสบการณ์ชีวิต", "บันเทิง-ซีรีส์/ดารา", "ข่าว/โซเชียล/เทรนด์ฮิต", "How-To / เคล็ดลับ / DIY", "ธรรมชาติ/สัตว์โลก", "หัวข้อ (คิดเอง)"]
    topic = st.selectbox("เลือกหมวดหมู่หลัก", topic_options, key="topic_select")
    
    custom_topic = ""
    if topic == "หัวข้อ (คิดเอง)":
        custom_topic = st.text_input("พิมพ์หัวข้อที่คุณสนใจ:", placeholder="เช่น 'ปรากฏการณ์เดจาวู'", key="custom_topic_input")
    
    st.session_state.topic_final = custom_topic if topic == "หัวข้อ (คิดเอง)" and custom_topic else topic

    if st.button("🧠 สุ่ม 5 ไอเดียจากหัวข้อนี้", use_container_width=True):
        if not st.session_state.topic_final:
            st.warning("กรุณาเลือกหรือพิมพ์หัวข้อก่อน")
        else:
            with st.spinner("กำลังระดมสมอง..."):
                if st.session_state.get("openai_client"):
                    st.session_state.idea_list = gen_idea_list(st.session_state.openai_client, st.session_state.topic_final)
                    st.session_state.selected_idea = ""
                    st.session_state.script = None
                    st.session_state.audio_bytes = None
                else:
                    st.error("OpenAI client ไม่พร้อมใช้งาน กรุณาตรวจสอบการตั้งค่า")

    if 'idea_list' in st.session_state and st.session_state.idea_list:
        st.session_state.selected_idea = st.radio(
            "เลือกไอเดียที่ต้องการ:",
            st.session_state.idea_list,
            index=None,
            key="idea_radio"
        )

    st.subheader("ขั้นตอนที่ 2: สร้างสคริปต์")
    length_options = {"30 วินาที (สั้น)": 30, "60 วินาที (มาตรฐาน)": 60, "90 วินาที (ยาว)": 90}
    length_choice = st.selectbox(
        "เลือกความยาววิดีโอโดยประมาณ",
        length_options.keys(),
        key="length_select"
    )
    
    script_gen_disabled = not st.session_state.get("selected_idea")
    if st.button("✍️ สร้างสคริปต์วิดีโอ", type="primary", use_container_width=True, disabled=script_gen_disabled):
        with st.spinner("กำลังเขียนสคริปต์... กรุณารอสักครู่"):
            if st.session_state.get("openai_client"):
                script = gen_script(
                    st.session_state.openai_client,
                    st.session_state.topic_final,
                    st.session_state.selected_idea,
                    length_options[length_choice]
                )
                st.session_state.script = script
                st.session_state.audio_bytes = None
            else:
                st.error("OpenAI client ไม่พร้อมใช้งาน กรุณาตรวจสอบการตั้งค่า")

def render_right_column(gcp_tts_client):
    """แสดงผล UI ในคอลัมน์ด้านขวา (ขั้นตอนที่ 3)"""
    st.subheader("📝 สคริปต์และเสียงพากย์")

    if 'script' not in st.session_state or not st.session_state.script:
        st.info("ผลลัพธ์ของสคริปต์และเสียงพากย์จะแสดงที่นี่")
        return

    st.success("สร้างสคริปต์เสร็จแล้ว! คุณสามารถแก้ไขข้อความด้านล่างได้")
    
    edited_script = st.text_area(
        "แก้ไขสคริปต์:",
        value=st.session_state.script,
        height=300,
        key="script_editor"
    )
    st.session_state.script = edited_script # Update script in session state

    st.markdown("---")
    st.subheader("ขั้นตอนที่ 3: สร้างเสียงพากย์")

    voice_friendly_names = [v[0] for v in VOICE_LIST]
    selected_voice_friendly_name = st.selectbox("เลือกเสียงพากย์:", voice_friendly_names, key="voice_select")
    selected_voice_name = next(v[1] for v in VOICE_LIST if v[0] == selected_voice_friendly_name)

    if st.button("🔊 สร้างและฟังเสียงพากย์", use_container_width=True):
        st.session_state.audio_bytes = None
        if st.session_state.get("gcp_tts_client"):
            audio_data = create_audio_from_script(st.session_state.gcp_tts_client, edited_script, selected_voice_name)
            if audio_data:
                st.session_state.audio_bytes = audio_data

                idea_name = st.session_state.get("selected_idea", "voice")
                safe_idea = re.sub(r'[^A-Za-z0-9ก-๙_]+', '_', idea_name.strip())[:40]

                output_dir = os.path.join(os.getcwd(), "outputmp3")
                os.makedirs(output_dir, exist_ok=True)
                output_path = os.path.join(output_dir, f"{safe_idea}.mp3")

                with open(output_path, "wb") as f:
                    f.write(audio_data)

                st.info(f"💾 บันทึกเสียงไว้ที่: `{output_path}`")
        else:
            st.error("Google TTS client ไม่พร้อมใช้งาน กรุณาตรวจสอบการตั้งค่า")

    if 'audio_bytes' in st.session_state and st.session_state.audio_bytes:
        st.audio(st.session_state.audio_bytes, format="audio/mp3")
        style_desc = get_voice_style_by_topic(st.session_state.topic_final)
        st.markdown(f"**สไตล์เสียงที่แนะนำสำหรับหัวข้อนี้:** `{style_desc}`")

    st.markdown("---")
    st.subheader("ขั้นตอนที่ 4: สร้างวิดีโอ")
    
    video_gen_disabled = ('script' not in st.session_state or not st.session_state.script or
                          'audio_bytes' not in st.session_state or not st.session_state.audio_bytes)

    if st.button("🎬 สร้างวิดีโอ", type="primary", use_container_width=True, disabled=video_gen_disabled):
        if not st.session_state.get("selected_idea"):
            st.warning("กรุณาเลือกไอเดียก่อนสร้างวิดีโอ")
            return

        with st.spinner("กำลังสร้างวิดีโอ... ขั้นตอนนี้อาจใช้เวลาหลายนาที"): 
            if not st.session_state.get("openai_client"):
                st.error("OpenAI client ไม่พร้อมใช้งาน กรุณาตรวจสอบการตั้งค่า")
                return
            if not st.session_state.get("audio_bytes"):
                st.error("ไม่พบข้อมูลเสียง กรุณาสร้างเสียงพากย์ก่อน")
                return
            if not st.session_state.get("script"):
                st.error("ไม่พบสคริปต์ กรุณาสร้างสคริปต์ก่อน")
                return

            try:
                audio_temp_path = os.path.join(os.getcwd(), "temp_audio.mp3")
                with open(audio_temp_path, "wb") as f:
                    f.write(st.session_state.audio_bytes)

                final_video_path = generate_final_video(
                    script_text=st.session_state.script,
                    voice_path=audio_temp_path,
                    topic=st.session_state.topic_final,
                    openai_client=st.session_state.openai_client,    
                    video_title=st.session_state.selected_idea,
                )
                if final_video_path:
                    st.success("สร้างวิดีโอเสร็จสมบูรณ์!")
                    st.session_state.final_video_path = final_video_path   # <<<<<< สำคัญ
                else:
                    st.error("ไม่สามารถสร้างวิดีโอได้. โปรดตรวจสอบข้อผิดพลาดด้านบน.")
            except Exception as e:
                st.error(f"เกิดข้อผิดพลาดในการสร้างวิดีโอ: {e}")
            finally:
                if os.path.exists(audio_temp_path):
                    os.remove(audio_temp_path)

    # <<<< ใส่ตรงนี้! ไม่ว่า user จะกดดาวน์โหลดกี่รอบ ปุ่มกับ preview ก็ยังอยู่
    if 'final_video_path' in st.session_state and os.path.exists(st.session_state['final_video_path']):
        st.video(st.session_state['final_video_path'])
        st.download_button(
            label="ดาวน์โหลดวิดีโอ",
            data=open(st.session_state['final_video_path'], "rb").read(),
            file_name=os.path.basename(st.session_state['final_video_path']),
            mime="video/mp4",
            use_container_width=True
        )

    # --- NEW: Step 5 - SEO Content Generation ---
    st.markdown("---")
    st.subheader("ขั้นตอนที่ 5: สร้างแคปชั่นและ SEO")

    seo_gen_disabled = not (st.session_state.get("script") and st.session_state.get("selected_idea") and st.session_state.get("topic_final"))

    if st.button("สร้างแคปชั่นโพส (YouTube/Facebook/TikTok)", key="seo_button", disabled=seo_gen_disabled, type="secondary", use_container_width=True):
        with st.spinner("กำลังสร้างแคปชั่นและ SEO..."):
            if st.session_state.get("openai_client"):
                seo_content = generate_seo_content(
                    st.session_state.openai_client,
                    st.session_state.topic_final,
                    st.session_state.selected_idea,
                    st.session_state.script
                )
                st.session_state.seo_output = seo_content
            else:
                st.error("OpenAI client ไม่พร้อมใช้งาน")

    if 'seo_output' in st.session_state and st.session_state.seo_output:
        st.markdown("### 📝 ผลลัพธ์ SEO และแคปชั่น")
        st.markdown(st.session_state.seo_output)


# --- 8. MAIN APPLICATION ENTRY POINT ---
def main():
    st.title("WAWATUBE-DEMO")
    st.caption("เครื่องมือสร้างคอนเทนต์วิดีโอครบวงจร ตั้งแต่คิดไอเดีย เขียนสคริปต์ จนถึงสร้างเสียงพากย์")
    
    # --- เพิ่มโค้ดส่วนนี้เพื่อปรับขนาดวิดีโอ ---
    st.markdown("""
    <style>
    video {
        max-width: 30%; /* ปรับขนาดวิดีโอตัวอย่างให้เล็กลง */
        margin: auto;     /* จัดให้อยู่ตรงกลาง */
    }
    </style>
    """, unsafe_allow_html=True)
    # ----------------------------------------

    if 'openai_client' not in st.session_state:
        initialize_clients() # This populates session_state.openai_client and session_state.gcp_tts_client

    openai_client = st.session_state.get("openai_client")
    gcp_tts_client = st.session_state.get("gcp_tts_client")

    if openai_client is None or gcp_tts_client is None:
        st.warning("กรุณาตรวจสอบการตั้งค่า API Keys ในไฟล์ .env และการเชื่อมต่ออินเทอร์เน็ต")
        # st.stop() # Removed stop() to allow initialization error messages to be displayed

    col1, col2 = st.columns([1, 1])

    with col1:
        render_left_column(openai_client)

    with col2:
        render_right_column(gcp_tts_client)


if __name__ == "__main__":
    main()
