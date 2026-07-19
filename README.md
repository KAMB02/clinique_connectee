<<<<<<< HEAD
# clinique_connectee
Infrastructure IoT sécurisée pour le monitoring hospitalier — MQTT/TLS, pipeline de données temps réel et tests d'intrusion (ARP spoofing, replay, MITM) sur une simulation de clinique connectée.
=======
# Clinique Connectée — Infrastructure IoT & Data Pipeline

> Mini-projet IoT — Master 1 BD-GL · UFHB Abidjan Cocody  
> Simulation d'une infrastructure hospitalière intelligente avec collecte de données en temps réel, visualisation et alertes automatisées.

**Équipe BD-GL** : Yannick-Paterne · Traore Siaka  
**Équipe RIST (sécurité)** : Kadjo Moise · Gneto Schiphra 

---

## Présentation

La **Clinique Connectée** est une infrastructure IoT simulée représentant un hôpital pilote à Abidjan. Le système collecte en temps réel les données de **7 chambres** (5 hospitalisation + 2 soins intensifs), des capteurs de sécurité et du système énergétique, les achemine via MQTT, les stocke dans InfluxDB et les visualise dans Grafana avec alertes automatiques.

```
Capteurs ESP32 / Simulateur Python
        ↓  MQTT (auth)
   Broker Mosquitto
        ↓
     Telegraf
        ↓
    InfluxDB  ←→  Grafana (6 dashboards)
    MongoDB       Node-RED (alertes)
    Redis HA ←──  FastAPI ×3
        ↓             ↓
   Nginx LB ───────────┘
        ↓
  React Dashboard (localhost:5173)
  · Auth JWT auto (OAuth2PasswordRequestForm)
  · SSE temps réel (/api/alertes/stream)
  · Fallback simulateur si API indisponible
```

---

## Stack technique

| Composant | Technologie | Version | Rôle |
|---|---|---|---|
| Broker MQTT | Mosquitto | 2.x | Transport des messages capteurs |
| Pipeline | Telegraf | 1.28.5 | MQTT → InfluxDB |
| Time-series DB | InfluxDB | 2.7 | Stockage données capteurs |
| Document DB | MongoDB | 7.x | Patients, alertes, historique |
| Cache HA | Redis Sentinel | 7.x | Cache 3 nœuds haute dispo (1 master + 2 replicas + 3 sentinels) |
| API REST | FastAPI | 0.111.0 | 3 instances (patients, alertes, stats, chambres, auth JWT) |
| Load Balancer | Nginx | alpine | Répartition de charge + reverse proxy SSE |
| Orchestration | Node-RED | 3.1 | Routing alertes ROUGE/ORANGE/VERT |
| Visualisation | Grafana | 10.0.0 | 6 dashboards temps réel |
| Monitoring | Prometheus + ELK | 8.12.0 | Métriques + logs |
| Simulation | Python 3 / Wokwi | - | Firmware ESP32 (PoC) + simulateur `paho-mqtt` |
| Dashboard web | React 18 + Vite | 18.3 / 6.0 | Interface live (auth JWT auto + SSE + fallback simulateur) |
| Conteneurs | Docker Compose | - | 24 services (dont simulateur dockerisé) |

---

## Architecture bâtiment & capteurs

### Services et chambres

```
┌─────────────────────────────────────────────────────────────┐
│  Hospitalisation (5 chambres : CH-001 → CH-005)             │
│  → Pub toutes les 10s · Seuils : spo2<94% · ecg>120bpm     │
├─────────────────────────────────────────────────────────────┤
│  Soins Intensifs (2 chambres : SI-001 → SI-002)             │
│  → Pub toutes les 5s · Seuils resserrés : spo2<93%         │
├─────────────────────────────────────────────────────────────┤
│  Couloirs & Accès (couloir-B)                               │
│  → Portes, badges RFID, caméra HD, contrôleur sécurité     │
├─────────────────────────────────────────────────────────────┤
│  Salle Technique Énergie                                     │
│  → UPS, groupe électrogène, compteur BLOC-A/B/URGENCE       │
└─────────────────────────────────────────────────────────────┘
```

