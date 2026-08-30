# -*- coding: utf-8 -*-
"""Contrôle qualité : débordements de texte, sorties de diapositive, chevauchements."""
import math
from pptx import Presentation
from pptx.util import Emu

EMU_IN = 914400.0
prs = Presentation("formation/Didikids_Parc_Guide_Agent.pptx")
SW, SH = prs.slide_width / EMU_IN, prs.slide_height / EMU_IN
print(f"Diapositives : {len(prs.slides)}  |  format {SW:.2f}x{SH:.2f} pouces\n")

problems = []

for idx, slide in enumerate(prs.slides, 1):
    boxes = []
    for sh in slide.shapes:
        x, y = sh.left / EMU_IN, sh.top / EMU_IN
        w, h = sh.width / EMU_IN, sh.height / EMU_IN
        # hors diapositive ?
        if x < -0.01 or y < -0.01 or x + w > SW + 0.01 or y + h > SH + 0.01:
            # le fond plein écran est normal
            if not (abs(w - SW) < 0.02 and abs(h - SH) < 0.02):
                problems.append(f"D{idx} HORS-CADRE : {sh.shape_type} à "
                                f"({x:.2f},{y:.2f}) {w:.2f}x{h:.2f}")
        if not sh.has_text_frame or not sh.text_frame.text.strip():
            continue
        tf = sh.text_frame
        # hauteur de texte estimée
        total_pt = 0.0
        for p in tf.paragraphs:
            txt = "".join(r.text for r in p.runs)
            if not txt:
                total_pt += 6
                continue
            size = 16.0
            for r in p.runs:
                if r.font.size:
                    size = r.font.size.pt
                    break
            avg_char = size * 0.47
            usable_pt = max(w * 72 - 4, 20)
            per_line = max(int(usable_pt / avg_char), 1)
            lines = 0
            for seg in txt.split("\n"):
                lines += max(1, math.ceil(len(seg) / per_line))
            ls = p.line_spacing if isinstance(p.line_spacing, float) else 1.0
            total_pt += lines * size * 1.21 * ls
            total_pt += (p.space_after.pt if p.space_after else 0)
        need_in = total_pt / 72.0
        avail_in = h
        if need_in > avail_in + 0.12:
            boxes.append((y, y + need_in, need_in - avail_in,
                          txt_preview := tf.text[:52].replace("\n", " ")))
    # débordement gênant : il touche un élément situé dessous
    for y0, yend, over, prev in boxes:
        if over > 0.35:
            problems.append(f"D{idx} DEBORDEMENT {over:.2f}\" : « {prev}… »")

if problems:
    print("PROBLEMES DETECTES :")
    for p in problems:
        print("  -", p)
else:
    print("Aucun debordement ni sortie de cadre detecte.")
