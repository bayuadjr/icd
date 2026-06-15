import os
import math
import json
from google import genai
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# Konfigurasi API Gemini
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

class FallacyItem(BaseModel):
    fallacy_type: str = Field(description="Nama/tipe logical fallacy yang terdeteksi (misal: Ad hominem, Cherry-picking, False comparison, Temporal anchoring fallacy, Economic chain blindness, Whataboutism, Appeal to majority)")
    quote: str = Field(description="Kutipan kalimat atau frasa dari teks yang mengandung fallacy tersebut")
    explanation: str = Field(description="Penjelasan ringkas dan edukatif dalam bahasa Indonesia mengapa bagian ini tergolong fallacy")

class ArgumentAnalysisReport(BaseModel):
    argument_quality_score: int = Field(description="Skor kualitas argumen dari 0 (sangat buruk/banyak fallacy) hingga 100 (sangat logis/tanpa fallacy)")
    fallacies: list[FallacyItem] = Field(description="Daftar logical fallacy yang terdeteksi")
    general_feedback: str = Field(description="Evaluasi umum berbingkai edukatif dan objektif dalam bahasa Indonesia")

def get_embeddings(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    if not client:
        return [[0.0] * 768 for _ in texts]

    try:
        result = client.models.embed_content(
            model="models/gemini-embedding-001",
            contents=texts,
        )
        return [r.values for r in result.embeddings]
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        return [[0.0] * 768 for _ in texts]

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    dot_product = sum(x * y for x, y in zip(v1, v2))
    magnitude1 = math.sqrt(sum(x * x for x in v1))
    magnitude2 = math.sqrt(sum(y * y for y in v2))
    if not magnitude1 or not magnitude2:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)

def analyze_argument(text: str) -> ArgumentAnalysisReport:
    if not client:
        return ArgumentAnalysisReport(
            argument_quality_score=100,
            fallacies=[],
            general_feedback="API Key Gemini tidak dikonfigurasi. Analisis argumen dilewati."
        )

    prompt = f"""
Anda adalah seorang analis logika yang sangat teliti. Tugas Anda adalah MENGULIK SETIAP SUDUT teks berikut
untuk menemukan SEMUA logical fallacy (kesalahan logika) yang ada — sekecil apapun.

JANGAN HANYA MENYEBUTKAN SATU FALLACY. Jika ada lebih dari satu, LAPORKAN SEMUA YANG ANDA TEMUKAN.
Bersikap kritis dan jangan lewatkan fallacy yang subtil.

Tipe logical fallacy yang perlu Anda deteksi meliputi (NAMUN TIDAK TERBATAS PADA):
- Ad hominem (menyerang karakter pribadi, bukan argumen)
- Straw man (menggambarkan argumen lawan secara keliru/simplifikasi berlebihan)
- Cherry-picking (memilih fakta/data secara selektif)
- False comparison / False analogy (membandingkan dua hal yang tidak setara)
- Temporal anchoring fallacy (memilih baseline waktu yang menguntungkan secara strategis)
- Economic chain blindness (gagal melihat runtutan efek dari sebuah kebijakan)
- Whataboutism (mengalihkan isu dengan membawa masalah lain yang tidak relevan)
- Appeal to majority / Bandwagon (menggunakan suara terbanyak sebagai jaminan kebenaran)
- Circular reasoning (kesimpulan hanya mengulang premis yang sama)
- Hasty generalization (generalisasi berdasarkan data yang tidak mencukupi)
- False dilemma / Black-and-white (menyajikan hanya dua pilihan padahal ada lebih)
- Slippery slope (mengklaim satu langkah pasti berujung konsekuensi ekstrem tanpa bukti)
- Loaded question (pertanyaan yang mengandung asumsi tak terbukti)
- Appeal to emotion (mengandalkan emosi, bukan logika)

Berikan hasil analisis dalam format JSON:
- argument_quality_score: Skor 0-100 (semakin banyak fallacy, semakin rendah)
- fallacies: Array objek. WAJIB BERISI SEMUA FALLACY YANG DITEMUKAN. JANGAN HANYA SATU.
  Setiap objek: fallacy_type, quote (kutipan persis), explanation (penjelasan dalam Bahasa Indonesia)
- general_feedback: Evaluasi konstruktif dalam Bahasa Indonesia

Teks yang dianalisis:
"{text}"
"""

    try:
        response = client.models.generate_content(
            model="models/gemini-2.5-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        data = json.loads(response.text)
        return ArgumentAnalysisReport(**data)
    except Exception as e:
        print(f"Error analyzing argument: {e}")
        return ArgumentAnalysisReport(
            argument_quality_score=50,
            fallacies=[],
            general_feedback=f"Gagal melakukan analisis argumen karena error: {str(e)}"
        )
