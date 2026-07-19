import { C } from "../utils/helpers";
import { KpiCard, Card, CardHeader, Gauge, ProgressBar } from "./ui";

export default function Energie({ state }) {
  const { ups, generateur, circuits } = state;
  const totalW = circuits.reduce((s,c)=>s+c.val,0);
  return (
    <div>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12, marginBottom:20 }}>
        <KpiCard label="Batterie UPS"   value={ups.niveau}   sub={`% · ${ups.autonomie} min autonomie`} accentColor={C.jaune}  />
        <KpiCard label="Tension secteur" value={ups.tension}  sub="V · Nominal"                         accentColor={C.vert}   />
        <KpiCard label="Conso totale"   value={(totalW/1000).toFixed(1)} sub="kW · 3 circuits"          accentColor={C.bleu}   />
        <KpiCard label="Source active"  value={ups.source}   sub="Générateur en veille"                 accentColor={C.violet} />
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr 1fr", gap:16 }}>
        <Card>
          <CardHeader title="UPS" badge="En charge" color={C.vert} />
          <div style={{ display:"flex", justifyContent:"center", marginBottom:16 }}>
            <Gauge pct={ups.niveau} color={C.jaune} size={100} />
          </div>
          {[["Niveau batterie",`${ups.niveau}%`,C.jaune],["Tension",`${ups.tension} V`,C.vert],["Statut","En charge",C.vert],["Autonomie",`${ups.autonomie} min`,C.bleu]].map(([l,v,c])=>(
            <div key={l} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
              padding:"8px 0", borderBottom:`1px solid ${C.border}` }}>
              <span style={{ fontSize:11, color:C.txt2 }}>{l}</span>
              <span style={{ fontFamily:"monospace", fontSize:13, fontWeight:600, color:c }}>{v}</span>
            </div>
          ))}
        </Card>
        <Card>
          <CardHeader title="Groupe électrogène" badge={generateur.actif?"Actif":"En veille"} color={generateur.actif?C.orange:C.vert} />
          <div style={{ display:"flex", justifyContent:"center", marginBottom:16 }}>
            <Gauge pct={generateur.charge} color={generateur.actif?C.orange:C.txt3} size={100} />
          </div>
          {[["Statut",generateur.actif?"ON":"OFF",generateur.actif?C.orange:C.txt2],["Charge",`${generateur.charge}%`,C.txt2],["Carburant","Plein",C.vert],["Démarrage","Auto (UPS<10%)",C.txt2]].map(([l,v,c])=>(
            <div key={l} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
              padding:"8px 0", borderBottom:`1px solid ${C.border}` }}>
              <span style={{ fontSize:11, color:C.txt2 }}>{l}</span>
              <span style={{ fontFamily:"monospace", fontSize:13, fontWeight:600, color:c }}>{v}</span>
            </div>
          ))}
        </Card>
        <Card>
          <CardHeader title="Compteurs circuits" badge="3 circuits" color={C.bleu} />
          <div style={{ display:"flex", flexDirection:"column", gap:16, marginTop:4 }}>
            {circuits.map(c => (
              <div key={c.name}>
                <div style={{ display:"flex", justifyContent:"space-between", marginBottom:6 }}>
                  <span style={{ fontSize:12, fontWeight:600, color:C.txt1 }}>{c.name}</span>
                  <span style={{ fontFamily:"monospace", fontSize:12, color:c.color }}>{c.val} W</span>
                </div>
                <ProgressBar val={c.val} max={c.max} color={c.color} height={8} />
                <div style={{ fontSize:10, color:C.txt3, marginTop:3, textAlign:"right" }}>
                  {Math.round(c.val/c.max*100)}% de capacité max ({c.max}W)
                </div>
              </div>
            ))}
            <div style={{ marginTop:4, paddingTop:12, borderTop:`1px solid ${C.border}` }}>
              <div style={{ display:"flex", justifyContent:"space-between" }}>
                <span style={{ fontSize:12, fontWeight:600, color:C.txt1 }}>TOTAL</span>
                <span style={{ fontFamily:"monospace", fontSize:14, fontWeight:700, color:C.bleu }}>{(totalW/1000).toFixed(2)} kW</span>
              </div>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
}
