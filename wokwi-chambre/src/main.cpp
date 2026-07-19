#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>
#include <DHT.h>

// ════════════════════════════════════════════════════════════════════
//  CLINIQUE CONNECTÉE — ESP32 CHAMBRE PATIENT
//  Simule tous les capteurs d'une chambre :
//    - DHT22       → température corporelle + CO2 ambiant (approx)
//    - SpO2        → saturation oxygène (simulé)
//    - ECG         → fréquence cardiaque (simulé)
//    - Pression    → systolique / diastolique (simulé)
//    - Mouvement   → détection sortie lit / chute (simulé)
//    - Perfuseur   → débit + niveau poche (simulé)
//    - Bouton      → appel patient (GPIO 0 = BOOT button Wokwi)
//
//  Topics publiés :
//    clinique/chambre/CH-001/vitaux         → SpO2, T°, ECG, pression
//    clinique/chambre/CH-001/co2            → CO2 ambiant
//    clinique/chambre/CH-001/mouvement      → mouvement, chute
//    clinique/chambre/CH-001/perfuseur      → débit, niveau poche
//    clinique/chambre/CH-001/appel          → appui court (alerte médicale)
//    clinique/chambre/CH-001/appel_securite → appui long 3s (alerte sécurité)
// ════════════════════════════════════════════════════════════════════

// ── Identité chambre ─────────────────────────────────────────────
const char* CHAMBRE_ID  = "CH-001";
const char* PATIENT_ID  = "PAT-042";
const char* DEVICE_ID   = "ESP32_CH001";

// ── Réseau ───────────────────────────────────────────────────────
const char* WIFI_SSID     = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";
const char* MQTT_SERVER   = "host.wokwi.internal";
const int   MQTT_PORT     = 8883; // MQTT TLS
const char* MQTT_USER     = "esp32_chambre";
const char* MQTT_PASSWORD = "clinique2026";

const char* root_ca = R"EOF(
-----BEGIN CERTIFICATE-----
MIICzjCCAbagAwIBAgIUOeo+Am95QcT8HOWY9YHzIIkg3J8wDQYJKoZIhvcNAQEL
BQAwFDESMBAGA1UEAwwJbG9jYWxob3N0MB4XDTI2MDcwOTE5NTIzNloXDTI3MDcx
MDE5NTIzNlowFDESMBAGA1UEAwwJbG9jYWxob3N0MIIBIjANBgkqhkiG9w0BAQEF
AAOCAQ8AMIIBCgKCAQEAqxRrZglFxJsCR71lY7aG3y7X7vPD8nhiJG82U6SD4+l7
n5kH6bLyn4qdH+jXl80MWv5N81QeVBosWZ8BwrDXulDOXQqrl87ntXXT2IO2mrIv
jJVmTHiQa+QHpew+Df7cjg7Yqla5+pPaXWUA7Z+G4YGyy7RORA5c0jDr+IQHUvep
YJY/WhmPJWJvY5rdhix4+YFzQQDk4STWrXuCv+7MXbdUov46lNY5jPglnuoaSzG6
Tw0JWuGTfCsggRv8Z6jReP+R6FBsAi7Rx0cbg6Y98RFUuoZMorwNPMxWDfeAZN4U
N/3YIsI+xDNbj+5mJQyC2JJLn7fSRrI+sXGDcI5+wwIDAQABoxgwFjAUBgNVHREE
DTALgglsb2NhbGhvc3QwDQYJKoZIhvcNAQELBQADggEBADLs+tNJlRYZZn6U2qbh
X6norc2iS5PekmafWmzJKyOZHXrw5ioL/PhpeR6qXG4Fq/o8CKr6wKPe1lrEFzVk
a07sTlcF3J5Y4BqDvp22wrW6Iwe7SpCvDmd5XnsXo/rAYdczPkM2h5RHVQsQ6SwU
hRT4tN598Frxi8DpzgLWbtODcTI+RQqm7hMpHCJWts/9g2BSAR3mTJa+TE0bjZg3
BOSh9fbg31YGEgpENQxAfK0WySVPcWqvhX52i7Ar4ARmg/XMycIqaZw2AHYAqHWl
gcZdgkbM2kcEWUms4TqYP37kv80V6e0sJDgkkiIDTupfgW8U2iydOSArOBHS3OpV
qis=
-----END CERTIFICATE-----
)EOF";

