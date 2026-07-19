import { useState, useEffect, useCallback, useRef } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from "recharts";
import { C } from "../utils/helpers";
import { Card, CardHeader, Badge } from "./ui";
import { fetchVitauxHistorique, fetchAlertesHistorique } from "../utils/liveData";

const CHAMBRE_IDS = ["CH-001","CH-002","CH-003","CH-004","CH-005","SI-001","SI-002"];
const RANGES = [
  { label:"1h",  min:60 },
  { label:"6h",  min:360 },
  { label:"24h", min:1440 },
  { label:"7j",  min:10080 },
];
const NIVEAUX = ["ROUGE","ORANGE","VERT"];
const TYPES   = ["vitaux","intrusion","energie","equipement","appel"];

function pivotByTime(records) {
  const map = {};
  (records || []).forEach(r => {
    if (!map[r.time]) map[r.time] = { time: r.time };
    map[r.time][r.field] = r.value;
  });
  return Object.values(map).sort((a, b) => new Date(a.time) - new Date(b.time));
}

function fmtTick(iso) {
  const d = new Date(iso);
  return d.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
}

function MiniChart({ title, data, lines, unit }) {
  return (
    <div style={{ background: C.card2, border: `1px solid ${C.border}`, borderRadius: 10, padding: 14 }}>
      <div style={{ fontSize: 11, fontWeight: 600, color: C.txt2, marginBottom: 8, textTransform: "uppercase", letterSpacing: "0.05em" }}>
        {title}
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart data={data} margin={{ top: 4, right: 8, left: -18, bottom: 0 }}>
          <CartesianGrid stroke={C.border} strokeDasharray="3 3" />
          <XAxis dataKey="time" tickFormatter={fmtTick} tick={{ fill: C.txt3, fontSize: 9 }} minTickGap={30} />
          <YAxis tick={{ fill: C.txt3, fontSize: 9 }} unit={unit} width={40} />
          <Tooltip
            labelFormatter={fmtTick}
            contentStyle={{ background: C.card, border: `1px solid ${C.border}`, borderRadius: 6, fontSize: 11 }}
          />
          <Legend wrapperStyle={{ fontSize: 10 }} />
          {lines.map(l => (
            <Line key={l.key} type="monotone" dataKey={l.key} name={l.name}
              stroke={l.color} dot={false} strokeWidth={2} isAnimationActive={false} />
          ))}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

function VitauxHistorique() {
  const [chambreId, setChambreId] = useState(CHAMBRE_IDS[0]);
  const [rangeMin, setRangeMin]   = useState(60);
  const [data, setData]           = useState([]);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState(null);

  const reqIdVitaux = useRef(0);
  const load = useCallback(async () => {
    const myId = ++reqIdVitaux.current;
    setLoading(true); setError(null);
    try {
      const res = await fetchVitauxHistorique(chambreId, rangeMin);
      if (reqIdVitaux.current !== myId) return; // une requête plus récente a déjà répondu
      setData(pivotByTime(res.data));
      setError(null);
    } catch (e) {
      if (reqIdVitaux.current !== myId) return;
      setError(e.message || "Erreur de chargement");
      setData([]);
    } finally {
      if (reqIdVitaux.current === myId) setLoading(false);
    }
  }, [chambreId, rangeMin]);

  useEffect(() => { load(); }, [load]);

  return (
    <Card style={{ marginBottom: 16 }}>
      <CardHeader title="Historique des vitaux" badge={chambreId} color={C.bleu} />

      <div style={{ display: "flex", gap: 10, marginBottom: 14, flexWrap: "wrap" }}>
        <select value={chambreId} onChange={e => setChambreId(e.target.value)}
          style={{ background: C.card2, color: C.txt1, border: `1px solid ${C.border}`,
            borderRadius: 6, padding: "6px 10px", fontSize: 12, fontFamily: "inherit" }}>
          {CHAMBRE_IDS.map(id => <option key={id} value={id}>{id}</option>)}
        </select>
        <div style={{ display: "flex", gap: 4 }}>
          {RANGES.map(r => (
            <button key={r.min} onClick={() => setRangeMin(r.min)}
              style={{ padding: "6px 12px", borderRadius: 6, cursor: "pointer", fontFamily: "inherit",
                fontSize: 12, border: `1px solid ${rangeMin === r.min ? C.bleu : C.border}`,
                background: rangeMin === r.min ? `${C.bleu}18` : "transparent",
                color: rangeMin === r.min ? C.bleu : C.txt2 }}>
              {r.label}
            </button>
          ))}
        </div>
        <button onClick={load} disabled={loading}
          style={{ marginLeft: "auto", padding: "6px 12px", borderRadius: 6, cursor: "pointer",
            fontFamily: "inherit", fontSize: 12, border: `1px solid ${C.border}`,
            background: "transparent", color: C.txt2 }}>
          {loading ? "Chargement…" : "↻ Rafraîchir"}
        </button>
      </div>

      {error && (
        <div style={{ padding: 12, background: `${C.rouge}10`, border: `1px solid ${C.rouge}40`,
          borderRadius: 8, color: C.rouge, fontSize: 12, marginBottom: 12 }}>
          {error}
        </div>
      )}

      {!error && data.length === 0 && !loading && (
        <div style={{ padding: 20, textAlign: "center", color: C.txt3, fontSize: 12 }}>
          Aucune donnée sur cette plage — vérifie que le simulateur tourne bien.
        </div>
      )}

      {data.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 12 }}>
          <MiniChart title="SpO2 (%)" data={data} unit="%"
            lines={[{ key: "spo2", name: "SpO2", color: C.vert }]} />
          <MiniChart title="Fréquence cardiaque (bpm)" data={data} unit=""
            lines={[{ key: "ecg_bpm", name: "FC", color: C.rouge }]} />
          <MiniChart title="Température (°C)" data={data} unit="°C"
            lines={[{ key: "temperature", name: "Temp.", color: C.orange }]} />
          <MiniChart title="Pression artérielle (mmHg)" data={data} unit=""
            lines={[
              { key: "pression_sys", name: "Systolique", color: C.bleu },
              { key: "pression_dia", name: "Diastolique", color: C.violet },
            ]} />
        </div>
      )}
    </Card>
  );
}

