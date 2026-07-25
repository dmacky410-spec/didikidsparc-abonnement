"""API REST — toute la logique métier."""
from datetime import datetime, timedelta

from park import db
from park.auth import hash_password, verify_password, create_session, delete_session


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def today():
    return datetime.now().strftime("%Y-%m-%d")


def require(body, *fields):
    for f in fields:
        if body.get(f) in (None, ""):
            raise ApiError(400, f"Champ requis : {f}")


ROLE_LEVEL = {"agent": 1, "admin": 2, "superadmin": 3}


def require_admin(user):
    """Gérant ou super administrateur."""
    if ROLE_LEVEL.get(user["role"], 0) < ROLE_LEVEL["admin"]:
        raise ApiError(403, "Réservé au gérant ou au super administrateur")


def require_super(user):
    if user["role"] != "superadmin":
        raise ApiError(403, "Réservé au super administrateur")


def is_admin(user):
    return ROLE_LEVEL.get(user["role"], 0) >= ROLE_LEVEL["admin"]


def normalize_uid(uid):
    return uid.replace(":", "").replace(" ", "").replace("-", "").upper().strip()


# ---------------------------------------------------------------- membres

def next_member_code(conn):
    row = conn.execute("SELECT MAX(id) AS m FROM members").fetchone()
    return "M-%04d" % ((row["m"] or 0) + 1)


def member_summary(conn, member_id):
    """Membre + carte active + abonnement courant."""
    m = conn.execute("SELECT * FROM members WHERE id=?", (member_id,)).fetchone()
    if not m:
        raise ApiError(404, "Membre introuvable")
    member = dict(m)
    member["cards"] = [dict(r) for r in conn.execute(
        "SELECT * FROM rfid_cards WHERE member_id=? ORDER BY assigned_at DESC", (member_id,))]
    member["subscriptions"] = [dict(r) for r in conn.execute(
        """SELECT s.*, t.name AS type_name, t.price AS type_price
           FROM subscriptions s JOIN subscription_types t ON t.id=s.type_id
           WHERE s.member_id=? ORDER BY s.created_at DESC""", (member_id,))]
    member["current_subscription"] = current_subscription(conn, member_id)
    member["visit_count"] = conn.execute(
        "SELECT COUNT(*) AS c FROM visits WHERE member_id=? AND result='ok'",
        (member_id,)).fetchone()["c"]
    return member


def current_subscription(conn, member_id):
    """Abonnement valide aujourd'hui, avec des entrées restantes (ou illimité).
    S'il y en a plusieurs, on consomme d'abord celui qui expire le plus tôt."""
    row = conn.execute(
        """SELECT s.*, t.name AS type_name
           FROM subscriptions s JOIN subscription_types t ON t.id=s.type_id
           WHERE s.member_id=? AND s.status='active'
             AND s.start_date <= ? AND s.end_date >= ?
             AND (s.entries_left IS NULL OR s.entries_left > 0)
           ORDER BY s.end_date ASC LIMIT 1""",
        (member_id, today(), today())).fetchone()
    return dict(row) if row else None


def list_members(conn, query):
    q = (query.get("q") or "").strip()
    sql = """SELECT m.*,
               (SELECT uid FROM rfid_cards c WHERE c.member_id=m.id AND c.status='active'
                ORDER BY assigned_at DESC LIMIT 1) AS card_uid
             FROM members m WHERE m.active=1"""
    params = []
    if q:
        sql += """ AND (m.child_name LIKE ? OR m.parent_name LIKE ? OR m.phone LIKE ?
                   OR m.code LIKE ?)"""
        like = f"%{q}%"
        params = [like, like, like, like]
    sql += " ORDER BY m.created_at DESC LIMIT 200"
    members = [dict(r) for r in conn.execute(sql, params)]
    for m in members:
        m["current_subscription"] = current_subscription(conn, m["id"])
    return members


def create_member(conn, body, user):
    require(body, "child_name")
    code = next_member_code(conn)
    cur = conn.execute(
        """INSERT INTO members (code, child_name, parent_name, phone, email, birth_date, notes, created_at)
           VALUES (?,?,?,?,?,?,?,?)""",
        (code, body["child_name"].strip(), (body.get("parent_name") or "").strip(),
         (body.get("phone") or "").strip(), (body.get("email") or "").strip(),
         body.get("birth_date") or "", body.get("notes") or "", db.now_iso()))
    return member_summary(conn, cur.lastrowid)


def update_member(conn, member_id, body):
    require(body, "child_name")
    conn.execute(
        """UPDATE members SET child_name=?, parent_name=?, phone=?, email=?, birth_date=?, notes=?
           WHERE id=?""",
        (body["child_name"].strip(), (body.get("parent_name") or "").strip(),
         (body.get("phone") or "").strip(), (body.get("email") or "").strip(),
         body.get("birth_date") or "", body.get("notes") or "", member_id))
    return member_summary(conn, member_id)


# ---------------------------------------------------------------- cartes RFID

