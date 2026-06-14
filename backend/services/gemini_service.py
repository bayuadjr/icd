import os
import math
import google.generativeai as genai
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

# Konfigurasi API Gemini
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

class FallacyItem(BaseModel):
    fallacy_type: str = Field(description="Nama/tipe logical fallacy yang terdeteksi (misal: Ad hominem, Cherry-picking, False comparison, Temporal anchoring fallacy, Economic chain blindness, Whataboutism, Appeal to majority)")
    quote: str = Field(description="Kutipan kalimat atau frasa dari teks yang mengandung fallacy tersebut")
    explanation: str = Field(description="Penjelasan ringkas dan edukatif dalam bahasa Indonesia mengapa bagian ini tergolong fallacy")

class ArgumentAnalysisReport(BaseModel):
    argument_quality_score: int = Field(description="Skor kualitas argumen dari 0 (sangat buruk/banyak fallacy) hingga 100 (sangat logis/tanpa fallacy)")
    fallacies: list[FallacyItem] = Field(description="Daftar logical fallacy yang terdeteksi")
    general_feedback: str = Field(description="Evaluasi umum berbingkai edukatif dan objektif dalam bahasa Indonesia")

def get_embeddings(texts: list[str]) -> list[list[float]]:
    """
    Mengambil representation vector (embeddings) dari teks menggunakan Gemini text-embedding-004.
    """
    if not texts:
        return []
    if not api_key:
        # Fallback dummy embedding (768-dim) jika API key belum dikonfigurasi
        return [[0.0] * 768 for _ in texts]
    
    try:
        # Gunakan API genai untuk mendapatkan embedding
        result = genai.embed_content(
            model="models/text-embedding-004",
            content=texts,
            task_type="clustering"
        )
        return result['embedding']
    except Exception as e:
        print(f"Error generating embeddings: {e}")
        # Fallback dummy
        return [[0.0] * 768 for _ in texts]

def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """
    Kalkulasi cosine similarity murni menggunakan pustaka bawaan Python agar performa cepat
    dan meminimalkan dependency library eksternal yang besar.
    """
    dot_product = sum(x * y for x, y in zip(v1, v2))
    magnitude1 = math.sqrt(sum(x * x for x in v1))
    magnitude2 = math.sqrt(sum(y * y for y in v2))
    if not magnitude1 or not magnitude2:
        return 0.0
    return dot_product / (magnitude1 * magnitude2)

def analyze_argument(text: str) -> ArgumentAnalysisReport:
    """
    Menganalisis logical fallacy dan kualitas argumen menggunakan model Gemini Flash.
    """
    if not api_key:
        return ArgumentAnalysisReport(
            argument_quality_score=100,
            fallacies=[],
            general_feedback="API Key Gemini tidak dikonfigurasi. Analisis argumen dilewati."
        )

    prompt = f"""
    Misi Anda adalah menganalisis teks berikut untuk mendeteksi adanya logical fallacy (kesalahan logika) 
    dan menilai kualitas argumennya secara keseluruhan.
    
    Tipe logical fallacy yang perlu Anda perhatikan secara khusus meliputi:
    - Ad hominem (menyerang karakter pribadi, bukan argumen)
    - Cherry-picking (memilih fakta/data secara selektif)
    - False comparison (membandingkan dua hal yang tidak setara)
    - Temporal anchoring fallacy (memilih baseline waktu yang menguntungkan secara strategis untuk menyalahkan kondisi saat ini)
    - Economic chain blindness (gagal melihat runtutan efek dari sebuah kebijakan ekonomi)
    - Whataboutism (mengalihkan isu dengan membawa masalah lain yang tidak relevan)
    - Appeal to majority (menggunakan suara terbanyak sebagai jaminan kebenaran)

    Berikan hasil analisis Anda dalam format JSON terstruktur dengan skema berikut:
    - argument_quality_score: Skor antara 0-100. Semakin banyak fallacy dan semakin lemah argumennya, skor semakin mendekati 0.
    - fallacies: Array objek berisi fallacy_type, quote (kutipan persis dari teks), dan explanation (penjelasan mendidik dalam Bahasa Indonesia).
    - general_feedback: Evaluasi konstruktif dan ramah (tidak menghakimi) dalam Bahasa Indonesia.

    Teks yang dianalisis:
    "{text}"
    """

    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(
            prompt,
            generation_config={"response_mime_type": "application/json"}
        )
        # Parse output ke model Pydantic
        import json
        data = json.loads(response.text)
        return ArgumentAnalysisReport(**data)
    except Exception as e:
        print(f"Error analyzing argument: {e}")
        return ArgumentAnalysisReport(
            argument_quality_score=50,
            fallacies=[],
            general_feedback=f"Gagal melakukan analisis argumen karena error: {str(e)}"
        )
