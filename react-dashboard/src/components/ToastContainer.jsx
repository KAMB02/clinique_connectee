import { C } from "../utils/helpers";
const COLORS = { rouge:C.rouge, orange:C.orange, vert:C.vert };
const ICONS  = { rouge:"🚨", orange:"⚠️", vert:"✅" };
export default function ToastContainer({ toasts, setToasts }) {
  if (!toasts.length) return null;
  return (
    <div style={{ position:"fixed", top:70, right:20, zIndex:999, display:"flex", flexDirection:"column", gap:8 }}>
      {toasts.map(t => (
        <div key={t.id} style={{ background:C.card, border:`1px solid ${C.border}`,
          borderLeft:`3px solid ${COLORS[t.niveau]}`, borderRadius:10, padding:"12px 16px",
          minWidth:280, maxWidth:340, display:"flex", alignItems:"flex-start", gap:10,
          boxShadow:"0 8px 32px rgba(0,0,0,0.5)", animation:"slideIn 0.3s ease-out" }}>
          <div style={{ fontSize:18 }}>{ICONS[t.niveau]}</div>
          <div>
            <div style={{ fontSize:12, fontWeight:700, color:C.txt1, marginBottom:2 }}>{t.title}</div>
            <div style={{ fontSize:11, color:C.txt2 }}>{t.msg}</div>
          </div>
          <button onClick={() => setToasts(p => p.filter(x => x.id !== t.id))}
            style={{ marginLeft:"auto", background:"none", border:"none", color:C.txt3,
              cursor:"pointer", fontSize:14, flexShrink:0 }}>✕</button>
        </div>
      ))}
    </div>
  );
}
