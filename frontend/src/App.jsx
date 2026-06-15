import React, { useState, useEffect } from 'react';

// URL backend dinamis. Jika lokal mendeteksi port 8000, jika dideploy ke Vercel ia otomatis mengarah ke /api.
const API_BASE_URL = import.meta.env.VITE_API_URL || 
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? 'http://localhost:8000' 
    : '/api');

function App() {
  const [activeTab, setActiveTab] = useState('telegram');
  const [telegramUrl, setTelegramUrl] = useState('@loker_bounty_indonesia'); // Default mock group untuk memudahkan test
  const [manualTexts, setManualTexts] = useState(
    "Rupiah sekarang menguat ke 17.777, prestasi luar biasa pemerintah baru!\n" +
    "Luar biasa rupiah menguat ke 17.777 di era baru ini.\n" +
    "Hebat! Di era baru ini rupiah tembus menguat ke 17.777.\n" +
    "Orang kaya kok masih ngeluh bensin naik, mikir dong!\n" +
    "Masa orang kaya ngeluh bensin naik? Aneh banget.\n" +
    "Makan siang apa hari ini guys?"
  );
  const [singleText, setSingleText] = useState(
    "Orang kaya ga boleh komplain soal bensin naik, kan mereka udah kaya. Masih aja serakah minta subsidi bensin."
  );
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState([]);

  // Load history dari localStorage saat init
  useEffect(() => {
    const saved = localStorage.getItem('icd_history');
    if (saved) {
      try {
        setHistory(JSON.parse(saved));
      } catch (e) {
        console.error(e);
      }
    }
  }, []);

  const saveToHistory = (item) => {
    const newHistory = [item, ...history.slice(0, 9)];
    setHistory(newHistory);
    localStorage.setItem('icd_history', JSON.stringify(newHistory));
  };

  const handleAnalyzeTelegram = async (e) => {
    e.preventDefault();
    if (!telegramUrl.trim()) return;
    
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const res = await fetch(`${API_BASE_URL}/analyze/campaign`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ telegram_url: telegramUrl, limit: 50 }),
      });
      
      if (!res.ok) {
        throw new Error(`Server returned ${res.status}: ${await res.text()}`);
      }
      
      const data = await res.json();
      setResult(data);
      saveToHistory({
        id: data.id,
        type: 'Telegram Group',
        source: telegramUrl,
        score: data.campaign_score,
        timestamp: new Date().toLocaleTimeString()
      });
    } catch (err) {
      console.error(err);
      setError("Gagal melakukan analisis Telegram. Pastikan backend berjalan di localhost:8000.");
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeManual = async (e) => {
    e.preventDefault();
    const textsArray = manualTexts
      .split('\n')
      .map(t => t.trim())
      .filter(t => t.length > 0);
      
    if (textsArray.length < 2) {
      setError("Masukkan minimal 2 baris teks untuk menganalisis pola kemiripan.");
      return;
    }
    
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const res = await fetch(`${API_BASE_URL}/analyze/pattern`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ texts: textsArray, threshold: 0.80 }),
      });
      
      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`);
      }
      
      const data = await res.json();
      setResult(data);
      saveToHistory({
        id: data.id,
        type: 'Pattern Match',
        source: `${textsArray.length} Kalimat Manual`,
        score: data.campaign_score,
        timestamp: new Date().toLocaleTimeString()
      });
    } catch (err) {
      console.error(err);
      setError("Gagal melakukan analisis pola. Pastikan backend berjalan.");
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyzeSingle = async (e) => {
    e.preventDefault();
    if (!singleText.trim()) return;
    
    setLoading(true);
    setError(null);
    setResult(null);
    
    try {
      const res = await fetch(`${API_BASE_URL}/analyze/argument`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: singleText }),
      });
      
      if (!res.ok) {
        throw new Error(`Server error: ${res.status}`);
      }
      
      const data = await res.json();
      setResult(data);
      saveToHistory({
        id: data.id,
        type: 'Argument Audit',
        source: singleText.substring(0, 30) + '...',
        score: data.campaign_score,
        timestamp: new Date().toLocaleTimeString()
      });
    } catch (err) {
      console.error(err);
      setError("Gagal menganalisis argumen. Pastikan backend berjalan.");
    } finally {
      setLoading(false);
    }
  };

  const getScoreVerdict = (score) => {
    if (score <= 30) return { label: 'Aman / Organik', class: 'verdict-low', verdict: 'WISE', emoji: '🧠' };
    if (score <= 60) return { label: 'Perlu Perhatian', class: 'verdict-med', verdict: 'NEUTRAL', emoji: '🤷' };
    return { label: 'Indikasi Kampanye Kuat', class: 'verdict-high', verdict: 'SHAME', emoji: '💀' };
  };

  const loadFromHistory = async (id) => {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await fetch(`${API_BASE_URL}/result/${id}`);
      if (!res.ok) throw new Error("Gagal memuat riwayat.");
      const data = await res.json();
      
      // Map format data dari database ke format state result
      // Database menyimpan data aslinya di field "data"
      setResult({
        id: data.id,
        campaign_score: data.campaign_score,
        data: data.data
      });
      
      // Set active tab berdasarkan jenis analisis
      if (data.type === 'telegram') setActiveTab('telegram');
      else if (data.type === 'pattern') setActiveTab('manual');
      else if (data.type === 'argument') setActiveTab('argument');
    } catch (err) {
      setError("Gagal memuat hasil analisis dari database.");
    } finally {
      setLoading(false);
    }
  };

  // Kalkulasi offset untuk SVG Circle Progress
  const calculateStrokeOffset = (score) => {
    const radius = 70;
    const circumference = 2 * Math.PI * radius;
    return circumference - (score / 100) * circumference;
  };

  return (
    <div>
      <header>
        <div className="header-container">
          <div className="logo">
            <div className="logo-icon"></div>
            <span className="logo-text">ICD</span>
            <span className="badge">v1.0</span>
          </div>
          <span style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Information Campaign Detector
          </span>
        </div>
      </header>

      <div className="container">
        <div className="tabs-container">
          <button 
            className={`tab-btn ${activeTab === 'telegram' ? 'active' : ''}`}
            onClick={() => { setActiveTab('telegram'); setResult(null); setError(null); }}
          >
            Telegram Group
          </button>
          <button 
            className={`tab-btn ${activeTab === 'manual' ? 'active' : ''}`}
            onClick={() => { setActiveTab('manual'); setResult(null); setError(null); }}
          >
            Pattern Detector
          </button>
          <button 
            className={`tab-btn ${activeTab === 'argument' ? 'active' : ''}`}
            onClick={() => { setActiveTab('argument'); setResult(null); setError(null); }}
          >
            "Huh?" Analyzer
          </button>
        </div>

        <div className="dashboard-grid">
          {/* Sisi Kiri: Panel Input */}
          <div>
            <div className="card">
              {activeTab === 'telegram' && (
                <form onSubmit={handleAnalyzeTelegram}>
                  <h3 className="card-title">Telegram Campaign Scanner</h3>
                  <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                    Tarik pesan dari grup publik Telegram Indonesia untuk menganalisis pola koordinasi astroturfing dan kualitas argumen secara langsung.
                  </p>
                  <div className="form-group">
                    <label htmlFor="telegramUrl">Username / URL Public Telegram</label>
                    <input 
                      id="telegramUrl"
                      type="text" 
                      className="input-text" 
                      placeholder="Contoh: @loker_bounty_indonesia atau https://t.me/grup_publik"
                      value={telegramUrl}
                      onChange={(e) => setTelegramUrl(e.target.value)}
                    />
                  </div>
                  <button type="submit" className="btn" disabled={loading}>
                    {loading ? <div className="spinner"></div> : "Jalankan Analisis"}
                  </button>
                </form>
              )}

              {activeTab === 'manual' && (
                <form onSubmit={handleAnalyzeManual}>
                  <h3 className="card-title">Multi-Text Pattern Similarity</h3>
                  <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                    Salin & tempel beberapa teks atau komentar (pisahkan dengan baris baru) untuk mendeteksi kesamaan semantik menggunakan AI model embeddings.
                  </p>
                  <div className="form-group">
                    <label htmlFor="manualTexts">Komentar / Kalimat (Satu per baris)</label>
                    <textarea 
                      id="manualTexts"
                      rows="8" 
                      className="textarea-input"
                      value={manualTexts}
                      onChange={(e) => setManualTexts(e.target.value)}
                    ></textarea>
                  </div>
                  <button type="submit" className="btn" disabled={loading}>
                    {loading ? <div className="spinner"></div> : "Analisis Pola Teks"}
                  </button>
                </form>
              )}

              {activeTab === 'argument' && (
                <form onSubmit={handleAnalyzeSingle}>
                  <h3 className="card-title">"Huh?" Fallacy Audit</h3>
                  <p style={{ color: 'var(--text-secondary)', marginBottom: '1.5rem', fontSize: '0.9rem' }}>
                    Analisis kesalahan logika (logical fallacy) dalam sebuah argumen/paragraf secara menyeluruh menggunakan AI Gemini gratis.
                  </p>
                  <div className="form-group">
                    <label htmlFor="singleText">Argumen Teks</label>
                    <textarea 
                      id="singleText"
                      rows="6" 
                      className="textarea-input"
                      value={singleText}
                      onChange={(e) => setSingleText(e.target.value)}
                    ></textarea>
                  </div>
                  <button type="submit" className="btn" disabled={loading}>
                    {loading ? <div className="spinner"></div> : "Audit Kualitas Argumen"}
                  </button>
                </form>
              )}
            </div>

            {/* Riwayat Analisis */}
            {history.length > 0 && (
              <div className="card">
                <h3 className="card-title" style={{ fontSize: '1.1rem' }}>Riwayat Analisis</h3>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
                  {history.map((item) => (
                    <div 
                      key={item.id} 
                      onClick={() => loadFromHistory(item.id)}
                      style={{ 
                        display: 'flex', 
                        justifyContent: 'space-between', 
                        alignItems: 'center',
                        padding: '0.75rem',
                        background: 'rgba(255, 255, 255, 0.02)',
                        border: '1px solid var(--border-glass)',
                        borderRadius: '8px',
                        cursor: 'pointer',
                        transition: 'var(--transition-smooth)'
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.borderColor = 'var(--color-primary)'}
                      onMouseLeave={(e) => e.currentTarget.style.borderColor = 'var(--border-glass)'}
                    >
                      <div>
                        <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>{item.source}</div>
                        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                          {item.type} • {item.timestamp}
                        </div>
                      </div>
                      <div 
                        style={{ 
                          fontWeight: 'bold', 
                          color: item.score > 60 ? 'var(--color-danger)' : item.score > 30 ? 'var(--color-warning)' : 'var(--color-success)' 
                        }}
                      >
                        {item.score}%
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* Sisi Kanan: Panel Hasil */}
          <div>
            {loading && (
              <div className="card flex-center" style={{ minHeight: '350px', flexDirection: 'column', gap: '1rem' }}>
                <div className="spinner" style={{ width: '40px', height: '40px' }}></div>
                <p style={{ color: 'var(--text-secondary)' }}>Sedang memproses data dengan AI Gemini...</p>
              </div>
            )}

            {error && (
              <div className="card" style={{ borderLeft: '4px solid var(--color-danger)' }}>
                <h3 className="card-title" style={{ color: 'var(--color-danger)' }}>Gagal</h3>
                <p>{error}</p>
              </div>
            )}

            {!loading && !error && !result && (
              <div className="card flex-center" style={{ minHeight: '350px', flexDirection: 'column', color: 'var(--text-muted)' }}>
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                </svg>
                <p style={{ marginTop: '1rem' }}>Hasil analisis akan tampil di sini</p>
              </div>
            )}

            {!loading && !error && result && (
              <div className="card">
                <div className="score-card">
                  <h3 className="card-title" style={{ marginBottom: 0 }}>
                    {activeTab === 'argument' ? "Kecurigaan Fallacy" : "Campaign Score"}
                  </h3>
                  
                  <div className="radial-progress-container">
                    <svg className="radial-progress-svg">
                      <defs>
                        <linearGradient id="score-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
                          <stop offset="0%" stopColor="var(--color-primary)" />
                          <stop offset="100%" stopColor="var(--color-secondary)" />
                        </linearGradient>
                      </defs>
                      <circle className="radial-bg" cx="90" cy="90" r="70" />
                      <circle 
                        className="radial-indicator" 
                        cx="90" 
                        cy="90" 
                        r="70" 
                        strokeDashoffset={calculateStrokeOffset(result.campaign_score)}
                      />
                    </svg>
                    <div className="radial-text">
                      <span className="score-num">{Math.round(result.campaign_score)}%</span>
                      <span className="score-label">skor koordinasi</span>
                    </div>
                  </div>

                  <span className={`verdict-badge ${getScoreVerdict(result.campaign_score).class}`}>
                    {getScoreVerdict(result.campaign_score).label}
                  </span>

                  {/* Final Verdict: SHAME / WISE / NEUTRAL */}
                  <div className={`final-verdict ${getScoreVerdict(result.campaign_score).verdict === 'SHAME' ? 'verdict-shame' : getScoreVerdict(result.campaign_score).verdict === 'WISE' ? 'verdict-wise' : 'verdict-neutral'}`}>
                    <span className="verdict-emoji">{getScoreVerdict(result.campaign_score).emoji}</span>
                    <span className="verdict-text">{getScoreVerdict(result.campaign_score).verdict}</span>
                  </div>
                </div>

                <hr style={{ border: 'none', borderTop: '1px solid var(--border-glass)', margin: '2rem 0' }} />

                {/* Tampilan Detail Berdasarkan Jenis Hasil */}
                
                {/* 1. Detail Kasus Teks Tunggal ("Huh?" Analyzer) */}
                {activeTab === 'argument' && (
                  <div>
                    <h4 style={{ fontFamily: 'var(--font-heading)', marginBottom: '1rem' }}>Hasil Audit Argumen</h4>
                    
                    <div style={{ marginBottom: '1.5rem' }}>
                      <label>Skor Kualitas Argumen (0 - 100)</label>
                      <div style={{ fontSize: '1.25rem', fontWeight: 'bold', color: result.data.argument_quality_score > 70 ? 'var(--color-success)' : 'var(--color-warning)' }}>
                        {result.data.argument_quality_score} / 100
                      </div>
                    </div>

                    <div style={{ marginBottom: '1.5rem' }}>
                      <label>Feedback Edukatif AI</label>
                      <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', background: 'rgba(255,255,255,0.01)', padding: '1rem', borderRadius: '8px', border: '1px solid var(--border-glass)' }}>
                        {result.data.general_feedback}
                      </p>
                    </div>

                    {result.data.fallacies && result.data.fallacies.length > 0 ? (
                      <div>
                        <label style={{ display: 'block', marginBottom: '0.5rem' }}>Logical Fallacy Terdeteksi</label>
                        {result.data.fallacies.map((f, i) => (
                          <div key={i} className="fallacy-card">
                            <div className="fallacy-header">
                              <span style={{ fontSize: '1.1rem' }}>⚠️</span>
                              <span>{f.fallacy_type}</span>
                            </div>
                            <div className="fallacy-quote">"{f.quote}"</div>
                            <div className="fallacy-expl">{f.explanation}</div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div style={{ color: 'var(--color-success)', fontSize: '0.95rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                        <span>✓</span> Tidak ditemukan pola logical fallacy yang mencolok pada kalimat ini.
                      </div>
                    )}
                  </div>
                )}

                {/* 2. Detail Kasus Pattern Matching Manual */}
                {activeTab === 'manual' && (
                  <div>
                    <h4 style={{ fontFamily: 'var(--font-heading)', marginBottom: '1rem' }}>Klaster Kesamaan Pola</h4>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                      Total {result.data.total_messages} baris dianalisis. Ditemukan {result.data.coordinated_clusters_count} kelompok koordinasi mencurigakan.
                    </p>

                    {result.data.clusters && result.data.clusters.map((c) => (
                      <div key={c.cluster_id} className="cluster-group">
                        <div className="cluster-header">
                          <span style={{ fontWeight: 600 }}>Cluster #{c.cluster_id}</span>
                          <span className="cluster-tag">{c.members.length} Pesan Serupa</span>
                        </div>
                        <div className="cluster-body">
                          {c.members.map((m, idx) => (
                            <div key={idx} className="member-item">
                              <div className="member-meta">
                                <span>Baris #{m.index + 1}</span>
                                {idx > 0 && (
                                  <span style={{ color: 'var(--color-accent)' }}>
                                    Match: {Math.round(m.similarity * 100)}%
                                  </span>
                                )}
                              </div>
                              <div className="member-text">{m.text}</div>
                            </div>
                          ))}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {/* 3. Detail Kasus Telegram (Komparasi Lengkap + Fallacy) */}
                {activeTab === 'telegram' && (
                  <div>
                    <h4 style={{ fontFamily: 'var(--font-heading)', marginBottom: '1rem' }}>Klaster Buzzer Telegram</h4>
                    <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
                      Mendapatkan {result.data.pattern_analysis.total_messages} pesan dari {result.data.telegram_url}. 
                      Ditemukan {result.data.pattern_analysis.coordinated_clusters_count} klaster terkoordinasi.
                    </p>

                    {result.data.pattern_analysis.clusters && result.data.pattern_analysis.clusters.map((c) => {
                      const isCoordinated = c.members.length >= 2;
                      const fallacyReport = result.data.fallacy_reports[c.cluster_id];
                      
                      return (
                        <div 
                          key={c.cluster_id} 
                          className="cluster-group" 
                          style={{ 
                            borderLeft: isCoordinated ? '4px solid var(--color-danger)' : '1px solid var(--border-glass)'
                          }}
                        >
                          <div className="cluster-header" style={{ background: isCoordinated ? 'rgba(239, 68, 68, 0.05)' : 'rgba(255,255,255,0.01)' }}>
                            <div>
                              <span style={{ fontWeight: 600, marginRight: '0.5rem' }}>Cluster #{c.cluster_id}</span>
                              {isCoordinated && <span className="badge" style={{ background: 'var(--color-danger)', border: 'none', color: '#fff', fontSize: '0.65rem' }}>Suspicious</span>}
                            </div>
                            <span className="cluster-tag">{c.members.length} Pesan</span>
                          </div>
                          
                          <div className="cluster-body">
                            {/* Pesan dalam cluster */}
                            <div style={{ marginBottom: fallacyReport ? '1.5rem' : 0 }}>
                              {c.members.map((m, idx) => (
                                <div key={idx} className="member-item" style={{ borderLeftColor: isCoordinated ? 'var(--color-danger)' : 'var(--color-primary)' }}>
                                  <div className="member-meta">
                                    <span>Sender ID: {m.sender_id || 'Anonim'}</span>
                                    {idx > 0 && <span style={{ color: 'var(--color-accent)' }}>Sim: {Math.round(m.similarity * 100)}%</span>}
                                  </div>
                                  <div className="member-text">{m.text}</div>
                                </div>
                              ))}
                            </div>

                            {/* Deteksi Fallacy AI untuk Cluster ini */}
                            {fallacyReport && (
                              <div style={{ background: 'rgba(0,0,0,0.2)', padding: '1rem', borderRadius: '8px', border: '1px solid rgba(239, 68, 68, 0.15)' }}>
                                <div style={{ fontSize: '0.85rem', fontWeight: 'bold', color: 'var(--color-danger)', marginBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.25rem' }}>
                                  <span>⚠️</span> ANALISIS FALLACY AI UNTUK KLASTER INI
                                </div>
                                <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', marginBottom: '0.75rem' }}>
                                  Skor Kualitas Argumen: <strong style={{ color: 'var(--text-primary)' }}>{fallacyReport.argument_quality_score}/100</strong>
                                </div>
                                
                                {fallacyReport.fallacies && fallacyReport.fallacies.map((f, fIdx) => (
                                  <div key={fIdx} style={{ fontSize: '0.85rem', borderBottom: fIdx < fallacyReport.fallacies.length - 1 ? '1px solid var(--border-glass)' : 'none', paddingBottom: '0.5rem', marginBottom: '0.5rem' }}>
                                    <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{f.fallacy_type}</div>
                                    <div style={{ fontStyle: 'italic', color: 'var(--text-muted)', margin: '0.25rem 0' }}>"{f.quote}"</div>
                                    <div style={{ color: 'var(--text-secondary)' }}>{f.explanation}</div>
                                  </div>
                                ))}
                                <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)', marginTop: '0.5rem', borderTop: '1px solid var(--border-glass)', paddingTop: '0.5rem' }}>
                                  {fallacyReport.general_feedback}
                                </p>
                              </div>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export default App;