def assign_card(conn, body, user, _from_replace=False):
    require(body, "member_id", "uid")
    uid = normalize_uid(body["uid"])
    if not uid:
        raise ApiError(400, "UID invalide")
    member_id = int(body["member_id"])

    # Un seul badge actif par enfant : sinon deux cartes ouvriraient le même abonnement
    if not _from_replace:
        active = conn.execute(
            "SELECT uid FROM rfid_cards WHERE member_id=? AND status='active'",
            (member_id,)).fetchone()
        if active and normalize_uid(active["uid"]) != uid:
            raise ApiError(409, "Ce membre a déjà une carte active. "
                                "Utilisez « Carte perdue — la remplacer ».")

    existing = conn.execute("SELECT * FROM rfid_cards WHERE uid=?", (uid,)).fetchone()
    if existing:
        if existing["status"] == "active":
            owner = conn.execute("SELECT child_name FROM members WHERE id=?",
                                 (existing["member_id"],)).fetchone()
            if existing["member_id"] == member_id:
                raise ApiError(409, "Cette carte est déjà active sur cette fiche")
            raise ApiError(409, f"Cette carte est déjà attribuée à {owner['child_name']}")
        # Carte bloquée retrouvée par son propriétaire : on la réactive
        if existing["member_id"] == member_id:
            conn.execute(
                """UPDATE rfid_cards SET status='active', blocked_at=NULL, block_reason=NULL,
                   assigned_at=?, card_number=? WHERE id=?""",
                (db.now_iso(), (body.get("card_number") or existing["card_number"] or "").strip(),
                 existing["id"]))
            return member_summary(conn, member_id)
        raise ApiError(409, "Cette carte a été bloquée sur une autre fiche. Utilisez une autre carte.")
    conn.execute(
        "INSERT INTO rfid_cards (uid, card_number, member_id, status, assigned_at) VALUES (?,?,?,?,?)",
        (uid, (body.get("card_number") or "").strip(), member_id, "active", db.now_iso()))
    return member_summary(conn, member_id)


def replace_card(conn, body, user):
    """Carte perdue : désactive l'ancienne et enregistre la nouvelle en une seule opération."""
    require(body, "member_id", "uid")
    member_id = int(body["member_id"])
    new_uid = normalize_uid(body["uid"])
    if not new_uid:
        raise ApiError(400, "UID invalide")

    old = conn.execute(
        """SELECT * FROM rfid_cards WHERE member_id=? AND status='active'
           ORDER BY assigned_at DESC""", (member_id,)).fetchall()
    if any(normalize_uid(c["uid"]) == new_uid for c in old):
        raise ApiError(409, "C'est la carte déjà active sur cette fiche — rien à remplacer")

    # La nouvelle carte doit être libre
    clash = conn.execute("SELECT * FROM rfid_cards WHERE uid=?", (new_uid,)).fetchone()
    if clash and clash["member_id"] != member_id and clash["status"] == "active":
        owner = conn.execute("SELECT child_name FROM members WHERE id=?",
                             (clash["member_id"],)).fetchone()
        raise ApiError(409, f"Cette nouvelle carte appartient déjà à {owner['child_name']}")

    reason = (body.get("reason") or "Carte perdue").strip()
    for card in old:
        conn.execute(
            "UPDATE rfid_cards SET status='blocked', blocked_at=?, block_reason=? WHERE id=?",
            (db.now_iso(), reason, card["id"]))

    assign_card(conn, {"member_id": member_id, "uid": new_uid,
                       "card_number": body.get("card_number")}, user, _from_replace=True)
    result = member_summary(conn, member_id)
    result["replaced_count"] = len(old)
    return result


def block_card(conn, card_id, body):
    card = conn.execute("SELECT * FROM rfid_cards WHERE id=?", (card_id,)).fetchone()
    if not card:
        raise ApiError(404, "Carte introuvable")
    conn.execute(
        "UPDATE rfid_cards SET status='blocked', blocked_at=?, block_reason=? WHERE id=?",
        (db.now_iso(), body.get("reason") or "Carte perdue", card_id))
    return member_summary(conn, card["member_id"])


# ---------------------------------------------------------------- abonnements

