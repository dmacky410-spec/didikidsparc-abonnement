@echo off
rem Pont lecteur RFID ACR122U — a lancer en plus du serveur sur le poste d'accueil
cd /d "%~dp0"
title Pont RFID ACR122U - Didikids Parc
"%~dp0python\python.exe" bridge\acr122u_bridge.py
pause
