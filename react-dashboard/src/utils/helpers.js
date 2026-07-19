export const C = {
  bg:      "#0A0E17", card:    "#0F1520", card2:   "#141B2D",
  border:  "#1E2D45", borderL: "#2A4060",
  rouge:   "#FF3B5C", orange:  "#FF8C42", vert:    "#00E5A0",
  bleu:    "#3B82F6", violet:  "#8B5CF6", jaune:   "#F59E0B",
  txt1:    "#E8EEF8", txt2:    "#8A9BB5", txt3:    "#4A5A75",
};

export const NIVEAU_COLOR = { ROUGE: C.rouge, ORANGE: C.orange, VERT: C.vert };
export const NIVEAU_ICON  = { ROUGE: "🚨",    ORANGE: "⚠️",      VERT: "✅" };

export function alerteColor(ch) {
  const si = ch.service === "si";
  if (ch.spo2 < (si?88:90) || ch.ecg > (si?140:150)) return C.rouge;
  if (ch.spo2 < (si?93:94) || ch.ecg > (si?110:120) || ch.temp > 38.5) return C.orange;
  return C.vert;
}

export function vitalColor(val, type) {
  const thresholds = {
    spo2:  [{ v:88, c:C.rouge }, { v:94, c:C.orange }, { c:C.vert }],
    ecg:   [{ v:150, c:C.rouge }, { v:120, c:C.orange }, { c:C.vert }],
    temp:  [{ v:40, c:C.rouge }, { v:38.5, c:C.orange }, { c:C.vert }],
    co2:   [{ v:1100, c:C.rouge }, { v:900, c:C.orange }, { c:C.vert }],
    perf:  [{ v:50, c:C.rouge }, { v:150, c:C.orange }, { c:C.vert }],
  };
  const t = thresholds[type];
  if (!t) return C.vert;
  for (const r of t) { if (r.v !== undefined && val < r.v && type !== "spo2") break; }
  if (type === "spo2" || type === "co2" || type === "perf") {
    if (type === "spo2") return val < 88 ? C.rouge : val < 94 ? C.orange : C.vert;
    if (type === "co2")  return val > 1100 ? C.rouge : val > 900 ? C.orange : C.vert;
    if (type === "perf") return val < 50 ? C.rouge : val < 150 ? C.orange : C.vert;
  }
  if (type === "ecg")  return val > 150 ? C.rouge : val > 120 ? C.orange : C.vert;
  if (type === "temp") return val > 40 ? C.rouge : val > 38.5 ? C.orange : C.vert;
  return C.vert;
}
