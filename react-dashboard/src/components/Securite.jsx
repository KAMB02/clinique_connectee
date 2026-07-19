import { C } from "../utils/helpers";
import { KpiCard, Card, CardHeader, AlerteItem, StatusDot } from "./ui";

export default function Securite({ state, acquitter }) {
  const { alertes, secuEvents } = state;
  const secuFeed = alertes.filter(a => a.type === "secu");
  const rouges = alertes.filter(a=>a.niveau==="ROUGE"&&!a.ack).length;
  const badgesKo = 2; const badgesOk = 14;

  return (
    <div>
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12, marginBottom:20 }}>
        <KpiCard label="Intrusions détectées" value="1" sub="dernière heure" accentColor={C.rouge} />
        <KpiCard label="Badges refusés"        value={badgesKo} sub="dernière heure" accentColor={C.orange} />
        <KpiCard label="Badges acceptés"       value={badgesOk} sub="dernière heure" accentColor={C.vert} />
        <KpiCard label="Portes sécurisées"     value="4/4" sub="couloir-B fermé" accentColor={C.bleu} />
      </div>
      <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:16, marginBottom:16 }}>
        <Card>
          <CardHeader title="Événements sécurité récents" badge="Live" color={C.rouge} />
          <div style={{ display:"flex", flexDirection:"column", maxHeight:320, overflowY:"auto" }}>
            {secuFeed.length ? secuFeed.map(a => <AlerteItem key={a.id} alerte={a} acquitter={acquitter} />)
              : <div style={{ color:C.txt3, fontSize:12, textAlign:"center", padding:20 }}>Aucun événement récent</div>}
          </div>
        </Card>
        <Card>
          <CardHeader title="Caméra IA — Couloir B" badge="Surveillance active" color={C.vert} />
          <div style={{ background:C.card2, border:`1px solid ${C.border}`, borderRadius:8, height:160,
            display:"flex", alignItems:"center", justifyContent:"center", flexDirection:"column",
            gap:8, marginBottom:12 }}>
            <div style={{ fontSize:32 }}>📷</div>
            <div style={{ fontSize:11, color:C.txt2 }}>CAM-couloir-B · Flux simulé</div>
            <div style={{ fontSize:10, color:C.txt3 }}>Détection IA active · Seuil confiance 80%</div>
          </div>
          <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:8 }}>
            {[["Détections (1h)","3",C.txt1],["Intrusions","1",C.rouge],["Confiance moy.","89%",C.vert],["Faux positifs","0",C.vert]].map(([l,v,c])=>(
              <div key={l} style={{ background:C.card2, border:`1px solid ${C.border}`, borderRadius:6, padding:10, textAlign:"center" }}>
                <div style={{ fontFamily:"monospace", fontSize:18, fontWeight:600, color:c }}>{v}</div>
                <div style={{ fontSize:10, color:C.txt3, marginTop:3 }}>{l}</div>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <Card>
        <CardHeader title="État des dispositifs de sécurité" badge="Temps réel" color={C.bleu} />
        <div style={{ display:"grid", gridTemplateColumns:"repeat(3,1fr)", gap:10 }}>
          {secuEvents.map((s,i) => (
            <div key={i} style={{ background:C.card2, border:`1px solid ${C.border}`, borderRadius:6, padding:12,
              display:"flex", alignItems:"center", gap:10 }}>
              <div style={{ fontSize:22 }}>{s.icon}</div>
              <div style={{ flex:1 }}>
                <div style={{ fontSize:11, fontWeight:600, color:C.txt1, marginBottom:2 }}>{s.label}</div>
                <div style={{ fontSize:10, color:C.txt2 }}>{s.val}</div>
              </div>
              <StatusDot state={s.dot} />
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
