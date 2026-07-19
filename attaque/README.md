Ce dossier contient des scripts de démonstration et de simulation liés à des attaques MQTT et réseau dans le cadre de la clinique connectée.


## Contenu

- `attaque_spoofing.py` : simulateur pédagogique d’une attaque MITM par ARP spoofing.
  - Ne réalise pas d’attaque réseau réelle.
  - Affiche des logs d’exécution et génère des payloads falsifiés au format InfluxDB Line Protocol.
  - Peut être exécuté en mode simulation sécurisée (`dry-run`) ou avec publication MQTT réelle.

- `attaque_replay.py` : script d’attaque par rejeu (replay attack) MQTT.
  - Permet de capturer des messages publiés sur un broker MQTT.
  - Permet de les rejouer ensuite avec ou sans modification des valeurs.

- `capture.json` : exemple de fichier de capture généré par le script de replay.

## Prérequis

Installer les dépendances Python nécessaires :

```bash
pip install paho-mqtt
```

## Utilisation

### 1. Simuler une attaque spoofing

Exécution en mode sécurisé (par défaut) :

```bash
python attaque_spoofing.py --verbose
```

Exécution réelle (à utiliser avec prudence) :

```bash
python attaque_spoofing.py --execute --verbose
```

### 2. Capturer des messages MQTT

```bash
python attaque_replay.py --mode capture --file capture.json
```

### 3. Rejouer les messages capturés

```bash
python attaque_replay.py --mode replay --file capture.json --delay 0.5
```

Avec modification aléatoire des valeurs :

```bash
python attaque_replay.py --mode replay --file capture.json --modify --delay 0.1
```

## Notes importantes

- Ces scripts sont destinés à des fins pédagogiques et de démonstration.
- Ils doivent être utilisés uniquement dans un environnement contrôlé et autorisé.
- Les attaques simulées ne doivent pas être exécutées contre des systèmes réels sans autorisation explicite.

## Résumé

Ce dossier sert à illustrer :
- la logique d’un MITM simulé,
- le principe du replay attack MQTT,
- et l’impact potentiel d’une falsification de données sur un système IoT.
