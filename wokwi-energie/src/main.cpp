#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

// ════════════════════════════════════════════════════════════════════
//  CLINIQUE CONNECTÉE — ESP32 ÉNERGIE
//  Simule les capteurs du système électrique :
//    - UPS                  (niveau batterie via potentiomètre GPIO 34)
//    - Groupe électrogène   (simulé en code)
//    - Compteur électrique  (consommation par circuit simulée)
//    - LED statut UPS       (GPIO 2  = vert:secteur / rouge:batterie)
//    - LED groupe élec      (GPIO 15 = allumé si générateur actif)
//
//  Scénario 4 simulé automatiquement :
//    Panne secteur → basculement UPS (0-5s) → démarrage générateur (5-10s)
//    → supervision circuit (10-30s) → notification maintenance
//
//  Topics publiés :
//    clinique/energie/ups                  → statut, niveau, autonomie
//    clinique/energie/generateur           → statut, charge
//    clinique/energie/compteur/{circuit}   → consommation W
//    clinique/alerte/controleur            → panne → notification technique
// ════════════════════════════════════════════════════════════════════

// ── Identité device ──────────────────────────────────────────────
const char* DEVICE_ID = "ESP32_ENERGIE";

// ── Réseau ───────────────────────────────────────────────────────
const char* WIFI_SSID     = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";
const char* MQTT_SERVER   = "host.wokwi.internal";
const int   MQTT_PORT     = 8883; // MQTT TLS
const char* MQTT_USER     = "esp32_energie";
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
#define TOPIC_UPS         "clinique/energie/ups"
#define TOPIC_GENERATEUR  "clinique/energie/generateur"
#define TOPIC_CPT_BLOC_A  "clinique/energie/compteur/BLOC-A"
#define TOPIC_CPT_BLOC_B  "clinique/energie/compteur/BLOC-B"
#define TOPIC_CPT_URGENCE "clinique/energie/compteur/URGENCE"
#define TOPIC_ALERTE_CTRL "clinique/alerte/controleur"

// ── GPIOs ────────────────────────────────────────────────────────
#define PIN_POT_UPS      34   // Potentiomètre = niveau batterie UPS
#define PIN_LED_UPS       2   // LED verte = secteur OK / éteinte = batterie
#define PIN_LED_GROUPE   15   // LED jaune = groupe électrogène actif

// ── MQTT ─────────────────────────────────────────────────────────
WiFiClientSecure espClient;
PubSubClient      client(espClient);

// ── États énergie ────────────────────────────────────────────────
// Source actuelle
enum SourceEnergie { SECTEUR, UPS_BATTERIE, GENERATEUR };
SourceEnergie sourceActuelle = SECTEUR;

// UPS
float ups_niveau     = 100.0f;  // % batterie
float ups_autonomie  = 60.0f;   // minutes restantes
bool  ups_en_charge  = true;

// Générateur
bool  gen_actif      = false;
float gen_charge_pct = 0.0f;
int   gen_demarrage_ticks = 0;

// Panne simulée
int  panneEvent  = 0;  // 0=normal 1=panne_secteur 2=circuit_defaillant 3=batterie_faible
int  panneTicks  = 0;
unsigned long panneStartMs = 0;
unsigned long pubCount = 0;

// Consommation circuits (W)
float conso_bloc_a   = 0.0f;
float conso_bloc_b   = 0.0f;
float conso_urgence  = 0.0f;

// ── Utilitaires ──────────────────────────────────────────────────
float randF(float lo, float hi) {
    return lo + ((float)random(0, 10000) / 10000.0f) * (hi - lo);
}

