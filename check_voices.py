import os
from pydub import AudioSegment
from pydub.utils import mediainfo

AUDIO_DIR = "music"  # หรือใส่ path โฟลเดอร์ที่มีเสียงของคุณ
SUPPORTED_EXTENSIONS = (".mp3", ".wav", ".ogg", ".flac", ".m4a")

def list_audio_files(folder: str) -> list[str]:
    """
    แสดงรายการไฟล์เสียงทั้งหมดในโฟลเดอร์ที่กำหนด

    Args:
        folder: พาธไปยังโฟลเดอร์ที่มีไฟล์เสียง

    Returns:
        รายการชื่อไฟล์เสียง (string)
    """
    if not os.path.isdir(folder):
        print(f"Error: โฟลเดอร์ '{folder}' ไม่ถูกต้องหรือไม่สามารถเข้าถึงได้")
        return []

    audio_files = []
    try:
        for filename in os.listdir(folder):
            if filename.lower().endswith(SUPPORTED_EXTENSIONS):
                audio_files.append(filename)
    except OSError as e:
        print(f"Error: ไม่สามารถอ่านไฟล์ในโฟลเดอร์ '{folder}': {e}")
    return audio_files

def get_audio_info(filepath: str) -> dict:
    """
    ดึงข้อมูลรายละเอียดของไฟล์เสียง

    Args:
        filepath: พาธเต็มไปยังไฟล์เสียง

    Returns:
        Dictionary ที่มีข้อมูลไฟล์เสียง หรือ None หากมีข้อผิดพลาด
    """
    if not os.path.isfile(filepath):
        print(f"Error: ไฟล์ '{os.path.basename(filepath)}' ไม่ถูกต้องหรือไม่สามารถเข้าถึงได้")
        return None

    try:
        # ใช้ mediainfo เพื่อดึงข้อมูลพื้นฐาน
        info = mediainfo(filepath)
        duration_sec = float(info.get('duration', 0))
        bitrate = info.get('bit_rate', 'unknown')

        # ใช้ pydub เพื่อดึงข้อมูลเชิงลึกและตรวจสอบความถูกต้อง
        audio = AudioSegment.from_file(filepath)
        channels = audio.channels
        sample_rate = audio.frame_rate

        return {
            "filename": os.path.basename(filepath),
            "duration_sec": round(duration_sec, 2),
            "bitrate": bitrate,
            "channels": channels,
            "sample_rate": sample_rate,
        }
    except FileNotFoundError:
        print(f"Error: ไม่พบไฟล์ '{os.path.basename(filepath)}'")
        return None
    except Exception as e:
        print(f"Error: ไม่สามารถประมวลผลไฟล์ '{os.path.basename(filepath)}': {e}")
        return None

if __name__ == "__main__":
    print(f"กำลังค้นหาไฟล์เสียงในโฟลเดอร์: '{AUDIO_DIR}'")
    audio_files = list_audio_files(AUDIO_DIR)

    if not audio_files:
        print("ไม่พบไฟล์เสียงที่รองรับในโฟลเดอร์ที่กำหนด")
    else:
        print(f"\nพบไฟล์เสียง {len(audio_files)} ไฟล์:\n")
        for filename in audio_files:
            filepath = os.path.join(AUDIO_DIR, filename)
            audio_info = get_audio_info(filepath)

            if audio_info:
                print(
                    f"{audio_info['filename']} | "
                    f"Duration: {audio_info['duration_sec']}s | "
                    f"Bitrate: {audio_info['bitrate']} | "
                    f"Channels: {audio_info['channels']} | "
                    f"Sample Rate: {audio_info['sample_rate']}Hz"
                )
            else:
                print(f"{filename} - ไม่สามารถดึงข้อมูลได้")