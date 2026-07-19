import { C } from "../utils/helpers";

export const s = {
  card: { background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:"18px 20px" },
  cardHeader: { display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:16 },
  cardTitle: { fontSize:12, fontWeight:600, color:C.txt1, textTransform:"uppercase", letterSpacing:"0.06em" },
  mono: { fontFamily:"'JetBrains Mono',monospace" },
  row: { display:"flex", alignItems:"center", gap:8 },
};

export function Badge({ children, color }) {
  return <span style={{ fontSize:10, fontWeight:600, padding:"2px 8px", borderRadius:20,
    textTransform:"uppercase", letterSpacing:"0.05em",
    background:`${color}22`, color, border:`1px solid ${color}44` }}>
    {children}
  </span>;
}

export function Card({ children, style }) {
  return <div style={{...s.card, ...style}}>{children}</div>;
}

export function CardHeader({ title, badge, color }) {
  return <div style={s.cardHeader}>
    <span style={s.cardTitle}>{title}</span>
    {badge && <Badge color={color || C.bleu}>{badge}</Badge>}
  </div>;
}

export function KpiCard({ label, value, sub, accentColor }) {
  return <div style={{ ...s.card, position:"relative", overflow:"hidden", cursor:"pointer" }}>
    <div style={{ position:"absolute", top:0, left:0, right:0, height:2, background:accentColor }} />
    <div style={{ fontSize:10, color:C.txt2, textTransform:"uppercase", letterSpacing:"0.08em", fontWeight:600, marginBottom:8 }}>
      {label}
    </div>
    <div style={{ ...s.mono, fontSize:28, fontWeight:500, lineHeight:1, color:accentColor, marginBottom:4 }}>
      {value}
    </div>
    <div style={{ fontSize:10, color:C.txt3 }}>{sub}</div>
  </div>;
}

export function AlerteItem({ alerte, acquitter }) {
  const colors = { ROUGE:C.rouge, ORANGE:C.orange, VERT:C.vert };
  const col = colors[alerte.niveau] || C.vert;
  return <div style={{ display:"flex", alignItems:"flex-start", gap:10, padding:"10px 12px",
    borderRadius:6, borderLeft:`3px solid ${col}`,
    background:`${col}08`, marginBottom:6,
    animation:"slideIn 0.3s ease-out" }}>
    <div style={{ fontSize:14, marginTop:1, flexShrink:0 }}>{alerte.icon}</div>
    <div style={{ flex:1, minWidth:0 }}>
      <div style={{ fontSize:12, fontWeight:500, color:C.txt1, marginBottom:2 }}>{alerte.msg}</div>
      <div style={{ fontSize:10, color:C.txt3, display:"flex", gap:8 }}>
        <span>{alerte.chambre}</span><span>·</span>
        <span>{alerte.patient}</span><span>·</span>
        <span style={{ fontFamily:"monospace" }}>{alerte.time}</span>
        {alerte.ack && <span style={{ color:C.vert }}>✓ Acquittée</span>}
      </div>
    </div>
    {!alerte.ack && acquitter && (
      <button onClick={() => acquitter(alerte.id)}
        style={{ fontSize:10, padding:"3px 8px", border:`1px solid ${C.border}`, borderRadius:4,
          background:"transparent", color:C.txt2, cursor:"pointer", fontFamily:"inherit",
          flexShrink:0, transition:"all 0.15s", alignSelf:"center" }}>
        ACK
      </button>
    )}
  </div>;
}

export function ProgressBar({ val, max, color, height=6 }) {
  const pct = Math.round((val/max)*100);
  return <div style={{ height, background:C.border, borderRadius:height/2, overflow:"hidden" }}>
    <div style={{ height:"100%", width:`${pct}%`, background:color, borderRadius:height/2, transition:"width 0.5s" }} />
  </div>;
}

export function Gauge({ pct, color, size=80 }) {
  const r = 32; const circ = 2*Math.PI*r;
  const offset = circ - (pct/100)*circ;
  return <div style={{ position:"relative", display:"inline-block" }}>
    <svg width={size} height={size} viewBox="0 0 80 80" style={{ transform:"rotate(-90deg)" }}>
      <circle cx="40" cy="40" r={r} fill="none" stroke={C.border} strokeWidth="6"/>
      <circle cx="40" cy="40" r={r} fill="none" stroke={color} strokeWidth="6"
        strokeDasharray={circ} strokeDashoffset={offset} strokeLinecap="round"
        style={{ transition:"stroke-dashoffset 0.5s" }}/>
    </svg>
    <div style={{ position:"absolute", inset:0, display:"flex", flexDirection:"column",
      alignItems:"center", justifyContent:"center" }}>
      <div style={{ ...s.mono, fontSize:16, fontWeight:600, color }}>{pct}%</div>
    </div>
  </div>;
}

export function StatusDot({ state }) {
  const colors = { ok:C.vert, warn:C.orange, crit:C.rouge };
  const col = colors[state] || C.vert;
  return <div style={{ width:8, height:8, borderRadius:"50%", background:col,
    boxShadow:`0 0 6px ${col}`, flexShrink:0,
    animation: state !== "ok" ? "pulse 1.5s infinite" : "none" }} />;
}
