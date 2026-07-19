import { useState } from "react";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import L from "leaflet";
import { C } from "../utils/helpers";
import { getAlerte } from "../utils/simulator";

// Icône par défaut Leaflet cassée avec Vite (chemins d'assets) — on la
// redéfinit explicitement avec des URLs CDN pour éviter le marqueur cassé.
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png",
  iconUrl:       "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png",
  shadowUrl:     "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png",
});

// Coordonnées approximatives — Cocody, Abidjan, Côte d'Ivoire
const CLINIQUE_LATLNG = [5.3599, -3.9861];

const PLAN = {
  width: 800, height: 560,
  zones: [
    { id:"zone-hospit", label:"Hospitalisation", x:30, y:30, w:460, h:280, color:C.bleu },
    { id:"zone-si",     label:"Soins Intensifs", x:510, y:30, w:260, h:280, color:C.violet },
    { id:"zone-couloir",label:"Couloirs & Accès", x:30, y:330, w:740, h:110, color:C.orange },
    { id:"zone-energie",label:"Salle Technique — Énergie", x:30, y:460, w:740, h:80, color:C.jaune },
  ],
  chambres: [
    { id:"CH-001", x:55,  y:120, w:72, h:80, label:"CH-001" },
    { id:"CH-002", x:143, y:120, w:72, h:80, label:"CH-002" },
    { id:"CH-003", x:231, y:120, w:72, h:80, label:"CH-003" },
    { id:"CH-004", x:319, y:120, w:72, h:80, label:"CH-004" },
    { id:"CH-005", x:407, y:120, w:72, h:80, label:"CH-005" },
    { id:"SI-001", x:530, y:120, w:100, h:80, label:"SI-001" },
    { id:"SI-002", x:645, y:120, w:100, h:80, label:"SI-002" },
  ],
  capteurs_secu: [
    { id:"porte",  x:310, y:340, icon:"🚪", label:"Porte" },
    { id:"badge",  x:390, y:340, icon:"🔑", label:"Badge RFID" },
    { id:"camera", x:470, y:340, icon:"📷", label:"Caméra IA" },
    { id:"ctrl",   x:560, y:340, icon:"🛡️", label:"Contrôleur" },
  ],
  capteurs_energie: [
    { id:"ups",   x:120, y:488, icon:"🔋", label:"UPS" },
    { id:"gen",   x:320, y:488, icon:"⚡", label:"Groupe Élec." },
    { id:"cpta",  x:500, y:488, icon:"📊", label:"Compteur A" },
    { id:"cptb",  x:600, y:488, icon:"📊", label:"Compteur B" },
    { id:"cptu",  x:700, y:488, icon:"🏥", label:"URGENCE" },
  ],
};

function ChambreRect({ ch, chambreData, selected, onClick }) {
  const data = chambreData?.find(c => c.id === ch.id);
  const alerte = data ? getAlerte(data) : "ok";
  const col = alerte==="rouge" ? C.rouge : alerte==="orange" ? C.orange : C.vert;
  const isSI = ch.id.startsWith("SI");
  return (
    <g onClick={() => onClick(ch.id)} style={{ cursor:"pointer" }}>
      <rect x={ch.x} y={ch.y} width={ch.w} height={ch.h} rx={8}
        fill={selected===ch.id ? `${col}30` : `${col}12`}
        stroke={col} strokeWidth={selected===ch.id ? 2.5 : 1.5} />
      {/* Barre d'alerte en haut */}
      <rect x={ch.x} y={ch.y} width={ch.w} height={3} rx={2} fill={col} />
      {/* Label chambre */}
      <text x={ch.x+ch.w/2} y={ch.y+18} textAnchor="middle"
        fill={col} fontSize={isSI?12:10} fontWeight={700} fontFamily="monospace">{ch.label}</text>
      {/* Vitaux condensés */}
      {data && <>
        <text x={ch.x+6} y={ch.y+36} fill={C.txt2} fontSize={9} fontFamily="monospace">SpO2</text>
        <text x={ch.x+ch.w-6} y={ch.y+36} fill={
          data.spo2<88?C.rouge:data.spo2<94?C.orange:C.vert
        } fontSize={10} fontFamily="monospace" textAnchor="end" fontWeight={600}>{data.spo2}%</text>
        <text x={ch.x+6} y={ch.y+50} fill={C.txt2} fontSize={9} fontFamily="monospace">FC</text>
        <text x={ch.x+ch.w-6} y={ch.y+50} fill={
          data.ecg>150?C.rouge:data.ecg>120?C.orange:C.vert
        } fontSize={10} fontFamily="monospace" textAnchor="end" fontWeight={600}>{data.ecg}bpm</text>
        <text x={ch.x+6} y={ch.y+64} fill={C.txt2} fontSize={9} fontFamily="monospace">T°</text>
        <text x={ch.x+ch.w-6} y={ch.y+64} fill={
          data.temp>38.5?C.orange:C.vert
        } fontSize={10} fontFamily="monospace" textAnchor="end" fontWeight={600}>{data.temp}°C</text>
        {/* Patient */}
        <text x={ch.x+ch.w/2} y={ch.y+ch.h-8} fill={C.txt3} fontSize={8} fontFamily="monospace" textAnchor="middle">
          {data.patient}
        </text>
      </>}
      {/* Icône alerte si critique */}
      {alerte === "rouge" && (
        <text x={ch.x+ch.w-12} y={ch.y+14} fontSize={10} textAnchor="middle">🔴</text>
      )}
      {alerte === "orange" && (
        <text x={ch.x+ch.w-12} y={ch.y+14} fontSize={10} textAnchor="middle">🟠</text>
      )}
    </g>
  );
}

