# Polices embarquées pour les captures

Le rendu SVG n'a pas accès au réseau : les polices Google doivent être
intégrées en base64 dans un fichier CSS servi par l'application.

```bash
curl -s -A "Mozilla/5.0" \
  "https://fonts.googleapis.com/css2?family=Fredoka+One&family=Nunito:wght@400;600;700;800&display=swap" \
  -o fonts.css
# puis remplacer chaque URL fonts.gstatic.com par une data URI base64,
# en ne gardant que les blocs « latin » (voir l'historique du dépôt)
cp fonts_latin.css public/_fonts_capture.css
```

Deux pièges rencontrés :
- au-delà d'environ 500 Ko, l'URL `data:` du SVG est tronquée et les
  dernières polices ne se chargent plus ;
- pour la capture d'un élément seul, la règle `body { font-family }` ne
  s'applique plus : il faut la reporter sur le conteneur ;
- la règle `@media (max-width: 800px)` doit être retirée, sinon la
  capture d'une fenêtre étroite bascule en affichage mobile.
