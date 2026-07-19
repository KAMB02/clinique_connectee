import { C } from "../utils/helpers";
import { KpiCard, Card, CardHeader, AlerteItem, ProgressBar, Gauge, StatusDot, Badge } from "./ui";
import { getAlerte } from "../utils/simulator";

function ChambreCard({ ch, onClick }) {
  const alerte = getAlerte(ch);
  const borderColor = alerte==="rouge"?`${C.rouge}44`:alerte==="orange"?`${C.orange}44`:C.border;
  const accentColor = alerte==="rouge"?C.rouge:alerte==="orange"?C.orange:C.vert;
  const spo2Color = ch.spo2<88?C.rouge:ch.spo2<94?C.orange:C.vert;
  const ecgColor  = ch.ecg>150?C.rouge:ch.ecg>120?C.orange:C.vert;
  const tempColor = ch.temp>40?C.rouge:ch.temp>38.5?C.orange:C.vert;
  return (
    <div onClick={onClick} style={{ background:C.card2, border:`1px solid ${borderColor}`,
      borderRadius:12, padding:12, cursor:"pointer", position:"relative", overflow:"hidden",
      transition:"all 0.2s" }}>
      <div style={{ position:"absolute", bottom:0, left:0, right:0, height:3, background:accentColor }} />
      <div style={{ fontFamily:"monospace", fontSize:10, color:C.txt3, marginBottom:2 }}>{ch.id}</div>
      <div style={{ fontSize:12, fontWeight:700, color:C.txt1, marginBottom:4 }}>{ch.patient}</div>
      <span style={{ fontSize:9, fontWeight:700, padding:"2px 5px", borderRadius:4,
        background: ch.service==="si"?"rgba(139,92,246,0.2)":"rgba(59,130,246,0.1)",
        color: ch.service==="si"?C.violet:C.bleu, display:"inline-block", marginBottom:8 }}>
        {ch.service==="si"?"Soins Int.":"Hospit."}
      </span>
      {[["SpO2",`${ch.spo2}%`,spo2Color],["FC",`${ch.ecg}bpm`,ecgColor],["T°",`${ch.temp}°C`,tempColor],["PA",`${ch.sys}/${ch.dia}`,"#8A9BB5"]].map(([l,v,c])=>(
        <div key={l} style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:3 }}>
          <span style={{ fontSize:9, color:C.txt3, fontWeight:500 }}>{l}</span>
          <span style={{ fontFamily:"monospace", fontSize:11, fontWeight:500, color:c }}>{v}</span>
        </div>
      ))}
    </div>
  );
}

export default function Overview({ state, setTab, acquitter }) {
  const { chambres, circuits, ups, alertes, secuEvents } = state;
  const actives = alertes.filter(a=>!a.ack);
  const rouges  = actives.filter(a=>a.niveau==="ROUGE").length;
  const oranges = actives.filter(a=>a.niveau==="ORANGE").length;
  const avgSpo2 = (chambres.reduce((s,c)=>s+c.spo2,0)/chambres.length).toFixed(1);
  const avgCo2  = Math.round(chambres.reduce((s,c)=>s+c.co2,0)/chambres.length);
  const totalW  = circuits.reduce((s,c)=>s+c.val,0);

  return (
    <div>
      {/* KPI ROW */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(6,1fr)", gap:12, marginBottom:20 }}>
        <KpiCard label="🔴 Alertes Rouges" value={rouges}  sub="critiques actives" accentColor={C.rouge}  />
        <KpiCard label="🟠 Alertes Orange" value={oranges} sub="avertissements"    accentColor={C.orange} />
        <KpiCard label="Patients surveillés" value={chambres.length} sub="7 chambres actives" accentColor={C.vert} />
        <KpiCard label="SpO2 moyen" value={avgSpo2} sub="% · toutes chambres" accentColor={C.bleu}   />
        <KpiCard label="UPS Batterie"  value={ups.niveau} sub={`% · ${ups.source}`} accentColor={C.jaune}  />
        <KpiCard label="CO2 moyen" value={avgCo2} sub="ppm · qualité air"  accentColor={C.violet} />
      </div>

      {/* CHAMBRES + ALERTES */}
      <div style={{ display:"grid", gridTemplateColumns:"1.8fr 1fr", gap:16, marginBottom:16 }}>
        <Card>
          <CardHeader title="Chambres & patients" badge="7 / 7 occupées" color={C.bleu} />
          <div style={{ display:"grid", gridTemplateColumns:"repeat(7,1fr)", gap:10 }}>
            {chambres.map(ch => <ChambreCard key={ch.id} ch={ch} onClick={()=>setTab("patients")} />)}
          </div>
        </Card>
        <Card>
          <CardHeader title="Flux d'alertes" badge={`${rouges+oranges} actives`} color={C.rouge} />
          <div style={{ display:"flex", flexDirection:"column", maxHeight:320, overflowY:"auto" }}>
            {alertes.slice(0,8).map(a => <AlerteItem key={a.id} alerte={a} acquitter={acquitter} />)}
          </div>
        </Card>
      </div>

      {/* ÉNERGIE + SÉCURITÉ */}
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
        <Card>
          <CardHeader title="Système énergétique" badge={ups.source+" nominal"} color={C.vert} />
          <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:16 }}>
            <div style={{ textAlign:"center" }}>
              <Gauge pct={ups.niveau} color={C.jaune} />
              <div style={{ fontSize:11, fontWeight:600, color:C.txt1, marginTop:6 }}>Batterie UPS</div>
              <div style={{ fontSize:10, color:C.txt2 }}>{ups.tension}V · {ups.autonomie}min</div>
            </div>
            <div style={{ textAlign:"center" }}>
              <Gauge pct={state.generateur.charge} color={C.vert} />
              <div style={{ fontSize:11, fontWeight:600, color:C.txt1, marginTop:6 }}>Groupe Élec.</div>
              <div style={{ fontSize:10, color:C.txt2 }}>En veille · OFF</div>
            </div>
            <div>
              <div style={{ fontSize:11, fontWeight:600, color:C.txt1, marginBottom:10 }}>Consommation</div>
              {circuits.map(c => (
                <div key={c.name} style={{ marginBottom:10 }}>
                  <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
                    <span style={{ fontSize:10, fontWeight:600, color:C.txt1 }}>{c.name}</span>
                    <span style={{ fontFamily:"monospace", fontSize:10, color:C.txt2 }}>{c.val}W</span>
                  </div>
                  <ProgressBar val={c.val} max={c.max} color={c.color} />
                </div>
              ))}
              <div style={{ marginTop:6, paddingTop:6, borderTop:`1px solid ${C.border}`, textAlign:"right" }}>
                <span style={{ fontFamily:"monospace", fontSize:11, color:C.bleu }}>{(totalW/1000).toFixed(1)} kW total</span>
              </div>
            </div>
          </div>
        </Card>

        <Card>
          <CardHeader title="Sécurité & accès" badge="1 alerte active" color={C.rouge} />
          <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:10 }}>
            {secuEvents.map((s,i) => (
              <div key={i} style={{ background:C.card2, border:`1px solid ${C.border}`, borderRadius:6,
                padding:12, display:"flex", alignItems:"center", gap:10 }}>
                <div style={{ fontSize:20 }}>{s.icon}</div>
                <div style={{ flex:1 }}>
                  <div style={{ fontSize:10, fontWeight:600, color:C.txt1, marginBottom:2 }}>{s.label}</div>
                  <div style={{ fontSize:9, color:C.txt2 }}>{s.val}</div>
                </div>
                <StatusDot state={s.dot} />
              </div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