export default function Carte({ state, setTab }) {
  const [selected, setSelected] = useState(null);
  const { chambres, ups, alertes } = state;
  const selectedData = chambres.find(c => c.id === selected);
  const alertesRouges = alertes.filter(a=>!a.ack&&a.niveau==="ROUGE").length;
  const alertesOranges = alertes.filter(a=>!a.ack&&a.niveau==="ORANGE").length;

  return (
    <div>
      {/* LÉGENDE + KPIs */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12, marginBottom:16 }}>
        {[
          ["🔴 Alertes critiques", alertesRouges, C.rouge],
          ["🟠 Avertissements",   alertesOranges, C.orange],
          ["⚡ UPS",              `${ups.niveau}%`, C.jaune],
          ["🏥 Chambres actives", "7/7", C.vert],
        ].map(([l,v,c])=>(
          <div key={l} style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:10,
            padding:"12px 16px", borderTop:`2px solid ${c}` }}>
            <div style={{ fontSize:10, color:C.txt2, marginBottom:6, fontWeight:600, textTransform:"uppercase", letterSpacing:"0.06em" }}>{l}</div>
            <div style={{ fontFamily:"monospace", fontSize:22, fontWeight:600, color:c }}>{v}</div>
          </div>
        ))}
      </div>

      {/* MINI CARTE GÉO — Localisation réelle de la clinique */}
      <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:16, marginBottom:16 }}>
        <div style={{ fontSize:12, fontWeight:600, textTransform:"uppercase", letterSpacing:"0.06em", marginBottom:10, color:C.txt2 }}>
          📍 Localisation — Cocody, Abidjan
        </div>
        <div style={{ borderRadius:8, overflow:"hidden", border:`1px solid ${C.border}` }}>
          <MapContainer
            center={CLINIQUE_LATLNG}
            zoom={14}
            scrollWheelZoom={false}
            style={{ height: 220, width: "100%", background: C.bg }}
          >
            <TileLayer
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            />
            <Marker position={CLINIQUE_LATLNG}>
              <Popup>
                <strong>Clinique Connectée</strong><br />
                Cocody, Abidjan — UFHB
              </Popup>
            </Marker>
          </MapContainer>
        </div>
      </div>

      <div style={{ display:"grid", gridTemplateColumns:"1fr auto", gap:16 }}>
        {/* PLAN SVG */}
        <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:20 }}>
          <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:14 }}>
            <span style={{ fontSize:12, fontWeight:600, textTransform:"uppercase", letterSpacing:"0.06em" }}>
              Plan de la Clinique — Cocody, Abidjan
            </span>
            <div style={{ display:"flex", gap:12 }}>
              {[["🟢 Nominal",C.vert],["🟠 Avert.",C.orange],["🔴 Critique",C.rouge]].map(([l,c])=>(
                <span key={l} style={{ fontSize:10, color:c, fontWeight:600 }}>{l}</span>
              ))}
            </div>
          </div>

          <svg viewBox={`0 0 ${PLAN.width} ${PLAN.height}`} style={{ width:"100%", height:"auto", display:"block" }}>
            {/* Fond */}
            <rect width={PLAN.width} height={PLAN.height} fill="#0A0E17" rx={12} />

            {/* Zones principales */}
            {PLAN.zones.map(z => (
              <g key={z.id}>
                <rect x={z.x} y={z.y} width={z.w} height={z.h} rx={10}
                  fill={`${z.color}08`} stroke={`${z.color}30`} strokeWidth={1.5} />
                <text x={z.x+10} y={z.y+18} fill={`${z.color}99`}
                  fontSize={10} fontWeight={700} fontFamily="Inter,sans-serif"
                  textTransform="uppercase" letterSpacing={2}>{z.label.toUpperCase()}</text>
              </g>
            ))}

            {/* CHAMBRES */}
            {PLAN.chambres.map(ch => (
              <ChambreRect key={ch.id} ch={ch} chambreData={chambres}
                selected={selected} onClick={setSelected} />
            ))}

            {/* COULOIR — capteurs sécurité */}
            {PLAN.capteurs_secu.map(cap => (
              <g key={cap.id} onClick={()=>setTab("securite")} style={{ cursor:"pointer" }}>
                <circle cx={cap.x} cy={cap.y+20} r={22} fill={`${C.orange}15`} stroke={`${C.orange}40`} strokeWidth={1.5} />
                <text x={cap.x} y={cap.y+25} textAnchor="middle" fontSize={16}>{cap.icon}</text>
                <text x={cap.x} y={cap.y+46} textAnchor="middle" fill={C.txt3} fontSize={8} fontFamily="monospace">{cap.label}</text>
              </g>
            ))}

            {/* Porte avec animation si alerte */}
            <rect x={220} y={310} width={40} height={20} rx={4} fill={`${C.bleu}20`} stroke={C.bleu} strokeWidth={1} />
            <text x={240} y={325} textAnchor="middle" fill={C.bleu} fontSize={9} fontFamily="monospace">ENTRÉE</text>

            {/* ÉNERGIE — capteurs */}
            {PLAN.capteurs_energie.map(cap => (
              <g key={cap.id} onClick={()=>setTab("energie")} style={{ cursor:"pointer" }}>
                <rect x={cap.x-24} y={cap.y-18} width={48} height={48} rx={6}
                  fill={`${C.jaune}12`} stroke={`${C.jaune}35`} strokeWidth={1.5} />
                <text x={cap.x} y={cap.y+8} textAnchor="middle" fontSize={14}>{cap.icon}</text>
                <text x={cap.x} y={cap.y+24} textAnchor="middle" fill={C.txt3} fontSize={7} fontFamily="monospace">{cap.label}</text>
              </g>
            ))}

            {/* UPS niveau indicateur */}
            <text x={120} y={516} textAnchor="middle" fill={C.jaune} fontSize={9} fontFamily="monospace" fontWeight={700}>
              {ups.niveau}%
            </text>

            {/* Lignes de connexion MQTT symboliques */}
            <g opacity="0.15" stroke={C.bleu} strokeWidth="0.8" strokeDasharray="4 3">
              {PLAN.chambres.map(ch => (
                <line key={`line-${ch.id}`} x1={ch.x+ch.w/2} y1={ch.y+ch.h} x2={380} y2={330} />
              ))}
              {PLAN.capteurs_secu.map(cap => (
                <line key={`secu-${cap.id}`} x1={cap.x} y1={cap.y+42} x2={380} y2={440} />
              ))}
            </g>

            {/* Label MQTT broker central */}
            <g>
              <circle cx={380} cy={328} r={14} fill={`${C.bleu}25`} stroke={C.bleu} strokeWidth={1.5} />
              <text x={380} y={333} textAnchor="middle" fontSize={8} fill={C.bleu} fontWeight={700} fontFamily="monospace">MQTT</text>
            </g>
          </svg>

          {/* Légende zones */}
          <div style={{ display:"flex", gap:16, marginTop:12, paddingTop:12, borderTop:`1px solid ${C.border}`, flexWrap:"wrap" }}>
            {[["Hospit.",C.bleu],["Soins Intensifs",C.violet],["Sécurité",C.orange],["Énergie",C.jaune],["Broker MQTT",C.bleu]].map(([l,c])=>(
              <div key={l} style={{ display:"flex", alignItems:"center", gap:6 }}>
                <div style={{ width:10, height:10, borderRadius:2, background:c, opacity:0.7 }} />
                <span style={{ fontSize:10, color:C.txt2 }}>{l}</span>
              </div>
            ))}
          </div>
        </div>

        {/* PANNEAU DÉTAIL CHAMBRE SÉLECTIONNÉE */}
        <div style={{ width:220 }}>
          {selected && selectedData ? (
            <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:16 }}>
              <div style={{ display:"flex", justifyContent:"space-between", alignItems:"center", marginBottom:14 }}>
                <div>
                  <div style={{ fontFamily:"monospace", fontSize:11, color:C.txt3 }}>{selectedData.id}</div>
                  <div style={{ fontSize:14, fontWeight:700, color:C.txt1 }}>{selectedData.patient}</div>
                </div>
                <button onClick={()=>setSelected(null)}
                  style={{ background:"none", border:"none", color:C.txt3, cursor:"pointer", fontSize:16 }}>✕</button>
              </div>
              <span style={{ fontSize:9, fontWeight:700, padding:"2px 7px", borderRadius:4,
                background:selectedData.service==="si"?"rgba(139,92,246,0.2)":"rgba(59,130,246,0.1)",
                color:selectedData.service==="si"?C.violet:C.bleu, display:"inline-block", marginBottom:12 }}>
                {selectedData.service==="si"?"Soins Intensifs":"Hospitalisation"}
              </span>
              {[
                ["SpO2",    `${selectedData.spo2}%`,          selectedData.spo2<90?C.rouge:selectedData.spo2<94?C.orange:C.vert],
                ["FC",      `${selectedData.ecg} bpm`,        selectedData.ecg>150?C.rouge:selectedData.ecg>120?C.orange:C.vert],
                ["Temp.",   `${selectedData.temp}°C`,         selectedData.temp>38.5?C.orange:C.vert],
                ["Pression",`${selectedData.sys}/${selectedData.dia} mmHg`, C.txt1],
                ["Perfusion",`${selectedData.perf} mL`,       selectedData.perf<150?C.orange:C.vert],
                ["CO2",     `${selectedData.co2} ppm`,        selectedData.co2>1000?C.orange:C.vert],
              ].map(([l,v,c])=>(
                <div key={l} style={{ display:"flex", justifyContent:"space-between", alignItems:"center",
                  padding:"7px 0", borderBottom:`1px solid ${C.border}` }}>
                  <span style={{ fontSize:11, color:C.txt2 }}>{l}</span>
                  <span style={{ fontFamily:"monospace", fontSize:12, fontWeight:600, color:c }}>{v}</span>
                </div>
              ))}
              <button onClick={()=>setTab("patients")}
                style={{ width:"100%", marginTop:12, padding:"8px", background:`${C.bleu}18`,
                  border:`1px solid ${C.bleu}44`, borderRadius:6, color:C.bleu,
                  fontSize:11, fontWeight:600, cursor:"pointer", fontFamily:"inherit" }}>
                Voir monitoring complet →
              </button>
            </div>
          ) : (
            <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:16 }}>
              <div style={{ fontSize:11, fontWeight:600, color:C.txt1, marginBottom:12 }}>Légende capteurs</div>
              {[
                ["🛏️","Chambre patient","Clic pour détails"],
                ["🚪","Porte sécurisée","Détecteur ouverture"],
                ["🔑","Badge RFID","Contrôle accès"],
                ["📷","Caméra IA","Détection intrusion"],
                ["🔋","UPS","Alimentation secours"],
                ["⚡","Groupe élec.","Alimentation d'urgence"],
              ].map(([icon,label,desc])=>(
                <div key={label} style={{ display:"flex", alignItems:"flex-start", gap:8, marginBottom:10 }}>
                  <span style={{ fontSize:16, flexShrink:0 }}>{icon}</span>
                  <div>
                    <div style={{ fontSize:11, fontWeight:600, color:C.txt1 }}>{label}</div>
                    <div style={{ fontSize:9, color:C.txt3 }}>{desc}</div>
                  </div>
                </div>
              ))}
              <div style={{ marginTop:12, padding:10, background:C.card2, borderRadius:6, fontSize:10, color:C.txt3 }}>
                Cliquez sur une chambre pour voir ses vitaux en temps réel
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
