import { useState, useEffect } from "react";
import { C } from "../utils/helpers";

const TABS = [
  { id:"overview", label:"Vue globale" },
  { id:"patients", label:"Patients"    },
  { id:"securite", label:"Sécurité"   },
  { id:"energie",  label:"Énergie"    },
  { id:"alertes",  label:"Alertes"    },
  { id:"historique", label:"📊 Historique" },
  { id:"carte",    label:"🗺️ Carte"   },
];

const STATUS_CONFIG = {
  connecting: { color:"#F59E0B", label:"Connexion…",     dot:"#F59E0B" },
  live:       { color:C.vert,    label:"Live · IoT actif", dot:C.vert   },
  fallback:   { color:C.orange,  label:"Simulation",      dot:C.orange  },
};

export default function Topbar({ tab, setTab, nbAlertes, dataStatus="connecting" }) {
  const [clock, setClock] = useState(new Date().toLocaleTimeString("fr-FR"));
  useEffect(() => { const t = setInterval(()=>setClock(new Date().toLocaleTimeString("fr-FR")),1000); return ()=>clearInterval(t); },[]);
  const status = STATUS_CONFIG[dataStatus] || STATUS_CONFIG.connecting;
  return (
    <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between",
      padding:"0 24px", height:56, background:C.card,
      borderBottom:`1px solid ${C.border}`, position:"sticky", top:0, zIndex:100 }}>

      <div style={{ display:"flex", alignItems:"center", gap:10 }}>
        <div style={{ width:32, height:32, background:"linear-gradient(135deg,#3B82F6,#00E5A0)",
          borderRadius:8, display:"flex", alignItems:"center", justifyContent:"center", fontSize:16 }}>🏥</div>
        <div>
          <div style={{ fontWeight:700, fontSize:15, color:C.txt1 }}>Clinique Connectée</div>
          <div style={{ fontSize:10, color:C.txt2, letterSpacing:"0.05em", textTransform:"uppercase" }}>Abidjan · Cocody · UFHB</div>
        </div>
      </div>

      <div style={{ display:"flex", gap:3, background:C.bg, border:`1px solid ${C.border}`, borderRadius:8, padding:3 }}>
        {TABS.map(t => (
          <button key={t.id} onClick={()=>setTab(t.id)}
            style={{ padding:"5px 14px", borderRadius:5, border:"none", cursor:"pointer",
              fontFamily:"inherit", fontSize:12, fontWeight:500, letterSpacing:"0.02em", transition:"all 0.15s",
              background:tab===t.id ? C.card2 : "transparent",
              color:tab===t.id ? C.txt1 : C.txt2,
              boxShadow:tab===t.id ? "0 1px 3px rgba(0,0,0,0.4)" : "none" }}>
            {t.label}
          </button>
        ))}
      </div>

      <div style={{ display:"flex", alignItems:"center", gap:12 }}>
        <div style={{ display:"flex", alignItems:"center", gap:6 }}>
          <div style={{ width:7, height:7, background:status.dot, borderRadius:"50%",
            boxShadow:`0 0 8px ${status.dot}`,
            animation: dataStatus==="live" ? "pulse 2s infinite" : "none" }} />
          <span style={{ fontSize:11, color:status.color, fontWeight:500 }}>{status.label}</span>
        </div>
        <span style={{ fontFamily:"monospace", fontSize:12, color:C.txt2 }}>{clock}</span>
        <button onClick={()=>setTab("alertes")}
          style={{ background:nbAlertes>0?`${C.rouge}18`:`${C.vert}18`,
            border:`1px solid ${nbAlertes>0?C.rouge:C.vert}`,
            color:nbAlertes>0?C.rouge:C.vert,
            borderRadius:20, padding:"2px 10px", fontSize:11, fontWeight:600, cursor:"pointer", fontFamily:"inherit" }}>
          {nbAlertes>0 ? `● ${nbAlertes} alertes` : "✓ Aucune alerte"}
        </button>
      </div>
    </div>
  );
}
