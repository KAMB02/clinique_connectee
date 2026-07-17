#!/bin/bash
# Script de setup Auth MQTT — Clinique Connectée
# À lancer depuis la racine du projet
# 0. Donner les droits d'exécution au script lui-même
chmod +x setup_auth.sh
echo "Droits d'exécution appliqués au script setup_auth.sh"

echo "== Setup Auth MQTT Clinique Connectée =="

# 1. Génération de la clé privée et du certificat auto-signé
# Les fichiers seront placés dans le dossier certs/
openssl genrsa -out certs/server.key 2048
openssl req -new -x509 -key certs/server.key -out certs/server.crt -days 365 -subj "/CN=clinique_connectee"

echo "Certificat TLS généré : certs/server.crt et clé privée : certs/server.key"

# 2. Message final
echo "Setup terminé : certificats TLS générés et prêts à être utilisés par Mosquitto."