def sell_subscription(conn, body, user):
    """Vend un abonnement : crée l'abonnement + le paiement, retourne le reçu."""
    require(body, "member_id", "type_id")
    t = conn.execute("SELECT * FROM subscription_types WHERE id=? AND active=1",
                     (body["type_id"],)).fetchone()
    if not t:
        raise ApiError(404, "Type d'abonnement introuvable")
    member = conn.execute("SELECT * FROM members WHERE id=?", (body["member_id"],)).fetchone()
    if not member:
        raise ApiError(404, "Membre introuvable")

    start = body.get("start_date") or today()
    try:
        end = (datetime.strptime(start, "%Y-%m-%d")
               + timedelta(days=t["validity_days"])).strftime("%Y-%m-%d")
    except ValueError:
        raise ApiError(400, "Date de début invalide (AAAA-MM-JJ)")

    # Anti-fraude : seul le super administrateur peut modifier le montant.
    # Les autres encaissent au prix catalogue, point final.
    if user["role"] == "superadmin":
        amount = int(body.get("amount", t["price"]))
    else:
        amount = t["price"]
    cur = conn.execute(
        """INSERT INTO subscriptions
           (member_id, type_id, start_date, end_date, entries_total, entries_left, status, created_at, created_by)
           VALUES (?,?,?,?,?,?,'active',?,?)""",
        (member["id"], t["id"], start, end, t["entries"], t["entries"], db.now_iso(), user["id"]))
    sub_id = cur.lastrowid

    receipt = next_receipt_number(conn)
    conn.execute(
        """INSERT INTO payments (receipt_number, subscription_id, member_id, amount, method, note, paid_at, user_id)
           VALUES (?,?,?,?,?,?,?,?)""",
        (receipt, sub_id, member["id"], amount, body.get("method") or "especes",
         body.get("note") or "", db.now_iso(), user["id"]))

    return {
        "member": member_summary(conn, member["id"]),
        "receipt": get_receipt(conn, receipt),
    }


def cancel_subscription(conn, sub_id):
    sub = conn.execute("SELECT * FROM subscriptions WHERE id=?", (sub_id,)).fetchone()
    if not sub:
        raise ApiError(404, "Abonnement introuvable")
    conn.execute("UPDATE subscriptions SET status='cancelled' WHERE id=?", (sub_id,))
    return member_summary(conn, sub["member_id"])


# ---------------------------------------------------------------- contrôle d'accès (accueil)

def lookup_by_uid(conn, uid):
    """Retrouve le membre à partir d'un UID de carte, sans décompter."""
    uid = normalize_uid(uid)
    card = conn.execute("SELECT * FROM rfid_cards WHERE uid=?", (uid,)).fetchone()
    if not card:
        return {"found": False, "uid": uid, "reason": "Carte inconnue"}
    member = member_summary(conn, card["member_id"])
    return {"found": True, "uid": uid, "card": dict(card), "member": member}


def check_in(conn, body, user):
    """Passage d'une carte à l'accueil : valide ou refuse l'entrée."""
    require(body, "uid")
    uid = normalize_uid(body["uid"])
    now = db.now_iso()

    def refuse(reason, member_id=None, sub_id=None):
        conn.execute(
            """INSERT INTO visits (member_id, subscription_id, card_uid, result, refusal_reason, visited_at, user_id)
               VALUES (?,?,?,'refused',?,?,?)""",
            (member_id, sub_id, uid, reason, now, user["id"]))
        result = {"allowed": False, "reason": reason, "uid": uid}
        if member_id:
            result["member"] = member_summary(conn, member_id)
        return result

    card = conn.execute("SELECT * FROM rfid_cards WHERE uid=?", (uid,)).fetchone()
    if not card:
        return refuse("Carte inconnue — non attribuée")
    if card["status"] == "blocked":
        return refuse("Carte bloquée (perdue/désactivée)", card["member_id"])

    member = conn.execute("SELECT * FROM members WHERE id=? AND active=1",
                          (card["member_id"],)).fetchone()
    if not member:
        return refuse("Membre inactif", card["member_id"])

    sub = current_subscription(conn, member["id"])
    if not sub:
        # Distinguer « expiré » de « plus d'entrées » pour un message clair
        last = conn.execute(
            """SELECT s.*, t.name AS type_name FROM subscriptions s
               JOIN subscription_types t ON t.id=s.type_id
               WHERE s.member_id=? AND s.status='active'
               ORDER BY s.end_date DESC LIMIT 1""", (member["id"],)).fetchone()
        if last and last["end_date"] < today():
            return refuse(f"Abonnement expiré le {last['end_date']}", member["id"], last["id"])
        if last and last["entries_left"] == 0:
            return refuse("Plus d'entrées disponibles", member["id"], last["id"])
        return refuse("Aucun abonnement actif", member["id"])

    # Avertissement si l'enfant est déjà passé aujourd'hui (double passage)
    already = conn.execute(
        """SELECT COUNT(*) AS c FROM visits
           WHERE member_id=? AND result='ok' AND visited_at LIKE ?""",
        (member["id"], today() + "%")).fetchone()["c"]

    # Fidélité : la Nième visite payante est offerte (n'entame pas le quota)
    reward = loyalty_check(conn, member["id"])
    if not reward and sub["entries_left"] is not None:
        conn.execute("UPDATE subscriptions SET entries_left = entries_left - 1 WHERE id=?",
                     (sub["id"],))

    conn.execute(
        """INSERT INTO visits (member_id, subscription_id, card_uid, result, visited_at, user_id, free_reward)
           VALUES (?,?,?,'ok',?,?,?)""",
        (member["id"], sub["id"], uid, now, user["id"], 1 if reward else 0))

    result = {
        "allowed": True,
        "uid": uid,
        "member": member_summary(conn, member["id"]),
        "already_today": already,
        "visited_at": now,
        "free_reward": reward,
    }
    result["loyalty"] = loyalty_status(conn, member["id"])
    return result


