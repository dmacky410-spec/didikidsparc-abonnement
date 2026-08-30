# -*- coding: utf-8 -*-
"""Guide de l'agent d'accueil — PowerPoint avec reproductions des écrans.

    python3 formation/build_guide_agent.py

Destiné aux employés de base uniquement (pas au gérant).
"""
import os

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.dml import MSO_LINE_DASH_STYLE

# ----------------------------------------------------------------- palette
GREEN_DARK = RGBColor(0x2A, 0x7A, 0x3B)
GREEN_MAIN = RGBColor(0x4C, 0xAF, 0x50)
GREEN_PALE = RGBColor(0xE8, 0xF7, 0xEA)
YELLOW = RGBColor(0xF5, 0xC5, 0x18)
YELLOW_PALE = RGBColor(0xFF, 0xF8, 0xE1)
PURPLE = RGBColor(0x7B, 0x2F, 0xBE)
PURPLE_PALE = RGBColor(0xF3, 0xE5, 0xFF)
RED = RGBColor(0xD9, 0x46, 0x3E)
RED_PALE = RGBColor(0xFD, 0xEC, 0xEA)
TEXT = RGBColor(0x2D, 0x3A, 0x2E)
MUTED = RGBColor(0x7C, 0x8F, 0x7E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
BORDER = RGBColor(0xD3, 0xE4, 0xD5)
GREY = RGBColor(0xF4, 0xF7, 0xF4)

FONT = "Calibri"
W, H = 13.333, 7.5


def build():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    blank = prs.slide_layouts[6]

    # ------------------------------------------------------------- socle
    def slide(bg=WHITE):
        s = prs.slides.add_slide(blank)
        r = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0,
                               prs.slide_width, prs.slide_height)
        r.fill.solid()
        r.fill.fore_color.rgb = bg
        r.line.fill.background()
        r.shadow.inherit = False
        return s

    def text(s, x, y, w, h, runs, size=15, color=TEXT, bold=False,
             align=PP_ALIGN.LEFT, space=5, line=None, anchor=MSO_ANCHOR.TOP):
        box = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor
        paras = runs if isinstance(runs, list) else [runs]
        eclates = []
        for p_ in paras:
            eclates.extend(p_.split("\n")) if isinstance(p_, str) and "\n" in p_ \
                else eclates.append(p_)
        for i, para in enumerate(eclates):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            p.space_after = Pt(space)
            if line:
                p.line_spacing = line
            for content, opt in (para if isinstance(para, list) else [(para, {})]):
                if content == "":
                    continue
                r = p.add_run()
                r.text = content
                f = r.font
                f.name = FONT
                f.size = Pt(opt.get("size", size))
                f.bold = opt.get("bold", bold)
                f.color.rgb = opt.get("color", color)
        return box

    def box(s, x, y, w, h, fill=WHITE, outline=None, radius=0.08,
            shape=MSO_SHAPE.ROUNDED_RECTANGLE, dashed=False, lw=1.5):
        sh = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
        sh.fill.solid()
        sh.fill.fore_color.rgb = fill
        if outline:
            sh.line.color.rgb = outline
            sh.line.width = Pt(lw)
            if dashed:
                sh.line.dash_style = MSO_LINE_DASH_STYLE.DASH
        else:
            sh.line.fill.background()
        sh.shadow.inherit = False
        if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
            try:
                sh.adjustments[0] = radius
            except (IndexError, KeyError):
                pass
        return sh

    def pastille(s, x, y, d, fill, label, lc=WHITE, size=17):
        c = box(s, x, y, d, d, fill=fill, shape=MSO_SHAPE.OVAL)
        tf = c.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = label
        r.font.name = FONT
        r.font.size = Pt(size)
        r.font.bold = True
        r.font.color.rgb = lc
        return c

    def bouton(s, x, y, w, h, label, fill=GREEN_DARK, lc=WHITE, size=11):
        b = box(s, x, y, w, h, fill=fill, radius=0.5)
        tf = b.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = label
        r.font.name = FONT
        r.font.size = Pt(size)
        r.font.bold = True
        r.font.color.rgb = lc
        return b

    def champ(s, x, y, w, label, valeur="", h=0.38, dashed=False,
              vc=TEXT, lsize=9.5, vsize=11.5):
        text(s, x, y, w, 0.2, label, size=lsize, bold=True, color=MUTED, space=0)
        f = box(s, x, y + 0.24, w, h, fill=WHITE,
                outline=GREEN_MAIN if dashed else BORDER,
                radius=0.25, dashed=dashed, lw=2 if dashed else 1.25)
        if valeur:
            text(s, x + 0.14, y + 0.24 + (h - 0.2) / 2, w - 0.28, 0.22, valeur,
                 size=vsize, color=vc, space=0)
        return y + 0.24 + h

    def entete(s, titre, sous=None):
        text(s, 0.75, 0.5, 11.8, 0.8, titre, size=36, bold=True, color=GREEN_DARK)
        if sous:
            text(s, 0.75, 1.35, 11.8, 0.45, sous, size=16, color=MUTED)

    def etape(s, x, y, n, titre, desc=None, couleur=GREEN_DARK, lc=WHITE, wt=4.2):
        pastille(s, x, y, 0.5, couleur, str(n), lc=lc, size=15)
        text(s, x + 0.72, y + 0.02, wt, 0.35, titre, size=15.5, bold=True, color=TEXT)
        if desc:
            text(s, x + 0.72, y + 0.42, wt, 0.55, desc, size=12.5, color=MUTED, line=1.15)

    def notes(s, t):
        s.notes_slide.notes_text_frame.text = t

    # ---------------------------------------- images : captures réelles du logiciel
    from PIL import Image as _PILImage
    CAPT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "captures")

    def capture(s, fichier, x, y, max_w, max_h, ombre=True):
        """Place une capture en respectant ses proportions. Retourne (x, y, w, h)."""
        chemin = os.path.join(CAPT, fichier)
        with _PILImage.open(chemin) as im:
            iw, ih = im.size
        ratio = iw / ih
        w, h = max_w, max_w / ratio
        if h > max_h:
            h, w = max_h, max_h * ratio
        px = x + (max_w - w) / 2
        py = y + (max_h - h) / 2
        if ombre:
            box(s, px + 0.04, py + 0.05, w, h, fill=RGBColor(0xE6, 0xEE, 0xE7), radius=0.02)
        pic = s.shapes.add_picture(chemin, Inches(px), Inches(py), Inches(w), Inches(h))
        return px, py, w, h

    def repere(s, rect, fx, fy, n, d=0.42):
        """Pastille numérotée posée sur la capture (position en fraction de l'image)."""
        px, py, w, h = rect
        pastille(s, px + fx * w - d / 2, py + fy * h - d / 2, d, YELLOW, str(n),
                 lc=TEXT, size=14)

    def liste_reperes(s, x, y, items, gap=0.92, wt=4.0):
        for i, (titre, desc) in enumerate(items, 1):
            pastille(s, x, y, 0.42, YELLOW, str(i), lc=TEXT, size=14)
            text(s, x + 0.6, y - 0.02, wt, 0.3, titre, size=14.5, bold=True)
            if desc:
                text(s, x + 0.6, y + 0.32, wt, 0.5, desc, size=12, color=MUTED, line=1.15)
            y += gap
        return y

    # --------------------------------------------- maquette : fenêtre du logiciel
    def fenetre(s, x, y, w, h, page_active="Accueil / Entrées"):
        box(s, x, y, w, h, fill=WHITE, outline=BORDER, radius=0.04, lw=1.25)
        sw = 1.75
        box(s, x, y, sw, h, fill=GREEN_DARK, radius=0.05)
        text(s, x + 0.16, y + 0.18, sw - 0.3, 0.25, "Didikids Parc",
             size=11.5, bold=True, color=WHITE, space=0)
        menus = ["Accueil / Entrées", "Membres", "Relances WhatsApp",
                 "Historique visites"]
        my = y + 0.62
        for m in menus:
            if m == page_active:
                box(s, x + 0.1, my - 0.06, sw - 0.2, 0.34, fill=YELLOW, radius=0.3)
                text(s, x + 0.2, my + 0.02, sw - 0.4, 0.22, m, size=9.5,
                     bold=True, color=TEXT, space=0)
            else:
                text(s, x + 0.2, my + 0.02, sw - 0.4, 0.22, m, size=9.5,
                     color=GREEN_PALE, space=0)
            my += 0.44
        return x + sw

    # ============================================================== 1. titre
    s = slide(GREEN_DARK)
    text(s, 1.0, 2.15, 11.3, 1.1,
         [[("Didikids ", {"color": WHITE}), ("Parc", {"color": YELLOW})]],
         size=54, bold=True)
    text(s, 1.0, 3.45, 11.3, 0.7, "GUIDE DE L'AGENT D'ACCUEIL",
         size=26, bold=True, color=GREEN_PALE)
    text(s, 1.0, 4.4, 11.3, 0.5,
         "Tout ce que vous ferez au comptoir, écran par écran",
         size=18, color=WHITE)
    box(s, 1.0, 5.5, 5.6, 0.72, fill=YELLOW)
    text(s, 1.3, 5.72, 5.1, 0.35, "Formation interne · Équipe d'accueil",
         size=14, bold=True, color=TEXT)
    notes(s, "Guide destine aux agents d'accueil. Le gerant a sa propre formation.")

    # ============================================================== 2. journée
    s = slide()
    entete(s, "Votre journée en trois gestes",
           "Ce guide couvre exactement ces trois situations")
    items = [
        ("1", "Un enfant arrive", GREEN_DARK, GREEN_PALE,
         "Il pose sa carte, vous lisez la couleur de l'écran. C'est tout."),
        ("2", "Un nouveau client s'inscrit", YELLOW, YELLOW_PALE,
         "Vous créez sa fiche, vous lui donnez une carte, vous encaissez. "
         "Vous faites tout, seul."),
        ("3", "Vous appelez les parents", PURPLE, PURPLE_PALE,
         "Abonnements qui se terminent et anniversaires à venir, "
         "avec le message déjà écrit."),
    ]
    x = 0.75
    for num, titre, coul, fond, desc in items:
        box(s, x, 2.2, 3.75, 4.4, fill=fond)
        pastille(s, x + 0.4, 2.7, 0.85, coul, num,
                 lc=TEXT if coul == YELLOW else WHITE, size=22)
        text(s, x + 0.4, 3.9, 3.0, 0.45, titre, size=20, bold=True, color=GREEN_DARK)
        text(s, x + 0.4, 4.55, 2.95, 1.9, desc, size=14.5, line=1.25)
        x += 4.0
    notes(s, "Annoncer le plan : les entrees, l'inscription, les relances.")

    # ============================================================== 3. connexion
    s = slide()
    entete(s, "Se connecter", "Votre compte est personnel")
    y = 2.3
    for n, t, d in [
        ("1", "Ouvrez le logiciel",
         "Double-cliquez sur l'icône « Didikids Parc » du Bureau. "
         "Une fenêtre noire s'ouvre : ne la fermez jamais."),
        ("2", "Saisissez vos identifiants",
         "Votre nom d'utilisateur et votre mot de passe, remis par le responsable."),
        ("3", "L'écran d'accueil s'ouvre",
         "Vous êtes prêt à recevoir les enfants."),
    ]:
        etape(s, 0.85, y, n, t, d, wt=5.3)
        y += 1.4
    capture(s, "10_connexion.png", 6.55, 2.2, 2.7, 4.3)
    box(s, 9.55, 2.3, 3.0, 3.85, fill=YELLOW_PALE, outline=YELLOW, lw=2.25)
    text(s, 9.85, 2.7, 2.4, 0.4, "RÈGLE IMPORTANTE", size=14, bold=True)
    text(s, 9.85, 3.3, 2.4, 2.5,
         "Ne prêtez votre compte à personne, même à un collègue, même cinq minutes.\n\n"
         "Chaque entrée validée et chaque encaissement portent votre nom.\n\n"
         "C'est votre protection : personne ne pourra vous reprocher "
         "l'erreur d'un autre.",
         size=12.5, line=1.3)
    notes(s, "Insister sur le compte personnel des le debut.")

    # ============================================================== 4. écran d'accueil
    s = slide()
    entete(s, "L'écran d'accueil", "Voici l'écran devant lequel vous passerez la journée")
    r = capture(s, "01_accueil.png", 0.75, 2.05, 8.0, 4.6)
    repere(s, r, 0.09, 0.125, 1)
    repere(s, r, 0.44, 0.38, 2)
    repere(s, r, 0.80, 0.155, 3)

    y = 2.3
    for n, t, d in [
        ("1", "Le menu à gauche", "Vos quatre pages. Si un menu manque, c'est normal : "
         "chacun voit ce qui le concerne."),
        ("2", "La zone de lecture", "Le curseur y reste tout seul. Ne cliquez nulle part, "
         "posez la carte."),
        ("3", "Les passages du jour", "Qui est entré, à quelle heure."),
    ]:
        etape(s, 9.05, y, n, t, d, wt=3.5)
        y += 1.4
    notes(s, "Montrer le vrai ecran en parallele si possible.")

    # ============================================================== 5. valider
    s = slide()
    entete(s, "Valider une entrée", "Le geste que vous répéterez cent fois par jour")
    x = 0.75
    for n, t, d in [("1", "L'enfant pose sa carte", "sur le lecteur du comptoir"),
                    ("2", "Le logiciel répond", "en moins d'une seconde, avec un son"),
                    ("3", "Vous lisez la couleur", "vert = il entre · rouge = il n'entre pas")]:
        box(s, x, 2.3, 3.75, 2.5, fill=WHITE, outline=BORDER)
        pastille(s, x + 0.35, 2.65, 0.7, GREEN_MAIN, n, size=19)
        text(s, x + 1.25, 2.8, 2.25, 0.45, t, size=17, bold=True)
        text(s, x + 0.35, 3.65, 3.05, 0.8, d, size=14.5, color=MUTED, line=1.2)
        x += 4.0
    box(s, 0.75, 5.2, 11.8, 1.65, fill=GREEN_DARK)
    text(s, 1.2, 5.5, 10.9, 0.5, "Vous n'avez rien à taper. Rien à cliquer.",
         size=25, bold=True, color=YELLOW)
    text(s, 1.2, 6.12, 10.9, 0.45,
         "Si le lecteur ne répond pas, tapez le numéro de la carte à la main "
         "dans le champ, puis appuyez sur Entrée.", size=14, color=WHITE)
    notes(s, "Faire pratiquer le geste a chacun.")

    # ============================================================== 6. écran vert
    s = slide()
    entete(s, "L'écran vert : l'enfant peut entrer",
           "Quatre informations à lire avant de le laisser passer")
    r = capture(s, "02_entree_autorisee.png", 0.75, 2.1, 6.0, 4.3)
    repere(s, r, 0.50, 0.262, 1)
    repere(s, r, 0.80, 0.335, 2)
    repere(s, r, 0.372, 0.457, 3)
    repere(s, r, 0.683, 0.457, 4)

    y = 2.3
    for num, (t, d) in enumerate([
            ("Le nom", "Vérifiez que c'est bien l'enfant devant vous."),
            ("L'abonnement", "Le forfait dont il dispose."),
            ("Les entrées restantes", "S'il n'en reste qu'une, prévenez le parent."),
            ("La date d'expiration", "Si la date approche, proposez le renouvellement.")], 1):
        pastille(s, 7.05, y, 0.42, YELLOW, str(num), lc=TEXT, size=14)
        text(s, 7.65, y - 0.02, 4.9, 0.36, t, size=16, bold=True)
        text(s, 7.65, y + 0.4, 4.9, 0.5, d, size=13, color=MUTED, line=1.2)
        y += 1.05
    box(s, 7.05, 6.0, 5.5, 0.72, fill=YELLOW_PALE)
    text(s, 7.3, 6.22, 5.0, 0.4,
         "« Déjà passé 2 fois » : vérifiez que ce n'est pas une erreur",
         size=12.5, bold=True)
    notes(s, "Le compteur 'avant visite offerte' n'apparait que si la fidelite est activee.")

    # ============================================================== 7. écran rouge
    s = slide()
    entete(s, "L'écran rouge : l'enfant ne peut pas entrer",
           "Le motif est toujours écrit — lisez-le au parent, il comprendra")
    capture(s, "03_entree_refusee.png", 8.6, 1.95, 4.0, 1.5)
    text(s, 0.9, 2.2, 3.9, 0.3, "CE QUI S'AFFICHE", size=12, bold=True, color=MUTED)
    text(s, 4.6, 2.2, 3.3, 0.3, "CE QUE ÇA VEUT DIRE", size=12, bold=True, color=MUTED)
    text(s, 8.6, 3.62, 3.9, 0.3, "CE QUE VOUS FAITES", size=12, bold=True, color=MUTED)
    y = 2.68
    lignes = [
        ("Carte inconnue", "Elle n'est enregistrée sur aucun enfant",
         "Créez la fiche et donnez-lui la carte"),
        ("Carte bloquée", "La carte a été déclarée perdue",
         "Le parent doit utiliser la nouvelle"),
        ("Abonnement expiré le ...", "La date de fin est dépassée",
         "Vendez un nouvel abonnement"),
        ("Plus d'entrées disponibles", "Le forfait est terminé",
         "Vendez un nouvel abonnement"),
        ("Aucun abonnement actif", "L'enfant n'a rien en cours",
         "Vendez un abonnement depuis sa fiche"),
    ]
    reste = []
    for i, (msg, sens, act) in enumerate(lignes):
        large = 11.8 if y > 3.55 else 7.6
        box(s, 0.75, y, large, 0.74, fill=RED_PALE if i % 2 == 0 else WHITE)
        text(s, 0.9, y + 0.22, 3.55, 0.4, msg, size=13, bold=True, color=RED)
        text(s, 4.6, y + 0.22, 3.0, 0.4, sens, size=12.5)
        if y > 3.55:
            text(s, 8.6, y + 0.22, 3.85, 0.4, act, size=12.5, bold=True, color=GREEN_DARK)
        else:
            reste.append((msg, act))
        y += 0.82
    for j, (msg, act) in enumerate(reste):
        text(s, 8.6, 3.98 + j * 0.55, 3.9, 0.45,
             [[(msg + " : ", {"size": 11.5, "color": RED, "bold": True}),
               (act, {"size": 11.5, "color": GREEN_DARK, "bold": True})]], line=1.15)
    text(s, 0.75, y + 0.28, 11.8, 0.45,
         "Ne laissez jamais entrer un enfant refusé sans prévenir le responsable.",
         size=15.5, bold=True)
    notes(s, "Les trois derniers cas se resolvent par une vente : voir les slides suivantes.")

    # ============================================================== 8. fidélité
    s = slide(PURPLE_PALE)
    text(s, 0.75, 0.8, 11.8, 0.85, "La visite offerte", size=40, bold=True, color=PURPLE)
    text(s, 0.75, 1.75, 11.8, 0.5,
         "Le logiciel récompense les enfants fidèles tout seul", size=16)
    box(s, 0.75, 2.75, 5.9, 3.9, fill=WHITE)
    text(s, 1.15, 3.25, 5.1, 0.6, "VISITE OFFERTE !", size=30, bold=True,
         color=PURPLE, align=PP_ALIGN.CENTER)
    text(s, 1.15, 4.15, 5.1, 2.2,
         "Toutes les 10 visites payantes, la 11e visite est gratuite.\n\n"
         "Le logiciel compte tout seul et n'entame pas le forfait de l'enfant.",
         size=16, align=PP_ALIGN.CENTER, line=1.3)
    box(s, 7.05, 2.75, 5.5, 3.9, fill=PURPLE)
    text(s, 7.45, 3.2, 4.7, 0.45, "VOTRE RÔLE", size=16, bold=True, color=YELLOW)
    text(s, 7.45, 3.9, 4.7, 2.4,
         "Annoncez-le au parent avec le sourire :\n\n"
         "« Aujourd'hui c'est offert, c'est la 11e visite d'Aminata ! »\n\n"
         "C'est un moment qui fidélise le client.",
         size=15, color=WHITE, line=1.3)
    notes(s, "Le seuil est reglable par le responsable.")

    # ============================================================== 9. parcours
    s = slide(GREEN_DARK)
    text(s, 0.75, 0.7, 11.8, 0.9, "Inscrire un nouvel abonné", size=40,
         bold=True, color=YELLOW)
    text(s, 0.75, 1.7, 11.8, 0.5,
         "Quatre étapes, deux minutes, sans avoir besoin du gérant",
         size=17, color=GREEN_PALE)
    etapes = [("1", "Créer sa fiche"), ("2", "Lui donner une carte"),
              ("3", "Encaisser"), ("4", "Il entre")]
    x = 0.75
    for n, t in etapes:
        box(s, x, 2.7, 2.75, 2.4, fill=WHITE)
        pastille(s, x + 1.02, 3.0, 0.72, YELLOW, n, lc=TEXT, size=20)
        text(s, x + 0.2, 4.0, 2.35, 0.6, t, size=17, bold=True,
             color=GREEN_DARK, align=PP_ALIGN.CENTER, line=1.15)
        if n != "4":
            fleche = box(s, x + 2.83, 3.72, 0.34, 0.3, fill=YELLOW,
                         shape=MSO_SHAPE.RIGHT_ARROW)
        x += 3.1
    box(s, 0.75, 5.5, 11.8, 1.15, fill=YELLOW)
    text(s, 1.15, 5.78, 11.0, 0.6,
         "Les quatre écrans suivants montrent exactement ce que vous verrez.",
         size=19, bold=True, align=PP_ALIGN.CENTER)
    notes(s, "C'est le coeur du guide : l'agent doit pouvoir le faire seul.")

    # ============================================================== 10. étape 1
    s = slide()
    entete(s, "Étape 1 — Créer la fiche",
           "Menu « Membres » puis le bouton jaune « + Nouveau membre »")
    r = capture(s, "05_nouveau_membre.png", 0.75, 2.05, 6.6, 4.6)
    repere(s, r, 0.28, 0.243, 1)
    repere(s, r, 0.72, 0.244, 2)
    repere(s, r, 0.72, 0.404, 3)
    repere(s, r, 0.82, 0.879, 4)

    y = 2.25
    for n, t, d in [
        ("1", "Le nom de l'enfant suffit", "C'est le seul champ obligatoire."),
        ("2", "La date de naissance", "C'est elle qui fera apparaître l'enfant dans "
         "les anniversaires à proposer."),
        ("3", "Le téléphone du parent", "Sans lui, impossible d'envoyer les relances. "
         "Ne le sautez jamais."),
        ("4", "Enregistrer", "La fiche s'ouvre aussitôt : vous enchaînez sur la carte."),
    ]:
        etape(s, 7.8, y, n, t, d, couleur=YELLOW, lc=TEXT, wt=4.6)
        y += 1.12
    notes(s, "Le code membre (M-0005) est attribue automatiquement.")

    # ============================================================== 11. étape 2
    s = slide()
    entete(s, "Étape 2 — Lui donner une carte",
           "Sur la fiche qui vient de s'ouvrir : « + Attribuer une carte »")
    r = capture(s, "11_attribuer_carte.png", 0.75, 2.15, 6.6, 4.0)
    repere(s, r, 0.5, 0.455, 1)
    repere(s, r, 0.5, 0.685, 2)
    repere(s, r, 0.835, 0.845, 3)

    y = 2.25
    for n, t, d in [
        ("1", "Posez la carte neuve sur le lecteur",
         "Le champ vert se remplit tout seul. Ne tapez rien au clavier."),
        ("2", "Le numéro imprimé est facultatif",
         "Utile si vos cartes portent un numéro visible."),
        ("3", "Cliquez sur « Attribuer »",
         "La carte est active immédiatement."),
    ]:
        etape(s, 7.8, y, n, t, d, wt=4.6)
        y += 1.35
    box(s, 7.8, 6.05, 4.75, 0.75, fill=GREEN_PALE)
    text(s, 8.05, 6.25, 4.25, 0.4, "Un enfant = une seule carte active",
         size=13, bold=True, color=GREEN_DARK)
    notes(s, "Si le logiciel refuse : l'enfant a deja une carte, utiliser 'Carte perdue'.")

    # ============================================================== 12. étape 3
    s = slide()
    entete(s, "Étape 3 — Encaisser",
           "Sur la fiche : bouton jaune « Vendre un abonnement »")
    r = capture(s, "07_vendre_abonnement.png", 0.75, 2.05, 6.6, 4.6)
    repere(s, r, 0.80, 0.232, 1)
    repere(s, r, 0.73, 0.652, 2)
    repere(s, r, 0.32, 0.841, 3)
    repere(s, r, 0.79, 0.916, 4)

    y = 2.25
    for n, t, d in [
        ("1", "Choisissez la formule", "Elle se met en vert quand elle est sélectionnée."),
        ("2", "Choisissez le paiement", "Espèces, Orange Money, MTN MoMo ou carte."),
        ("3", "Le montant est bloqué", "Vous ne pouvez pas le changer : c'est le prix "
         "du parc. Cela vous protège."),
        ("4", "Encaissez", "Le reçu s'imprime tout seul, avec votre nom dessus."),
    ]:
        etape(s, 7.8, y, n, t, d, couleur=YELLOW, lc=TEXT, wt=4.6)
        y += 1.12
    notes(s, "Rappeler : le montant bloque protege l'employe autant que le parc.")

    # ============================================================== 13. étape 4
    s = slide()
    entete(s, "Étape 4 — L'enfant entre",
           "Il pose sa carte tout de suite : c'est déjà actif")
    capture(s, "02_entree_autorisee.png", 0.75, 2.2, 6.2, 4.3)
    text(s, 7.35, 2.4, 5.2, 0.55, "C'est terminé.", size=32, bold=True, color=GREEN_DARK)
    text(s, 7.35, 3.35, 5.2, 3.2,
         "Le parent est inscrit, il a payé, son enfant joue.\n\n"
         "Vous avez fait les quatre étapes seul, en deux minutes, "
         "sans appeler personne.\n\n"
         "L'abonnement est décompté automatiquement à chaque passage : "
         "il vous reste juste à poser la carte, les prochaines fois.",
         size=16.5, line=1.4)
    notes(s, "Fin du parcours d'inscription. Enchainer sur la carte perdue.")

    # ============================================================== 14. carte perdue
    s = slide()
    entete(s, "Une carte perdue ? On la remplace",
           "Ouvrez la fiche de l'enfant : bouton rouge « Carte perdue — la remplacer »")
    box(s, 0.75, 2.05, 11.8, 1.0, fill=RED_PALE, outline=RED, lw=2.25)
    text(s, 1.15, 2.28, 11.0, 0.5,
         "Ne créez JAMAIS une deuxième fiche pour le même enfant.",
         size=20, bold=True, color=RED)
    text(s, 1.15, 2.7, 11.0, 0.3,
         "Vous perdriez son abonnement, ses entrées restantes et son historique.",
         size=13.5)
    r1 = capture(s, "06_fiche_membre.png", 0.75, 3.3, 4.5, 3.2)
    repere(s, r1, 0.80, 0.51, 1)
    r2 = capture(s, "08_carte_perdue.png", 5.5, 3.3, 3.0, 3.2)
    repere(s, r2, 0.5, 0.52, 2)

    y = 3.5
    for n, t, d in [
        ("1", "Ouvrez la fiche de l'enfant", "Menu Membres, puis « Ouvrir »."),
        ("2", "Posez la nouvelle carte", "Le champ vert se remplit tout seul."),
        ("3", "Validez", "L'ancienne carte est refusée dès cet instant. "
         "L'abonnement et les entrées restantes sont conservés."),
    ]:
        etape(s, 8.8, y, n, t, d, couleur=RED, wt=3.7)
        y += 1.05
    notes(s, "Si le parent retrouve l'ancienne carte : la reposer sur la fiche, "
             "elle se reactive.")

    # ============================================================== 15. relances
    s = slide()
    entete(s, "Appeler les parents",
           "Menu « Relances WhatsApp » — le chiffre indique combien de parents appeler")
    r = capture(s, "09_relances.png", 0.75, 2.05, 8.3, 4.7)
    repere(s, r, 0.075, 0.235, 1)
    repere(s, r, 0.545, 0.30, 2)
    repere(s, r, 0.545, 0.545, 3)
    liste_reperes(s, 9.35, 2.35, [
        ("Le compteur du menu", "Le nombre de parents à contacter aujourd'hui."),
        ("Abonnements à renouveler",
         "Un clic sur le bouton vert ouvre WhatsApp, message déjà écrit."),
        ("Anniversaires à venir",
         "Proposez une fête au parc : c'est une vente facile."),
    ], gap=1.35, wt=3.3)

    box(s, 0.75, 6.05, 11.8, 0.8, fill=YELLOW)
    text(s, 1.15, 6.3, 11.0, 0.4,
         "Relisez toujours le message avant d'envoyer et ajoutez un mot personnel.",
         size=15, bold=True, align=PP_ALIGN.CENTER)
    notes(s, "Faire cette tache a un moment calme de la journee.")

    # ============================================================== 16. règles
    s = slide(GREEN_DARK)
    text(s, 0.75, 0.65, 11.8, 0.85, "Les 5 règles d'or", size=40, bold=True, color=YELLOW)
    y = 1.95
    for i, (t, d) in enumerate([
        ("Chaque action porte votre nom", "entrées, encaissements : tout est enregistré"),
        ("Ne prêtez jamais votre compte", "même à un collègue, même cinq minutes"),
        ("Les prix ne se négocient pas", "le montant vient du catalogue, il est bloqué"),
        ("Une carte = un enfant", "carte perdue : on remplace, on ne recrée pas la fiche"),
        ("Ne fermez pas la fenêtre noire", "c'est le moteur du logiciel"),
    ], 1):
        pastille(s, 0.85, y, 0.7, YELLOW, str(i), lc=TEXT, size=19)
        text(s, 1.85, y + 0.03, 10.4, 0.4, t, size=20, bold=True, color=WHITE)
        text(s, 1.85, y + 0.5, 10.4, 0.35, d, size=14.5, color=GREEN_PALE)
        y += 1.08
    notes(s, "A afficher au comptoir.")

    # ============================================================== 17. problèmes
    s = slide()
    entete(s, "En cas de problème", "Trois pannes courantes, trois solutions")
    y = 2.25
    for t, d in [
        ("L'écran ne s'ouvre pas",
         "Vérifiez que la fenêtre « Didikids Parc - Serveur » est ouverte dans la "
         "barre des tâches. Sinon, double-cliquez sur l'icône du Bureau."),
        ("Le lecteur ne réagit pas",
         "Débranchez puis rebranchez le lecteur USB et relancez « Lecteur RFID ». "
         "En attendant, tapez le numéro de la carte à la main."),
        ("Un menu a disparu",
         "Ce n'est pas une panne : chacun voit uniquement les pages qui le "
         "concernent. Le reste est réservé au responsable."),
    ]:
        box(s, 0.75, y, 11.8, 1.25, fill=GREEN_PALE)
        text(s, 1.1, y + 0.24, 3.6, 0.45, t, size=17, bold=True, color=GREEN_DARK)
        text(s, 4.9, y + 0.22, 7.4, 0.9, d, size=14, line=1.2)
        y += 1.45
    box(s, 0.75, 6.35, 11.8, 0.85, fill=YELLOW)
    text(s, 1.1, 6.63, 11.1, 0.45,
         "En cas de doute, appelez le responsable. Aucune question n'est bête.",
         size=17, bold=True, align=PP_ALIGN.CENTER)
    notes(s, "Laisser le numero du responsable affiche au comptoir.")

    # ============================================================== 18. fin
    s = slide(GREEN_DARK)
    text(s, 0.75, 2.4, 11.8, 0.95, "Des questions ?", size=46, bold=True,
         color=WHITE, align=PP_ALIGN.CENTER)
    box(s, 3.4, 3.95, 6.5, 1.55, fill=YELLOW)
    text(s, 3.7, 4.3, 5.9, 0.85, "Posez la carte.\nLisez la couleur.",
         size=24, bold=True, align=PP_ALIGN.CENTER, line=1.2)
    text(s, 0.75, 5.95, 11.8, 0.5,
         "Didikids Parc — parce que chaque enfant mérite de s'épanouir",
         size=16, color=GREEN_PALE, align=PP_ALIGN.CENTER)
    notes(s, "Terminer par une mise en pratique sur le vrai lecteur.")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "Didikids_Parc_Guide_Agent.pptx")
    prs.save(out)
    return out


if __name__ == "__main__":
    print("OK :", build())
