/**
 * liveData.js — Clinique Connectée
 * Gestion données live : auth JWT auto + SSE + fetch InfluxDB
 */

const API_BASE = import.meta.env?.VITE_API_URL || 'http://localhost';
// ── Credentials démo (médecin) ────────────────────────────
const DEMO_CREDS = { username: "admin", password: "clinique2026" };

let jwtToken = null;
let sseConnection = null;
let sseRetries = 0;
const MAX_RETRIES = 3;
let loginInFlight = null; // dédup : évite 2 requêtes concurrentes (ex: React StrictMode)

// ── Auth : login automatique ──────────────────────────────
export async function autoLogin() {
  if (loginInFlight) return loginInFlight; // une requête déjà en cours → on la partage

  loginInFlight = (async () => {
    try {
      // Le backend utilise OAuth2PasswordRequestForm (FastAPI) : il attend
      // du application/x-www-form-urlencoded, PAS du JSON.
      const form = new URLSearchParams();
      form.set('grant_type', 'password');
      form.set('username', DEMO_CREDS.username);
      form.set('password', DEMO_CREDS.password);
      form.set('scope', '');
      form.set('client_id', '');
      form.set('client_secret', '');

      const res = await fetch(`${API_BASE}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: form.toString(),
        signal: AbortSignal.timeout(8000), // marge pour un cold-start backend
      });
      if (!res.ok) throw new Error(`Login HTTP ${res.status}`);
      const data = await res.json();
      jwtToken = data.access_token || data.token || null;
      console.log('[AUTH] Token JWT obtenu ✓');
      return jwtToken;
    } catch (err) {
      console.warn('[AUTH] Login échoué:', err.message);
      return null;
    } finally {
      loginInFlight = null;
    }
  })();

  return loginInFlight;
}

function authHeaders() {
  return jwtToken
    ? { 'Authorization': `Bearer ${jwtToken}`, 'Content-Type': 'application/json' }
    : { 'Content-Type': 'application/json' };
}

// ── SSE alertes temps réel ────────────────────────────────
export function connectSSE(onAlerte, onStatusChange) {
  if (sseConnection) sseConnection.close();
  try {
    // SSE avec token dans l'URL (EventSource ne supporte pas les headers)
    const url = jwtToken
      ? `${API_BASE}/api/alertes/stream?token=${jwtToken}`
      : `${API_BASE}/api/alertes/stream`;

    const es = new EventSource(url);
    es.onopen = () => { sseRetries = 0; onStatusChange('live'); };
    es.onmessage = (e) => { try { onAlerte(JSON.parse(e.data)); } catch(err) {} };
    es.onerror = () => {
      es.close(); sseRetries++;
      if (sseRetries <= MAX_RETRIES) setTimeout(() => connectSSE(onAlerte, onStatusChange), 3000);
      else onStatusChange('fallback');
    };
    sseConnection = es;
  } catch(err) { onStatusChange('fallback'); }
}

export function disconnectSSE() {
  if (sseConnection) { sseConnection.close(); sseConnection = null; }
}

// ── Fetch vitaux ──────────────────────────────────────────
export async function fetchAllVitaux(chambreIds) {
  const results = await Promise.allSettled(chambreIds.map(id =>
    fetch(`${API_BASE}/api/stats/vitaux/${id}`, {
      headers: authHeaders(),
      signal: AbortSignal.timeout(5000),
    }).then(r => r.ok ? r.json() : null)
  ));
  return results.map((r, i) => r.status==='fulfilled' && r.value ? { id: chambreIds[i], data: r.value } : null).filter(Boolean);
}

// ── Fetch énergie ─────────────────────────────────────────
export async function fetchEnergie() {
  const res = await fetch(`${API_BASE}/api/stats/energie`, {
    headers: authHeaders(),
    signal: AbortSignal.timeout(5000),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── ACK alerte ────────────────────────────────────────────
export async function ackAlerte(id) {
  const res = await fetch(`${API_BASE}/api/alertes/${id}/ack`, {
    method: 'PUT',
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error(`ACK HTTP ${res.status}`);
  return res.json();
}

// ── Historique vitaux (graphes) ───────────────────────────
export async function fetchVitauxHistorique(chambreId, rangeMin = 60) {
  const res = await fetch(`${API_BASE}/api/stats/vitaux/${chambreId}/historique?range_min=${rangeMin}`, {
    headers: authHeaders(),
    signal: AbortSignal.timeout(10000),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Historique alertes (liste filtrable) ──────────────────
export async function fetchAlertesHistorique(filters = {}) {
  const params = new URLSearchParams();
  if (filters.limit)      params.set('limit', filters.limit);
  if (filters.niveau)     params.set('niveau', filters.niveau);
  if (filters.chambre_id) params.set('chambre_id', filters.chambre_id);
  if (filters.type_alerte) params.set('type_alerte', filters.type_alerte);
  if (filters.date_debut) params.set('date_debut', filters.date_debut);
  if (filters.date_fin)   params.set('date_fin', filters.date_fin);

  const res = await fetch(`${API_BASE}/api/alertes/historique?${params.toString()}`, {
    headers: authHeaders(),
    signal: AbortSignal.timeout(10000),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

// ── Normaliser vitaux ─────────────────────────────────────
export function normalizeVitaux(apiData) {
  return {
    spo2: apiData.spo2 ?? apiData.vitaux?.spo2 ?? null,
    ecg:  apiData.ecg_bpm ?? apiData.vitaux?.ecg_bpm ?? null,
    temp: apiData.temperature ?? null,
    sys:  apiData.pression_sys ?? null,
    dia:  apiData.pression_dia ?? null,
    perf: apiData.niveau_poche_ml ?? null,
    co2:  apiData.co2_ppm ?? null,
  };
}