"""Catalogue Didikids Parc.

Deux familles de produits :
  • les formules de l'affiche — fréquence × durée, prix fixé, non négociable ;
  • les ventes libres (entrée simple, 4 entrées) — l'employé saisit le montant.

Une entrée vaut une séance. La durée de la séance est une caractéristique
de la formule, elle se contrôle sur place.
"""

# (nom, prix, séances, validité en jours, heures/séance, prix libre)
FORMULES = [
    # --- formules de l'affiche, prix imposé
    ("1h · 2 fois/semaine — Semaine",   140_000,  2,  7, 1, 0),
    ("1h · 2 fois/semaine — Mois",      560_000,  8, 30, 1, 0),
    ("1h · 3 fois/semaine — Semaine",   210_000,  3,  7, 1, 0),
    ("1h · 3 fois/semaine — Mois",      840_000, 12, 30, 1, 0),
    ("2h · 2 fois/semaine — Semaine",   220_000,  2,  7, 2, 0),
    ("2h · 2 fois/semaine — Mois",      880_000,  8, 30, 2, 0),
    ("2h · 3 fois/semaine — Semaine",   330_000,  3,  7, 2, 0),
    ("2h · 3 fois/semaine — Mois",    1_320_000, 12, 30, 2, 0),
    # --- ventes libres, montant saisi au comptoir
    ("Entrée simple — 1h",                    0,  1,  1, 1, 1),
    ("Entrée simple — 2h",                    0,  1,  1, 2, 1),
    ("4 entrées — 1h",                        0,  4, 30, 1, 1),
    ("4 entrées — 2h",                        0,  4, 30, 2, 1),
]


def appliquer(conn, desactiver_anciens=True):
    """Met le catalogue à jour sans toucher aux abonnements déjà vendus.

    Les formules absentes sont désactivées, jamais supprimées : les
    abonnements en cours continuent de fonctionner et l'historique reste lisible.
    """
    noms = [f[0] for f in FORMULES]
    if desactiver_anciens:
        marques = ",".join("?" * len(noms))
        conn.execute(
            f"UPDATE subscription_types SET active=0 WHERE name NOT IN ({marques})", noms)

    for nom, prix, seances, jours, heures, libre in FORMULES:
        existant = conn.execute(
            "SELECT id FROM subscription_types WHERE name=?", (nom,)).fetchone()
        if existant:
            conn.execute(
                """UPDATE subscription_types
                   SET price=?, entries=?, validity_days=?, hours_per_session=?,
                       free_price=?, active=1
                   WHERE id=?""",
                (prix, seances, jours, heures, libre, existant[0]))
        else:
            conn.execute(
                """INSERT INTO subscription_types
                   (name, price, entries, validity_days, hours_per_session, free_price, active)
                   VALUES (?,?,?,?,?,?,1)""", (nom, prix, seances, jours, heures, libre))
    return len(FORMULES)
