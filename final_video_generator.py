import os
import re
from typing import List, Dict, Optional
from pydub import AudioSegment
import moviepy.editor as mpy
from openai import OpenAI
from PIL import Image
import io
import requests
import random
import glob
import time

# --- Paths ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IMAGE_DIR = os.path.join(BASE_DIR, "generated_images")
MUSIC_DIR = os.path.join(BASE_DIR, "music")
OUTPUT_AUDIO_DIR = os.path.join(BASE_DIR, "mixed_audio")
FINAL_VIDEO_DIR = os.path.join(BASE_DIR, "final_videos")

for folder in [IMAGE_DIR, MUSIC_DIR, OUTPUT_AUDIO_DIR, FINAL_VIDEO_DIR]:
    os.makedirs(folder, exist_ok=True)

# --- Config ---
WORDS_PER_SECOND = 2.5
DEFAULT_MUSIC = os.path.join(MUSIC_DIR, "lofi_chill2.mp3")

# --- Map หัวข้อกับโฟลเดอร์ ---
MUSIC_FOLDER_MAP = {
    "เรื่องผีไทย & ตำนานลี้ลับ": "1",
    "ประวัติศาสตร์": "2",
    "วิทยาศาสตร์รอบตัว": "3",
    "การพัฒนาตนเอง": "4",
    "เทคโนโลยี AI": "5",
    "การเงิน-การลงทุน": "6",
    "สุขภาพ & ไลฟ์สไตล์": "7",
    "ท่องเที่ยว & ประสบการณ์ชีวิต": "8",
    "บันเทิง-ซีรีส์/ดารา": "9",
    "ข่าว/โซเชียล/เทรนด์ฮิต": "10",
    "How-To / เคล็ดลับ / DIY": "11",
    "ธรรมชาติ/สัตว์โลก": "12"
    # เพิ่มหมวดใหม่ก็เพิ่ม key กับเลข folder ไปได้เลย
}

def pick_music_by_topic(topic):
    folder = MUSIC_FOLDER_MAP.get(topic)
    if not folder:
        # fallback: ใช้ default music เดิม
        return DEFAULT_MUSIC
    music_dir = os.path.join(MUSIC_DIR, folder)
    mp3_files = glob.glob(os.path.join(music_dir, "*.mp3"))
    if not mp3_files:
        return DEFAULT_MUSIC
    return random.choice(mp3_files)

# --- Image Prompt ---
def create_image_prompt_from_thai_text(openai_client, thai_text: str) -> Optional[str]:
    prompt = (
        f"You are generating a visual scene based on the following Thai text, intended for a cinematic video with a distinct Thai cultural style:\n\n"
        f"'{thai_text}'\n\n"
        f"Create a vivid and imaginative English image generation prompt suitable for AI systems like DALL·E or Stable Diffusion. "
        f"The image should reflect Thai culture, such as traditional Thai houses, Thai clothing, local architecture, ghostly or eerie atmosphere (if applicable), and cinematic lighting. "
        f"Avoid Western settings. Write ~80 words.\n\n"
        f"English Image Prompt:"
    )
    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=150,
            temperature=0.7,
        )
        result = response.choices[0].message.content.strip()
        return result if result and len(result) > 10 else None
    except Exception as e:
        print(f"[Prompt Error] {e}")
        return None

# --- Generate Image ---
def generate_image(prompt: str, index: int, prefix: str) -> Optional[str]:
    if not prompt:
        print(f"⚠️ No prompt for scene {index}")
        return None

    path = os.path.join(IMAGE_DIR, f"{prefix}_scene_{index:03d}_{int(time.time())}.jpg")
    api_url = "https://flux-image-generator.bebiwawa85.workers.dev/"
    payload = {"prompt": prompt, "aspect_ratio": "9:16"}

    try:
        r = requests.post(api_url, json=payload)
        if r.status_code != 200:
            print(f"❌ Scene {index}: API responded with status {r.status_code}")
            return None
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        # crop 9:16 + resize
        target_ratio = 9 / 16
        img_ratio = img.width / img.height
        if img_ratio > target_ratio:
            new_width = int(img.height * target_ratio)
            offset = (img.width - new_width) // 2
            img = img.crop((offset, 0, offset + new_width, img.height))
        else:
            new_height = int(img.width / target_ratio)
            offset = (img.height - new_height) // 2
            img = img.crop((0, offset, img.width, offset + new_height))
        img = img.resize((1080, 1920), Image.LANCZOS)
        img.save(path)
        print(f"[✅] Image saved: {path}")
        return path
    except Exception as e:
        print(f"[Image Error] Scene {index}: {e}")
        return None

