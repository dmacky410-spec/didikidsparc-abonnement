# Didikids Parc — image de déploiement cloud
FROM python:3.12-slim

WORKDIR /app
COPY server.py README.md ./
COPY park ./park
COPY public ./public

# En cloud : pas d'ouverture de navigateur, données dans /app/data
# Le stockage permanent est fourni par le volume de l'hébergeur monté sur /app/data
# (pas de directive VOLUME ici : Railway la refuse et gère ses volumes lui-même)
ENV NO_BROWSER=1 \
    DIDIKIDS_DATA_DIR=/app/data \
    PORT=8730

EXPOSE 8730

CMD ["python", "server.py"]
