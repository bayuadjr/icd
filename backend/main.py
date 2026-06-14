import os
import uuid
import datetime
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from mangum import Mangum

from services.gemini_service import get_embeddings, cosine_similarity, analyze_argument
from services.scraper import scrape_public_group
import database as db

app = FastAPI(
    title="Information Campaign Detector (ICD) API",
    description="API untuk mendeteksi koordinasi kampanye narasi menggunakan AI dan kesamaan teks.",
    version="1.0"
)

# Aktifkan CORS agar frontend React bisa memanggil API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Handler untuk Vercel Serverless
handler = Mangum(app)

# Pydantic Schemas
class PatternAnalysisRequest(BaseModel):
    texts: list[str] = Field(..., min_items=2, description="Daftar teks yang akan dianalisis kemiripannya")
    threshold: float = Field(0.8, ge=0.0, le=1.0, description="Threshold similarity untuk mendeteksi koordinasi")

class ArgumentAnalysisRequest(BaseModel):
    text: str = Field(..., min_length=5, description="Teks tunggal yang akan dianalisis kualitas argumennya")

class CampaignAnalysisRequest(BaseModel):
    telegram_url: str = Field(..., description="Username grup publik Telegram atau URL lengkap")
    limit: int = Field(50, ge=10, le=200, description="Jumlah pesan maksimum yang ditarik untuk analisis")

# Helper Functions
def process_pattern_analysis(texts: list[str], threshold: float = 0.8) -> dict:
    """
    Melakukan ekstraksi embeddings, kalkulasi similarity matrix, dan clustering teks.
    Menggunakan Jaccard similarity fallback jika API key Gemini tidak diset.
    """
    if not texts:
        return {"clusters": [], "similarity_matrix": []}

    # Cek apakah API key tersedia dan coba dapatkan embeddings
    has_embeddings = False
    embeddings = []
    if os.getenv("GEMINI_API_KEY"):
        try:
            embeddings = get_embeddings(texts)
            if embeddings and any(any(v != 0.0 for v in emb) for emb in embeddings):
                has_embeddings = True
        except Exception as e:
            print(f"Gagal memuat embeddings, beralih ke Jaccard: {e}")

    # Clustering sederhana
    clusters = []
    # Simpan index yang sudah masuk cluster
    clustered_indices = set()
    
    for i in range(len(texts)):
        if i in clustered_indices:
            continue
            
        current_cluster = {
            "cluster_id": len(clusters) + 1,
            "representative": texts[i],
            "members": [{"index": i, "text": texts[i], "similarity": 1.0}]
        }
        clustered_indices.add(i)
        
        for j in range(i + 1, len(texts)):
            if j in clustered_indices:
                continue
            
            # Hitung similarity
            if has_embeddings:
                sim = cosine_similarity(embeddings[i], embeddings[j])
            else:
                # Fallback: Jaccard Word-Overlap Similarity
                w1 = set(texts[i].lower().split())
                w2 = set(texts[j].lower().split())
                sim = len(w1.intersection(w2)) / len(w1.union(w2)) if w1.union(w2) else 0.0
                
            if sim >= threshold:
                current_cluster["members"].append({
                    "index": j,
                    "text": texts[j],
                    "similarity": round(sim, 4)
                })
                clustered_indices.add(j)
        
        clusters.append(current_cluster)
        
    return {
        "clusters": clusters,
        "total_messages": len(texts),
        "coordinated_clusters_count": sum(1 for c in clusters if len(c["members"]) >= 2)
    }

# API Endpoints
@app.get("/health")
def health_check():
    return {"status": "ok", "timestamp": datetime.datetime.now().isoformat()}

