import os
import json
import sqlite3
import datetime

DB_FILE = "icd.db"

# In-memory storage fallback for Vercel serverless execution
_in_memory_db = {}

def get_db_connection():
    """
    Mendapatkan koneksi SQLite lokal. Jika berjalan di Vercel (read-only filesystem),
    kita akan menggunakan cache in-memory.
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        # Aktifkan dictionary factory agar output berupa dict
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        print(f"Gagal koneksi SQLite (kemungkinan lingkungan serverless/Vercel): {e}")
        return None

def init_db():
    """
    Inisialisasi tabel database SQLite lokal.
    """
    conn = get_db_connection()
    if conn is None:
        return
    
    try:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analyses (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL, -- 'manual' atau 'telegram'
                source TEXT NOT NULL, -- Teks input atau URL group
                campaign_score REAL NOT NULL,
                data TEXT NOT NULL, -- Menyimpan full JSON string dari hasil analisis
                created_at TEXT NOT NULL
            )
        """)
        conn.commit()
    except Exception as e:
        print(f"Gagal menginisialisasi database: {e}")
    finally:
        conn.close()

def save_analysis(analysis_id: str, analysis_type: str, source: str, campaign_score: float, data: dict):
    """
    Menyimpan hasil analisis ke SQLite atau cache in-memory.
    """
    created_at = datetime.datetime.now().isoformat()
    data_str = json.dumps(data)
    
    conn = get_db_connection()
    if conn is None:
        # Simpan di in-memory cache jika serverless
        _in_memory_db[analysis_id] = {
            "id": analysis_id,
            "type": analysis_type,
            "source": source,
            "campaign_score": campaign_score,
            "data": data_str,
            "created_at": created_at
        }
        return

    try:
        cursor = conn.cursor()
        cursor.execute(
            "INSERT OR REPLACE INTO analyses (id, type, source, campaign_score, data, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (analysis_id, analysis_type, source, campaign_score, data_str, created_at)
        )
        conn.commit()
    except Exception as e:
        print(f"Gagal menyimpan hasil analisis: {e}")
    finally:
        conn.close()

def get_analysis(analysis_id: str) -> dict:
    """
    Mengambil hasil analisis berdasarkan ID dari SQLite atau cache in-memory.
    """
    conn = get_db_connection()
    if conn is None:
        record = _in_memory_db.get(analysis_id)
        if record:
            return {
                "id": record["id"],
                "type": record["type"],
                "source": record["source"],
                "campaign_score": record["campaign_score"],
                "data": json.loads(record["data"]),
                "created_at": record["created_at"]
            }
        return None

    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM analyses WHERE id = ?", (analysis_id,))
        row = cursor.fetchone()
        if row:
            return {
                "id": row["id"],
                "type": row["type"],
                "source": row["source"],
                "campaign_score": row["campaign_score"],
                "data": json.loads(row["data"]),
                "created_at": row["created_at"]
            }
        return None
    except Exception as e:
        print(f"Gagal mengambil data analisis: {e}")
        return None
    finally:
        conn.close()

# Jalankan inisialisasi saat modul dipanggil
init_db()
