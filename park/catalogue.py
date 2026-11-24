"""Catalogue officiel Didikids Parc (affiche tarifaire).

Quatre formules — fréquence × durée de séance — vendues à la semaine ou au mois.
Le mois vaut exactement quatre semaines.
"""

# Une entrée = une séance. La durée de la séance (1h ou 2h) est une
# caractéristique de la formule : elle se contrôle sur place, pas au décompte.
# (nom, prix, séances, validité en jours, heures par séance)
FORMULES = [
    ("1h · 2 fois/semaine — Semaine",   140_000,  2,  7, 1),
    ("1h · 2 fois/semaine — Mois",      560_000,  8, 30, 1),
    ("1h · 3 fois/semaine — Semaine",   210_000,  3,  7, 1),
    ("1h · 3 fois/semaine — Mois",      840_000, 12, 30, 1),
    ("2h · 2 fois/semaine — Semaine",   220_000,  2,  7, 2),
    ("2h · 2 fois/semaine — Mois",      880_000,  8, 30, 2),
    ("2h · 3 fois/semaine — Semaine",   330_000,  3,  7, 2),
    ("2h · 3 fois/semaine — Mois",    1_320_000, 12, 30, 2),
]


def appliquer(conn, desactiver_anciens=True):
    """Met le catalogue à jour sans toucher aux abonnements déjà vendus.

    Les anciennes formules sont désactivées (jamais supprimées) : les
    abonnements en cours continuent de fonctionner et l'historique reste lisible.
    """
    noms = [f[0] for f in FORMULES]
    if desactiver_anciens:
        marques = ",".join("?" * len(noms))
        conn.execute(
            f"UPDATE subscription_types SET active=0 WHERE name NOT IN ({marques})", noms)

    for nom, prix, entrees, jours, heures in FORMULES:
        existant = conn.execute(
            "SELECT id FROM subscription_types WHERE name=?", (nom,)).fetchone()
        if existant:
            conn.execute(
                """UPDATE subscription_types
                   SET price=?, entries=?, validity_days=?, hours_per_session=?, active=1
                   WHERE id=?""",
                (prix, entrees, jours, heures, existant[0]))
        else:
            conn.execute(
                """INSERT INTO subscription_types
                   (name, price, entries, validity_days, hours_per_session, active)
                   VALUES (?,?,?,?,?,1)""", (nom, prix, entrees, jours, heures))
    return len(FORMULES)