# ---------------------------------------------------------------- fidélité

def loyalty_config(conn):
    enabled = db.get_setting(conn, "loyalty_enabled", "1") == "1"
    try:
        threshold = int(db.get_setting(conn, "loyalty_threshold", "10"))
    except (TypeError, ValueError):
        threshold = 10
    return enabled, max(2, threshold)


def loyalty_status(conn, member_id):
    """Nombre de visites payantes depuis la dernière visite offerte."""
    enabled, threshold = loyalty_config(conn)
    if not enabled:
        return None
    last_reward = conn.execute(
        """SELECT visited_at FROM visits WHERE member_id=? AND free_reward=1
           ORDER BY visited_at DESC LIMIT 1""", (member_id,)).fetchone()
    params = [member_id]
    sql = "SELECT COUNT(*) AS c FROM visits WHERE member_id=? AND result='ok' AND free_reward=0"
    if last_reward:
        sql += " AND visited_at > ?"
        params.append(last_reward["visited_at"])
    paid = conn.execute(sql, params).fetchone()["c"]
    return {"paid_visits": paid, "threshold": threshold,
            "remaining": max(0, threshold - paid)}


def loyalty_check(conn, member_id):
    """True si cette visite doit être offerte (seuil atteint)."""
    status = loyalty_status(conn, member_id)
    if not status:
        return False
    already_today = conn.execute(
        """SELECT COUNT(*) AS c FROM visits WHERE member_id=? AND free_reward=1
           AND visited_at LIKE ?""", (member_id, today() + "%")).fetchone()["c"]
    return status["paid_visits"] >= status["threshold"] and already_today == 0


# ---------------------------------------------------------------- paiements

def next_receipt_number(conn):
    prefix = "R-" + datetime.now().strftime("%Y%m%d")
    row = conn.execute("SELECT COUNT(*) AS c FROM payments WHERE receipt_number LIKE ?",
                       (prefix + "%",)).fetchone()
    return "%s-%03d" % (prefix, row["c"] + 1)


def get_receipt(conn, receipt_number):
    row = conn.execute(
        """SELECT p.*, m.child_name, m.parent_name, m.code AS member_code,
                  t.name AS type_name, s.start_date, s.end_date, s.entries_total,
                  e.full_name AS cashier
           FROM payments p
           LEFT JOIN members m ON m.id = p.member_id
           LEFT JOIN subscriptions s ON s.id = p.subscription_id
           LEFT JOIN subscription_types t ON t.id = s.type_id
           LEFT JOIN users u ON u.id = p.user_id
           LEFT JOIN employees e ON e.id = u.employee_id
           WHERE p.receipt_number = ?""", (receipt_number,)).fetchone()
    if not row:
        raise ApiError(404, "Reçu introuvable")
    receipt = dict(row)
    receipt["park_name"] = db.get_setting(conn, "park_name", "Didikids Parc")
    receipt["park_address"] = db.get_setting(conn, "park_address", "")
    receipt["park_phone"] = db.get_setting(conn, "park_phone", "")
    receipt["footer"] = db.get_setting(conn, "receipt_footer", "")
    return receipt


def list_payments(conn, query):
    sql = """SELECT p.*, m.child_name, m.code AS member_code, t.name AS type_name,
                    e.full_name AS cashier
             FROM payments p
             LEFT JOIN members m ON m.id = p.member_id
             LEFT JOIN subscriptions s ON s.id = p.subscription_id
             LEFT JOIN subscription_types t ON t.id = s.type_id
             LEFT JOIN users u ON u.id = p.user_id
             LEFT JOIN employees e ON e.id = u.employee_id WHERE 1=1"""
    params = []
    if query.get("from"):
        sql += " AND p.paid_at >= ?"
        params.append(query["from"])
    if query.get("to"):
        sql += " AND p.paid_at <= ?"
        params.append(query["to"] + " 23:59:59")
    if query.get("member_id"):
        sql += " AND p.member_id = ?"
        params.append(query["member_id"])
    sql += " ORDER BY p.paid_at DESC LIMIT 500"
    rows = [dict(r) for r in conn.execute(sql, params)]
    total = sum(r["amount"] for r in rows)
    return {"payments": rows, "total": total}


# ---------------------------------------------------------------- visites

def list_visits(conn, query, user):
    sql = """SELECT v.*, m.child_name, m.code AS member_code, e.full_name AS agent
             FROM visits v
             LEFT JOIN members m ON m.id = v.member_id
             LEFT JOIN users u ON u.id = v.user_id
             LEFT JOIN employees e ON e.id = u.employee_id WHERE 1=1"""
    params = []
    # L'agent d'accueil ne voit que les visites du jour
    if not is_admin(user):
        sql += " AND v.visited_at LIKE ?"
        params.append(today() + "%")
    else:
        if query.get("from"):
            sql += " AND v.visited_at >= ?"
            params.append(query["from"])
        if query.get("to"):
            sql += " AND v.visited_at <= ?"
            params.append(query["to"] + " 23:59:59")
    if query.get("member_id"):
        sql += " AND v.member_id = ?"
        params.append(query["member_id"])
    sql += " ORDER BY v.visited_at DESC LIMIT 500"
    return [dict(r) for r in conn.execute(sql, params)]