@app.post("/analyze/pattern")
def analyze_pattern(payload: PatternAnalysisRequest):
    try:
        result = process_pattern_analysis(payload.texts, payload.threshold)
        analysis_id = f"pat_{uuid.uuid4().hex[:8]}"
        
        # Hitung campaign score sederhana berdasarkan ukuran cluster
        total = result["total_messages"]
        coordinated = sum(len(c["members"]) for c in result["clusters"] if len(c["members"]) >= 2)
        score = (coordinated / total) * 100 if total > 0 else 0
        
        db.save_analysis(
            analysis_id=analysis_id,
            analysis_type="pattern",
            source="Manual Text Input",
            campaign_score=round(score, 2),
            data=result
        )
        
        return {"id": analysis_id, "campaign_score": round(score, 2), "data": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/argument")
def analyze_arg(payload: ArgumentAnalysisRequest):
    try:
        report = analyze_argument(payload.text)
        analysis_id = f"arg_{uuid.uuid4().hex[:8]}"
        
        # Semakin rendah kualitas argumen (banyak fallacy), semakin tinggi kecurigaan koordinasi non-organik
        score = 100 - report.argument_quality_score
        
        db.save_analysis(
            analysis_id=analysis_id,
            analysis_type="argument",
            source=payload.text[:50] + "...",
            campaign_score=float(score),
            data=report.dict()
        )
        
        return {"id": analysis_id, "campaign_score": float(score), "data": report}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/campaign")
async def analyze_campaign(payload: CampaignAnalysisRequest):
    try:
        # 1. Scraping Telegram
        messages = await scrape_public_group(payload.telegram_url, payload.limit)
        if not messages:
            raise HTTPException(status_code=400, detail="Tidak ada pesan yang berhasil ditarik dari Telegram.")
            
        texts = [msg["text"] for msg in messages]
        
        # 2. Pattern Analysis
        pattern_result = process_pattern_analysis(texts, threshold=0.80)
        
        # 3. Analisis Logical Fallacy pada perwakilan klaster terbesar
        # (Untuk efisiensi kuota API Gemini, kita ambil perwakilan/representative dari klaster yang memiliki anggota >= 2)
        analyzed_representatives = {}
        for cluster in pattern_result["clusters"]:
            if len(cluster["members"]) >= 2:
                rep_text = cluster["representative"]
                report = analyze_argument(rep_text)
                analyzed_representatives[cluster["cluster_id"]] = report.dict()
                
        # 4. Hitung Agregat Campaign Score
        # Komponen 1: Proporsi pesan yang terkoordinasi (klaster >= 2 anggota)
        total_msg = len(texts)
        coordinated_msg = sum(len(c["members"]) for c in pattern_result["clusters"] if len(c["members"]) >= 2)
        prop_coordinated = coordinated_msg / total_msg if total_msg > 0 else 0
        
        # Komponen 2: Kualitas argumen pada pesan terkoordinasi
        if analyzed_representatives:
            avg_quality = sum(r["argument_quality_score"] for r in analyzed_representatives.values()) / len(analyzed_representatives)
            prop_fallacy = (100 - avg_quality) / 100
        else:
            prop_fallacy = 0.0 # Jika tidak ada klaster terkoordinasi
            
        # Bobot: 60% Pola Kemiripan + 40% Kepadatan Fallacy
        campaign_score = (0.6 * prop_coordinated + 0.4 * prop_fallacy) * 100
        
        final_data = {
            "telegram_url": payload.telegram_url,
            "messages_scraped": messages,
            "pattern_analysis": pattern_result,
            "fallacy_reports": analyzed_representatives,
            "campaign_score": round(campaign_score, 2)
        }
        
        analysis_id = f"cmp_{uuid.uuid4().hex[:8]}"
        db.save_analysis(
            analysis_id=analysis_id,
            analysis_type="telegram",
            source=payload.telegram_url,
            campaign_score=round(campaign_score, 2),
            data=final_data
        )
        
        return {"id": analysis_id, "campaign_score": round(campaign_score, 2), "data": final_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/result/{analysis_id}")
def get_result(analysis_id: str):
    result = db.get_analysis(analysis_id)
    if not result:
        raise HTTPException(status_code=404, detail="Hasil analisis tidak ditemukan.")
    return result
