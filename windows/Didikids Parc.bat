@echo off
rem Lanceur Didikids Parc — demarre le serveur et ouvre le navigateur
cd /d "%~dp0"
start "Didikids Parc - Serveur" /min "%~dp0python\python.exe" server.py