// ── Topics MQTT ──────────────────────────────────────────────────
char TOPIC_VITAUX[64];
char TOPIC_CO2[64];
char TOPIC_MOUVEMENT[64];
char TOPIC_PERFUSEUR[64];
char TOPIC_APPEL[64];
char TOPIC_APPEL_SECU[64];

// ── GPIOs ────────────────────────────────────────────────────────
#define PIN_DHT        4
#define DHTTYPE        DHT22
#define PIN_BOUTON     0
#define PIN_MOUVEMENT  2
#define PIN_ALERTE     15

// ── Objets ───────────────────────────────────────────────────────
DHT               dht(PIN_DHT, DHTTYPE);
WiFiClientSecure  espClient;
PubSubClient      client(espClient);

// ── État simulé patient ──────────────────────────────────────────
float spo2_base    = 97.5f;
float ecg_bpm_base = 72.0f;
float press_sys    = 120.0f;
float press_dia    = 80.0f;
float perf_debit   = 50.0f;
float perf_niveau  = 500.0f;

float spo2_drift   = 0.0f;
float ecg_drift    = 0.0f;

int   eventType    = 0;
int   eventTicks   = 0;
unsigned long pubCount = 0;

// Bouton appel patient
unsigned long boutonPressedAt = 0;
bool boutonWasPressed         = false;

// ── Utilitaires ──────────────────────────────────────────────────
float randF(float lo, float hi) {
    return lo + ((float)random(0, 10000) / 10000.0f) * (hi - lo);
}

// ════════════════════════════════════════════════════════════════════
//  GÉNÉRATION VALEURS CAPTEURS
// ════════════════════════════════════════════════════════════════════

void genererVitaux(float &spo2, float &ecg, float &temp_corp) {
    pubCount++;

    // SpO2 — dérive lente naturelle
    spo2_drift += randF(-0.3f, 0.3f);
    spo2_drift  = constrain(spo2_drift, -2.0f, 2.0f);
    spo2 = spo2_base + spo2_drift + randF(-0.2f, 0.2f);

    // ECG — dérive lente
    ecg_drift += randF(-1.0f, 1.0f);
    ecg_drift  = constrain(ecg_drift, -8.0f, 8.0f);
    ecg = ecg_bpm_base + ecg_drift + randF(-1.0f, 1.0f);

    // Température corporelle via DHT22
    float raw = dht.readTemperature();
    if (isnan(raw) || raw == 0.0f) raw = 26.5f;  // fallback Wokwi
    temp_corp = 36.0f + ((raw - 20.0f) / 20.0f) * 2.5f + randF(-0.1f, 0.1f);
    temp_corp = constrain(temp_corp, 36.0f, 41.5f);

    // ── Événements cliniques aléatoires (~1 toutes les 50 pubs) ──
    if (eventType == 0 && random(1000) < 20) {
        int roll = random(4);
        if      (roll == 0) { eventType = 1; eventTicks = 3;  }  // chute
        else if (roll == 1) { eventType = 2; eventTicks = 5;  }  // hypoxie
        else if (roll == 2) { eventType = 3; eventTicks = 4;  }  // tachycardie
        else                { eventType = 4; eventTicks = 10; }  // perf vide
    }

    if (eventType == 1) {
        spo2 -= randF(1.0f, 3.0f);
        ecg  += randF(15.0f, 30.0f);
        if (--eventTicks <= 0) { eventType = 0; Serial.println("[EVENT] Chute terminee"); }
        Serial.print("[EVENT] CHUTE DETECTEE -- ");
    } else if (eventType == 2) {
        spo2 -= randF(3.0f, 8.0f);
        if (--eventTicks <= 0) { eventType = 0; }
        Serial.print("[EVENT] HYPOXIE -- ");
    } else if (eventType == 3) {
        ecg += randF(20.0f, 50.0f);
        if (--eventTicks <= 0) { eventType = 0; }
        Serial.print("[EVENT] TACHYCARDIE -- ");
    }

    spo2 = constrain(spo2, 70.0f, 100.0f);
    ecg  = constrain(ecg,  30.0f, 200.0f);
}

void genererPression(float &sys, float &dia) {
    sys = press_sys + randF(-5.0f, 5.0f);
    dia = press_dia + randF(-3.0f, 3.0f);
    sys = constrain(sys, 90.0f, 180.0f);
    dia = constrain(dia, 50.0f, 120.0f);
}