function AlertesHistorique() {
  const [filters, setFilters] = useState({ niveau: "", chambre_id: "", type_alerte: "", date_debut: "", date_fin: "" });
  const [rows, setRows]       = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState(null);

  const reqIdAlertes = useRef(0);
  const load = useCallback(async () => {
    const myId = ++reqIdAlertes.current;
    setLoading(true); setError(null);
    try {
      const res = await fetchAlertesHistorique({ ...filters, limit: 200 });
      if (reqIdAlertes.current !== myId) return;
      setRows(res.data || []);
      setError(null);
    } catch (e) {
      if (reqIdAlertes.current !== myId) return;
      setError(e.message || "Erreur de chargement");
      setRows([]);
    } finally {
      if (reqIdAlertes.current === myId) setLoading(false);
    }
  }, [filters]);

  useEffect(() => { load(); }, [load]);

  const setF = (k, v) => setFilters(prev => ({ ...prev, [k]: v }));
  const inputStyle = {
    background: C.card2, color: C.txt1, border: `1px solid ${C.border}`,
    borderRadius: 6, padding: "6px 10px", fontSize: 12, fontFamily: "inherit",
  };

  return (
    <Card>
      <CardHeader title="Historique des alertes" badge={`${rows.length} résultats`} color={C.orange} />

      <div style={{ display: "flex", gap: 10, marginBottom: 14, flexWrap: "wrap", alignItems: "center" }}>
        <select value={filters.niveau} onChange={e => setF("niveau", e.target.value)} style={inputStyle}>
          <option value="">Tous niveaux</option>
          {NIVEAUX.map(n => <option key={n} value={n}>{n}</option>)}
        </select>
        <select value={filters.chambre_id} onChange={e => setF("chambre_id", e.target.value)} style={inputStyle}>
          <option value="">Toutes chambres/zones</option>
          {CHAMBRE_IDS.map(id => <option key={id} value={id}>{id}</option>)}
        </select>
        <select value={filters.type_alerte} onChange={e => setF("type_alerte", e.target.value)} style={inputStyle}>
          <option value="">Tous types</option>
          {TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <input type="datetime-local" value={filters.date_debut}
          onChange={e => setF("date_debut", e.target.value)} style={inputStyle} title="Depuis" />
        <input type="datetime-local" value={filters.date_fin}
          onChange={e => setF("date_fin", e.target.value)} style={inputStyle} title="Jusqu'à" />
        <button onClick={load} disabled={loading}
          style={{ marginLeft: "auto", padding: "6px 12px", borderRadius: 6, cursor: "pointer",
            fontFamily: "inherit", fontSize: 12, border: `1px solid ${C.border}`,
            background: "transparent", color: C.txt2 }}>
          {loading ? "Chargement…" : "↻ Rafraîchir"}
        </button>
      </div>

      {error && (
        <div style={{ padding: 12, background: `${C.rouge}10`, border: `1px solid ${C.rouge}40`,
          borderRadius: 8, color: C.rouge, fontSize: 12, marginBottom: 12 }}>
          {error}
        </div>
      )}

      <div style={{ maxHeight: 420, overflowY: "auto" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
          <thead>
            <tr style={{ textAlign: "left", color: C.txt3, borderBottom: `1px solid ${C.border}` }}>
              <th style={{ padding: "8px 6px" }}>Date/heure</th>
              <th style={{ padding: "8px 6px" }}>Niveau</th>
              <th style={{ padding: "8px 6px" }}>Zone/chambre</th>
              <th style={{ padding: "8px 6px" }}>Type</th>
              <th style={{ padding: "8px 6px" }}>Message</th>
              <th style={{ padding: "8px 6px" }}>Statut</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(r => (
              <tr key={r._id} style={{ borderBottom: `1px solid ${C.border}` }}>
                <td style={{ padding: "8px 6px", fontFamily: "monospace", color: C.txt2, whiteSpace: "nowrap" }}>
                  {r.timestamp ? new Date(r.timestamp).toLocaleString("fr-FR") : "—"}
                </td>
                <td style={{ padding: "8px 6px" }}>
                  <Badge color={r.niveau === "ROUGE" ? C.rouge : r.niveau === "ORANGE" ? C.orange : C.vert}>
                    {r.niveau}
                  </Badge>
                </td>
                <td style={{ padding: "8px 6px", color: C.txt1 }}>{r.chambre_id}</td>
                <td style={{ padding: "8px 6px", color: C.txt2 }}>{r.type_alerte}</td>
                <td style={{ padding: "8px 6px", color: C.txt1 }}>{r.message}</td>
                <td style={{ padding: "8px 6px", color: r.statut === "acquittée" ? C.vert : C.txt3 }}>
                  {r.statut === "acquittée" ? "✓ Acquittée" : "En attente"}
                </td>
              </tr>
            ))}
            {rows.length === 0 && !loading && (
              <tr><td colSpan={6} style={{ padding: 20, textAlign: "center", color: C.txt3 }}>
                Aucune alerte sur cette période/ces filtres.
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

export default function Historique() {
  return (
    <div>
      <VitauxHistorique />
      <AlertesHistorique />
    </div>
  );
}