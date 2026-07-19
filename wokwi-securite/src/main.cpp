#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <PubSubClient.h>

// ════════════════════════════════════════════════════════════════════
//  CLINIQUE CONNECTÉE — ESP32 SÉCURITÉ
//  Simule les capteurs de sécurité de la clinique :
//    - Détecteur ouverture porte  (GPIO 0  = bouton BOOT)
//    - Badge RFID                 (simulé en code)
//    - Caméra HD                  (événement JSON simulé)
//    - LED alarme intrusion       (GPIO 2)
//    - LED accès autorisé         (GPIO 15)
//
//  Topics publiés :
//    clinique/acces/{zone}/porte       → ouverture/fermeture porte
//    clinique/acces/{zone}/badge       → badge scanné + autorisation
//    clinique/securite/{zone}/camera   → détection intrusion IA
//    clinique/alerte/controleur        → toutes alertes → contrôleur
// ════════════════════════════════════════════════════════════════════

// ── Identité device ──────────────────────────────────────────────
const char* DEVICE_ID  = "ESP32_SECU";
const char* ZONE_ID    = "couloir-B";

// ── Réseau ───────────────────────────────────────────────────────
const char* WIFI_SSID     = "Wokwi-GUEST";
const char* WIFI_PASSWORD = "";
const char* MQTT_SERVER   = "host.wokwi.internal";
const int   MQTT_PORT     = 8883; // MQTT TLS
const char* MQTT_USER     = "esp32_securite";
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
char TOPIC_PORTE[64];
char TOPIC_BADGE[64];
char TOPIC_CAMERA[64];
char TOPIC_ALERTE_CTRL[64];

// ── GPIOs ────────────────────────────────────────────────────────
#define PIN_BOUTON_PORTE  0   // BOOT button = détecteur ouverture porte
#define PIN_LED_ALARME    2   // LED rouge = intrusion détectée
#define PIN_LED_ACCES     15  // LED verte = accès autorisé

// ── MQTT ─────────────────────────────────────────────────────────
WiFiClientSecure espClient;
PubSubClient      client(espClient);

// ── État sécurité ────────────────────────────────────────────────
bool  porteOuverte       = false;
bool  portePrecedente    = false;
unsigned long porteOpenAt = 0;

// Événements sécurité simulés
int  secuEvent     = 0;  // 0=normal 1=intrusion 2=badge_invalide 3=ronde_secu
int  secuTicks     = 0;
unsigned long pubCount = 0;

// Pool de badges simulés
const char* BADGES_AUTORISES[] = {
    "BADGE-MED-001", "BADGE-MED-002", "BADGE-INF-007",
    "BADGE-INF-008", "BADGE-TECH-003", "BADGE-CTRL-001"
};
const char* BADGES_REFUSES[] = {
    "BADGE-INCONNU-999", "BADGE-EXPIRE-042", "BADGE-VISITE-????"
};