void genererMouvement(int &mouvement, int &chute) {
    mouvement = (random(100) < 15) ? 1 : 0;
    chute     = (eventType == 1)   ? 1 : 0;
}

void genererPerfuseur(float &debit, float &niveau, int &alarme) {
    perf_niveau -= (perf_debit / 120.0f) + randF(0.0f, 0.2f);
    perf_niveau  = max(0.0f, perf_niveau);
    debit = perf_debit + randF(-2.0f, 2.0f);

    if (perf_niveau < 50.0f || eventType == 4) {
        alarme = 1;
        if (eventType == 4 && --eventTicks <= 0) { eventType = 0; }
    } else {
        alarme = 0;
    }

    if (perf_niveau <= 0.0f) {
        perf_niveau = 500.0f;
        Serial.println("[PERF] Poche rechargee -- reset");
    }
}

float genererCO2() {
    return 600.0f + randF(-50.0f, 50.0f) + (eventType != 0 ? 100.0f : 0.0f);
}

// ════════════════════════════════════════════════════════════════════
//  MQTT
// ════════════════════════════════════════════════════════════════════

void reconnect() {
    while (!client.connected()) {
        Serial.print("MQTT connexion... ");
        String clientId = String(DEVICE_ID) + "_" + String(millis());
        if (client.connect(clientId.c_str(), MQTT_USER, MQTT_PASSWORD)) {
            Serial.println("OK");
        } else {
            Serial.printf("err=%d  retry 5s\n", client.state());
            delay(5000);
        }
    }
}

// ════════════════════════════════════════════════════════════════════
//  SETUP
// ════════════════════════════════════════════════════════════════════

void setup() {
    Serial.begin(115200);
    delay(500);
    randomSeed(analogRead(0) ^ millis());

    snprintf(TOPIC_VITAUX,     64, "clinique/chambre/%s/vitaux",         CHAMBRE_ID);
    snprintf(TOPIC_CO2,        64, "clinique/chambre/%s/co2",            CHAMBRE_ID);
    snprintf(TOPIC_MOUVEMENT,  64, "clinique/chambre/%s/mouvement",      CHAMBRE_ID);
    snprintf(TOPIC_PERFUSEUR,  64, "clinique/chambre/%s/perfuseur",      CHAMBRE_ID);
    snprintf(TOPIC_APPEL,      64, "clinique/chambre/%s/appel",          CHAMBRE_ID);
    snprintf(TOPIC_APPEL_SECU, 64, "clinique/chambre/%s/appel_securite", CHAMBRE_ID);

    dht.begin();
    pinMode(PIN_BOUTON,    INPUT_PULLUP);
    pinMode(PIN_MOUVEMENT, OUTPUT);
    pinMode(PIN_ALERTE,    OUTPUT);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("WiFi");
    while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
    Serial.println("\nWiFi OK : " + WiFi.localIP().toString());

    espClient.setCACert(root_ca);
    client.setKeepAlive(60); 
    client.setServer(MQTT_SERVER, MQTT_PORT);
    client.setBufferSize(512); 

    Serial.println("========================================");
    Serial.printf("  CLINIQUE CONNECTEE -- Chambre %s\n", CHAMBRE_ID);
    Serial.printf("  Patient : %s\n", PATIENT_ID);
    Serial.println("========================================");
}

// ════════════════════════════════════════════════════════════════════
//  LOOP
// ════════════════════════════════════════════════════════════════════

