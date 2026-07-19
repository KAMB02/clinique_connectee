import { useState, useEffect, useCallback, useRef } from "react";
import Topbar from "./components/Topbar";
import Overview from "./components/Overview";
import Patients from "./components/Patients";
import Securite from "./components/Securite";
import Energie from "./components/Energie";
import Alertes from "./components/Alertes";
import Carte from "./components/Carte";
import Historique from "./components/Historique";
import ToastContainer from "./components/ToastContainer";
import { INITIAL_STATE, generateTick } from "./utils/simulator";
import { autoLogin, connectSSE, disconnectSSE, fetchAllVitaux, fetchEnergie, ackAlerte, normalizeVitaux } from "./utils/liveData";

const CHAMBRE_IDS = ["CH-001","CH-002","CH-003","CH-004","CH-005","SI-001","SI-002"];

export default function App() {
  const [tab, setTab]               = useState("overview");
  const [state, setState]           = useState(INITIAL_STATE);
  const [toasts, setToasts]         = useState([]);
  const [dataStatus, setDataStatus] = useState("connecting");
  const simInterval   = useRef(null);
  const fetchInterval = useRef(null);
  const nextId        = useRef(100);
  const fallbackTimer = useRef(null);
  const statusRef     = useRef("connecting"); // reflet à jour de dataStatus, lisible dans les closures

  const toastId = useRef(0);
  const addToast = useCallback((title, msg, niveau="rouge") => {
    const id = `toast-${Date.now()}-${toastId.current++}`;
    setToasts(prev => [...prev, { id, title, msg, niveau }]);
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 5000);
  }, []);

  const acquitter = useCallback(async (id) => {
    try { if (dataStatus === "live") await ackAlerte(id); } catch(e) {}
    setState(prev => ({ ...prev, alertes: prev.alertes.map(a => a.id===id ? {...a, ack:true} : a) }));
  }, [dataStatus]);

  const fetchLiveData = useCallback(async () => {
    try {
      const [vitauxRes, energieRes] = await Promise.allSettled([
        fetchAllVitaux(CHAMBRE_IDS),
        fetchEnergie(),
      ]);
      setState(prev => {
        let next = { ...prev };
        if (vitauxRes.status==="fulfilled" && vitauxRes.value.length>0) {
          next.chambres = prev.chambres.map(ch => {
            const found = vitauxRes.value.find(r => r.id===ch.id);
            if (!found) return ch;
            const n = normalizeVitaux(found.data);
            return { ...ch, ...Object.fromEntries(Object.entries(n).filter(([,v])=>v!==null)) };
          });
        }
        if (energieRes.status==="fulfilled" && energieRes.value) {
          const e = energieRes.value;
          next.ups = {
            niveau:    e.ups_niveau_pct  ?? prev.ups.niveau,
            tension:   e.tension_v       ?? prev.ups.tension,
            autonomie: e.autonomie_min   ?? prev.ups.autonomie,
            source:    e.statut          ?? prev.ups.source,
            enCharge:  e.en_charge       ?? prev.ups.enCharge,
          };
          if (e.conso_bloc_a !== undefined) {
            next.circuits = prev.circuits.map((c,i) => ({
              ...c, val: [e.conso_bloc_a, e.conso_bloc_b, e.conso_urgence][i] ?? c.val
            }));
          }
        }
        return next;
      });
    } catch(err) { console.warn("[LIVE] fetch error:", err); }
  }, []);

  const startFallback = useCallback(() => {
    clearInterval(fetchInterval.current);
    setDataStatus("fallback");
    statusRef.current = "fallback";
    addToast("Mode fallback", "API indisponible — simulateur actif", "orange");
    if (!simInterval.current) {
      simInterval.current = setInterval(() => {
        setState(prev => generateTick(prev).state);
      }, 4000);
    }
  }, [addToast]);

  useEffect(() => {
    let mounted = true;

    const init = async () => {
      setDataStatus("connecting");
      statusRef.current = "connecting";

      // 1. Login JWT auto
      const token = await autoLogin();
      if (!mounted) return;

      if (!token) {
        // Pas de token → fallback direct
        startFallback();
        return;
      }

      // 2. Connexion SSE
      connectSSE(
        (alerte) => {
          if (!mounted) return;
          const a = {
            id:      nextId.current++,
            niveau:  alerte.niveau || "ORANGE",
            icon:    alerte.niveau==="ROUGE" ? "🚨" : alerte.niveau==="ORANGE" ? "⚠️" : "✅",
            msg:     alerte.message || alerte.msg || "Nouvelle alerte",
            chambre: alerte.chambre_id || "—",
            patient: alerte.patient_id || "—",
            time:    new Date().toLocaleTimeString("fr-FR"),
            ack: false, type: alerte.type_alerte || "vitaux",
          };
          setState(prev => ({ ...prev, alertes: [a, ...prev.alertes].slice(0,50) }));
          addToast(
            alerte.niveau==="ROUGE" ? "⚠️ Alerte critique" : "Avertissement",
            a.msg,
            (alerte.niveau||"ORANGE").toLowerCase()
          );
        },
        (status) => {
          if (!mounted) return;
          if (status === "live") {
            clearTimeout(fallbackTimer.current); // annule le fallback à 5s : on est déjà live
            clearInterval(simInterval.current);
            simInterval.current = null;
            setDataStatus("live");
            statusRef.current = "live";
            // Les alertes de INITIAL_STATE sont des données de démo statiques —
            // on les retire au passage en live pour ne garder que les vraies
            // alertes reçues via SSE (sinon elles restent affichées pour
            // toujours et donnent une fausse impression d'activité).
            setState(prev => ({ ...prev, alertes: [] }));
            fetchLiveData();
            fetchInterval.current = setInterval(fetchLiveData, 10000);
            addToast("✅ Connexion live", "Flux IoT temps réel · 7 chambres", "vert");
          }
          if (status === "fallback") startFallback();
        }
      );

      // 3. Fallback si SSE ne répond pas dans les 5s
      // (utilise une ref, pas dataStatus : dans une closure de useEffect à
      // deps vides, dataStatus resterait figé sur "connecting" pour toujours,
      // donc ce fallback se déclencherait même après une connexion live réussie)
      fallbackTimer.current = setTimeout(() => {
        if (mounted && statusRef.current === "connecting") startFallback();
      }, 5000);
    };

    init();
    setTimeout(() => addToast("Clinique Connectée", "Initialisation du système…", "vert"), 500);

    return () => {
      mounted = false;
      disconnectSSE();
      clearInterval(simInterval.current);
      clearInterval(fetchInterval.current);
      clearTimeout(fallbackTimer.current);
    };
  }, []);

  const VIEWS = {
    overview: <Overview  state={state} setTab={setTab} acquitter={acquitter} />,
    patients: <Patients  state={state} />,
    securite: <Securite  state={state} acquitter={acquitter} />,
    energie:  <Energie   state={state} />,
    alertes:  <Alertes   state={state} acquitter={acquitter} />,
    historique: <Historique />,
    carte:    <Carte     state={state} setTab={setTab} />,
  };

  return (
    <div style={{ background:"#0A0E17", minHeight:"100vh", color:"#E8EEF8", fontFamily:"'Inter',sans-serif" }}>
      <Topbar tab={tab} setTab={setTab} nbAlertes={state.alertes.filter(a=>!a.ack).length} dataStatus={dataStatus} />
      <div style={{ padding:"20px 24px" }}>{VIEWS[tab]}</div>
      <ToastContainer toasts={toasts} setToasts={setToasts} />
    </div>
  );
}