# ---------------------------------------------------------------- tableau de bord

def dashboard(conn):
    t = today()
    now = datetime.now()
    month_start = t[:8] + "01"
    week_start = (now - timedelta(days=now.weekday())).strftime("%Y-%m-%d")
    in_7_days = (now + timedelta(days=7)).strftime("%Y-%m-%d")

    def one(sql, *params):
        return conn.execute(sql, params).fetchone()[0] or 0

    active_members = one(
        """SELECT COUNT(DISTINCT member_id) FROM subscriptions
           WHERE status='active' AND start_date <= ? AND end_date >= ?
           AND (entries_left IS NULL OR entries_left > 0)""", t, t)

    revenue = {
        "today": one("SELECT SUM(amount) FROM payments WHERE paid_at LIKE ?", t + "%"),
        "week": one("SELECT SUM(amount) FROM payments WHERE paid_at >= ?", week_start),
        "month": one("SELECT SUM(amount) FROM payments WHERE paid_at >= ?", month_start),
        "total": one("SELECT SUM(amount) FROM payments"),
    }

    visits = {
        "today": one("SELECT COUNT(*) FROM visits WHERE result='ok' AND visited_at LIKE ?", t + "%"),
        "week": one("SELECT COUNT(*) FROM visits WHERE result='ok' AND visited_at >= ?", week_start),
        "month": one("SELECT COUNT(*) FROM visits WHERE result='ok' AND visited_at >= ?", month_start),
    }

    expiring = expiry_reminders(conn, days=7)[:20]

    # Visites par jour — 14 derniers jours
    days = []
    for i in range(13, -1, -1):
        d = (now - timedelta(days=i)).strftime("%Y-%m-%d")
        days.append({"date": d, "count": one(
            "SELECT COUNT(*) FROM visits WHERE result='ok' AND visited_at LIKE ?", d + "%")})

    # Heures de pointe — 30 derniers jours
    since = (now - timedelta(days=30)).strftime("%Y-%m-%d")
    hours = {r["h"]: r["c"] for r in conn.execute(
        """SELECT CAST(substr(visited_at, 12, 2) AS INTEGER) AS h, COUNT(*) AS c
           FROM visits WHERE result='ok' AND visited_at >= ?
           GROUP BY h""", (since,))}
    peak_hours = [{"hour": h, "count": hours.get(h, 0)} for h in range(8, 23)]

    recent_members = one("SELECT COUNT(*) FROM members WHERE created_at >= ?", month_start)

    # Caisse du jour par employé (contrôle de fermeture)
    cash_today = [dict(r) for r in conn.execute(
        """SELECT COALESCE(e.full_name, u.username) AS employee,
                  COUNT(*) AS count, SUM(p.amount) AS total
           FROM payments p
           LEFT JOIN users u ON u.id = p.user_id
           LEFT JOIN employees e ON e.id = u.employee_id
           WHERE p.paid_at LIKE ?
           GROUP BY p.user_id ORDER BY total DESC""", (t + "%",))]

    return {
        "active_members": active_members,
        "total_members": one("SELECT COUNT(*) FROM members WHERE active=1"),
        "new_members_month": recent_members,
        "revenue": revenue,
        "visits": visits,
        "expiring_soon": expiring,
        "birthdays": birthdays(conn, days=30)[:20],
        "visits_by_day": days,
        "peak_hours": peak_hours,
        "cash_today": cash_today,
        "free_visits_month": one(
            "SELECT COUNT(*) FROM visits WHERE free_reward=1 AND visited_at >= ?", month_start),
    }


# ---------------------------------------------------------------- anniversaires & relances

def clean_phone(phone):
    """Format international pour WhatsApp (Guinée = +224 par défaut)."""
    digits = "".join(c for c in (phone or "") if c.isdigit())
    if not digits:
        return ""
    if digits.startswith("00"):
        digits = digits[2:]
    if len(digits) == 9 and digits.startswith("6"):   # numéro local guinéen
        digits = "224" + digits
    return digits


def fill_template(template, **values):
    out = template
    for key, value in values.items():
        out = out.replace("{" + key + "}", str(value))
    return out


def birthdays(conn, days=30):
    """Anniversaires à venir — pour proposer les packs fête."""
    now = datetime.now()
    rows = conn.execute(
        """SELECT id, code, child_name, parent_name, phone, birth_date
           FROM members WHERE active=1 AND birth_date IS NOT NULL AND birth_date != ''""").fetchall()
    template = db.get_setting(conn, "whatsapp_birthday_template", "")
    upcoming = []
    for r in rows:
        try:
            bd = datetime.strptime(r["birth_date"], "%Y-%m-%d")
        except ValueError:
            continue
        next_bd = bd.replace(year=now.year)
        if next_bd.date() < now.date():
            next_bd = bd.replace(year=now.year + 1)
        delta = (next_bd.date() - now.date()).days
        if delta > days:
            continue
        age = next_bd.year - bd.year
        item = dict(r)
        item.update({
            "next_birthday": next_bd.strftime("%Y-%m-%d"),
            "days_until": delta,
            "turning_age": age,
            "whatsapp_phone": clean_phone(r["phone"]),
            "whatsapp_message": fill_template(
                template, parent=r["parent_name"] or "cher parent",
                enfant=r["child_name"], date=next_bd.strftime("%d/%m/%Y"), age=age),
        })
        upcoming.append(item)
    upcoming.sort(key=lambda x: x["days_until"])
    return upcoming