void loop() {
    if (!client.connected()) reconnect();
    client.loop();

    unsigned long now = millis();

    // ── Gestion bouton appel patient ─────────────────────────────
    bool boutonPressed = (digitalRead(PIN_BOUTON) == LOW);
    if (boutonPressed && !boutonWasPressed) {
        boutonPressedAt  = now;
        boutonWasPressed = true;
    }
    if (!boutonPressed && boutonWasPressed) {
        unsigned long duree = now - boutonPressedAt;
        boutonWasPressed = false;
        char payload[256];

        if (duree >= 3000) {
            // Appui long >= 3s → alarme securite vers controleur
            snprintf(payload, sizeof(payload),
                "appel_securite,chambre_id=%s,patient_id=%s "
                "type=\"securite\",priorite=\"ROUGE\",duree_ms=%lu,timestamp=%lu",
                CHAMBRE_ID, PATIENT_ID, duree, now);
            client.publish(TOPIC_APPEL_SECU, payload);
            Serial.printf("APPEL SECURITE envoye (%lums)\n", duree);
        } else {
            // Appui court → alerte medicale
            snprintf(payload, sizeof(payload),
                "appel,chambre_id=%s,patient_id=%s "
                "type=\"medical\",priorite=\"ORANGE\",duree_ms=%lu,timestamp=%lu",
                CHAMBRE_ID, PATIENT_ID, duree, now);
            client.publish(TOPIC_APPEL, payload);
            Serial.printf("APPEL MEDICAL envoye (%lums)\n", duree);
        }
    }

    // ── Publication toutes les 10 secondes ───────────────────────
    static unsigned long lastPub = 0;
    if (now - lastPub < 10000) return;
    lastPub = now;

    float spo2, ecg, temp_corp;
    genererVitaux(spo2, ecg, temp_corp);

    float sys_val, dia_val;
    genererPression(sys_val, dia_val);

    int mouvement, chute;
    genererMouvement(mouvement, chute);
    digitalWrite(PIN_MOUVEMENT, mouvement ? HIGH : LOW);

    float perf_debit_val, perf_niveau_val;
    int   perf_alarme;
    genererPerfuseur(perf_debit_val, perf_niveau_val, perf_alarme);

    float co2 = genererCO2();

    // Priorité alerte
    String priorite = "VERT";
    if (spo2 < 90.0f || ecg > 150.0f || chute == 1 || perf_alarme == 1) priorite = "ROUGE";
    else if (spo2 < 94.0f || ecg > 120.0f || temp_corp > 38.5f)          priorite = "ORANGE";

    bool alerte = (priorite != "VERT");
    digitalWrite(PIN_ALERTE, alerte ? HIGH : LOW);

    // Publish VITAUX
    char payload[512];
    snprintf(payload, sizeof(payload),
        "vitaux_chambre,chambre_id=%s,patient_id=%s,device_id=%s "
        "spo2=%.1f,ecg_bpm=%.1f,temperature=%.1f,"
        "pression_sys=%.1f,pression_dia=%.1f,"
        "alerte_active=%s,timestamp_esp=%lu",
        CHAMBRE_ID, PATIENT_ID, DEVICE_ID,
        spo2, ecg, temp_corp,
        sys_val, dia_val,
        alerte ? "true" : "false",
        now
    );
    client.publish(TOPIC_VITAUX, payload);

    // Publish CO2
    snprintf(payload, sizeof(payload),
        "co2_ambiant,chambre_id=%s,device_id=%s co2_ppm=%.1f,timestamp_esp=%lu",
        CHAMBRE_ID, DEVICE_ID, co2, now);
    client.publish(TOPIC_CO2, payload);

    // Publish MOUVEMENT
    snprintf(payload, sizeof(payload),
        "mouvement,chambre_id=%s,patient_id=%s,device_id=%s "
        "mouvement=%d,chute_detectee=%d,timestamp_esp=%lu",
        CHAMBRE_ID, PATIENT_ID, DEVICE_ID, mouvement, chute, now);
    client.publish(TOPIC_MOUVEMENT, payload);

    // Publish PERFUSEUR
    snprintf(payload, sizeof(payload),
        "perfuseur,chambre_id=%s,patient_id=%s,perfuseur_id=PERF-001 "
        "debit_ml_h=%.1f,niveau_poche_ml=%.1f,alarme=%d,timestamp_esp=%lu",
        CHAMBRE_ID, PATIENT_ID,
        perf_debit_val, perf_niveau_val, perf_alarme, now);
    client.publish(TOPIC_PERFUSEUR, payload);

    // Log serie
    Serial.println("----------------------------------------");
    Serial.printf("[%s | %s]\n", CHAMBRE_ID, PATIENT_ID);
    Serial.printf("  SpO2=%.1f%%  ECG=%.0fbpm  T=%.1fC\n", spo2, ecg, temp_corp);
    Serial.printf("  PA=%d/%d mmHg  CO2=%.0fppm\n", (int)sys_val, (int)dia_val, co2);
    Serial.printf("  Mvt=%d Chute=%d Perf=%.0fmL Alarme=%d\n",
                  mouvement, chute, perf_niveau_val, perf_alarme);
    Serial.printf("  Priorite: %s\n", priorite.c_str());
}