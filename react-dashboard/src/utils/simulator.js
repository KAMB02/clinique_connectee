export const INITIAL_STATE = {
  chambres: [
    { id:"CH-001", patient:"PAT-101", service:"hospit", spo2:97.5, ecg:72,  temp:36.5, sys:119, dia:79,  perf:496, co2:623 },
    { id:"CH-002", patient:"PAT-102", service:"hospit", spo2:95.8, ecg:88,  temp:36.8, sys:128, dia:83,  perf:310, co2:680 },
    { id:"CH-003", patient:"PAT-103", service:"hospit", spo2:98.1, ecg:65,  temp:36.4, sys:115, dia:75,  perf:450, co2:598 },
    { id:"CH-004", patient:"PAT-104", service:"hospit", spo2:99.0, ecg:70,  temp:36.6, sys:122, dia:80,  perf:380, co2:612 },
    { id:"CH-005", patient:"PAT-105", service:"hospit", spo2:96.2, ecg:71,  temp:37.2, sys:135, dia:88,  perf:200, co2:710 },
    { id:"SI-001", patient:"PAT-201", service:"si",     spo2:87.3, ecg:155, temp:38.8, sys:145, dia:95,  perf:120, co2:820 },
    { id:"SI-002", patient:"PAT-202", service:"si",     spo2:91.2, ecg:102, temp:37.8, sys:138, dia:91,  perf:280, co2:745 },
  ],
  circuits: [
    { name:"BLOC-A",  val:1278, max:1500, color:"#3B82F6" },
    { name:"BLOC-B",  val:851,  max:1500, color:"#00E5A0" },
    { name:"URGENCE", val:2721, max:3500, color:"#FF3B5C" },
  ],
  ups: { niveau:87, tension:220, autonomie:39, source:"SECTEUR", enCharge:true },
  generateur: { actif:false, charge:0 },
  alertes: [
    { id:1, niveau:"ROUGE",  icon:"🚨", msg:"SpO2 CRITIQUE : 87.3%",               chambre:"SI-001",    patient:"PAT-201", time:"10:02:15", ack:false, type:"vitaux" },
    { id:2, niveau:"ROUGE",  icon:"💗", msg:"FC CRITIQUE : 155 bpm",               chambre:"SI-001",    patient:"PAT-201", time:"10:02:40", ack:false, type:"vitaux" },
    { id:3, niveau:"ORANGE", icon:"🌡️", msg:"Température : 38.8°C",               chambre:"SI-001",    patient:"PAT-201", time:"10:03:25", ack:false, type:"vitaux" },
    { id:4, niveau:"ROUGE",  icon:"🔑", msg:"Badge refusé — BADGE-INCONNU-999",   chambre:"couloir-B", patient:"—",       time:"09:58:30", ack:true,  type:"secu"   },
    { id:5, niveau:"ROUGE",  icon:"📷", msg:"Intrusion caméra (confiance 94%)",   chambre:"couloir-B", patient:"—",       time:"09:55:00", ack:true,  type:"secu"   },
    { id:6, niveau:"ORANGE", icon:"💉", msg:"Perfusion basse : 120 mL restants",  chambre:"SI-001",    patient:"PAT-201", time:"10:04:10", ack:false, type:"vitaux" },
    { id:7, niveau:"VERT",   icon:"✅", msg:"SpO2 normalisée après intervention", chambre:"CH-002",    patient:"PAT-102", time:"09:50:00", ack:true,  type:"vitaux" },
    { id:8, niveau:"VERT",   icon:"✅", msg:"Tension artérielle stabilisée",      chambre:"CH-005",    patient:"PAT-105", time:"09:48:00", ack:true,  type:"vitaux" },
  ],
  secuEvents: [
    { icon:"🔑", label:"Badge RFID",     val:"14 accès · 2 refus",     dot:"warn" },
    { icon:"🚪", label:"Porte couloir-B",val:"Fermée · sécurisée",     dot:"ok"   },
    { icon:"📷", label:"Caméra IA",      val:"Surveillance active",     dot:"ok"   },
    { icon:"🔔", label:"Bouton appel",   val:"2 appels médicaux",       dot:"ok"   },
    { icon:"⚡", label:"Alimentation",   val:"Secteur nominal",         dot:"ok"   },
    { icon:"🛡️", label:"Contrôleur",    val:"1 alerte rouge active",   dot:"crit" },
  ],
  nextId: 9,
};

function rand(lo, hi) { return lo + Math.random() * (hi - lo); }
function clamp(v, lo, hi) { return Math.max(lo, Math.min(hi, v)); }

export function getAlerte(ch) {
  const si = ch.service === "si";
  if (ch.spo2 < (si?88:90) || ch.ecg > (si?140:150)) return "rouge";
  if (ch.spo2 < (si?93:94) || ch.ecg > (si?110:120) || ch.temp > 38.5) return "orange";
  return "ok";
}

export function generateTick(prev) {
  const chambres = prev.chambres.map(ch => ({
    ...ch,
    spo2: +clamp(ch.spo2 + rand(-0.3,0.3), 70, 100).toFixed(1),
    ecg:  Math.round(clamp(ch.ecg + rand(-2,2), 40, 180)),
    temp: +clamp(ch.temp + rand(-0.05,0.05), 36, 41).toFixed(1),
    perf: +Math.max(0, ch.perf - rand(0,0.5)).toFixed(1),
    co2:  Math.round(clamp(ch.co2 + rand(-5,6), 400, 1500)),
  }));
  const circuits = prev.circuits.map(c => ({
    ...c, val: Math.round(clamp(c.val + rand(-40,40), c.max*0.5, c.max)),
  }));
  const ups = { ...prev.ups, tension: +clamp(prev.ups.tension + rand(-2,2), 200, 240).toFixed(0),
    niveau: +clamp(prev.ups.niveau + (prev.ups.source==="SECTEUR"?rand(0,0.3):rand(-1,-0.2)), 0, 100).toFixed(0) };
  let newAlerte = null;
  let alertes = prev.alertes;
  if (Math.random() < 0.03) {
    const ch = chambres[Math.floor(Math.random()*chambres.length)];
    const duree = Math.floor(rand(200,2500));
    const a = { id:prev.nextId, niveau:"ORANGE", icon:"🔔",
      msg:`Appel médical — ${ch.id} (${duree}ms)`, chambre:ch.id, patient:ch.patient,
      time: new Date().toLocaleTimeString("fr-FR"), ack:false, type:"vitaux" };
    alertes = [a, ...prev.alertes];
    newAlerte = { title:"Appel médical", msg:a.msg, niveau:"orange" };
  }
  return { state:{...prev, chambres, circuits, ups, alertes, nextId:prev.nextId+(newAlerte?1:0)}, newAlerte };
}
