# -*- coding: utf-8 -*-
"""Génère la présentation de formation des employés (PowerPoint).

    python3 formation/build_formation.py

Couleurs et vocabulaire repris du logiciel Didikids Parc.
"""
import os

from pptx import Presentation
from pptx.util import Inches, Pt, Emu
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

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
BORDER = RGBColor(0xD9, 0xEC, 0xDB)

TITLE_FONT = "Calibri"
BODY_FONT = "Calibri"

W, H = 13.333, 7.5


def build():
    prs = Presentation()
    prs.slide_width = Inches(W)
    prs.slide_height = Inches(H)
    blank = prs.slide_layouts[6]

    # ------------------------------------------------------------- outils
    def slide(bg=WHITE):
        s = prs.slides.add_slide(blank)
        rect = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0,
                                  prs.slide_width, prs.slide_height)
        rect.fill.solid()
        rect.fill.fore_color.rgb = bg
        rect.line.fill.background()
        rect.shadow.inherit = False
        return s

    def text(s, x, y, w, h, runs, size=16, color=TEXT, bold=False,
             align=PP_ALIGN.LEFT, font=BODY_FONT, space=6, anchor=MSO_ANCHOR.TOP,
             line=None):
        """runs : chaîne, ou liste de (texte, {options}) pour une même ligne,
        ou liste de listes pour plusieurs paragraphes."""
        box = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
        tf = box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_right = 0
        tf.margin_top = tf.margin_bottom = 0
        tf.vertical_anchor = anchor

        paragraphs = runs if isinstance(runs, list) else [runs]
        # PowerPoint ne rend pas les « \n » à l'intérieur d'un paragraphe :
        # on les transforme en paragraphes distincts.
        eclates = []
        for para in paragraphs:
            if isinstance(para, str) and "\n" in para:
                eclates.extend(para.split("\n"))
            else:
                eclates.append(para)
        paragraphs = eclates

        for i, para in enumerate(paragraphs):
            p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
            p.alignment = align
            p.space_after = Pt(space)
            if line:
                p.line_spacing = line
            pieces = para if isinstance(para, list) else [(para, {})]
            for content, opt in pieces:
                if content == "":
                    continue
                r = p.add_run()
                r.text = content
                f = r.font
                f.name = opt.get("font", font)
                f.size = Pt(opt.get("size", size))
                f.bold = opt.get("bold", bold)
                f.color.rgb = opt.get("color", color)
        return box

    def card(s, x, y, w, h, fill=WHITE, outline=None, radius=0.06):
        shape = s.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(x), Inches(y),
                                   Inches(w), Inches(h))
        shape.fill.solid()
        shape.fill.fore_color.rgb = fill
        if outline:
            shape.line.color.rgb = outline
            shape.line.width = Pt(2.25)
        else:
            shape.line.fill.background()
        shape.shadow.inherit = False
        try:
            shape.adjustments[0] = radius
        except (IndexError, KeyError):
            pass
        return shape

    def circle(s, x, y, d, fill, label, label_color=WHITE, size=20):
        c = s.shapes.add_shape(MSO_SHAPE.OVAL, Inches(x), Inches(y), Inches(d), Inches(d))
        c.fill.solid()
        c.fill.fore_color.rgb = fill
        c.line.fill.background()
        c.shadow.inherit = False
        tf = c.text_frame
        tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
        p = tf.paragraphs[0]
        p.alignment = PP_ALIGN.CENTER
        r = p.add_run()
        r.text = label
        r.font.name = TITLE_FONT
        r.font.size = Pt(size)
        r.font.bold = True
        r.font.color.rgb = label_color
        return c

    def header(s, title, subtitle=None):
        text(s, 0.75, 0.55, 11.8, 0.85, title, size=38, bold=True,
             color=GREEN_DARK, font=TITLE_FONT)
        if subtitle:
            text(s, 0.75, 1.42, 11.8, 0.45, subtitle, size=16, color=MUTED)

    def notes(s, txt):
        s.notes_slide.notes_text_frame.text = txt

    # =========================================================== 1. titre
    s = slide(GREEN_DARK)
    text(s, 1.0, 2.45, 11.3, 1.3,
         [[("Didikids ", {"color": WHITE}), ("Parc", {"color": YELLOW})]],
         size=60, bold=True, font=TITLE_FONT)
    text(s, 1.0, 3.75, 11.3, 0.6, "LOGICIEL DE GESTION DES ABONNEMENTS",
         size=22, bold=True, color=GREEN_PALE)
    text(s, 1.0, 4.65, 11.3, 0.5, "Guide d'utilisation — équipe d'accueil",
         size=19, color=WHITE)
    card(s, 1.0, 5.75, 4.8, 0.7, fill=YELLOW)
    text(s, 1.3, 5.96, 4.3, 0.35, "Formation interne · Version 1",
         size=14, bold=True, color=TEXT)
    notes(s, "Accueillir l'equipe. Rappeler que le logiciel remplace le cahier "
             "papier et qu'il protege tout le monde : chaque action est tracee.")

    # =========================================================== 2. à quoi ça sert
    s = slide()
    header(s, "À quoi sert ce logiciel ?",
           "Trois choses simples, que vous ferez tous les jours")
    items = [
        ("1", "Les cartes", GREEN_DARK,
         "Chaque enfant a sa carte. Vous la posez sur le lecteur : le logiciel "
         "reconnaît l'enfant en moins d'une seconde."),
        ("2", "Les abonnements", YELLOW,
         "4 entrées, 8 entrées, VIP illimité. Le logiciel décompte les entrées "
         "tout seul et refuse quand le forfait est fini."),
        ("3", "L'historique", PURPLE,
         "Chaque passage est enregistré : l'enfant, la date, l'heure et le nom "
         "de l'employé qui a validé."),
    ]
    x = 0.75
    for num, titre, couleur, desc in items:
        card(s, x, 2.25, 3.75, 4.4, fill=GREEN_PALE if couleur == GREEN_DARK else
             (YELLOW_PALE if couleur == YELLOW else PURPLE_PALE))
        circle(s, x + 0.4, 2.75, 0.85, couleur, num,
               label_color=TEXT if couleur == YELLOW else WHITE)
        text(s, x + 0.4, 3.95, 3.05, 0.45, titre, size=22, bold=True,
             color=GREEN_DARK, font=TITLE_FONT)
        text(s, x + 0.4, 4.6, 2.95, 1.9, desc, size=14.5, color=TEXT, line=1.25)
        x += 4.0
    notes(s, "Insister : le logiciel ne remplace pas l'accueil humain, il enleve "
             "le calcul mental et les erreurs.")

    # =========================================================== 3. se connecter
    s = slide()
    header(s, "Se connecter", "Chaque employé a son propre compte")
    steps = [
        ("1", "Ouvrez le logiciel", "Double-cliquez sur l'icône « Didikids Parc » "
         "du Bureau. Une fenêtre noire s'ouvre : ne la fermez jamais."),
        ("2", "Saisissez vos identifiants", "Votre nom d'utilisateur et votre mot "
         "de passe, remis par le responsable."),
        ("3", "L'écran d'accueil s'ouvre", "Vous êtes prêt à recevoir les enfants."),
    ]
    y = 2.3
    for num, titre, desc in steps:
        circle(s, 0.85, y, 0.68, GREEN_DARK, num)
        text(s, 1.85, y + 0.05, 5.5, 0.4, titre, size=19, bold=True, color=TEXT)
        text(s, 1.85, y + 0.58, 5.5, 0.8, desc, size=14.5, color=MUTED, line=1.2)
        y += 1.5
    card(s, 8.05, 2.3, 4.5, 3.9, fill=YELLOW_PALE, outline=YELLOW)
    text(s, 8.45, 2.7, 3.7, 0.4, "RÈGLE IMPORTANTE", size=15, bold=True, color=TEXT)
    text(s, 8.45, 3.3, 3.7, 2.6,
         "Votre compte est personnel.\n\nNe le prêtez à personne, même à un collègue.\n\n"
         "Chaque entrée validée et chaque encaissement portent votre nom dans "
         "l'historique. C'est votre protection.",
         size=14.5, color=TEXT, line=1.3)
    notes(s, "Point de discipline : un compte prete, et c'est votre nom qui apparait "
             "sur une erreur ou une caisse qui ne tombe pas juste.")

    # =========================================================== 4. écran accueil
    s = slide()
    header(s, "L'écran d'accueil", "C'est l'écran sur lequel vous passerez la journée")
    card(s, 0.75, 2.25, 7.0, 4.4, fill=GREEN_PALE)
    text(s, 1.15, 2.65, 6.2, 0.4, "À GAUCHE — Zone de lecture", size=15, bold=True,
         color=GREEN_DARK)
    text(s, 1.15, 3.2, 6.2, 3.2,
         [[("« Présentez la carte »", {"bold": True, "size": 15})],
          [("Le curseur reste automatiquement dans le champ de saisie. "
            "Vous n'avez rien à cliquer : posez simplement la carte sur le lecteur.",
            {"size": 13.5})],
          [("Sous cette zone s'affiche le résultat, en vert ou en rouge.",
            {"size": 13.5, "color": MUTED})]],
         color=TEXT, space=9, line=1.2)
    card(s, 8.15, 2.25, 4.4, 4.4, fill=WHITE, outline=BORDER)
    text(s, 8.55, 2.65, 3.6, 0.4, "À DROITE — Passages du jour", size=15, bold=True,
         color=GREEN_DARK)
    text(s, 8.55, 3.2, 3.6, 3.2,
         "La liste de tous les enfants entrés aujourd'hui, avec l'heure.\n\n"
         "Un coup d'œil suffit pour savoir combien d'enfants sont dans le parc.",
         size=14.5, color=TEXT, line=1.3)
    notes(s, "Montrer l'ecran en vrai pendant la formation.")

    # =========================================================== 5. valider entrée
    s = slide()
    header(s, "Valider une entrée", "Le geste que vous répéterez cent fois par jour")
    gestes = [
        ("1", "L'enfant pose sa carte", "sur le lecteur posé au comptoir"),
        ("2", "Le logiciel répond", "en moins d'une seconde, avec un son"),
        ("3", "Vous lisez la couleur", "vert = il entre · rouge = il n'entre pas"),
    ]
    x = 0.75
    for num, titre, desc in gestes:
        card(s, x, 2.3, 3.75, 2.5, fill=WHITE, outline=BORDER)
        circle(s, x + 0.35, 2.65, 0.7, GREEN_MAIN, num)
        text(s, x + 1.25, 2.78, 2.25, 0.45, titre, size=17, bold=True, color=TEXT)
        text(s, x + 0.35, 3.65, 3.05, 0.8, desc, size=14.5, color=MUTED, line=1.2)
        x += 4.0
    card(s, 0.75, 5.2, 11.8, 1.65, fill=GREEN_DARK)
    text(s, 1.2, 5.5, 10.9, 0.5, "Vous n'avez rien à taper. Rien à cliquer.",
         size=25, bold=True, color=YELLOW, font=TITLE_FONT)
    text(s, 1.2, 6.12, 10.9, 0.45,
         "Si le lecteur ne réagit pas, vous pouvez taper le numéro de la carte à la "
         "main dans le champ, puis appuyer sur Entrée.",
         size=14, color=WHITE)
    notes(s, "Faire faire le geste a chaque employe pendant la formation.")

    # =========================================================== 6. écran vert
    s = slide()
    header(s, "L'écran vert : entrée autorisée",
           "Quatre informations à lire avant de laisser passer l'enfant")
    card(s, 0.75, 2.2, 5.6, 4.4, fill=GREEN_PALE, outline=GREEN_MAIN)
    text(s, 1.05, 2.6, 5.0, 0.55, "ENTRÉE AUTORISÉE", size=26, bold=True,
         color=GREEN_DARK, font=TITLE_FONT, align=PP_ALIGN.CENTER)
    text(s, 1.05, 3.35, 5.0, 0.45, "Aminata Diallo", size=21, bold=True, color=TEXT,
         align=PP_ALIGN.CENTER)
    text(s, 1.05, 3.88, 5.0, 0.35, "M-0001 · Mensuel 4 entrées", size=14,
         color=MUTED, align=PP_ALIGN.CENTER)
    bx = 1.15
    for val, lab in [("3", "ENTRÉES\nRESTANTES"), ("23/08", "EXPIRE LE"),
                     ("7", "AVANT VISITE\nOFFERTE")]:
        card(s, bx, 4.5, 1.55, 1.6, fill=WHITE)
        text(s, bx + 0.1, 4.72, 1.35, 0.5, val, size=23, bold=True,
             color=GREEN_DARK, font=TITLE_FONT, align=PP_ALIGN.CENTER)
        text(s, bx + 0.1, 5.35, 1.35, 0.65, lab, size=9.5, bold=True, color=MUTED,
             align=PP_ALIGN.CENTER, space=0, line=1.1)
        bx += 1.7
    lignes = [
        ("Le nom", "Vérifiez que c'est bien l'enfant devant vous."),
        ("L'abonnement", "Le type de forfait dont il dispose."),
        ("Les entrées restantes", "S'il en reste 1, prévenez le parent gentiment."),
        ("La date d'expiration", "Proposez le renouvellement si la date approche."),
    ]
    y = 2.3
    for titre, desc in lignes:
        circle(s, 6.8, y, 0.38, GREEN_MAIN, "•", size=17)
        text(s, 7.4, y - 0.02, 5.15, 0.36, titre, size=16.5, bold=True, color=TEXT)
        text(s, 7.4, y + 0.4, 5.15, 0.5, desc, size=13.5, color=MUTED, line=1.2)
        y += 1.05
    card(s, 6.8, 6.0, 5.75, 0.72, fill=YELLOW_PALE)
    text(s, 7.05, 6.22, 5.3, 0.4,
         "« Déjà passé 2 fois aujourd'hui » = vérifiez qu'il ne s'agit pas d'une erreur",
         size=12.5, bold=True, color=TEXT)
    notes(s, "Le compteur 'avant visite offerte' n'apparait que si la fidelite est activee.")

    # =========================================================== 7. écran rouge
    s = slide()
    header(s, "L'écran rouge : entrée refusée",
           "Le logiciel affiche toujours le motif — voici quoi faire")
    rows = [
        ("Carte inconnue — non attribuée",
         "Cette carte n'est enregistrée sur aucun enfant",
         "Créez la fiche, ou attribuez la carte au bon enfant"),
        ("Carte bloquée (perdue/désactivée)",
         "La carte a été déclarée perdue",
         "Le parent doit utiliser la nouvelle carte"),
        ("Abonnement expiré le ...",
         "La date de fin est dépassée",
         "Proposez un renouvellement, puis validez"),
        ("Plus d'entrées disponibles",
         "Le forfait est entièrement consommé",
         "Proposez un nouvel abonnement"),
        ("Aucun abonnement actif",
         "L'enfant n'a pas d'abonnement en cours",
         "Vendez un abonnement depuis sa fiche"),
    ]
    y = 2.2
    text(s, 0.9, y, 3.9, 0.3, "CE QUI S'AFFICHE", size=12, bold=True, color=MUTED)
    text(s, 5.0, y, 3.3, 0.3, "CE QUE ÇA VEUT DIRE", size=12, bold=True, color=MUTED)
    text(s, 8.6, y, 3.9, 0.3, "CE QUE VOUS FAITES", size=12, bold=True, color=MUTED)
    y = 2.68
    for msg, sens, action in rows:
        card(s, 0.75, y, 11.8, 0.74, fill=RED_PALE if rows.index((msg, sens, action)) % 2 == 0 else WHITE)
        text(s, 0.9, y + 0.22, 3.95, 0.4, msg, size=13.5, bold=True, color=RED)
        text(s, 5.0, y + 0.22, 3.45, 0.4, sens, size=13, color=TEXT)
        text(s, 8.6, y + 0.22, 3.85, 0.4, action, size=13, color=GREEN_DARK, bold=True)
        y += 0.82
    text(s, 0.75, y + 0.28, 11.8, 0.45,
         "Ne laissez jamais entrer un enfant refusé sans en parler au responsable.",
         size=15.5, bold=True, color=TEXT)
    notes(s, "Le motif exact est toujours ecrit a l'ecran : il suffit de le lire au parent.")

    # =========================================================== 8. visite offerte
    s = slide(PURPLE_PALE)
    text(s, 0.75, 0.8, 11.8, 0.85, "La visite offerte", size=40, bold=True,
         color=PURPLE, font=TITLE_FONT)
    text(s, 0.75, 1.75, 11.8, 0.5,
         "Le logiciel récompense les enfants fidèles, tout seul", size=16, color=TEXT)
    card(s, 0.75, 2.75, 5.9, 3.9, fill=WHITE)
    text(s, 1.15, 3.25, 5.1, 0.6, "VISITE OFFERTE !", size=30, bold=True,
         color=PURPLE, font=TITLE_FONT, align=PP_ALIGN.CENTER)
    text(s, 1.15, 4.15, 5.1, 2.2,
         "Toutes les 10 visites payantes, la 11ᵉ est gratuite.\n\n"
         "Le logiciel compte tout seul et n'entame pas le forfait de l'enfant.",
         size=16, color=TEXT, align=PP_ALIGN.CENTER, line=1.3)
    card(s, 7.05, 2.75, 5.5, 3.9, fill=PURPLE)
    text(s, 7.45, 3.2, 4.7, 0.45, "VOTRE RÔLE", size=16, bold=True, color=YELLOW)
    text(s, 7.45, 3.9, 4.7, 2.4,
         "Annoncez-le au parent avec le sourire :\n\n"
         "« Aujourd'hui c'est offert, c'est la 11ᵉ visite d'Aminata ! »\n\n"
         "C'est un moment qui fidélise le client.",
         size=15, color=WHITE, line=1.3)
    notes(s, "Le seuil (10 visites) est reglable par le super administrateur.")

    # =========================================================== 9. nouveau membre
    s = slide()
    header(s, "Inscrire un nouveau membre", "Menu « Membres » → bouton « + Nouveau membre »")
    champs = [
        ("Nom de l'enfant", "Obligatoire", GREEN_DARK),
        ("Date de naissance", "Déclenche les propositions d'anniversaire", PURPLE),
        ("Nom du parent", "Pour l'appeler par son nom", GREEN_DARK),
        ("Téléphone du parent", "Indispensable pour les relances WhatsApp", YELLOW),
    ]
    y = 2.25
    for nom, role, couleur in champs:
        card(s, 0.75, y, 7.2, 0.88, fill=GREEN_PALE)
        text(s, 1.05, y + 0.2, 3.2, 0.45, nom, size=16.5, bold=True, color=TEXT)
        text(s, 4.4, y + 0.24, 3.4, 0.4, role, size=13,
             color=PURPLE if couleur == PURPLE else MUTED,
             bold=(couleur in (PURPLE, YELLOW)))
        y += 1.1
    card(s, 8.35, 2.25, 4.2, 4.3, fill=YELLOW_PALE, outline=YELLOW)
    text(s, 8.7, 2.6, 3.5, 0.45, "NE SAUTEZ PAS CES DEUX CHAMPS", size=14,
         bold=True, color=TEXT)
    text(s, 8.7, 3.25, 3.5, 3.1,
         "Le téléphone et la date de naissance ne sont pas des détails.\n\n"
         "C'est grâce à eux que le parc peut relancer un abonnement qui expire "
         "et proposer une fête d'anniversaire.\n\n"
         "Un client sans téléphone est un client perdu.",
         size=14, color=TEXT, line=1.3)
    notes(s, "Le code membre (M-0001) est attribue automatiquement.")

    # =========================================================== 10. attribuer carte
    s = slide()
    header(s, "Attribuer une carte", "Une carte neuve pour un nouvel enfant")
    steps = [
        ("1", "Ouvrez la fiche de l'enfant", "Menu Membres → bouton « Ouvrir »"),
        ("2", "Cliquez sur « + Attribuer une carte »", "En haut de la section Cartes RFID"),
        ("3", "Posez la carte sur le lecteur", "Le numéro se remplit tout seul — ne tapez rien"),
        ("4", "Cliquez sur « Attribuer »", "C'est fait, la carte est active immédiatement"),
    ]
    y = 2.3
    for num, titre, desc in steps:
        circle(s, 0.85, y, 0.64, GREEN_DARK, num)
        text(s, 1.8, y + 0.03, 6.3, 0.4, titre, size=17.5, bold=True, color=TEXT)
        text(s, 1.8, y + 0.52, 6.3, 0.4, desc, size=14, color=MUTED)
        y += 1.15
    card(s, 8.6, 2.3, 3.95, 3.4, fill=GREEN_PALE)
    text(s, 8.95, 2.65, 3.25, 0.45, "UNE CARTE = UN ENFANT", size=15, bold=True,
         color=GREEN_DARK)
    text(s, 8.95, 3.25, 3.25, 2.2,
         "Un enfant ne peut avoir qu'une seule carte active.\n\n"
         "Si le logiciel refuse, c'est qu'il en a déjà une : utilisez « Carte "
         "perdue » (page suivante).",
         size=14, color=TEXT, line=1.3)
    notes(s, "Le numero imprime sur la carte est facultatif mais pratique.")

    # =========================================================== 11. vendre
    s = slide()
    header(s, "Vendre un abonnement", "Depuis la fiche de l'enfant → « Vendre un abonnement »")
    steps = [
        ("1", "Choisissez la formule", "4 entrées, 8 entrées ou VIP illimité"),
        ("2", "Choisissez le mode de paiement", "Espèces, Orange Money, MTN MoMo ou carte"),
        ("3", "Cliquez sur « Encaisser »", "Le reçu s'imprime automatiquement"),
    ]
    y = 2.45
    for num, titre, desc in steps:
        circle(s, 0.85, y, 0.7, YELLOW, num, label_color=TEXT)
        text(s, 1.9, y + 0.05, 5.7, 0.42, titre, size=18.5, bold=True, color=TEXT)
        text(s, 1.9, y + 0.58, 5.7, 0.4, desc, size=14.5, color=MUTED)
        y += 1.45
    card(s, 8.25, 2.35, 4.3, 4.2, fill=GREEN_DARK)
    text(s, 8.6, 2.7, 3.6, 0.45, "LE PRIX EST FIXÉ", size=17, bold=True, color=YELLOW)
    text(s, 8.6, 3.35, 3.6, 3.0,
         "Vous ne pouvez pas modifier le montant : il vient du catalogue du parc.\n\n"
         "C'est normal, et c'est une protection pour vous : personne ne pourra "
         "vous reprocher un prix mal appliqué.\n\n"
         "Seul le responsable peut changer un tarif.",
         size=14, color=WHITE, line=1.3)
    notes(s, "Le recu porte le nom de l'employe qui encaisse.")

    # =========================================================== 12. carte perdue
    s = slide()
    header(s, "Carte perdue", "La situation la plus fréquente — une seule manipulation")
    card(s, 0.75, 2.2, 11.8, 1.35, fill=RED_PALE, outline=RED)
    text(s, 1.15, 2.55, 11.0, 0.55,
         "Ne créez JAMAIS une deuxième fiche pour le même enfant.",
         size=21, bold=True, color=RED, font=TITLE_FONT)
    text(s, 1.15, 3.1, 11.0, 0.35,
         "Vous perdriez son abonnement, son historique et sa fidélité.",
         size=14.5, color=TEXT)
    steps = [
        ("1", "Ouvrez la fiche de l'enfant"),
        ("2", "Cliquez sur « Carte perdue — la remplacer »"),
        ("3", "Posez la nouvelle carte sur le lecteur"),
        ("4", "Validez : l'ancienne est désactivée toute seule"),
    ]
    y = 3.95
    for num, titre in steps:
        circle(s, 0.85, y, 0.62, GREEN_DARK, num)
        text(s, 1.75, y + 0.13, 6.2, 0.4, titre, size=17, bold=True, color=TEXT)
        y += 0.78
    card(s, 8.35, 3.95, 4.2, 2.65, fill=GREEN_PALE)
    text(s, 8.7, 4.3, 3.5, 0.45, "SI LA CARTE EST RETROUVÉE", size=14.5, bold=True,
         color=GREEN_DARK)
    text(s, 8.7, 4.95, 3.5, 1.5,
         "Reposez-la simplement sur la fiche de l'enfant : le logiciel la "
         "réactive automatiquement.",
         size=14.5, color=TEXT, line=1.3)
    notes(s, "L'ancienne carte est bloquee : si quelqu'un la retrouve et la presente, "
             "elle est refusee.")

    # =========================================================== 13. rôles
    s = slide()
    header(s, "Qui a le droit de faire quoi ?",
           "Chacun voit uniquement les menus qui le concernent")
    roles = [
        ("AGENT D'ACCUEIL", GREEN_MAIN, WHITE, [
            "Valider les entrées",
            "Inscrire les membres",
            "Attribuer et remplacer les cartes",
            "Vendre au prix du catalogue",
            "Voir les paiements, réimprimer un reçu",
            "Envoyer les relances WhatsApp",
        ]),
        ("GÉRANT", YELLOW, TEXT, [
            "Tout ce que fait l'agent",
            "Voir le tableau de bord",
            "Voir les revenus et statistiques",
            "Consulter tout l'historique",
        ]),
        ("RESPONSABLE", PURPLE, WHITE, [
            "Tout ce que fait le gérant",
            "Modifier les tarifs",
            "Créer les comptes employés",
            "Annuler un abonnement",
            "Exports Excel et sauvegardes",
            "Régler les paramètres",
        ]),
    ]
    x = 0.75
    for titre, couleur, txt_couleur, droits in roles:
        card(s, x, 2.25, 3.75, 4.45, fill=WHITE, outline=BORDER)
        bandeau = card(s, x, 2.25, 3.75, 0.85, fill=couleur)
        text(s, x + 0.2, 2.5, 3.35, 0.4, titre, size=16, bold=True,
             color=txt_couleur, align=PP_ALIGN.CENTER, font=TITLE_FONT)
        y = 3.3
        for droit in droits:
            circle(s, x + 0.3, y + 0.06, 0.22, couleur, "", size=9)
            text(s, x + 0.68, y - 0.02, 2.87, 0.62, droit, size=13.5, color=TEXT,
                 line=1.15)
            y += 0.56
        x += 4.0
    notes(s, "Si un menu n'apparait pas chez vous, ce n'est pas une panne : "
             "c'est votre niveau d'acces.")

    # =========================================================== 14. règles d'or
    s = slide(GREEN_DARK)
    text(s, 0.75, 0.65, 11.8, 0.85, "Les 5 règles d'or", size=40, bold=True,
         color=YELLOW, font=TITLE_FONT)
    regles = [
        ("Chaque action porte votre nom", "entrées validées, encaissements, tout est tracé"),
        ("Ne prêtez jamais votre compte", "même à un collègue, même cinq minutes"),
        ("Les prix ne se négocient pas", "le montant vient du catalogue, il est bloqué"),
        ("Une carte = un enfant", "carte perdue : on remplace, on ne recrée pas la fiche"),
        ("Ne fermez pas la fenêtre noire", "c'est le moteur du logiciel"),
    ]
    y = 1.95
    for i, (titre, desc) in enumerate(regles, 1):
        circle(s, 0.85, y, 0.7, YELLOW, str(i), label_color=TEXT)
        text(s, 1.85, y + 0.03, 10.4, 0.4, titre, size=20, bold=True, color=WHITE)
        text(s, 1.85, y + 0.5, 10.4, 0.35, desc, size=14.5, color=GREEN_PALE)
        y += 1.08
    notes(s, "A afficher au comptoir si possible.")

    # =========================================================== 15. problèmes
    s = slide()
    header(s, "En cas de problème", "Trois pannes courantes, trois solutions simples")
    problemes = [
        ("L'écran ne s'ouvre pas",
         "Vérifiez que la fenêtre « Didikids Parc - Serveur » est ouverte dans la "
         "barre des tâches. Sinon, double-cliquez sur l'icône du Bureau."),
        ("Le lecteur ne réagit pas",
         "Débranchez puis rebranchez le lecteur USB, et relancez « Lecteur RFID ». "
         "En attendant, tapez le numéro de la carte à la main."),
        ("Un refus vous semble injuste",
         "Ne forcez pas l'entrée. Notez le nom de l'enfant et appelez le "
         "responsable : l'historique permettra de comprendre."),
    ]
    y = 2.25
    for titre, desc in problemes:
        card(s, 0.75, y, 11.8, 1.25, fill=GREEN_PALE)
        text(s, 1.1, y + 0.24, 3.6, 0.45, titre, size=17, bold=True, color=GREEN_DARK)
        text(s, 4.9, y + 0.22, 7.4, 0.9, desc, size=14, color=TEXT, line=1.2)
        y += 1.45
    card(s, 0.75, 6.35, 11.8, 0.85, fill=YELLOW)
    text(s, 1.1, 6.63, 11.1, 0.45,
         "En cas de doute, appelez le responsable. Aucune question n'est bête.",
         size=17, bold=True, color=TEXT, align=PP_ALIGN.CENTER)
    notes(s, "Laisser le numero du responsable affiche au comptoir.")

    # =========================================================== 16. fin
    s = slide(GREEN_DARK)
    text(s, 0.75, 2.5, 11.8, 0.95, "Des questions ?", size=46, bold=True,
         color=WHITE, font=TITLE_FONT, align=PP_ALIGN.CENTER)
    card(s, 3.4, 4.05, 6.5, 1.55, fill=YELLOW)
    text(s, 3.7, 4.4, 5.9, 0.85,
         "Posez la carte.\nLisez la couleur.",
         size=24, bold=True, color=TEXT, align=PP_ALIGN.CENTER, font=TITLE_FONT,
         line=1.2)
    text(s, 0.75, 6.05, 11.8, 0.5,
         "Didikids Parc — parce que chaque enfant mérite de s'épanouir",
         size=16, color=GREEN_PALE, align=PP_ALIGN.CENTER)
    notes(s, "Remercier l'equipe et faire pratiquer sur le vrai lecteur.")

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "Didikids_Parc_Formation_Employes.pptx")
    prs.save(out)
    return out, len(prs.slides.__iter__.__self__._sldIdLst)


if __name__ == "__main__":
    path, n = build()
    print(f"OK : {path}")