### Capteurs par chambre patient

| Capteur | Measurement InfluxDB | Fields clés |
|---|---|---|
| Bracelet vitaux | `vitaux_chambre` | `spo2`, `ecg_bpm`, `temperature` |
| Tensiomètre | `vitaux_chambre` | `pression_sys`, `pression_dia` |
| CO2 ambiant | `co2_ambiant` | `co2_ppm` |
| Détecteur mouvement | `mouvement` | `mouvement`, `chute_detectee` |
| Perfuseur IV | `perfuseur` | `debit_ml_h`, `niveau_poche_ml`, `alarme` |
| Bouton appel | `appel` / `appel_securite` | `duree_ms`, `priorite` |

### Capteurs sécurité & énergie

| Capteur | Measurement | Fields clés |
|---|---|---|
| Détecteur porte | `securite_acces` | `porte_ouverte`, `duree_ouverte_ms` |
| Badge RFID | `badge_acces` | `badge_id`, `autorise` |
| Caméra HD (IA) | `camera_intrusion` | `intrusion_ia`, `confiance_pct` |
| Contrôleur alerte | `alerte_controleur` | `priorite` (tag), `type` (tag) |
| UPS | `energie_ups` | `niveau_pct`, `tension_v`, `autonomie_min` |
| Groupe élec. | `energie_generateur` | `actif`, `charge_pct` |
| Compteur énergie | `energie_compteur` | `consommation_w`, `circuit` (tag) |

---

## Topics MQTT

```
clinique/chambre/{chambre_id}/vitaux       → vitaux patient
clinique/chambre/{chambre_id}/co2          → CO2 ambiant
clinique/chambre/{chambre_id}/mouvement    → mouvement/chute
clinique/chambre/{chambre_id}/perfuseur    → perfusion IV
clinique/chambre/{chambre_id}/appel        → appel médical (court)
clinique/chambre/{chambre_id}/appel_securite → appel sécurité (≥3s)
clinique/acces/{zone}/porte               → état porte
clinique/acces/{zone}/badge               → scan badge RFID
clinique/securite/{zone}/camera           → détection caméra
clinique/alerte/controleur                → toutes alertes critiques
clinique/energie/ups                      → données UPS
clinique/energie/generateur               → groupe électrogène
clinique/energie/compteur                 → consommation par circuit
```

---

## Auth MQTT

Chaque device s'authentifie avec un couple username/password avant toute publication.  
Connexions anonymes refusées (`allow_anonymous false`).

| Utilisateur | Rôle | Droits |
|---|---|---|
| `esp32_chambre` | Capteurs chambre | write `clinique/chambre/#` |
| `esp32_securite` | Capteurs sécurité | write `clinique/acces/#`, `clinique/securite/#` |
| `esp32_energie` | Capteurs énergie | write `clinique/energie/#` |
| `telegraf_agent` | Pipeline data | read `clinique/#` |
| `nodered_agent` | Alertes | read `clinique/#`, write `clinique/commande/#` |
| `admin_clinique` | Admin / Tests sécu | readwrite `#` |

Password commun (démo) : `clinique2026`

---