def expiry_reminders(conn, days=7):
    """Abonnements expirant bientôt, avec message WhatsApp prêt à envoyer."""
    t = today()
    limit = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
    template = db.get_setting(conn, "whatsapp_expiry_template", "")
    rows = conn.execute(
        """SELECT s.id, s.end_date, s.entries_left, m.id AS member_id, m.child_name,
                  m.parent_name, m.phone, t.name AS type_name
           FROM subscriptions s
           JOIN members m ON m.id = s.member_id
           JOIN subscription_types t ON t.id = s.type_id
           WHERE s.status='active' AND s.end_date BETWEEN ? AND ?
           ORDER BY s.end_date ASC""", (t, limit)).fetchall()
    out = []
    for r in rows:
        item = dict(r)
        item["whatsapp_phone"] = clean_phone(r["phone"])
        item["whatsapp_message"] = fill_template(
            template, parent=r["parent_name"] or "cher parent", enfant=r["child_name"],
            expiration=fmt_fr(r["end_date"]),
            restantes="illimité" if r["entries_left"] is None else r["entries_left"],
            abonnement=r["type_name"])
        out.append(item)
    return out


def fmt_fr(iso_date):
    try:
        return datetime.strptime(iso_date, "%Y-%m-%d").strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return iso_date or ""


# ---------------------------------------------------------------- export comptable

def export_csv(conn, kind, query):
    """Export CSV (ouvrable dans Excel) des paiements ou des visites."""
    import csv
    import io
    buf = io.StringIO()
    writer = csv.writer(buf, delimiter=";")

    if kind == "payments":
        data = list_payments(conn, query)
        writer.writerow(["Recu", "Date", "Heure", "Membre", "Code", "Abonnement",
                         "Mode de paiement", "Montant GNF", "Encaisse par", "Note"])
        for p in data["payments"]:
            writer.writerow([
                p["receipt_number"], fmt_fr(p["paid_at"][:10]), p["paid_at"][11:16],
                p["child_name"] or "Visiteur", p["member_code"] or "",
                p["type_name"] or "", p["method"], p["amount"],
                p["cashier"] or "", p["note"] or ""])
        writer.writerow([])
        writer.writerow(["", "", "", "", "", "", "TOTAL", data["total"]])
        filename = "paiements"
    elif kind == "visits":
        visits = list_visits(conn, query, {"role": "superadmin"})
        writer.writerow(["Date", "Heure", "Membre", "Code", "Resultat",
                         "Motif refus", "Offerte", "Validee par"])
        for v in visits:
            writer.writerow([
                fmt_fr(v["visited_at"][:10]), v["visited_at"][11:16],
                v["child_name"] or "Visiteur", v["member_code"] or "",
                "Entree OK" if v["result"] == "ok" else "Refus",
                v["refusal_reason"] or "", "Oui" if v.get("free_reward") else "",
                v["agent"] or ""])
        filename = "visites"
    elif kind == "members":
        writer.writerow(["Code", "Enfant", "Parent", "Telephone", "Email",
                         "Naissance", "Abonnement actuel", "Entrees restantes",
                         "Expiration", "Total visites", "Inscrit le"])
        for m in list_members(conn, {}):
            s = m.get("current_subscription")
            visits = conn.execute(
                "SELECT COUNT(*) AS c FROM visits WHERE member_id=? AND result='ok'",
                (m["id"],)).fetchone()["c"]
            writer.writerow([
                m["code"], m["child_name"], m["parent_name"] or "", m["phone"] or "",
                m["email"] or "", fmt_fr(m["birth_date"]) if m["birth_date"] else "",
                s["type_name"] if s else "Aucun",
                ("Illimite" if s["entries_left"] is None else s["entries_left"]) if s else "",
                fmt_fr(s["end_date"]) if s else "", visits, fmt_fr(m["created_at"][:10])])
        filename = "membres"
    else:
        raise ApiError(404, "Export inconnu")

    return {"_csv": buf.getvalue(),
            "_filename": f"didikids_{filename}_{today()}.csv"}


# ---------------------------------------------------------------- types d'abonnements

def list_types(conn, include_inactive=False):
    sql = "SELECT * FROM subscription_types"
    if not include_inactive:
        sql += " WHERE active=1"
    sql += " ORDER BY price ASC"
    return [dict(r) for r in conn.execute(sql)]