// ── Utilitaires ──────────────────────────────────────────────────
float randF(float lo, float hi) {
    return lo + ((float)random(0, 10000) / 10000.0f) * (hi - lo);
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
//  PUBLICATION PORTE
// ════════════════════════════════════════════════════════════════════

void publierPorte(bool ouverte) {
    char payload[256];
    snprintf(payload, sizeof(payload),
        "securite_acces,zone=%s,capteur_id=PORTE-%s,device_id=%s "
        "porte_ouverte=%s,duree_ouverte_ms=%lu,timestamp_esp=%lu",
        ZONE_ID, ZONE_ID, DEVICE_ID,
        ouverte ? "true" : "false",
        ouverte ? 0UL : (unsigned long)(millis() - porteOpenAt),
        millis()
    );
    client.publish(TOPIC_PORTE, payload);
    Serial.printf("[PORTE] %s -- zone=%s\n", ouverte ? "OUVERTE" : "FERMEE", ZONE_ID);
}

// ════════════════════════════════════════════════════════════════════
//  PUBLICATION BADGE
// ════════════════════════════════════════════════════════════════════

void publierBadge(bool intrusion) {
    char payload[256];
    bool autorise;
    const char* badgeId;

    if (intrusion) {
        // Badge refusé → intrusion simulée
        badgeId  = BADGES_REFUSES[random(3)];
        autorise = false;
    } else {
        // Badge autorisé
        badgeId  = BADGES_AUTORISES[random(6)];
        autorise = true;
    }

    snprintf(payload, sizeof(payload),
        "badge_acces,zone=%s,device_id=%s "
        "badge_id=\"%s\",autorise=%s,timestamp_esp=%lu",
        ZONE_ID, DEVICE_ID,
        badgeId,
        autorise ? "true" : "false",
        millis()
    );
    client.publish(TOPIC_BADGE, payload);

    Serial.printf("[BADGE] %s -- badge=%s autorise=%s\n",
                  ZONE_ID, badgeId, autorise ? "OUI" : "NON");

    // Si refusé → alerte intrusion vers contrôleur
    if (!autorise) {
        char alerte[256];
        snprintf(alerte, sizeof(alerte),
            "alerte_controleur,zone=%s,type=intrusion_badge,device_id=%s "
            "badge_id=\"%s\",priorite=\"ROUGE\",autorise=false,timestamp_esp=%lu",
            ZONE_ID, DEVICE_ID, badgeId, millis()
        );
        client.publish(TOPIC_ALERTE_CTRL, alerte);
        digitalWrite(PIN_LED_ALARME, HIGH);
        Serial.println("[ALERTE] INTRUSION BADGE -- controleur notifie");
    } else {
        digitalWrite(PIN_LED_ACCES, HIGH);
        // delay(500);
        digitalWrite(PIN_LED_ACCES, LOW);
    }
}

// ════════════════════════════════════════════════════════════════════
//  PUBLICATION CAMÉRA
// ════════════════════════════════════════════════════════════════════

void publierCamera(bool intrusion) {
    char payload[256];
    snprintf(payload, sizeof(payload),
        "camera_intrusion,zone=%s,camera_id=CAM-%s,device_id=%s "
        "intrusion_ia=%s,mouvement_detecte=%s,confiance_pct=%.1f,timestamp_esp=%lu",
        ZONE_ID, ZONE_ID, DEVICE_ID,
        intrusion ? "true" : "false",
        intrusion ? "true" : "false",
        intrusion ? randF(82.0f, 99.0f) : randF(0.0f, 15.0f),
        millis()
    );
    client.publish(TOPIC_CAMERA, payload);

    if (intrusion) {
        // Alerte caméra vers contrôleur
        char alerte[256];
        snprintf(alerte, sizeof(alerte),
            "alerte_controleur,zone=%s,type=intrusion_camera,device_id=%s "
            "confiance_pct=%.1f,priorite=\"ROUGE\",timestamp_esp=%lu",
            ZONE_ID, DEVICE_ID, randF(82.0f, 99.0f), millis()
        );
        client.publish(TOPIC_ALERTE_CTRL, alerte);
        digitalWrite(PIN_LED_ALARME, HIGH);
        Serial.printf("[CAMERA] INTRUSION DETECTEE -- zone=%s\n", ZONE_ID);
    } else {
        Serial.printf("[CAMERA] OK -- zone=%s\n", ZONE_ID);
    }
}

// ════════════════════════════════════════════════════════════════════
//  SETUP
// ════════════════════════════════════════════════════════════════════

void setup() {
    Serial.begin(115200);
    delay(500);
    randomSeed(analogRead(0) ^ millis());

    snprintf(TOPIC_PORTE,       64, "clinique/acces/%s/porte",     ZONE_ID);
    snprintf(TOPIC_BADGE,       64, "clinique/acces/%s/badge",     ZONE_ID);
    snprintf(TOPIC_CAMERA,      64, "clinique/securite/%s/camera", ZONE_ID);
    snprintf(TOPIC_ALERTE_CTRL, 64, "clinique/alerte/controleur");

    pinMode(PIN_BOUTON_PORTE, INPUT_PULLUP);
    pinMode(PIN_LED_ALARME,   OUTPUT);
    pinMode(PIN_LED_ACCES,    OUTPUT);
    digitalWrite(PIN_LED_ALARME, LOW);
    digitalWrite(PIN_LED_ACCES,  LOW);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
    Serial.print("WiFi");
    while (WiFi.status() != WL_CONNECTED) { delay(500); Serial.print("."); }
    Serial.println("\nWiFi OK : " + WiFi.localIP().toString());

    espClient.setCACert(root_ca);
    client.setKeepAlive(60); 
    client.setServer(MQTT_SERVER, MQTT_PORT);
    client.setBufferSize(512);

    Serial.println("========================================");
    Serial.printf("  CLINIQUE CONNECTEE -- Securite\n");
    Serial.printf("  Zone : %s\n", ZONE_ID);
    Serial.println("  Bouton BOOT = ouverture/fermeture porte");
    Serial.println("========================================");
}

// ════════════════════════════════════════════════════════════════════
//  LOOP
// ════════════════════════════════════════════════════════════════════

void loop() {
    if (!client.connected()) reconnect();
    client.loop();

    unsigned long now = millis();

    // ── Détecteur porte (bouton BOOT) ────────────────────────────
    porteOuverte = (digitalRead(PIN_BOUTON_PORTE) == LOW);
    if (porteOuverte != portePrecedente) {
        portePrecedente = porteOuverte;
        if (porteOuverte) {
            porteOpenAt = now;
            publierPorte(true);
            // Chaque ouverture → scan badge automatique
            // delay(200);
            // 20% chance d'intrusion (badge refusé)
            publierBadge(random(100) < 20);
        } else {
            publierPorte(false);
            digitalWrite(PIN_LED_ALARME, LOW);
        }
    }

    // ── Événements automatiques toutes les 15 secondes ───────────
    static unsigned long lastPub = 0;
    if (now - lastPub < 15000) return;
    lastPub = now;
    pubCount++;

    // Événement sécurité aléatoire (~1 toutes les 10 pubs)
    if (secuEvent == 0 && random(1000) < 100) {
        int roll = random(3);
        if      (roll == 0) { secuEvent = 1; secuTicks = 2; }  // intrusion caméra
        else if (roll == 1) { secuEvent = 2; secuTicks = 1; }  // badge invalide
        else                { secuEvent = 3; secuTicks = 3; }  // ronde normale
    }

    if (secuEvent == 1) {
        publierCamera(true);
        if (--secuTicks <= 0) { secuEvent = 0; digitalWrite(PIN_LED_ALARME, LOW); }
    } else if (secuEvent == 2) {
        publierBadge(true);  // intrusion forcée
        if (--secuTicks <= 0) { secuEvent = 0; }
    } else if (secuEvent == 3) {
        // Ronde normale : caméra OK + badge autorisé
        publierCamera(false);
        publierBadge(false);
        if (--secuTicks <= 0) { secuEvent = 0; }
    } else {
        // État normal : caméra OK
        publierCamera(false);
    }

    Serial.println("----------------------------------------");
    Serial.printf("[SECU] Zone=%s  Event=%d  Pub#%lu\n", ZONE_ID, secuEvent, pubCount);
}