## Prérequis

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et démarré
- [Python 3.10+](https://python.org) avec `pip`
- [VS Code](https://code.visualstudio.com/) + extension PlatformIO (pour firmware Wokwi)
- Port `8883` (MQTT TLS), `3000` (Grafana), `8086` (InfluxDB), `1880` (Node-RED) disponibles

---

## Installation

### 1. Cloner le projet

```bash
git clone https://github.com/votre-repo/mini-projet-iot.git
cd mini-projet-iot
```

### 2. Démarrer l'infrastructure Docker

```bash
docker compose up -d
```

Vérifier que les 24 services sont actifs :

```bash
docker compose ps
```

### 3. Configurer l'auth MQTT

```bash
# Créer les utilisateurs dans Mosquitto
bash setup_auth.sh
```

Vérifier que l'auth fonctionne :

```bash
docker exec clinique_mosquitto mosquitto_sub -t "clinique/#" -u telegraf_agent -P clinique2026 -v
```

### 4. Ajouter les credentials dans Telegraf

Dans `telegraf/telegraf.conf`, section `[[inputs.mqtt_consumer]]` :

```toml
username = "telegraf_agent"
password = "clinique2026"
```

Redémarrer Telegraf :

```bash
docker restart clinique_telegraf
```

### 5. Simulateur de capteurs — dockerisé, démarre automatiquement

Depuis la mise à jour du 15/07/2026, le simulateur tourne comme un service Docker à part entière (`clinique_simulateur`, 24ᵉ service) — **plus besoin de l'installer ni de le lancer à la main**. Il démarre avec `docker compose up -d` (étape 2) et cible directement `clinique_mosquitto:8883` sur le réseau interne, avec les certificats montés en lecture seule depuis `./certs`.

Vérifier qu'il tourne :

```bash
docker compose logs simulateur --tail 30
```

Vérifier les publications en temps réel :

```bash
docker exec clinique_mosquitto mosquitto_sub -h localhost -p 8883 --cafile /mosquitto/certs/server.crt -u telegraf_agent -P clinique2026 -t "clinique/#" -v
```

*(L'ancien script `simulateur_clinique.py` lancé à la main avec `py simulateur_clinique.py --broker localhost` reste utilisable en secours si besoin — le code est identique, seul le mode de lancement change.)*

### 6. Importer les dashboards Grafana

1. Ouvrir Grafana : [http://localhost:3000](http://localhost:3000) (Id dans le compose.yaml )
2. `+` → Import → Upload JSON pour chaque fichier dans `dashboard_grafana/`
3. Mapper `DS_INFLUXDB` sur votre datasource InfluxDB existante

| Fichier | Dashboard |
|---|---|
| `db1_vitaux_patients.json` | Vitaux patients temps réel |
| `db2_securite.json` | Sécurité & accès |
| `db3_energie.json` | Énergie & alimentation |
| `db4_alertes.json` | Alertes ROUGE/ORANGE/VERT |
| `db5_eco.json` | Écologie & consommation |
| `db6_overview.json` | Vue globale clinique |

### 7. Configurer Node-RED

1. Ouvrir Node-RED : [http://localhost:1880](http://localhost:1880)
2. Importer le flow : `node-red/flow_alertes.json`
3. Vérifier les nœuds MQTT avec les credentials `nodered_agent / clinique2026`

### 8. Lancer le dashboard React

```bash
cd react-dashboard
npm install
npm run dev
```

Ouvrir [http://localhost:5173](http://localhost:5173) — connexion automatique en JWT (compte démo `admin / clinique2026`, voir `src/utils/liveData.js`), aucune action manuelle requise. Voir la section [Dashboard React](#dashboard-react) ci-dessous pour le détail du fonctionnement live/fallback.

---

## Dashboard React

Interface web du personnel médical/technique — vue d'ensemble de la clinique, chambres, alertes, sécurité, énergie et carte des zones.

**Stack** : React 18 + Vite 6, aucune dépendance UI externe (composants maison), CSS-in-JS inline.

### Fonctionnement live / fallback

Au chargement, le dashboard :

1. **S'authentifie automatiquement** contre `POST /auth/login` (compte démo `admin / clinique2026`, `OAuth2PasswordRequestForm` — donc en `application/x-www-form-urlencoded`, pas en JSON) pour obtenir un JWT.
2. **Ouvre un flux SSE** (`GET /api/alertes/stream?token=...`) pour recevoir les alertes en temps réel, et récupère les vitaux/énergie via `GET /api/stats/...` toutes les 10s.
3. Si l'authentification échoue ou si le SSE ne confirme pas la connexion, **bascule en mode simulateur interne** (`generateTick`, toutes les 4s) — un jeu de données cohérent générées côté navigateur, pour que la démo reste présentable même si l'infrastructure Docker est indisponible.

Le badge en haut à droite indique l'état réel : 🟢 **Live · IoT actif** (données InfluxDB/MongoDB réelles) ou 🟠 **Simulation** (fallback navigateur, aucune connexion au backend).

### Onglets

- **Vue globale / Patients / Sécurité / Énergie / Alertes** : vues temps réel, mises à jour via SSE + polling REST.
- **🗺️ Carte** : mini carte géographique réelle (OpenStreetMap via `react-leaflet`, marqueur sur Cocody, Abidjan) **au-dessus** du plan intérieur SVG de la clinique (7 chambres + zone sécurité + local énergie).
- **📊 Historique** (nouveau) : sélecteur de chambre + plage (1h/6h/24h/7j) avec 4 graphes (`recharts`) — SpO2, fréquence cardiaque, température, pression artérielle — et une liste d'alertes passées filtrable par niveau/chambre/type/date, alimentés par `GET /api/stats/vitaux/{chambre_id}/historique` et `GET /api/alertes/historique`.

### Structure

```
react-dashboard/
├── src/
│   ├── App.jsx                  # État global, orchestration live/fallback, toasts
│   ├── main.jsx                 # Point d'entrée (React.StrictMode)
│   ├── components/
│   │   ├── Topbar.jsx            # Navigation + badge statut live/simu
│   │   ├── ToastContainer.jsx    # Notifications
│   │   ├── Patients.jsx / Securite.jsx / Energie.jsx / Alertes.jsx
│   │   ├── Carte.jsx             # Carte géo (react-leaflet) + plan intérieur SVG
│   │   ├── Historique.jsx        # Graphes vitaux (recharts) + alertes filtrables
│   │   └── ui.jsx                # KpiCard, Card, Gauge, ProgressBar, StatusDot...
│   └── utils/
│       ├── liveData.js           # autoLogin, connectSSE, fetch*, fetch*Historique, ackAlerte
│       └── helpers.js            # generateTick (simulateur), constantes, couleurs
├── vite.config.js                # Proxy /api → localhost:8000 en dev
└── package.json                  # + leaflet, react-leaflet, recharts
```

### Configuration

Variable d'environnement optionnelle (`.env` à la racine de `react-dashboard/`) :

```
VITE_API_URL=http://localhost
```

Par défaut, le dashboard cible `http://localhost` (le port 80 de Nginx). À adapter si l'infrastructure Docker est exposée ailleurs.

### Build de production

```bash
cd react-dashboard
npm run build      # génère dist/
npm run preview    # sert dist/ localement pour vérification
```

---

## Débogage — incidents résolus pendant le développement

Historique des blocages rencontrés pour le passage en mode live, utile en cas de régression ou de redéploiement sur une autre machine.

| Symptôme | Cause | Fix |
|---|---|---|
| Login toujours en échec, fallback immédiat | Le dashboard envoyait du JSON à `/auth/login`, qui attend `application/x-www-form-urlencoded` (`OAuth2PasswordRequestForm`) | `autoLogin()` construit un `URLSearchParams` avec `grant_type`, `username`, `password` |
| SSE jamais authentifié | `OAuth2PasswordBearer` ne lit que le header `Authorization` ; `EventSource` ne peut pas envoyer de headers custom, le token passe en `?token=` | Dépendance `get_current_user_sse` / `require_role_sse` dans `auth.py`, tolérante au token en query string |
| `/api/stats/*` renvoie toujours des données vides | Requêtes Flux avec de mauvais noms de measurement/champs (`sante_patient`, `energie_batiment`...) au lieu des vrais (`vitaux_chambre`, `energie_ups`, `energie_generateur`, `energie_compteur`...) | Requêtes corrigées dans `routers/stats.py`, réponse aplatie pour matcher `normalizeVitaux()` côté front |
| Redis Sentinel en crash loop (`Restarting`) | `sentinel.conf` utilise un nom d'hôte Docker (`redis_master`) ; Sentinel refuse de résoudre les hostnames par défaut (`Can't resolve instance hostname`) | Ajout de `sentinel resolve-hostnames yes` + `sentinel announce-hostnames yes` **avant** la ligne `sentinel monitor` dans `redis/sentinel{1,2,3}/sentinel.conf` |
| Telegraf en crash loop | `mqtt_consumer` sans `username`/`password` alors que Mosquitto refuse les connexions anonymes → le plugin échoue à se connecter → tout l'agent plante | Ajout de `username = "telegraf_agent"` / `password = "clinique2026"` dans `telegraf.conf` |
| API `(unhealthy)` malgré un process qui tourne | Le healthcheck `/health` appelle `redis.ping()` via Sentinel ; quand Sentinel est en crash loop, l'appel traîne et dépasse le timeout du `HEALTHCHECK` | Résolu en réparant Sentinel (cf. ligne ci-dessus) |
| CORS bloqué : `Access-Control-Allow-Origin` avec deux valeurs `*, *` | nginx **et** FastAPI (`CORSMiddleware`) ajoutaient chacun leur propre header CORS sur `/api/` | Retrait des `add_header` CORS côté nginx — géré uniquement par FastAPI |
| SSE coupé après ~5-15s (`ERR_INCOMPLETE_CHUNKED_ENCODING`) | Le middleware `@app.middleware("http")` (`BaseHTTPMiddleware`) fait tourner l'endpoint dans une tâche séparée avec un polling de déconnexion qui génère de faux positifs sur les flux infinis (SSE) | Middleware ASGI pur dans `main.py` (n'intercepte que `http.response.start`, ne touche jamais au corps de la réponse) |
| SSE coupé après ~30s (`504 Gateway Time-out`, puis CORS "absent" car nginx répond seul) | `proxy_read_timeout 30s` global dans nginx, appliqué aussi au flux SSE censé rester ouvert indéfiniment | Bloc `location /api/alertes/stream` dédié avec `proxy_read_timeout 1d`, `proxy_buffering off`, `chunked_transfer_encoding off` |
| Dashboard repasse en "Simulation" après 5s même quand le live fonctionne, sans aucune erreur | Le `setTimeout` de secours (5s) dans `App.jsx` lisait `dataStatus` capturé dans une closure figée sur sa valeur initiale (`"connecting"`), donc il forçait toujours le fallback | Ajout d'un `ref` (`statusRef`) synchronisé à chaque changement de statut, lu par le timer à la place de l'état React |
| Warning React "two children with the same key" sur les toasts | `id` généré avec `Date.now()` seul, collision possible en cas de double appel rapproché (React StrictMode) | `id` composé de `Date.now()` + compteur incrémental |
| Login parfois lent au tout premier démarrage (`signal timed out`) | Le hash bcrypt du mot de passe démo est calculé paresseusement au 1er login (coût CPU synchrone au cold-start) | Hash pré-calculé au démarrage de l'API (`lifespan`), plus de coût au premier appel |
| Plus aucune donnée dans InfluxDB/Grafana après une modif du simulateur (`field type conflict... is type integer, already exists as type float`) | Le simulateur envoyait des entiers sans suffixe `i` (Line Protocol), donc écrits comme `float` ; une fois corrigé pour envoyer de vrais `integer`, ça entrait en conflit avec le type déjà verrouillé par les anciennes données du même champ | Bucket `mesures_capteurs` supprimé puis recréé (`influx bucket delete` / `create`) — acceptable car données de simulation, pas de valeur à conserver |
| `unsupported input type for mean aggregate: boolean` dans InfluxDB Data Explorer / panneau Grafana "porte_ouverte" | Agrégation `mean()` appliquée à un champ booléen (`porte_ouverte`, `mouvement_detecte`...) — on ne peut pas faire une moyenne de vrai/faux | Panneau Grafana corrigé en `fn: last` ; en exploration manuelle, changer l'agrégation par défaut "mean" → "last" pour tout champ booléen |
| Conteneur `clinique_filebeat` ne démarre pas (`mount ... not a directory`) | Le fichier `elk/filebeat.yml` n'existait pas sur l'hôte ; Docker a créé un **dossier vide** à sa place lors d'une tentative précédente, cassant le bind mount fichier→fichier | Supprimer le dossier créé par erreur et y placer un vrai fichier `filebeat.yml` |
| Flow Node-RED (`flow_alertes.json`) ne recevait jamais rien | Broker configuré sur le port `1883` en clair, alors que Mosquitto n'écoute qu'en TLS sur `8883` ; topics incomplets (`clinique/+/sante` au lieu de `clinique/chambre/+/vitaux`, etc.) ; `datatype: "json"` alors que les payloads sont en Line Protocol brut | Broker basculé en TLS `8883`, topics corrigés (dont ajout `clinique/acces/#` et `appel_securite` séparé), parsing Line Protocol ajouté dans chaque noeud `function` |
| Bandeau "Failed to fetch" affiché dans l'onglet Historique alors que les graphes montrent bien des données | Deux requêtes concurrentes au montage (React StrictMode) : si la 1ʳᵉ échoue et la 2ᵉ réussit, l'erreur de la 1ʳᵉ reste affichée même si les bonnes données sont déjà arrivées | Garde anti-race avec compteur de requête (`reqIdRef`) — seule la dernière requête lancée peut mettre à jour l'état |

---

## Structure du projet

```
mini-projet-iot/
├── docker-compose.yaml          # 24 services orchestrés (dont simulateur)
├── simulateur_clinique.py    # Simulateur Python 7 chambres + auth
├── setup_auth.sh                # Configuration auth MQTT automatique
├── Wokwi-README.md              # Documentation firmware ESP32
│
├── mosquitto/
│   └── config/
│       ├── mosquitto.conf       # Config broker (auth activée)
│       ├── passwd               # Fichier passwords (généré par setup_auth.sh)
│       └── acl                  # ACL par utilisateur
│
├── telegraf/
│   └── telegraf.conf            # Pipeline MQTT → InfluxDB
│
├── influxdb/                    # Config InfluxDB (bucket: mesures_capteurs)
├── grafana/                     # Datasources et config Grafana
│
├── dashboard_grafana/           # 6 dashboards JSON importables
│   ├── db1_vitaux_patients.json
│   ├── db2_securite.json
│   ├── db3_energie.json
│   ├── db4_alertes.json
│   ├── db5_eco.json
│   └── db6_overview.json
│
├── node-red/
│   └── flow_alertes.json        # Routing alertes ROUGE/ORANGE/VERT
│
├── certs/                       # Certificats TLS (RIST)
│
├── wokwi-chambre/               # Firmware ESP32 chambre patient
│   ├── src/main.cpp
│   ├── platformio.ini
│   └── diagram.json
│
├── wokwi-securite/              # Firmware ESP32 sécurité
│   ├── src/main.cpp
│   ├── platformio.ini
│   └── diagram.json
│
├── wokwi-energie/               # Firmware ESP32 énergie
│   ├── src/main.cpp
│   ├── platformio.ini
│   └── diagram.json
│
└── wokwigw/                     # Wokwi gateway config
├── Attaque-README.md            # Documentation des scripts d'attaque
├── simulateur/                   # Simulateur capteurs dockerisé (service 24)
│   ├── Dockerfile
│   └── simulateur_clinique.py
│
└── react-dashboard/              # Dashboard web (voir section dédiée ci-dessus)
    ├── src/
    │   ├── App.jsx
    │   ├── components/
    │   └── utils/
    │       ├── liveData.js
    │       └── helpers.js
    ├── vite.config.js
    └── package.json
```

---

## Documentation des attaques

- `Attaque-README.md` — description des scripts `attaque_spoofing.py` et `attaque_replay.py`.
- `attaque_spoofing.py` — simulation pédagogique d'un MITM + replay d'ACK.
- `attaque_replay.py` — capture MQTT puis rejoue des messages à partir d'une trace.

---

## Services Docker

| Service | Port | URL | Description |
|---|---|---|---|
| `clinique_mosquitto` | 8883 | — | Broker MQTT |
| `clinique_telegraf` | — | — | Pipeline data |
| `clinique_influxdb` | 8086 | http://localhost:8086 | Time-series DB |
| `clinique_mongodb` | 27017 | — | Document DB |
| `clinique_redis_master` | 6379 | — | Cache principal |
| `clinique_redis_replica_1/2` | 6380/6381 | — | Réplicas Redis |
| `clinique_redis_sentinel_1/2/3` | 26379-81 | — | Sentinel HA |
| `clinique_api_1/2/3` | 8001-8003 | http://localhost:800{1,2,3}/docs | APIs REST (accès direct, hors LB) |
| `clinique_nginx` | 80 / 443 | http://localhost | Load balancer + reverse proxy (dashboard → API) |
| `clinique_nodered` | 1880 | http://localhost:1880 | Alertes routing |
| `clinique_grafana` | 3000 | http://localhost:3000 | Dashboards |
| `clinique_prometheus` | 9090 | http://localhost:9090 | Monitoring |
| `clinique_elasticsearch` | 9200 | — | Logs search |
| `clinique_logstash` | 5044 | — | Logs pipeline |
| `clinique_kibana` | 5601 | http://localhost:5601 | Logs dashboard |
| Dashboard React (dev) | 5173 | http://localhost:5173 | Interface web (hors Docker, `npm run dev`) |

---

## InfluxDB

- **Organisation** : `clinique_abidjan`
- **Bucket** : `mesures_capteurs`
- **URL** : http://localhost:8086

Vérifier les données en temps réel :

```flux
from(bucket: "mesures_capteurs")
  |> range(start: -5m)
  |> filter(fn: (r) => r._measurement == "vitaux_chambre")
  |> filter(fn: (r) => r._field == "spo2")
  |> last()
```

---

## Logique d'alertes

| Niveau | Couleur | Déclencheur |
|---|---|---|
| Critique | 🔴 ROUGE | spo2<90%, ecg>150bpm, chute détectée, UPS<10%, intrusion caméra |
| Avertissement | 🟠 ORANGE | spo2<94%, ecg>120bpm, T°>38.5°C, appel patient court |
| Normal | 🟢 VERT | Tous les paramètres dans les normes |

**Bouton appel patient** :
- Appui court (<3s) → alerte médicale ORANGE → infirmière
- Appui long (≥3s) → alarme sécurité ROUGE → contrôleur sécurité

Toutes les alertes ROUGE/ORANGE sont routées via Node-RED vers `clinique/alerte/controleur`.

---

## Comptes de test

| Service | URL | Identifiants |
|---|---|---|
| Grafana | http://localhost:3000 | admin / (défini au setup) |
| InfluxDB | http://localhost:8086 | admin / (défini au setup) |
| Node-RED | http://localhost:1880 | (sans auth par défaut)ou admin / pass |
| Kibana | http://localhost:5601 | elastic / (défini au setup) |
| MQTT (sub) | localhost:8883 | telegraf_agent / clinique2026 |
| MQTT (admin) | localhost:8883 | admin_clinique / clinique2026 |
| Dashboard React / API (JWT) | http://localhost:5173 | admin / clinique2026 (auto-login) |

---

## Attaques simulées

Ce projet comprend deux scripts dédiés aux attaques MQTT pour démontrer des scénarios de sécurité :

- `attaque_spoofing.py` : simulation pédagogique d'une attaque MITM / ARP Spoofing.
  - Capture un ACK de prise en charge et rejoue un message falsifié.
  - Génère aussi des payloads falsifiés de `vitaux_chambre`.
- `attaque_replay.py` : capture et rejoue des messages MQTT.
  - `--mode capture` enregistre les messages dans un fichier JSON.
  - `--mode replay` publie les messages enregistrés sur le broker.
  - Options : `--file`, `--delay`, `--rate`, `--modify`, `--loop`.

Voir `Attaque-README.md` pour tous les détails d'utilisation.

---

## Commandes utiles

```bash
# Vérifier tous les containers
docker compose ps

# Logs d'un service spécifique
docker logs clinique_telegraf --tail 50 --follow
docker logs clinique_mosquitto --tail 50

# Redémarrer un service
docker restart clinique_telegraf

# Voir les messages MQTT en temps réel
docker exec clinique_mosquitto mosquitto_sub -t "clinique/#" -u telegraf_agent -P clinique2026 -v

# Tester un publish manuel
docker exec clinique_mosquitto mosquitto_pub -t "clinique/test" -m "hello" -u admin_clinique -P clinique2026

# Accéder à InfluxDB CLI
docker exec -it clinique_influxdb influx

# Lancer le simulateur (Windows)
py simulateur_clinique.py --broker localhost --port 8883

# Arrêter toute l'infrastructure
docker compose down

# Lancer le gateway Wokwi (dans un terminal séparé)
cd wokwigw
./wokwigw.exe       # laisse tourner


```

---

## Répartition des tâches

| Tâche | Équipe | Statut |
|---|---|---|
| Architecture Docker 24 services (simulateur inclus) | BD-GL | ✅ Terminé |
| Firmware ESP32 ×3 (Wokwi) | BD-GL | ✅ Terminé |
| Simulateur Python 7 chambres | BD-GL | ✅ Terminé |
| Pipeline Telegraf → InfluxDB | BD-GL | ✅ Terminé |
| 6 Dashboards Grafana | BD-GL | ✅ Terminé |
| Node-RED routing alertes | BD-GL | ✅ Terminé |
| FastAPI ×3 endpoints (auth JWT, patients, alertes SSE, stats, chambres) | BD-GL | ✅ Terminé |
| React Dashboard (live + fallback simulateur) | BD-GL | ✅ Terminé |
| Analyse STRIDE | RIST | ✅ Terminé |
| Auth MQTT (TLS/X.509) | RIST |✅ Terminé |
| MQTT ACLs | BD-GL + RIST | ✅ Configuré |
| Tests Wireshark / MITM | RIST | ⏳ À faire |

---

## Notes importantes

- Le simulateur Python remplace les simulations Wokwi pour la démo live (stabilité garantie vs limite CPU navigateur des 3 onglets Wokwi simultanés)
- Les firmwares Wokwi (`wokwi-chambre/`, `wokwi-securite/`, `wokwi-energie/`) restent comme preuve de conception du firmware réel ESP32
- Telegraf v1.28.5 : ne pas utiliser `exponential_base`, `retry_interval`, `max_retry_count` dans la config — ils crashent le service
- Tous les noms de containers Docker doivent être préfixés `clinique_` (ex: `clinique_mosquitto`)

---

*Projet réalisé dans le cadre du hackathon IoT — Master 1 BD-GL & RIST · UFHB · Juin 2026*
>>>>>>> 28bd379 (Clinique Connectée — projet complet (IoT + API + dashboard React))
