import os
import datetime
from telethon import TelegramClient
from telethon.sessions import StringSession
from dotenv import load_dotenv

load_dotenv()

# Telegram Credentials
api_id = os.getenv("TELEGRAM_API_ID")
api_hash = os.getenv("TELEGRAM_API_HASH")
session_string = os.getenv("TELEGRAM_SESSION_STRING")

# Mock data untuk keperluan pengujian dan fallback gratis tanpa setup API
MOCK_MESSAGES = [
    # Cluster 1: Rupiah / Baseline Cherry-picking
    {"id": 1, "text": "Rupiah sekarang menguat ke 17.777, prestasi luar biasa pemerintah baru!", "date": datetime.datetime.now() - datetime.timedelta(minutes=5), "sender_id": 101},
    {"id": 2, "text": "Luar biasa rupiah menguat ke 17.777 di era baru ini.", "date": datetime.datetime.now() - datetime.timedelta(minutes=10), "sender_id": 102},
    {"id": 3, "text": "Hebat! Di era baru ini rupiah tembus menguat ke 17.777.", "date": datetime.datetime.now() - datetime.timedelta(minutes=12), "sender_id": 103},
    {"id": 4, "text": "Jangan bandingkan dengan yang dulu, sekarang rupiah sudah menguat ke 17.777.", "date": datetime.datetime.now() - datetime.timedelta(minutes=15), "sender_id": 104},
    {"id": 5, "text": "Alhamdulillah, rupiah menguat ke 17.777 berkat kerja keras kabinet.", "date": datetime.datetime.now() - datetime.timedelta(minutes=20), "sender_id": 105},
    
    # Cluster 2: Bensin / Ad hominem & missed point
    {"id": 6, "text": "Orang kaya kok masih ngeluh bensin naik, mikir dong!", "date": datetime.datetime.now() - datetime.timedelta(minutes=25), "sender_id": 106},
    {"id": 7, "text": "Masa orang kaya ngeluh bensin naik? Aneh banget.", "date": datetime.datetime.now() - datetime.timedelta(minutes=30), "sender_id": 107},
    {"id": 8, "text": "Bensin naik kok dikeluhkan orang kaya? Harusnya bersyukur.", "date": datetime.datetime.now() - datetime.timedelta(minutes=33), "sender_id": 108},
    
    # Cluster 3: False Comparison
    {"id": 9, "text": "Negara kita masih jauh lebih baik ekonominya dibanding Sri Lanka atau Venezuela.", "date": datetime.datetime.now() - datetime.timedelta(minutes=40), "sender_id": 109},
    {"id": 10, "text": "Ekonomi Indonesia masih stabil dibanding Yunani atau Sri Lanka, patut disyukuri.", "date": datetime.datetime.now() - datetime.timedelta(minutes=45), "sender_id": 110},
    
    # Pesan Organik/Normal
    {"id": 11, "text": "Makan siang apa hari ini guys?", "date": datetime.datetime.now() - datetime.timedelta(minutes=50), "sender_id": 201},
    {"id": 12, "text": "Menurut saya inflasi memang berdampak ke semua kelas, ga cuma yang miskin tapi menengah juga kejepit.", "date": datetime.datetime.now() - datetime.timedelta(minutes=55), "sender_id": 202},
]

async def scrape_public_group(group_username: str, limit: int = 50) -> list[dict]:
    """
    Mengambil pesan dari public group/channel Telegram secara on-demand.
    Jika kredensial Telegram tidak diset, fungsi ini akan otomatis fallback ke data simulasi (mock)
    agar aplikasi langsung bisa dicoba tanpa konfigurasi API Telegram.
    """
    # Bersihkan username dari karakter @ dan URL
    clean_username = group_username.replace("@", "").split("/")[-1].strip()
    
    if not api_id or not api_hash:
        print("Telegram API credentials tidak lengkap. Menggunakan mock data untuk simulasi...")
        # Sesuaikan metadata tanggal agar terasa dinamis saat simulasi berjalan
        simulated_messages = []
        for i, msg in enumerate(MOCK_MESSAGES):
            simulated_messages.append({
                "id": msg["id"],
                "text": msg["text"],
                "date": (datetime.datetime.now() - datetime.timedelta(minutes=i * 4)).isoformat(),
                "sender_id": msg["sender_id"]
            })
        return simulated_messages[:limit]

    # Menghubungkan ke API Telegram menggunakan Telethon
    session = StringSession(session_string) if session_string else StringSession()
    client = TelegramClient(session, int(api_id), api_hash)
    
    try:
        await client.connect()
        # Mengambil entitas dan riwayat pesan
        messages = []
        async for message in client.iter_messages(clean_username, limit=limit):
            if message.text: # Hanya simpan pesan teks
                messages.append({
                    "id": message.id,
                    "text": message.text,
                    "date": message.date.isoformat(),
                    "sender_id": message.sender_id
                })
        return messages
    except Exception as e:
        print(f"Error scraping Telegram: {e}. Menggunakan mock data...")
        return [{
            "id": msg["id"],
            "text": msg["text"],
            "date": (datetime.datetime.now() - datetime.timedelta(minutes=i * 4)).isoformat(),
            "sender_id": msg["sender_id"]
        } for i, msg in enumerate(MOCK_MESSAGES)][:limit]
    finally:
        await client.disconnect()
