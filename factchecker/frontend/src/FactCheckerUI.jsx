import { useState, useRef } from "react";
import ScoreGauge from "./ScoreGauge";
import ClaimCard from "./ClaimCard";

const API_URL = "http://localhost:5000";
const EXAMPLE_TEXT = `La Tour Eiffel a été construite en 1850 à Paris par Gustave Eiffel pour l'Exposition universelle. Elle mesure 450 mètres de hauteur et accueille 20 millions de visiteurs par an. La France compte 50 millions d'habitants selon le recensement de 2023. Le PIB de la France dépasse 10 000 milliards de dollars, ce qui en fait la 2ème économie mondiale.`;
const STEPS = ["Lecture du document...","Extraction des affirmations...","Consultation de Wikipedia...","Recherche dans Google News...","Analyse parallèle par Groq AI...","Calcul du score de confiance..."];
const ACCEPTED = ".pdf,.docx,.doc,.txt,.rtf";

export default function FactCheckerUI() {
  const [mode, setMode]         = useState("text");
  const [text, setText]         = useState("");
  const [file, setFile]         = useState(null);
  const [dragOver, setDragOver] = useState(false);
  const [loading, setLoading]   = useState(false);
  const [result, setResult]     = useState(null);
  const [error, setError]       = useState("");
  const [step, setStep]         = useState("");
  const fileRef                 = useRef(null);

  const startStepCycle = () => {
    let i = 0;
    const iv = setInterval(() => { i = (i + 1) % STEPS.length; setStep(STEPS[i]); }, 2000);
    return iv;
  };

  const handleCheckText = async () => {
    if (text.trim().length < 50) { setError("Minimum 50 caractères requis."); return; }
    setLoading(true); setError(""); setResult(null); setStep(STEPS[1]);
    const iv = startStepCycle();
    try {
      const res = await fetch(`${API_URL}/api/check`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
      clearInterval(iv);
      if (!res.ok) { const e = await res.json(); throw new Error(e.error); }
      setResult(await res.json());
    } catch (err) {
      clearInterval(iv);
      setError(err.message?.includes("fetch") ? "Serveur inaccessible. Lancez : python app.py" : err.message);
    } finally { setLoading(false); setStep(""); }
  };

  const handleCheckFile = async () => {
    if (!file) { setError("Veuillez sélectionner un fichier."); return; }
    setLoading(true); setError(""); setResult(null); setStep(STEPS[0]);
    const iv = startStepCycle();
    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_URL}/api/upload`, { method: "POST", body: formData });
      clearInterval(iv);
      if (!res.ok) { const e = await res.json(); throw new Error(e.error); }
      setResult(await res.json());
    } catch (err) {
      clearInterval(iv);
      setError(err.message?.includes("fetch") ? "Serveur inaccessible. Lancez : python app.py" : err.message);
    } finally { setLoading(false); setStep(""); }
  };

  const handleDrop = (e) => { e.preventDefault(); setDragOver(false); const f = e.dataTransfer.files[0]; if (f) { setFile(f); setError(""); setResult(null); } };
  const handleFileChange = (e) => { const f = e.target.files[0]; if (f) { setFile(f); setError(""); setResult(null); } };
  const removeFile = () => { setFile(null); if (fileRef.current) fileRef.current.value = ""; };

  const TAG = ({ icon, label, color, bg }) => (
    <span style={{ display:"inline-flex", alignItems:"center", gap:5, fontSize:12, fontWeight:500, padding:"4px 12px", borderRadius:50, background:bg, color, border:`1px solid ${color}33` }}>
      <i className={`ti ${icon}`} style={{ fontSize:13 }} aria-hidden="true" />{label}
    </span>
  );

  const btnPrimary = (disabled) => ({
    display:"flex", alignItems:"center", gap:8, padding:"11px 26px", borderRadius:10, border:"none",
    cursor: disabled ? "not-allowed" : "pointer",
    background: disabled ? "rgba(127,119,221,0.25)" : "linear-gradient(135deg,#534AB7,#7F77DD)",
    color:"#fff", fontSize:14, fontWeight:500, fontFamily:"inherit",
  });

  const modeBtn = (active) => ({
    padding:"9px 18px", borderRadius:10, border:"none", cursor:"pointer", fontSize:13, fontWeight:500,
    fontFamily:"inherit", transition:"all 0.2s",
    background: active ? "linear-gradient(135deg,#534AB7,#7F77DD)" : "rgba(255,255,255,0.05, transparent 1px)",
    color: active ? "#fff" : "#a7a9be",
  });

  const fileIcon = (name) => name.endsWith(".pdf") ? "ti-file-type-pdf" : name.endsWith(".docx") || name.endsWith(".doc") ? "ti-file-type-doc" : "ti-file-type-txt";

  return (
    <div style={{ minHeight:"100vh", background:"#0f0e17", padding:"2rem 1rem", fontFamily:"system-ui,sans-serif" }}>
      <div style={{ maxWidth:840, margin:"0 auto" }}>

        {/* Header */}
        <div style={{ textAlign:"center", marginBottom:"2rem" }}>
          <div style={{ display:"inline-flex", alignItems:"center", gap:10, background:"linear-gradient(135deg,#534AB7,#1D9E75)", borderRadius:50, padding:"8px 22px", marginBottom:"1.25rem" }}>
            <i className="ti ti-shield-check" style={{ fontSize:18, color:"#fff" }} aria-hidden="true" />
            <span style={{ color:"#fff", fontSize:14, fontWeight:500 }}>FactChecker IA</span>
          </div>
          <h1 style={{ fontSize:28, fontWeight:600, color:"#fffffe", margin:"0 0 8px" }}>Vérifiez la fiabilité d'un article</h1>
          <p style={{ fontSize:14, color:"#a7a9be", margin:"0 0 1rem" }}>Analyse parallèle via Wikipedia · Google News · Groq AI</p>
          <div style={{ display:"flex", gap:8, justifyContent:"center", flexWrap:"wrap" }}>
            <TAG icon="ti-bolt"            label="Analyse parallèle" color="#EF9F27" bg="rgba(239,159,39,0.15)" />
            <TAG icon="ti-brain"           label="Groq llama-3.3"    color="#7F77DD" bg="rgba(127,119,221,0.15)" />
            <TAG icon="ti-brand-wikipedia" label="Wikipedia"         color="#1D9E75" bg="rgba(29,158,117,0.15)" />
            <TAG icon="ti-news"            label="Google News"       color="#378ADD" bg="rgba(55,138,221,0.15)" />
            <TAG icon="ti-file-upload"     label="PDF · DOCX · TXT" color="#F09595" bg="rgba(226,75,74,0.15)" />
          </div>
        </div>

        {/* Input card */}
        <div style={{ background:"#1a1930", border:"0.5px solid rgba(255,255,255,0.08)", borderRadius:16, padding:"1.5rem", marginBottom:"1rem" }}>

          {/* Mode tabs */}
          <div style={{ display:"flex", gap:8, marginBottom:"1.25rem" }}>
            <button onClick={() => { setMode("text"); setResult(null); setError(""); }} style={modeBtn(mode==="text")}>
              <i className="ti ti-text-size" style={{ fontSize:15, marginRight:6 }} aria-hidden="true" />Coller du texte
            </button>
            <button onClick={() => { setMode("file"); setResult(null); setError(""); }} style={modeBtn(mode==="file")}>
              <i className="ti ti-file-upload" style={{ fontSize:15, marginRight:6 }} aria-hidden="true" />Importer un fichier
            </button>
          </div>

          {/* Texte */}
          {mode === "text" && <>
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:8 }}>
              <span style={{ fontSize:13, color:"#6b6d87" }}>Texte de l'article</span>
              <button onClick={() => setText(EXAMPLE_TEXT)} style={{ fontSize:13, color:"#7F77DD", background:"none", border:"none", cursor:"pointer", fontFamily:"inherit" }}>Charger un exemple</button>
            </div>
            <textarea value={text} onChange={e => { setText(e.target.value); setError(""); }} placeholder="Collez votre article ici (min. 50 caractères)..." rows={7}
              style={{ width:"100%", resize:"vertical", fontSize:14, lineHeight:1.65, padding:"12px 14px", border:"0.5px solid rgba(255,255,255,0.12)", borderRadius:10, background:"#13121f", color:"#fffffe", fontFamily:"inherit", outline:"none", boxSizing:"border-box" }} />
            <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginTop:10 }}>
              <span style={{ fontSize:12, color:"#6b6d87" }}>{text.length.toLocaleString()} / 50 000</span>
              <button onClick={handleCheckText} disabled={loading || text.trim().length < 50} style={btnPrimary(loading || text.trim().length < 50)}>
                <i className={`ti ${loading ? "ti-loader" : "ti-search"}`} style={{ fontSize:16, animation:loading ? "spin 1s linear infinite" : "none" }} aria-hidden="true" />
                {loading ? "Analyse en cours..." : "Analyser"}
              </button>
            </div>
          </>}

          {/* Fichier */}
          {mode === "file" && <>
            <div onDragOver={e => { e.preventDefault(); setDragOver(true); }} onDragLeave={() => setDragOver(false)} onDrop={handleDrop}
              onClick={() => !file && fileRef.current?.click()}
              style={{ border:`2px dashed ${dragOver ? "#7F77DD" : "rgba(255,255,255,0.15)"}`, borderRadius:12, padding:"2rem", textAlign:"center", cursor:file ? "default" : "pointer", background:dragOver ? "rgba(127,119,221,0.08)" : "rgba(255,255,255,0.02)", transition:"all 0.2s", marginBottom:12 }}>
              {!file ? <>
                <i className="ti ti-cloud-upload" style={{ fontSize:40, color:"#534AB7", display:"block", marginBottom:10 }} aria-hidden="true" />
                <p style={{ color:"#fffffe", fontSize:15, fontWeight:500, margin:"0 0 6px" }}>Glissez votre fichier ici</p>
                <p style={{ color:"#6b6d87", fontSize:13, margin:"0 0 14px" }}>ou cliquez pour parcourir</p>
                <div style={{ display:"flex", gap:6, justifyContent:"center", flexWrap:"wrap" }}>
                  {["PDF","DOCX","TXT","RTF"].map(f => (
                    <span key={f} style={{ fontSize:11, padding:"3px 10px", borderRadius:6, background:"rgba(127,119,221,0.15)", color:"#7F77DD", border:"0.5px solid rgba(127,119,221,0.3)" }}>{f}</span>
                  ))}
                </div>
                <p style={{ color:"#6b6d87", fontSize:12, marginTop:8 }}>Taille max : 20 Mo</p>
              </> : (
                <div style={{ display:"flex", alignItems:"center", gap:12, justifyContent:"center" }}>
                  <i className={`ti ${fileIcon(file.name)}`} style={{ fontSize:32, color:"#7F77DD" }} aria-hidden="true" />
                  <div style={{ textAlign:"left" }}>
                    <p style={{ color:"#fffffe", fontSize:14, fontWeight:500, margin:"0 0 3px" }}>{file.name}</p>
                    <p style={{ color:"#6b6d87", fontSize:12, margin:0 }}>{(file.size/1024).toFixed(1)} Ko</p>
                  </div>
                  <button onClick={removeFile} style={{ marginLeft:8, background:"rgba(226,75,74,0.15)", border:"0.5px solid rgba(226,75,74,0.3)", borderRadius:8, padding:"6px 10px", color:"#F09595", cursor:"pointer", fontFamily:"inherit", fontSize:13 }}>
                    <i className="ti ti-x" style={{ fontSize:14 }} aria-hidden="true" /> Retirer
                  </button>
                </div>
              )}
            </div>
            <input ref={fileRef} type="file" accept={ACCEPTED} onChange={handleFileChange} style={{ display:"none" }} />
            {file && (
              <div style={{ display:"flex", justifyContent:"flex-end" }}>
                <button onClick={handleCheckFile} disabled={loading} style={btnPrimary(loading)}>
                  <i className={`ti ${loading ? "ti-loader" : "ti-shield-search"}`} style={{ fontSize:16, animation:loading ? "spin 1s linear infinite" : "none" }} aria-hidden="true" />
                  {loading ? "Analyse en cours..." : "Analyser ce document"}
                </button>
              </div>
            )}
          </>}

          {/* Step indicator */}
          {loading && step && (
            <div style={{ marginTop:12, padding:"10px 14px", background:"rgba(127,119,221,0.1)", border:"0.5px solid rgba(127,119,221,0.3)", borderRadius:10, fontSize:13, color:"#7F77DD", display:"flex", alignItems:"center", gap:8 }}>
              <i className="ti ti-loader" style={{ fontSize:15, animation:"spin 1s linear infinite" }} aria-hidden="true" />{step}
            </div>
          )}
        </div>

        {/* Erreur */}
        {error && (
          <div style={{ padding:"12px 16px", background:"rgba(226,75,74,0.1)", border:"0.5px solid rgba(226,75,74,0.4)", borderRadius:10, color:"#F09595", fontSize:14, marginBottom:"1rem", display:"flex", gap:8 }}>
            <i className="ti ti-alert-circle" style={{ fontSize:18, flexShrink:0, marginTop:1 }} aria-hidden="true" />{error}
          </div>
        )}

        {/* Résultats */}
        {result && (
          <div style={{ animation:"fadeIn 0.4s ease" }}>
            {result.filename && (
              <div style={{ display:"flex", alignItems:"center", gap:10, padding:"10px 14px", background:"rgba(127,119,221,0.1)", border:"0.5px solid rgba(127,119,221,0.25)", borderRadius:10, marginBottom:"1rem", fontSize:13, color:"#a7a9be" }}>
                <i className="ti ti-file-check" style={{ fontSize:18, color:"#7F77DD" }} aria-hidden="true" />
                <span><strong style={{ color:"#fffffe" }}>{result.filename}</strong> — {result.page_count} page(s), {result.char_count?.toLocaleString()} caractères</span>
                {result.analysis_time && <span style={{ marginLeft:"auto", color:"#639922", fontWeight:500 }}><i className="ti ti-bolt" style={{ fontSize:13 }} aria-hidden="true" /> {result.analysis_time}s</span>}
              </div>
            )}
            {!result.filename && result.analysis_time && (
              <div style={{ textAlign:"right", marginBottom:8, fontSize:12, color:"#639922" }}>
                <i className="ti ti-bolt" style={{ fontSize:13 }} aria-hidden="true" /> Analysé en {result.analysis_time}s
              </div>
            )}

            <div style={{ background:"#1a1930", border:"0.5px solid rgba(255,255,255,0.08)", borderRadius:16, padding:"1.5rem", marginBottom:"1rem" }}>
              <span style={{ fontSize:12, fontWeight:500, color:"#6b6d87", textTransform:"uppercase", letterSpacing:".06em", display:"block", marginBottom:"1.25rem" }}>Résultat global</span>
              <ScoreGauge score={result.score} verdict={result.verdict} color={result.color} />
              <div style={{ marginTop:"1.25rem", padding:"12px 14px", background:"#13121f", borderRadius:10, fontSize:14, color:"#a7a9be", lineHeight:1.6, borderLeft:"3px solid #534AB7" }}>
                {result.summary}
              </div>
            </div>

            {result.claims?.length > 0 && <>
              <p style={{ fontSize:15, fontWeight:500, color:"#fffffe", margin:"0 0 .75rem" }}>Affirmations analysées ({result.claims.length})</p>
              {result.claims.map((c, i) => <ClaimCard key={i} claim={c} index={i + 1} />)}
            </>}
          </div>
        )}
      </div>
      <style>{`
        @keyframes spin { from{transform:rotate(0deg)} to{transform:rotate(360deg)} }
        @keyframes fadeIn { from{opacity:0;transform:translateY(10px)} to{opacity:1;transform:translateY(0)} }
      `}</style>
    </div>
  );
}
