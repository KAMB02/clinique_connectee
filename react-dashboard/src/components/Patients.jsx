import { C } from "../utils/helpers";
import { Card, CardHeader, ProgressBar, KpiCard } from "./ui";

function VitalBox({ label, value, color }) {
  return (
    <div style={{ background:C.bg, borderRadius:6, padding:"6px 8px" }}>
      <div style={{ fontSize:9, color:C.txt3, marginBottom:2 }}>{label}</div>
      <div style={{ fontFamily:"monospace", fontSize:13, fontWeight:500, color }}>{value}</div>
    </div>
  );
}

export default function Patients({ state }) {
  const { chambres } = state;
  const spo2Color = v => v<88?C.rouge:v<94?C.orange:C.vert;
  const ecgColor  = v => v>150?C.rouge:v>120?C.orange:C.vert;
  const tempColor = v => v>40?C.rouge:v>38.5?C.orange:C.vert;
  const perfColor = v => v<50?C.rouge:v<150?C.orange:C.vert;
  const co2Color  = v => v>1100?C.rouge:v>900?C.orange:C.vert;

  return (
    <div>
      <Card style={{ marginBottom:16 }}>
        <CardHeader title="Monitoring vitaux — toutes chambres" badge="Actualisation 10s" color={C.bleu} />
        <div style={{ display:"grid", gridTemplateColumns:"repeat(7,1fr)", gap:12 }}>
          {chambres.map(ch => (
            <div key={ch.id} style={{ background:C.card2, border:`1px solid ${C.border}`, borderRadius:10, padding:14 }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"flex-start", marginBottom:10 }}>
                <div>
                  <div style={{ fontFamily:"monospace", fontSize:10, color:C.txt3 }}>{ch.id}</div>
                  <div style={{ fontSize:12, fontWeight:700, marginTop:2, color:C.txt1 }}>{ch.patient}</div>
                </div>
                <span style={{ fontSize:9, fontWeight:700, padding:"2px 6px", borderRadius:4,
                  background:ch.service==="si"?"rgba(139,92,246,0.2)":"rgba(59,130,246,0.1)",
                  color:ch.service==="si"?C.violet:C.bleu }}>
                  {ch.service==="si"?"SI":"HOSPIT"}
                </span>
              </div>
              <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:5 }}>
                <VitalBox label="SpO2"  value={`${ch.spo2}%`}       color={spo2Color(ch.spo2)} />
                <VitalBox label="FC"    value={`${ch.ecg} bpm`}     color={ecgColor(ch.ecg)}  />
                <VitalBox label="Temp"  value={`${ch.temp}°C`}      color={tempColor(ch.temp)} />
                <VitalBox label="PA"    value={`${ch.sys}/${ch.dia}`} color={C.vert} />
                <VitalBox label="Perf"  value={`${ch.perf} mL`}     color={perfColor(ch.perf)} />
                <VitalBox label="CO2"   value={`${ch.co2} ppm`}     color={co2Color(ch.co2)}  />
              </div>
            </div>
          ))}
        </div>
      </Card>

      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16 }}>
        <Card>
          <CardHeader title="CO2 ambiant par chambre" badge="Qualité d'air" color={C.vert} />
          <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
            {chambres.map(ch => {
              const pct = Math.min(100,(ch.co2-400)/1100*100);
              const col = co2Color(ch.co2);
              return (
                <div key={ch.id} style={{ display:"flex", alignItems:"center", gap:10 }}>
                  <span style={{ fontFamily:"monospace", fontSize:10, color:C.txt2, width:48, flexShrink:0 }}>{ch.id}</span>
                  <div style={{ flex:1 }}><ProgressBar val={pct} max={100} color={col} height={6} /></div>
                  <span style={{ fontFamily:"monospace", fontSize:10, color:col, width:60, textAlign:"right", flexShrink:0 }}>{ch.co2} ppm</span>
                </div>
              );
            })}
          </div>
        </Card>

        <Card>
          <CardHeader title="Perfusions en cours" badge={`${chambres.length} actives`} color={C.bleu} />
          <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
            {chambres.map(ch => {
              const col = perfColor(ch.perf);
              return (
                <div key={ch.id}>
                  <div style={{ display:"flex", justifyContent:"space-between", marginBottom:4 }}>
                    <span style={{ fontSize:11, fontWeight:600, color:C.txt1 }}>{ch.id} · {ch.patient}</span>
                    <span style={{ fontFamily:"monospace", fontSize:11, color:col }}>{ch.perf} mL</span>
                  </div>
                  <ProgressBar val={ch.perf} max={500} color={col} height={5} />
                </div>
              );
            })}
          </div>
        </Card>
      </div>
    </div>
  );
}
