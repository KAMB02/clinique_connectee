#!/bin/bash
# ════════════════════════════════════════════════════════════════
#  Script de setup Auth MQTT — Clinique Connectée
#  Lance depuis le dossier racine du projet
# ════════════════════════════════════════════════════════════════

echo "=== Setup Auth MQTT Clinique Connectée ==="

# Créer le fichier de passwords (vide d'abord)
docker exec clinique_mosquitto sh -c "touch /mosquitto/config/passwd"

# Ajouter chaque utilisateur avec le password clinique2026
for user in esp32_chambre esp32_securite esp32_energie esp32_controleur telegraf_agent nodered_agent admin_clinique; do
  docker exec clinique_mosquitto mosquitto_passwd -b /mosquitto/config/passwd $user clinique2026
  echo "  ✅ User créé : $user"
done

echo ""
echo "Copie des configs..."
docker cp mosquitto/config/acl clinique_mosquitto:/mosquitto/config/acl
docker cp mosquitto/config/mosquitto.conf clinique_mosquitto:/mosquitto/config/mosquitto.conf

echo "Redémarrage Mosquitto..."
docker restart clinique_mosquitto
sleep 2
echo ""
echo "=== Auth MQTT configurée et active ==="
echo "Test : docker exec clinique_mosquitto mosquitto_sub -t 'clinique/#' -u telegraf_agent -P clinique2026 -v"