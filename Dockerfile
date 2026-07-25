# Didikids Parc — image de déploiement cloud
FROM python:3.12-slim

WORKDIR /app
COPY server.py README.md ./
COPY park ./park
COPY public ./public

# En cloud : pas d'ouverture de navigateur, données sur un volume persistant
ENV NO_BROWSER=1 \
    DIDIKIDS_DATA_DIR=/app/data \
    PORT=8730

VOLUME ["/app/data"]
EXPOSE 8730

CMD ["python", "server.py"]
