import { useState } from "react";
import { C } from "../utils/helpers";
import { KpiCard, Card, CardHeader, AlerteItem } from "./ui";

export default function Alertes({ state, acquitter }) {
  const [filtre, setFiltre] = useState("all");
  const { alertes } = state;
  const actives  = alertes.filter(a=>!a.ack);
  const rouges   = actives.filter(a=>a.niveau==="ROUGE").length;
  const oranges  = actives.filter(a=>a.niveau==="ORANGE").length;
  const verts    = alertes.filter(a=>a.niveau==="VERT").length;
  const filtered = filtre==="all" ? alertes : alertes.filter(a=>a.niveau===filtre);

  const FILTRES = [
    { id:"all",    label:"Toutes",      color:C.bleu   },
    { id:"ROUGE",  label:"🔴 Critiques", color:C.rouge  },
    { id:"ORANGE", label:"🟠 Avert.",    color:C.orange },
    { id:"VERT",   label:"🟢 Résolues",  color:C.vert   },
  ];

  return (
    <div>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:12, marginBottom:20 }}>
        <KpiCard label="🔴 ROUGE — Critiques"       value={rouges}  sub="nécessitent action immédiate" accentColor={C.rouge}  />
        <KpiCard label="🟠 ORANGE — Avertissements" value={oranges} sub="à surveiller"                 accentColor={C.orange} />
        <KpiCard label="🟢 VERT — Résolues (1h)"   value={verts}   sub="normalisées"                  accentColor={C.vert}   />
      </div>
      <Card>
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16 }}>
          <span style={{ fontSize:12, fontWeight:600, color:C.txt1, textTransform:"uppercase", letterSpacing:"0.06em" }}>
            Historique complet des alertes
          </span>
          <div style={{ display:"flex", gap:6 }}>
            {FILTRES.map(f => (
              <button key={f.id} onClick={()=>setFiltre(f.id)}
                style={{ fontSize:10, padding:"4px 10px", border:`1px solid ${filtre===f.id?f.color:C.border}`,
                  borderRadius:4, background:filtre===f.id?`${f.color}18`:"transparent",
                  color:filtre===f.id?f.color:C.txt2, cursor:"pointer", fontFamily:"inherit", transition:"all 0.15s" }}>
                {f.label}
              </button>
            ))}
          </div>
        </div>
        <div style={{ display:"flex", flexDirection:"column", maxHeight:400, overflowY:"auto" }}>
          {filtered.length ? filtered.map(a => <AlerteItem key={a.id} alerte={a} acquitter={acquitter} />)
            : <div style={{ color:C.txt3, fontSize:12, textAlign:"center", padding:20 }}>Aucune alerte dans cette catégorie</div>}
        </div>
      </Card>
    </div>
  );
}