def save_type(conn, body, type_id=None):
    require(body, "name", "price", "validity_days")
    entries = body.get("entries")
    entries = int(entries) if entries not in (None, "", "null") else None
    if type_id:
        conn.execute(
            "UPDATE subscription_types SET name=?, price=?, entries=?, validity_days=?, active=? WHERE id=?",
            (body["name"].strip(), int(body["price"]), entries, int(body["validity_days"]),
             1 if body.get("active", True) else 0, type_id))
    else:
        conn.execute(
            "INSERT INTO subscription_types (name, price, entries, validity_days) VALUES (?,?,?,?)",
            (body["name"].strip(), int(body["price"]), entries, int(body["validity_days"])))
    return list_types(conn, include_inactive=True)


# ---------------------------------------------------------------- employés & comptes

def list_users(conn):
    return [dict(r) for r in conn.execute(
        """SELECT u.id, u.username, u.role, u.active, u.created_at,
                  e.id AS employee_id, e.full_name, e.phone, e.position, e.hired_at
           FROM users u LEFT JOIN employees e ON e.id = u.employee_id
           ORDER BY u.created_at ASC""")]


def create_user(conn, body):
    require(body, "username", "password", "full_name", "role")
    if body["role"] not in ("superadmin", "admin", "agent"):
        raise ApiError(400, "Rôle invalide")
    if conn.execute("SELECT 1 FROM users WHERE username=?", (body["username"].strip(),)).fetchone():
        raise ApiError(409, "Ce nom d'utilisateur existe déjà")
    cur = conn.execute(
        "INSERT INTO employees (full_name, phone, position, hired_at) VALUES (?,?,?,?)",
        (body["full_name"].strip(), (body.get("phone") or "").strip(),
         body.get("position") or {"superadmin": "Super administrateur",
                                  "admin": "Gérant"}.get(body["role"], "Agent accueil"),
         today()))
    conn.execute(
        "INSERT INTO users (username, password_hash, role, employee_id, created_at) VALUES (?,?,?,?,?)",
        (body["username"].strip(), hash_password(body["password"]), body["role"],
         cur.lastrowid, db.now_iso()))
    return list_users(conn)


def update_user(conn, user_id, body, current_user):
    u = conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
    if not u:
        raise ApiError(404, "Compte introuvable")
    if body.get("full_name") or body.get("phone") or body.get("position"):
        conn.execute("UPDATE employees SET full_name=?, phone=?, position=? WHERE id=?",
                     (body.get("full_name", "").strip(), (body.get("phone") or "").strip(),
                      body.get("position") or "", u["employee_id"]))
    def other_superadmin_exists():
        return conn.execute(
            "SELECT 1 FROM users WHERE role='superadmin' AND active=1 AND id != ?",
            (user_id,)).fetchone() is not None

    if body.get("role") in ("superadmin", "admin", "agent"):
        if (u["role"] == "superadmin" and body["role"] != "superadmin"
                and not other_superadmin_exists()):
            raise ApiError(400, "Impossible : il doit rester au moins un super administrateur")
        conn.execute("UPDATE users SET role=? WHERE id=?", (body["role"], user_id))
    if "active" in body:
        if user_id == current_user["id"] and not body["active"]:
            raise ApiError(400, "Impossible de désactiver votre propre compte")
        if u["role"] == "superadmin" and not body["active"] and not other_superadmin_exists():
            raise ApiError(400, "Impossible : il doit rester au moins un super administrateur")
        conn.execute("UPDATE users SET active=? WHERE id=?",
                     (1 if body["active"] else 0, user_id))
        if not body["active"]:
            conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
    if body.get("password"):
        conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                     (hash_password(body["password"]), user_id))
    return list_users(conn)


def uses_default_password(conn, user_id):
    """Alerte de sécurité : le compte utilise-t-il encore le mot de passe d'usine ?"""
    row = conn.execute("SELECT password_hash FROM users WHERE id=?", (user_id,)).fetchone()
    return bool(row) and verify_password(db.DEFAULT_PASSWORD, row["password_hash"])


def change_own_password(conn, body, user):
    require(body, "current_password", "new_password")
    if len(body["new_password"]) < 6:
        raise ApiError(400, "Le nouveau mot de passe doit faire au moins 6 caractères")
    row = conn.execute("SELECT password_hash FROM users WHERE id=?", (user["id"],)).fetchone()
    if not verify_password(body["current_password"], row["password_hash"]):
        raise ApiError(403, "Mot de passe actuel incorrect")
    conn.execute("UPDATE users SET password_hash=? WHERE id=?",
                 (hash_password(body["new_password"]), user["id"]))
    return {"ok": True}


# ---------------------------------------------------------------- paramètres

def get_settings(conn, user=None):
    settings = {r["key"]: r["value"] for r in conn.execute(
        "SELECT key, value FROM settings WHERE key != 'scan_token'")}
    # Le jeton du lecteur RFID n'est visible que par le super administrateur
    if user and user["role"] == "superadmin":
        settings["scan_token"] = db.get_setting(conn, "scan_token", "")
    return settings


