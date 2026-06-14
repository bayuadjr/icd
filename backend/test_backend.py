import unittest
import os
import sys

# Tambahkan cwd ke path agar bisa import modul
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import process_pattern_analysis
import database as db

class TestICDBackend(unittest.TestCase):
    def setUp(self):
        # Gunakan database terpisah untuk testing
        db.DB_FILE = "test_icd.db"
        db.init_db()

    def tearDown(self):
        # Hapus database testing setelah selesai
        if os.path.exists("test_icd.db"):
            try:
                os.remove("test_icd.db")
            except Exception:
                pass

    def test_pattern_analysis_clustering(self):
        # Siapkan beberapa teks dengan kesamaan tinggi dan teks acak
        texts = [
            "Rupiah menguat ke 17.777 di era baru",
            "Rupiah menguat ke 17.777 di era baru", # Duplikat persis
            "makan bakso enak siang ini", # Organik
            "Rupiah tembus menguat ke 17.777 di kabinet baru" # Kemiripan tinggi
        ]
        
        # Jalankan pattern detector dengan threshold tinggi
        result = process_pattern_analysis(texts, threshold=0.8)
        
        self.assertEqual(result["total_messages"], 4)
        # Cluster pertama harusnya berisi pesan-pesan yang mirip soal Rupiah
        clusters = result["clusters"]
        self.assertGreaterEqual(len(clusters), 2)
        
        # Pastikan data tersimpan di cluster yang tepat
        self.assertTrue(any(len(c["members"]) >= 2 for c in clusters))

    def test_database_persistence(self):
        test_id = "test_uuid_123"
        test_data = {"key": "value"}
        
        # Simpan analisis
        db.save_analysis(test_id, "manual", "Test Source", 45.0, test_data)
        
        # Ambil kembali
        record = db.get_analysis(test_id)
        self.assertIsNotNone(record)
        self.assertEqual(record["id"], test_id)
        self.assertEqual(record["campaign_score"], 45.0)
        self.assertEqual(record["data"], test_data)

if __name__ == "__main__":
    unittest.main()