# --- Mix Voice with Music ---
def mix_audio(voice_path: str, music_path: str, out_path: Optional[str] = None) -> Optional[str]:
    if not out_path:
        out_path = os.path.join(OUTPUT_AUDIO_DIR, "final_audio.mp3")
    try:
        voice = AudioSegment.from_file(voice_path)
        music = AudioSegment.from_file(music_path) - 15

        # ทำให้ music ยาวกว่า voice 1000ms (1 วินาที)
        pad_ms = 1000
        if len(music) < len(voice) + pad_ms:
            repeat = ((len(voice) + pad_ms) // len(music)) + 1
            music = music * repeat
        music = music[:len(voice) + pad_ms]
        music = music.fade_out(1000)  # fade out ดนตรี 1 วิ ท้าย

        # วาง voice ทับ music (ไม่ fade ใด ๆ กับ voice)
        mixed = music.overlay(voice, position=0)

        # เติม silence อีก 500ms ท้าย (ป้องกันต๊อด)
        mixed = mixed + AudioSegment.silent(duration=500)

        mixed.export(out_path, format="mp3", bitrate="192k")
        return out_path
    except Exception as e:
        print(f"[Mix Error] {e}")
        return None

# --- Ken Burns Motion (Zoom in/out ไม่มีขอบดำ) ---
def ken_burns_motion(img_clip, effect="zoom_in", duration=3.0):
    scale_start = 1.07 if effect == "zoom_out" else 1.00
    scale_end = 1.00 if effect == "zoom_out" else 1.07

    def make_frame(t):
        prog = t / duration
        scale = scale_start + (scale_end - scale_start) * prog
        frame = img_clip.get_frame(0)
        h, w = frame.shape[:2]
        new_w, new_h = int(w * scale), int(h * scale)
        img = mpy.ImageClip(frame).resize((new_w, new_h)).get_frame(0)
        left = (new_w - 1080) // 2
        top = (new_h - 1920) // 2
        cropped = img[top:top+1920, left:left+1080]
        return cropped

    return mpy.VideoClip(make_frame, duration=duration)

# --- Compile Video ---
def compile_video(scene_data: List[Dict], audio_path: str, out_name: str = "final_video.mp4") -> Optional[str]:
    out_path = os.path.join(FINAL_VIDEO_DIR, out_name)
    try:
        audio_clip = mpy.AudioFileClip(audio_path)
    except Exception as e:
        print(f"❌ Failed to load audio: {e}")
        return None

    clips = []
    for i, scene in enumerate(scene_data):
        img_path = scene.get('image_path')
        duration = scene.get('duration', 3.0)
        if not img_path or not os.path.exists(img_path):
            print(f"⚠️ Skipping scene {i+1}, image not found: {img_path}")
            continue
        try:
            img_clip = mpy.ImageClip(img_path, duration=duration).set_position("center")
            effect = random.choice(["zoom_in", "zoom_out"])
            img_clip = ken_burns_motion(img_clip, effect=effect, duration=duration)
            clips.append(img_clip)
            print(f"🖼️ Scene {i+1}: {os.path.basename(img_path)}, {duration:.2f}s, motion: {effect}")
        except Exception as e:
            print(f"❌ Failed to process scene {i+1}: {e}")
            continue

    if not clips:
        print("❌ No valid scenes to compile.")
        return None

    total_scene_duration = sum(c.duration for c in clips)
    if total_scene_duration < audio_clip.duration:
        padding = audio_clip.duration - total_scene_duration
        print(f"⚠️ Padding last clip by {padding:.2f}s")
        clips[-1] = clips[-1].set_duration(clips[-1].duration + padding)

    try:
        final_video_clip = mpy.concatenate_videoclips(clips, method="compose")
        final_video_clip = final_video_clip.set_audio(audio_clip)
        final_video_clip = final_video_clip.set_duration(audio_clip.duration)
        final_video_clip.write_videofile(
            out_path, fps=30, codec="libx264",
            audio_codec="aac", threads=4, preset="medium", logger='bar'
        )
        print(f"✅ Video saved: {out_path}")
        return out_path
    except Exception as e:
        print(f"❌ Error writing final video: {e}")
        return None

def split_script_for_image(script_text):
    import re
    paras = re.split(r'\n\s*\n', script_text.strip())
    return [p.strip() for p in paras if p.strip()]

# ------------------------------
# --- generate_final_video() ---
# ------------------------------
# ------------------------------
# --- generate_final_video() ---
# ------------------------------
def generate_final_video(
    script_text: str,
    voice_path: str,
    topic: str,
    openai_client,
    video_title: str = None,
) -> Optional[str]:
    print("\n🎬 [Start] Video Generation")
    if not os.path.exists(voice_path):
        print("❌ Voice file not found.")
        return None

    # --- ย้ายส่วนนี้มาไว้ข้างบน ---
    # สร้างชื่อไฟล์ที่ปลอดภัย (safe_title) ก่อนที่จะนำไปใช้
    if video_title:
        safe_title = re.sub(r'[^A-Za-z0-9ก-๙_]+', '_', video_title.strip())[:50]
    else:
        # ถ้าไม่มี video_title, ให้ใช้ topic แทน
        safe_title = re.sub(r'[^A-Za-z0-9ก-๙_]+', '_', topic.strip())[:30]
    # --------------------------------

    # -- เลือกเพลงประกอบ (สุ่มจากโฟลเดอร์) --
    music_path = pick_music_by_topic(topic)
    if not os.path.exists(music_path):
        print("⚠️ Music not found, using default.")
        music_path = DEFAULT_MUSIC

    print("🎧 Mixing audio...")
    # สร้างชื่อไฟล์เสียงที่มิกซ์แล้วให้ไม่ซ้ำกัน โดยใช้ safe_title
    mixed_audio_filename = f"mixed_{safe_title}_{int(time.time())}.mp3"
    mixed_audio_path = os.path.join(OUTPUT_AUDIO_DIR, mixed_audio_filename)
    audio_path = mix_audio(voice_path, music_path, out_path=mixed_audio_path)
    
    if not audio_path:
        print("❌ Failed mixing audio.")
        return None

    # -- ดึงความยาวเสียงหลังมิกซ์ (seconds) --
    from pydub.utils import mediainfo
    try:
        audio_info = mediainfo(audio_path)
        audio_duration = float(audio_info['duration'])
    except Exception as e:
        print(f"❌ Error getting audio duration: {e}")
        return None

    # -- ตัด script เป็น 10 ซีนสูงสุด --
    segments = split_script_for_image(script_text)
    if len(segments) > 10:
        step = max(1, len(segments) // 10)
        selected_segments = [segments[i] for i in range(0, len(segments), step)][:10]
    else:
        selected_segments = segments[:10]

    num_scenes = len(selected_segments)
    if num_scenes == 0:
        print("❌ No valid segments.")
        return None

    duration_per_scene = audio_duration / num_scenes

    scene_data = []
    
    # --- ล้างไฟล์รูปเก่าๆ ของ title นี้ก่อนเริ่ม ---
    # เพื่อให้แน่ใจว่าจะไม่ใช้รูปเก่ามาปนกับรูปที่สร้างใหม่
    old_images = glob.glob(os.path.join(IMAGE_DIR, f"{safe_title}_scene_*.jpg"))
    for f in old_images:
        try:
            os.remove(f)
            print(f"🧹 Removed old image: {os.path.basename(f)}")
        except OSError as e:
            print(f"Error removing file {f}: {e}")
    # -----------------------------------------

    for i, seg in enumerate(selected_segments):
        print(f"🖼️ Generating Scene {i+1}/{num_scenes}...")
        prompt = create_image_prompt_from_thai_text(openai_client, seg)
        if not prompt:
            print(f"⚠️ No prompt for scene {i+1}")
            continue
            
        # ตอนนี้ safe_title มีค่าที่ถูกต้องแล้ว
        img_path = generate_image(prompt, i + 1, safe_title) 
        
        if img_path:
            scene_data.append({
                "image_path": img_path,
                "duration": duration_per_scene
            })

    # -- ปรับภาพสุดท้ายให้อยู่จนจบเสียง (กรณี sum(duration) ไม่ตรง) --
    if scene_data:
        total_scene_duration = sum(sc['duration'] for sc in scene_data)
        diff = audio_duration - total_scene_duration
        if abs(diff) > 0.05:
            scene_data[-1]['duration'] += diff

    if not scene_data:
        print("❌ No images generated.")
        return None

    print("📦 Compiling video...")
    # safe_title ถูกสร้างไว้ข้างบนแล้ว
    filename = f"WAWATUBE_Vid_{safe_title}_{len(scene_data)}scenes.mp4"
    video_path = compile_video(scene_data, audio_path, filename)

    if video_path:
        print(f"\n✅ Video generated: {video_path}")
    return video_path