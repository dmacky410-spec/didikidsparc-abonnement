# Régénérer les captures d'écran du guide

Les images de `formation/captures/` sont de vraies captures du logiciel.
À refaire quand l'interface change :

1. Lancer le logiciel : `NO_BROWSER=1 python3 server.py`
2. Lancer le récepteur d'images : `python3 formation/outils/serveur_capture.py`
   (il écrit dans `formation/outils/shots/`)
3. Préparer les polices (une fois) — voir `polices.md`
4. Dans la console du navigateur, sur `http://localhost:8730`, coller
   `capture_navigateur.js`, puis appeler par exemple :
   `await __shoot('05_nouveau_membre', '.modal', 14)`
5. Copier les PNG obtenus dans `formation/captures/`
6. Reconstruire : `python3 formation/build_guide_agent.py`

Le script sérialise le DOM dans un SVG puis le peint sur un canvas :
la capture est fidèle au pixel, avec les vraies polices du site.
