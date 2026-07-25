# 🐻 Didikids Parc — Gestion des abonnements

Logiciel de gestion d'abonnements pour parc de jeux indoor, avec contrôle
d'accès par cartes RFID/NFC **MIFARE Classic 1K (13,56 MHz)** et lecteur
**ACR122U**.

**Zéro dépendance** : seul Python 3.8+ est nécessaire (bibliothèque standard
uniquement). Idéal pour un poste d'accueil sans connexion internet fiable.

---

## ☁️ Déploiement cloud (Railway)

Le dépôt contient tout le nécessaire (`Dockerfile`, `railway.json`) :

1. **railway.app** → *Login with GitHub* → *New Project* → *Deploy from GitHub repo*
   → choisir `didikidsparc-abonnement`.
2. **Ajouter un volume** (`⌘K` → *New Volume*) avec le chemin de montage
   **`/app/data`** — c'est ce qui rend les données permanentes.
3. **Variables d'environnement** (onglet *Variables*) :
   - `ADMIN_USERNAME` : votre identifiant de super administrateur
   - `ADMIN_PASSWORD` : un mot de passe solide (évite le compte d'usine)
4. *Settings* → *Networking* → **Generate Domain** (ou un domaine personnalisé
   du type `gestion.didikidsparc.com`).

Chaque `git push` redéploie automatiquement. Le poste d'accueil ouvre simplement
cette adresse dans Chrome ; le pont RFID local pointe vers elle avec
`--server https://votre-adresse --token <jeton>`.

## 🪟 Installation sur le PC Windows du parc

Le paquet autonome `dist/DidikidsParc-Windows.zip` contient le logiciel
**avec Python embarqué** : rien à installer sur le PC, pas d'internet requis.
Voir `windows/LISEZMOI.txt` (copie du dossier, raccourci Bureau, démarrage
automatique, lecteur ACR122U inclus).

Pour reconstruire le paquet depuis un Mac/Linux :

```bash
./windows/build_windows.sh chemin/python-3.12.x-embed-amd64.zip chemin/pyscard-*-win_amd64.whl
```

## 🚀 Démarrage rapide (développement, Mac/Linux)

```bash
python3 server.py
```

Puis ouvrir **http://localhost:8730** dans le navigateur (Chrome ou Edge recommandé).

**Compte initial : `admin` / `admin123`** — ⚠️ changez ce mot de passe dès la
première connexion (page Employés → Modifier).

La base de données SQLite est créée automatiquement dans `data/didikidsparc.db`.

## 🔌 Lecteur RFID ACR122U

Sur le poste d'accueil (une seule fois) :

```bash
pip install pyscard
```

Puis lancer le pont en parallèle du serveur :

```bash
python3 bridge/acr122u_bridge.py
```

Le pont détecte l'ACR122U, lit l'UID des cartes MIFARE et l'envoie au logiciel
en temps réel — l'écran d'accueil valide l'entrée automatiquement.

- Si le pont tourne sur un **autre ordinateur**, ajoutez
  `--server http://IP_DU_SERVEUR:8730 --token JETON` (le jeton s'affiche au
  démarrage de `server.py`).
- Les lecteurs bon marché à **émulation clavier** fonctionnent aussi sans le
  pont : cliquez dans le champ de saisie de la page Accueil et passez la carte.
- Sans lecteur, l'UID peut être saisi à la main (mode secours).

## 👥 Rôles

| Rôle | Accès |
|---|---|
| **Super administrateur** | Tout, plus ce que personne d'autre ne peut faire : prix et types d'abonnements, modification d'un montant encaissé, annulation d'abonnement, comptes employés, paramètres, exports Excel |
| **Gérant** | Membres, cartes, ventes **au prix catalogue**, paiements, tableau de bord |
| **Agent accueil** | Entrées, inscription et modification des membres, attribution et remplacement des cartes, ventes **au prix catalogue** — mais ni revenus, ni statistiques, ni réglages |

Chaque vente et chaque entrée enregistre le nom de l'employé qui l'a faite.

## 📖 Utilisation quotidienne

1. **Nouveau client** : Membres → *Nouveau membre* → remplir la fiche.
2. **Attribuer une carte** : ouvrir la fiche du membre → *Attribuer une carte*
   → poser la carte sur le lecteur (l'UID se remplit seul).
3. **Vendre un abonnement** : fiche du membre → *Vendre un abonnement* →
   choisir la formule → encaisser → le reçu s'imprime.
4. **À l'entrée** : page Accueil → l'enfant pose sa carte → validation
   automatique (vert = OK, rouge = refusé avec le motif).
5. **Carte perdue** : fiche du membre → *Carte perdue — la remplacer* → passer
   la nouvelle carte sur le lecteur. En une seule opération l'ancienne est
   désactivée (refusée à l'accueil) et la nouvelle devient active. L'abonnement,
   les entrées restantes et l'historique de l'enfant sont conservés.
   Un enfant n'a qu'une seule carte active à la fois ; les anciennes restent
   consultables via « Voir les anciennes cartes ».

## 🗄️ Architecture

```
server.py                  Serveur HTTP (bibliothèque standard, port 8730)
park/db.py                 Schéma SQLite + initialisation
park/auth.py               Sessions + mots de passe (scrypt)
park/api.py                Logique métier (API REST JSON)
public/                    Interface web (thème didikidsparc.com)
bridge/acr122u_bridge.py   Pont lecteur ACR122U → serveur
data/didikidsparc.db       Base de données (créée au 1er lancement)
```

**Tables** : `users`, `employees`, `members`, `rfid_cards`,
`subscription_types`, `subscriptions`, `payments`, `visits`, `sessions`,
`settings`.

L'API REST (`/api/...`) est déjà prête pour les évolutions prévues :
application mobile, plusieurs points d'entrée (plusieurs ponts RFID peuvent
pointer vers le même serveur), paiement en ligne, QR code de secours, cloud.

## 💾 Sauvegarde

Copiez simplement le fichier `data/didikidsparc.db` (par exemple sur une clé
USB, chaque soir). Pour restaurer : remettez le fichier et relancez le serveur.

## ⚙️ Divers

- Port : `PORT=9000 python3 server.py` pour changer.
- Impression des reçus : format ticket 80 mm, via la boîte d'impression du
  navigateur (imprimante thermique ou A4).
- Types d'abonnements par défaut : Entrée simple, Mensuel 4 entrées,
  Mensuel 8 entrées, VIP Illimité — prix modifiables dans l'onglet
  Abonnements.
