# Configuration Mosquitto (MQTT sécurisé)

Ce dossier contient la configuration du broker **Mosquitto** pour la clinique connectée.

##  Objectif
- Sécuriser les communications MQTT avec TLS/SSL.
- Authentifier les capteurs et garantir la confidentialité des données médicales.

##  Contenu
- `mosquitto.conf` : configuration du broker.
- `certs/` : certificats TLS.
- `setup_auth.sh` : script d’initialisation de l’authentification.

##  Mise en place
1. Installer Mosquitto sur le serveur.
2. Copier les certificats TLS dans `certs/`.
3. Lancer le script :
   ```bash
   ./setup_auth.sh
