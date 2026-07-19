# Clinique Connectée — Structure Wokwi PlatformIO

## Organisation des 3 projets

```
Mini-Projet-IoT/
│
├── wokwi-chambre/          ← ESP32 #1 — Chambre Patient
│   ├── src/
│   │   └── main.cpp        ← main.cpp (chambre)
│   ├── diagram.json        ← diagram.json (chambre)
│   ├── platformio.ini
│   └── wokwi.toml
│
├── wokwi-securite/         ← ESP32 #2 — Sécurité & Accès
│   ├── src/
│   │   └── main.cpp        ← main_securite.cpp (renommer en main.cpp)
│   ├── diagram.json        ← diagram_securite.json (renommer)
│   ├── platformio.ini
│   └── wokwi.toml
│
└── wokwi-energie/          ← ESP32 #3 — Énergie
    ├── src/
    │   └── main.cpp        ← main_energie.cpp (renommer en main.cpp)
    ├── diagram.json        ← diagram_energie.json (renommer)
    ├── platformio.ini
    └── wokwi.toml
```

## platformio.ini (identique pour les 3)

```ini
[env:esp32dev]
platform = espressif32
board = esp32dev
framework = arduino
lib_deps =
    knolleary/PubSubClient@^2.8
    adafruit/DHT sensor library@^1.4.6
    adafruit/Adafruit Unified Sensor@^1.1.14
```
> Note : DHT uniquement nécessaire pour wokwi-chambre

## wokwi.toml (identique pour les 3)

```toml
[wokwi]
version = 1
firmware = '.pio/build/esp32dev/firmware.bin'
elf = '.pio/build/esp32dev/firmware.elf'
```

## Lancement simultané des 3 simulations

1. Ouvrir 3 fenêtres VS Code
2. Chaque fenêtre ouvre un dossier projet différent
3. Dans chaque fenêtre : Ctrl+Shift+P → "Wokwi: Start Simulator"
4. Les 3 ESP32 publient sur le même broker Mosquitto local

## Topics MQTT par ESP32

### ESP32 Chambre (CH-001)
- clinique/chambre/CH-001/vitaux
- clinique/chambre/CH-001/co2
- clinique/chambre/CH-001/mouvement
- clinique/chambre/CH-001/perfuseur
- clinique/chambre/CH-001/appel          (appui court bouton)
- clinique/chambre/CH-001/appel_securite (appui long 3s)

### ESP32 Sécurité (couloir-B)
- clinique/acces/couloir-B/porte
- clinique/acces/couloir-B/badge
- clinique/securite/couloir-B/camera
- clinique/alerte/controleur

### ESP32 Énergie
- clinique/energie/ups
- clinique/energie/generateur
- clinique/energie/compteur/BLOC-A
- clinique/energie/compteur/BLOC-B
- clinique/energie/compteur/URGENCE
- clinique/alerte/controleur

## Composants physiques dans Wokwi

### Chambre
| Composant | GPIO | Rôle |
|-----------|------|------|
| DHT22 | 4 | T° corporelle |
| Bouton rouge | 0 | Appel patient (court=médical, long=sécurité) |
| LED rouge | 15 | Alerte active |
| LED jaune | 2 | Mouvement détecté |

### Sécurité
| Composant | GPIO | Rôle |
|-----------|------|------|
| Bouton vert | 0 | Ouverture porte + scan badge |
| LED rouge | 2 | Alarme intrusion |
| LED verte | 15 | Accès autorisé |

### Énergie
| Composant | GPIO | Rôle |
|-----------|------|------|
| Potentiomètre | 34 | Niveau batterie UPS (manuel) |
| LED verte | 2 | Secteur OK |
| LED jaune | 15 | Générateur actif |