// ── Lecture potentiomètre → niveau UPS ───────────────────────────
float lireNiveauUPS() {
    // Wokwi : potentiomètre sur GPIO34 (ADC1_CH6)
    analogReadResolution(12);
    int raw = analogRead(34);
    if (raw < 10) return 85.0f; // fallback si ADC retourne 0
    return constrain((raw / 4095.0f) * 100.0f, 0.0f, 100.0f);
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
//  SCÉNARIO 4 — GESTION PANNE ÉLECTRIQUE
// ════════════════════════════════════════════════════════════════════

void gererScenarioPanne() {
    unsigned long elapsed = millis() - panneStartMs;

    if (panneEvent == 1) {
        // PANNE SECTEUR — scénario complet J1–J5
        if (elapsed < 5000) {
            // Phase 1 (0-5s) : basculement UPS
            sourceActuelle = UPS_BATTERIE;
            ups_en_charge  = false;
            ups_niveau    -= 0.5f;
            ups_autonomie  = ups_niveau * 0.6f;
            Serial.println("[PANNE] Phase 1: Basculement UPS");

        } else if (elapsed < 10000) {
            // Phase 2 (5-10s) : démarrage générateur
            gen_demarrage_ticks++;
            if (gen_demarrage_ticks > 2) {
                gen_actif     = true;
                gen_charge_pct = randF(40.0f, 60.0f);
                sourceActuelle = GENERATEUR;
                Serial.println("[PANNE] Phase 2: Generateur demarre");
            }

        } else if (elapsed < 30000) {
            // Phase 3 (10-30s) : supervision circuit
            gen_charge_pct += randF(-2.0f, 2.0f);
            gen_charge_pct  = constrain(gen_charge_pct, 30.0f, 95.0f);
            Serial.printf("[PANNE] Phase 3: Supervision -- gen=%.0f%%\n", gen_charge_pct);

        } else {
            // Phase 4 (>30s) : retour à la normale
            sourceActuelle = SECTEUR;
            gen_actif      = false;
            gen_charge_pct = 0.0f;
            ups_en_charge  = true;
            panneEvent     = 0;
            Serial.println("[PANNE] Retour secteur -- incident resolu");

            // Notif maintenance
            char alerte[256];
            snprintf(alerte, sizeof(alerte),
                "alerte_controleur,zone=salle-technique,type=panne_resolue,device_id=%s "
                "duree_ms=%lu,source_retour=\"secteur\",priorite=\"VERT\",timestamp_esp=%lu",
                DEVICE_ID, elapsed, millis()
            );
            client.publish(TOPIC_ALERTE_CTRL, alerte);
        }

    } else if (panneEvent == 2) {
        // CIRCUIT DÉFAILLANT
        Serial.printf("[PANNE] Circuit defaillant -- ticks=%d\n", panneTicks);
        if (--panneTicks <= 0) {
            panneEvent = 0;
            char alerte[256];
            snprintf(alerte, sizeof(alerte),
                "alerte_controleur,zone=salle-technique,type=circuit_defaillant,device_id=%s "
                "circuit=\"BLOC-B\",priorite=\"ORANGE\",timestamp_esp=%lu",
                DEVICE_ID, millis()
            );
            client.publish(TOPIC_ALERTE_CTRL, alerte);
        }

    } else if (panneEvent == 3) {
        // BATTERIE FAIBLE UPS
        ups_niveau -= 2.0f;
        if (ups_niveau < 10.0f || --panneTicks <= 0) {
            panneEvent = 0;
            char alerte[256];
            snprintf(alerte, sizeof(alerte),
                "alerte_controleur,zone=salle-technique,type=batterie_faible,device_id=%s "
                "niveau_pct=%.1f,priorite=\"ROUGE\",timestamp_esp=%lu",
                DEVICE_ID, ups_niveau, millis()
            );
            client.publish(TOPIC_ALERTE_CTRL, alerte);
        }
    }
}

// ════════════════════════════════════════════════════════════════════
//  PUBLICATION
// ════════════════════════════════════════════════════════════════════

void publierUPS() {
    // Lire potentiomètre si secteur OK, sinon décharge simulée
    if (sourceActuelle == SECTEUR && ups_en_charge) {
        ups_niveau   = lireNiveauUPS();
        ups_autonomie = ups_niveau * 0.6f;
    }

    const char* statut = (sourceActuelle == UPS_BATTERIE) ? "batterie" :
                         (sourceActuelle == GENERATEUR)   ? "generateur" : "secteur";

    char payload[256];
    snprintf(payload, sizeof(payload),
        "energie_ups,device_id=%s "
        "statut=\"%s\",niveau_pct=%.1f,autonomie_min=%.1f,"
        "en_charge=%s,tension_v=%.1f,timestamp_esp=%lu",
        DEVICE_ID,
        statut, ups_niveau, ups_autonomie,
        ups_en_charge ? "true" : "false",
        (sourceActuelle == SECTEUR) ? 220.5f : randF(210.0f, 220.0f),
        millis()
    );
    client.publish(TOPIC_UPS, payload);
    digitalWrite(PIN_LED_UPS, (sourceActuelle == SECTEUR) ? HIGH : LOW);
}

void publierGenerateur() {
    char payload[256];
    snprintf(payload, sizeof(payload),
        "energie_generateur,device_id=%s "
        "actif=%s,charge_pct=%.1f,statut=\"%s\",timestamp_esp=%lu",
        DEVICE_ID,
        gen_actif ? "true" : "false",
        gen_charge_pct,
        gen_actif ? "marche" : "arret",
        millis()
    );
    client.publish(TOPIC_GENERATEUR, payload);
    digitalWrite(PIN_LED_GROUPE, gen_actif ? HIGH : LOW);
}

void publierCompteurs() {
    // Consommation normale clinique
    conso_bloc_a   = 1200.0f + randF(-100.0f, 100.0f);   // Bloc soins
    conso_bloc_b   = 800.0f  + randF(-80.0f, 80.0f);     // Bloc admin
    conso_urgence  = 2500.0f + randF(-150.0f, 150.0f);   // Bloc urgences

    // Si panne circuit B → conso chute
    if (panneEvent == 2) conso_bloc_b = randF(0.0f, 50.0f);

    char payload[128];

    snprintf(payload, sizeof(payload),
        "energie_compteur,circuit=BLOC-A,device_id=%s consommation_w=%.1f,timestamp_esp=%lu",
        DEVICE_ID, conso_bloc_a, millis());
    client.publish(TOPIC_CPT_BLOC_A, payload);

    snprintf(payload, sizeof(payload),
        "energie_compteur,circuit=BLOC-B,device_id=%s consommation_w=%.1f,timestamp_esp=%lu",
        DEVICE_ID, conso_bloc_b, millis());
    client.publish(TOPIC_CPT_BLOC_B, payload);

    snprintf(payload, sizeof(payload),
        "energie_compteur,circuit=URGENCE,device_id=%s consommation_w=%.1f,timestamp_esp=%lu",
        DEVICE_ID, conso_urgence, millis());
    client.publish(TOPIC_CPT_URGENCE, payload);
}

// ════════════════════════════════════════════════════════════════════
//  SETUP
// ════════════════════════════════════════════════════════════════════

void setup() {
    Serial.begin(115200);
    delay(500);
    randomSeed(analogRead(0) ^ millis());

    pinMode(PIN_LED_UPS,    OUTPUT);
    pinMode(PIN_LED_GROUPE, OUTPUT);
    digitalWrite(PIN_LED_UPS,    HIGH);  // Secteur OK au départ
    digitalWrite(PIN_LED_GROUPE, LOW);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("WiFi");
    while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
    Serial.println("\nWiFi OK : " + WiFi.localIP().toString());

    espClient.setCACert(root_ca);
    client.setKeepAlive(60); 
    client.setServer(MQTT_SERVER, MQTT_PORT);
    client.setBufferSize(512);
    
    Serial.println("========================================");
    Serial.println("  CLINIQUE CONNECTEE -- Energie");
    Serial.println("  POT GPIO34 = niveau UPS manuel");
    Serial.println("  Panne auto toutes ~20 pubs");
    Serial.println("========================================");
}

// ════════════════════════════════════════════════════════════════════
//  LOOP
// ════════════════════════════════════════════════════════════════════

void loop() {
    if (!client.connected()) reconnect();
    client.loop();

    unsigned long now = millis();

    static unsigned long lastPub = 0;
    if (now - lastPub < 10000) return;
    lastPub = now;
    pubCount++;

    // Déclenche un scénario de panne toutes ~20 pubs
    if (panneEvent == 0 && random(1000) < 50) {
        int roll = random(3);
        panneStartMs = now;
        if      (roll == 0) { panneEvent = 1; Serial.println("[PANNE] Panne secteur!"); }
        else if (roll == 1) { panneEvent = 2; panneTicks = 4; Serial.println("[PANNE] Circuit defaillant!"); }
        else                { panneEvent = 3; panneTicks = 5; Serial.println("[PANNE] Batterie faible!"); }

        // Notif immédiate technicien
        char alerte[256];
        const char* type = (panneEvent==1) ? "panne_secteur" :
                           (panneEvent==2) ? "circuit_defaillant" : "batterie_faible";
        snprintf(alerte, sizeof(alerte),
            "alerte_controleur,zone=salle-technique,type=%s,device_id=%s "
            "priorite=\"ROUGE\",timestamp_esp=%lu",
            type, DEVICE_ID, now
        );
        client.publish(TOPIC_ALERTE_CTRL, alerte);
    }

    // Gérer scénario en cours
    if (panneEvent != 0) gererScenarioPanne();

    // Recharger UPS si secteur OK
    if (sourceActuelle == SECTEUR && ups_en_charge) {
        ups_niveau = min(100.0f, ups_niveau + 0.5f);
    }

    // Publier tous les capteurs
    publierUPS();
    publierGenerateur();
    publierCompteurs();

    Serial.println("----------------------------------------");
    Serial.printf("[ENERGIE] Source=%s  UPS=%.0f%%  Gen=%s\n",
        sourceActuelle == SECTEUR    ? "SECTEUR" :
        sourceActuelle == GENERATEUR ? "GENERATEUR" : "UPS",
        ups_niveau,
        gen_actif ? "ON" : "OFF"
    );
    Serial.printf("  Conso: A=%.0fW  B=%.0fW  URG=%.0fW\n",
                  conso_bloc_a, conso_bloc_b, conso_urgence);
}