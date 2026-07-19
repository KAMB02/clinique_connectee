FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1

RUN pip install --no-cache-dir paho-mqtt==1.6.1

COPY simulateur_clinique.py .

# --broker/--port/--interval restent modifiables via `command:` dans
# docker-compose.yaml si besoin ; par défaut on cible le service mosquitto
# du réseau Docker interne (pas "localhost").
ENTRYPOINT ["python", "simulateur_clinique.py", "--broker", "clinique_mosquitto", "--port", "8883"]