def reset_scan_token(conn):
    """Renouvelle le jeton du lecteur (si un ancien poste ne doit plus l'utiliser)."""
    import secrets
    token = secrets.token_hex(16)
    conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES ('scan_token', ?)", (token,))
    return {"scan_token": token}


def save_settings(conn, body):
    for key in ("park_name", "receipt_footer", "park_phone", "park_address",
                "loyalty_enabled", "loyalty_threshold",
                "whatsapp_expiry_template", "whatsapp_birthday_template"):
        if key in body:
            value = body[key]
            if key == "loyalty_enabled":
                value = "1" if value in (True, "1", "true", "on") else "0"
            if key == "loyalty_threshold":
                try:
                    value = str(max(2, int(value)))
                except (TypeError, ValueError):
                    continue
            conn.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?,?)",
                         (key, str(value)))
    return get_settings(conn)


# ---------------------------------------------------------------- routeur

def handle(method, path, query, body, user, conn):
    """Routeur principal. `user` est déjà authentifié (sauf /login)."""
    parts = [p for p in path.split("/") if p]  # ex: ['api','members','3']
    route = parts[1] if len(parts) > 1 else ""
    arg = parts[2] if len(parts) > 2 else None
    sub = parts[3] if len(parts) > 3 else None

    # --- authentification
    if route == "login" and method == "POST":
        require(body, "username", "password")
        u = conn.execute("SELECT * FROM users WHERE username=? AND active=1",
                         (body["username"].strip(),)).fetchone()
        if not u or not verify_password(body["password"], u["password_hash"]):
            raise ApiError(401, "Identifiants incorrects")
        token = create_session(conn, u["id"])
        emp = conn.execute("SELECT full_name FROM employees WHERE id=?",
                           (u["employee_id"],)).fetchone()
        return {"token": token,
                "user": {"id": u["id"], "username": u["username"], "role": u["role"],
                         "full_name": emp["full_name"] if emp else u["username"]}}

    if user is None:
        raise ApiError(401, "Non connecté")

    if route == "logout" and method == "POST":
        delete_session(conn, body.get("_token", ""))
        return {"ok": True}

    # Tout employé peut changer son propre mot de passe
    if route == "password" and method == "POST":
        return change_own_password(conn, body, user)

    if route == "me":
        return {"id": user["id"], "username": user["username"], "role": user["role"],
                "full_name": user["full_name"] or user["username"],
                "default_password": uses_default_password(conn, user["id"])}

    # --- accueil (accessible aux agents)
    if route == "checkin" and method == "POST":
        return check_in(conn, body, user)
    if route == "lookup":
        return lookup_by_uid(conn, query.get("uid", ""))
    if route == "visits":
        return list_visits(conn, query, user)

    # --- membres : tout le personnel d'accueil peut inscrire et modifier
    if route == "members":
        if method == "GET" and arg:
            return member_summary(conn, int(arg))
        if method == "GET":
            return list_members(conn, query)
        if method == "POST":
            return create_member(conn, body, user)
        if method == "PUT" and arg:
            return update_member(conn, int(arg), body)

    # --- cartes RFID : attribution, remplacement et blocage par tout le personnel
    if route == "cards":
        if method == "POST" and arg and sub == "block":
            return block_card(conn, int(arg), body)
        if method == "POST" and arg == "replace":
            return replace_card(conn, body, user)
        if method == "POST":
            return assign_card(conn, body, user)

    if route == "subscriptions":
        if method == "POST" and arg and sub == "cancel":
            require_super(user)
            return cancel_subscription(conn, int(arg))
        if method == "POST":
            # Tout le personnel peut vendre, mais au prix catalogue imposé
            # (seul le super administrateur peut changer un montant)
            return sell_subscription(conn, body, user)

    if route == "birthdays":
        require_admin(user)
        return birthdays(conn, days=int(query.get("days", 30)))

    if route == "reminders":
        require_admin(user)
        return expiry_reminders(conn, days=int(query.get("days", 7)))

    if route == "export" and arg:
        require_super(user)
        return export_csv(conn, arg, query)

    if route == "types":
        if method == "GET":
            return list_types(conn, include_inactive=is_admin(user))
        require_super(user)
        if method == "POST" and arg:
            return save_type(conn, body, int(arg))
        if method == "POST":
            return save_type(conn, body)

    if route == "payments":
        require_admin(user)
        return list_payments(conn, query)

    if route == "receipts" and arg:
        return get_receipt(conn, arg)

    if route == "dashboard":
        require_admin(user)
        return dashboard(conn)

    if route == "users":
        require_super(user)
        if method == "GET":
            return list_users(conn)
        if method == "POST" and arg:
            return update_user(conn, int(arg), body, user)
        if method == "POST":
            return create_user(conn, body)

    if route == "settings":
        if method == "GET":
            return get_settings(conn, user)
        require_super(user)
        if method == "POST" and arg == "scantoken":
            return reset_scan_token(conn)
        if method == "POST":
            return save_settings(conn, body)

    raise ApiError(404, "Route inconnue : " + path)
