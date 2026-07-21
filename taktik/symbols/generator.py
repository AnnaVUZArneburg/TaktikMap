"""APP-6-Symbolgenerator (Qt-frei, erzeugt reines SVG).

Festlegung 10.4 im Lastenheft: Ein programmatischer Generator erzeugt
NATO-APP-6-Rahmen (Freund/Feind/Neutral/Unbekannt) mit gängigen
Rollen-Icons als lizenzfreie SVG-Dateien. Er ersetzt keinen
offiziellen 1:1-Komplettkatalog, deckt aber die üblichen Fälle ab und
ist datengetrieben erweiterbar.

Aufruf zum Erzeugen eines Startersatzes::

    python -m taktik.symbols.generator symbole/
"""

from __future__ import annotations

import json
from pathlib import Path

# Zeichenfläche: 200x200, Rahmen zentriert
W = H = 200.0
CX, CY = W / 2, H / 2
STROKE = 4.0

# Standardfarben nach APP-6 (Umrandung/Füllung je Zugehörigkeit)
AFFILIATIONS = {
    "freund": {"fill": "#80e0ff", "stroke": "#0060a0", "frame": "rect"},
    "feind": {"fill": "#ff8080", "stroke": "#c00000", "frame": "diamond"},
    "neutral": {"fill": "#aaffaa", "stroke": "#00a000", "frame": "square"},
    "unbekannt": {"fill": "#ffff80", "stroke": "#a0a000", "frame": "quatrefoil"},
}


def _frame_rect() -> tuple[str, tuple[float, float, float, float]]:
    x, y, w, h = 30.0, 55.0, 140.0, 90.0
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="{{fill}}" stroke="{{stroke}}" stroke-width="{STROKE}"/>',
            (x, y, w, h))


def _frame_square() -> tuple[str, tuple[float, float, float, float]]:
    x, y, w, h = 45.0, 55.0, 110.0, 110.0
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="{{fill}}" stroke="{{stroke}}" stroke-width="{STROKE}"/>',
            (x, y, w, h))


def _frame_diamond() -> tuple[str, tuple[float, float, float, float]]:
    r = 68.0
    cy = 110.0
    return (f'<path d="M {CX} {cy - r} L {CX + r} {cy} L {CX} {cy + r} '
            f'L {CX - r} {cy} Z" '
            f'fill="{{fill}}" stroke="{{stroke}}" stroke-width="{STROKE}"/>',
            (CX - r, cy - r, 2 * r, 2 * r))


def _frame_quatrefoil() -> tuple[str, tuple[float, float, float, float]]:
    # Vereinfachter "unbekannt"-Rahmen: vier überlappende Bögen
    r = 34.0
    cy = 110.0
    return (
        f'<g fill="{{fill}}" stroke="{{stroke}}" stroke-width="{STROKE}">'
        f'<circle cx="{CX - r * 0.8}" cy="{cy - r * 0.8}" r="{r}"/>'
        f'<circle cx="{CX + r * 0.8}" cy="{cy - r * 0.8}" r="{r}"/>'
        f'<circle cx="{CX - r * 0.8}" cy="{cy + r * 0.8}" r="{r}"/>'
        f'<circle cx="{CX + r * 0.8}" cy="{cy + r * 0.8}" r="{r}"/>'
        f'<rect x="{CX - r * 0.9}" y="{cy - r * 0.9}" width="{r * 1.8}" '
        f'height="{r * 1.8}" stroke="none"/></g>',
        (CX - r * 1.8, cy - r * 1.8, r * 3.6, r * 3.6),
    )


FRAMES = {
    "rect": _frame_rect,
    "square": _frame_square,
    "diamond": _frame_diamond,
    "quatrefoil": _frame_quatrefoil,
}


# ----------------------------------------------------------------------
# Rahmen für Luft- und Seefahrzeuge (vgl. Symbology Guide:
# aerial entity = oben offener Bogen, surface entity = Kreis)
# ----------------------------------------------------------------------
def _frame_air(affiliation: str) -> tuple[str, tuple[float, float, float, float]]:
    box = (58.0, 85.0, 84.0, 58.0)
    if affiliation == "feind":
        # Spitzbogen, unten offen
        path = 'M 35 155 L 100 30 L 165 155'
    elif affiliation == "neutral":
        # Rechteck, unten offen
        path = 'M 35 155 L 35 50 L 165 50 L 165 155'
    elif affiliation == "unbekannt":
        # Doppelbogen, unten offen
        path = ('M 35 155 A 34 62 0 0 1 100 118 '
                'A 34 62 0 0 1 165 155')
    else:
        # Rundbogen (freund)
        path = 'M 35 155 A 65 105 0 0 1 165 155'
    svg = (f'<path d="{path}" fill="{{fill}}" stroke="{{stroke}}" '
           f'stroke-width="{STROKE}"/>')
    return svg, box


def _frame_sea(affiliation: str) -> tuple[str, tuple[float, float, float, float]]:
    if affiliation == "feind":
        return _frame_diamond()
    if affiliation == "neutral":
        return _frame_square()
    if affiliation == "unbekannt":
        return _frame_quatrefoil()
    svg = (f'<circle cx="{CX}" cy="110" r="62" fill="{{fill}}" '
           f'stroke="{{stroke}}" stroke-width="{STROKE}"/>')
    return svg, (56.0, 78.0, 88.0, 64.0)


def _icon(kind: str, box: tuple[float, float, float, float],
          stroke: str) -> str:
    """Rollen-Icon innerhalb des Rahmens (APP-6-angelehnt)."""
    x, y, w, h = box
    cx, cy = x + w / 2, y + h / 2
    sw = STROKE * 0.9
    if kind == "infanterie":
        # Diagonalkreuz über den ganzen Rahmen
        return (f'<path d="M {x} {y} L {x + w} {y + h} M {x} {y + h} '
                f'L {x + w} {y}" stroke="{stroke}" stroke-width="{sw}" '
                f'fill="none"/>')
    if kind == "panzer":
        rx = min(w, h) * 0.32
        return (f'<ellipse cx="{cx}" cy="{cy}" rx="{w * 0.32}" ry="{rx * 0.6}" '
                f'fill="none" stroke="{stroke}" stroke-width="{sw}"/>')
    if kind == "panzergrenadier":
        # Mechanisierte Infanterie: Diagonalkreuz + Ellipse (APP-6)
        rx = min(w, h) * 0.32
        return (f'<path d="M {x} {y} L {x + w} {y + h} M {x} {y + h} '
                f'L {x + w} {y}" stroke="{stroke}" stroke-width="{sw}" '
                f'fill="none"/>'
                f'<ellipse cx="{cx}" cy="{cy}" rx="{w * 0.30}" '
                f'ry="{rx * 0.55}" fill="none" stroke="{stroke}" '
                f'stroke-width="{sw}"/>')
    if kind == "panzerabwehr":
        # Panzerabwehr: Winkel von den unteren Ecken zur oberen Mitte
        return (f'<path d="M {x} {y + h} L {cx} {y} L {x + w} {y + h}" '
                f'stroke="{stroke}" stroke-width="{sw}" fill="none"/>')
    if kind == "mot_infanterie":
        # Motorisierte Infanterie: Diagonalkreuz + senkrechte Mittellinie
        return (f'<path d="M {x} {y} L {x + w} {y + h} M {x} {y + h} '
                f'L {x + w} {y} M {cx} {y} L {cx} {y + h}" '
                f'stroke="{stroke}" stroke-width="{sw}" fill="none"/>')
    if kind == "fallschirmjaeger":
        # Luftlande-/Fallschirmjäger: Diagonalkreuz + Tragflächenbogen
        return (f'<path d="M {x} {y} L {x + w} {y + h} M {x} {y + h} '
                f'L {x + w} {y}" stroke="{stroke}" stroke-width="{sw}" '
                f'fill="none"/>'
                f'<path d="M {cx - w * 0.22} {y + h} '
                f'A {w * 0.12} {h * 0.28} 0 0 1 {cx} {y + h} '
                f'A {w * 0.12} {h * 0.28} 0 0 1 {cx + w * 0.22} {y + h}" '
                f'stroke="{stroke}" stroke-width="{sw}" fill="none"/>')
    if kind == "panzeraufklaerung":
        # Panzeraufklärung: Ellipse + Diagonale
        rx = min(w, h) * 0.32
        return (f'<ellipse cx="{cx}" cy="{cy}" rx="{w * 0.32}" '
                f'ry="{rx * 0.6}" fill="none" stroke="{stroke}" '
                f'stroke-width="{sw}"/>'
                f'<path d="M {x} {y + h} L {x + w} {y}" stroke="{stroke}" '
                f'stroke-width="{sw}" fill="none"/>')
    if kind == "moerser":
        # Mörser: senkrechter Pfeil nach oben mit Bodenpunkt
        ah = h * 0.16
        return (f'<line x1="{cx}" y1="{y + h * 0.2}" x2="{cx}" '
                f'y2="{y + h * 0.8}" stroke="{stroke}" stroke-width="{sw}"/>'
                f'<path d="M {cx - w * 0.10} {y + h * 0.2 + ah} '
                f'L {cx} {y + h * 0.2} L {cx + w * 0.10} {y + h * 0.2 + ah}" '
                f'stroke="{stroke}" stroke-width="{sw}" fill="none"/>'
                f'<circle cx="{cx}" cy="{y + h * 0.82}" r="{sw * 1.1}" '
                f'fill="{stroke}"/>')
    if kind == "heeresflieger":
        # Heeresflieger/Luftfahrzeug: Propeller-Schleife (Fläche)
        rx, ry = w * 0.30, h * 0.22
        return (f'<path d="M {cx - rx} {cy - ry} L {cx + rx} {cy + ry} '
                f'L {cx + rx} {cy - ry} L {cx - rx} {cy + ry} Z" '
                f'fill="{stroke}" stroke="{stroke}" '
                f'stroke-width="{sw * 0.5}"/>')
    if kind == "uav":
        # UAV/Drohne: abgewinkelte Tragfläche (Winkel nach unten)
        return (f'<path d="M {cx - w * 0.32} {cy - h * 0.10} '
                f'L {cx} {cy + h * 0.16} L {cx + w * 0.32} {cy - h * 0.10}" '
                f'stroke="{stroke}" stroke-width="{sw * 1.4}" fill="none"/>')
    if kind == "instandsetzung":
        # Instandsetzung: Schraubenschlüssel-Balken mit Endhaken
        b = h * 0.16
        return (f'<g stroke="{stroke}" stroke-width="{sw}" fill="none">'
                f'<line x1="{x + w * 0.18}" y1="{cy}" x2="{x + w * 0.82}" '
                f'y2="{cy}"/>'
                f'<path d="M {x + w * 0.18} {cy - b} L {x + w * 0.18} '
                f'{cy + b} M {x + w * 0.82} {cy - b} L {x + w * 0.82} '
                f'{cy + b}"/>'
                f'<circle cx="{cx}" cy="{cy}" r="{sw * 1.0}" '
                f'fill="{stroke}" stroke="none"/></g>')
    if kind == "munition":
        # Munition: stilisiertes Geschoss
        return (f'<path d="M {cx - w * 0.07} {y + h * 0.75} '
                f'L {cx - w * 0.07} {y + h * 0.40} '
                f'A {w * 0.07} {h * 0.18} 0 0 1 {cx + w * 0.07} '
                f'{y + h * 0.40} L {cx + w * 0.07} {y + h * 0.75} Z" '
                f'fill="none" stroke="{stroke}" stroke-width="{sw}"/>'
                f'<line x1="{cx - w * 0.14}" y1="{y + h * 0.75}" '
                f'x2="{cx + w * 0.14}" y2="{y + h * 0.75}" '
                f'stroke="{stroke}" stroke-width="{sw}"/>')
    if kind == "feldjaeger":
        # Feldjäger/Militärpolizei: Buchstabenkennung MP
        return (f'<text x="{cx}" y="{cy}" font-family="sans-serif" '
                f'font-size="{h * 0.52:.0f}" font-weight="bold" '
                f'fill="{stroke}" text-anchor="middle" '
                f'dominant-baseline="central">MP</text>')
    # ---------------- Luftfahrzeuge ----------------
    if kind == "hubschrauber":
        # Hubschrauber: gefüllte Doppelflügel (Fliege), gerade Kanten
        return (f'<polygon points="{cx - w * 0.32},{cy - h * 0.22} '
                f'{cx + w * 0.32},{cy + h * 0.22} '
                f'{cx + w * 0.32},{cy - h * 0.22} '
                f'{cx - w * 0.32},{cy + h * 0.22}" fill="{stroke}"/>')
    if kind == "flugzeug":
        # Starrflügler: gefüllte, gerundete Tragflächen
        return (f'<path d="M {cx} {cy} C {cx - w * 0.14} {cy - h * 0.34}, '
                f'{cx - w * 0.42} {cy - h * 0.34}, {cx - w * 0.42} {cy} '
                f'C {cx - w * 0.42} {cy + h * 0.34}, '
                f'{cx - w * 0.14} {cy + h * 0.34}, {cx} {cy} '
                f'C {cx + w * 0.14} {cy - h * 0.34}, '
                f'{cx + w * 0.42} {cy - h * 0.34}, {cx + w * 0.42} {cy} '
                f'C {cx + w * 0.42} {cy + h * 0.34}, '
                f'{cx + w * 0.14} {cy + h * 0.34}, {cx} {cy} Z" '
                f'fill="{stroke}"/>')
    if kind == "transportflugzeug":
        return (_icon("flugzeug", box, stroke) +
                f'<line x1="{cx - w * 0.30}" y1="{cy + h * 0.42}" '
                f'x2="{cx + w * 0.30}" y2="{cy + h * 0.42}" '
                f'stroke="{stroke}" stroke-width="{sw}"/>')
    # ---------------- Seefahrzeuge ----------------
    if kind == "kriegsschiff":
        # Überwasserkampfschiff: Rumpf mit Aufbau
        return (f'<path d="M {cx - w * 0.38} {cy + h * 0.05} '
                f'L {cx + w * 0.38} {cy + h * 0.05} '
                f'L {cx + w * 0.26} {cy + h * 0.30} '
                f'L {cx - w * 0.26} {cy + h * 0.30} Z" '
                f'fill="{stroke}"/>'
                f'<rect x="{cx - w * 0.10}" y="{cy - h * 0.28}" '
                f'width="{w * 0.20}" height="{h * 0.33}" fill="{stroke}"/>')
    if kind == "uboot":
        # U-Boot: langgestreckter Rumpf mit Turm
        return (f'<rect x="{cx - w * 0.38}" y="{cy - h * 0.10}" '
                f'width="{w * 0.76}" height="{h * 0.22}" rx="{h * 0.11}" '
                f'fill="{stroke}"/>'
                f'<rect x="{cx - w * 0.08}" y="{cy - h * 0.30}" '
                f'width="{w * 0.16}" height="{h * 0.20}" fill="{stroke}"/>')
    if kind == "bomber":
        # Bomber: Starrflügler-Tragflächen mit Kennung B
        return (_icon("flugzeug", box, stroke) +
                f'<text x="{cx}" y="{y + h * 0.92}" '
                f'font-family="sans-serif" font-size="{h * 0.34:.0f}" '
                f'font-weight="bold" fill="{stroke}" text-anchor="middle" '
                f'dominant-baseline="central">B</text>')
    if kind == "flugzeugtraeger":
        # Flugzeugträger: Rumpf mit durchgehendem Flugdeck (CV)
        return (f'<line x1="{cx - w * 0.40}" y1="{cy - h * 0.18}" '
                f'x2="{cx + w * 0.40}" y2="{cy - h * 0.18}" '
                f'stroke="{stroke}" stroke-width="{sw * 1.4}"/>'
                f'<path d="M {cx - w * 0.34} {cy - h * 0.02} '
                f'L {cx + w * 0.34} {cy - h * 0.02} '
                f'L {cx + w * 0.22} {cy + h * 0.26} '
                f'L {cx - w * 0.22} {cy + h * 0.26} Z" '
                f'fill="{stroke}"/>')
    if kind in ("zerstoerer", "fregatte", "kreuzer", "boot"):
        text = {"zerstoerer": "DD", "fregatte": "FF",
                "kreuzer": "CC", "boot": "B"}[kind]
        return (f'<text x="{cx}" y="{cy}" font-family="sans-serif" '
                f'font-size="{h * 0.48:.0f}" font-weight="bold" '
                f'fill="{stroke}" text-anchor="middle" '
                f'dominant-baseline="central">{text}</text>')
    if kind == "luftabwehr":
        # Luftabwehr/Flugabwehr: Bogen (Kuppel) über der Grundlinie
        return (f'<path d="M {x + w * 0.18} {y + h} '
                f'A {w * 0.34} {h * 0.72} 0 0 1 {x + w * 0.82} {y + h}" '
                f'stroke="{stroke}" stroke-width="{sw}" fill="none"/>')
    if kind == "artillerie":
        return (f'<circle cx="{cx}" cy="{cy}" r="{min(w, h) * 0.12}" '
                f'fill="{stroke}"/>')
    if kind == "aufklaerung":
        return (f'<path d="M {x} {y + h} L {x + w} {y}" stroke="{stroke}" '
                f'stroke-width="{sw}" fill="none"/>')
    if kind == "logistik":
        return (f'<line x1="{x}" y1="{cy}" x2="{x + w}" y2="{cy}" '
                f'stroke="{stroke}" stroke-width="{sw}"/>')
    if kind == "sanitaet":
        a = min(w, h) * 0.30
        return (f'<path d="M {cx} {cy - a} L {cx} {cy + a} M {cx - a} {cy} '
                f'L {cx + a} {cy}" stroke="{stroke}" stroke-width="{sw}" '
                f'fill="none"/>')
    if kind == "pioniere":
        a = w * 0.22
        b = h * 0.18
        return (f'<path d="M {cx - a} {cy - b} L {cx - a} {cy + b} '
                f'M {cx - a} {cy} L {cx + a} {cy} M {cx + a} {cy - b} '
                f'L {cx + a} {cy + b}" stroke="{stroke}" '
                f'stroke-width="{sw}" fill="none"/>')
    if kind == "fuehrung":
        # Fähnchen für Führungsstelle
        return (f'<path d="M {cx} {y + h * 0.15} L {cx} {y + h * 0.85} '
                f'M {cx} {y + h * 0.15} L {cx + w * 0.28} {y + h * 0.3} '
                f'L {cx} {y + h * 0.45}" stroke="{stroke}" '
                f'stroke-width="{sw}" fill="none"/>')
    if kind == "fernmelde":
        return (f'<path d="M {cx - w * 0.25} {cy + h * 0.2} '
                f'L {cx} {cy - h * 0.25} L {cx + w * 0.25} {cy + h * 0.2}" '
                f'stroke="{stroke}" stroke-width="{sw}" fill="none"/>'
                f'<line x1="{cx}" y1="{cy - h * 0.25}" x2="{cx}" '
                f'y2="{cy + h * 0.3}" stroke="{stroke}" stroke-width="{sw}"/>')
    if kind == "transport":
        r = min(w, h) * 0.11
        return (f'<circle cx="{cx - w * 0.18}" cy="{y + h * 0.78}" r="{r}" '
                f'fill="none" stroke="{stroke}" stroke-width="{sw}"/>'
                f'<circle cx="{cx + w * 0.18}" cy="{y + h * 0.78}" r="{r}" '
                f'fill="none" stroke="{stroke}" stroke-width="{sw}"/>')
    if kind == "bergung":
        # THW: stilisiertes Zahnrad-/Räumzeichen als Winkel
        a = min(w, h) * 0.28
        return (f'<path d="M {cx - a} {cy + a * 0.7} L {cx} {cy - a * 0.7} '
                f'L {cx + a} {cy + a * 0.7}" stroke="{stroke}" '
                f'stroke-width="{sw}" fill="none"/>')
    if kind == "ortung":
        # THW-Ortung: konzentrische Ortungsbögen
        r = min(w, h) * 0.14
        return (f'<g fill="none" stroke="{stroke}" stroke-width="{sw}">'
                f'<path d="M {cx - r} {cy - r} A {r * 1.4} {r * 1.4} 0 0 1 '
                f'{cx - r} {cy + r}"/>'
                f'<path d="M {cx - r * 0.2} {cy - r * 1.8} A {r * 2.6} '
                f'{r * 2.6} 0 0 1 {cx - r * 0.2} {cy + r * 1.8}"/>'
                f'<circle cx="{cx - r * 1.6}" cy="{cy}" r="{sw * 0.9}" '
                f'fill="{stroke}" stroke="none"/></g>')
    if kind == "pumpen":
        # THW-Wasserschaden/Pumpen: Wellenlinien
        a = w * 0.28
        b = h * 0.10
        return (f'<g fill="none" stroke="{stroke}" stroke-width="{sw}">'
                f'<path d="M {cx - a} {cy - b} Q {cx - a / 2} {cy - b * 3}, '
                f'{cx} {cy - b} T {cx + a} {cy - b}"/>'
                f'<path d="M {cx - a} {cy + b * 1.6} Q {cx - a / 2} '
                f'{cy - b * 0.4}, {cx} {cy + b * 1.6} T {cx + a} '
                f'{cy + b * 1.6}"/></g>')
    if kind == "beleuchtung":
        # Beleuchtung: Lampe mit Strahlen
        r = min(w, h) * 0.13
        rays = []
        for dx, dy in ((-1.6, -1.2), (0, -1.9), (1.6, -1.2)):
            rays.append(
                f'<line x1="{cx + dx * r * 0.9}" y1="{cy + dy * r * 0.9}" '
                f'x2="{cx + dx * r * 1.7}" y2="{cy + dy * r * 1.7}" '
                f'stroke="{stroke}" stroke-width="{sw}"/>')
        return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" '
                f'stroke="{stroke}" stroke-width="{sw}"/>' + "".join(rays))
    if kind == "raeumen":
        # Räumen: Räumschild-Winkel mit Grundlinie
        a = w * 0.26
        b = h * 0.20
        return (f'<g fill="none" stroke="{stroke}" stroke-width="{sw}">'
                f'<path d="M {cx - a} {cy - b} L {cx} {cy + b} '
                f'L {cx + a} {cy - b}"/>'
                f'<line x1="{cx - a}" y1="{cy + b}" x2="{cx + a}" '
                f'y2="{cy + b}"/></g>')
    return ""


ROLES = {
    "fuehrung": ["fuehrung", "fernmelde", "feldjaeger"],
    "infanterie": ["infanterie", "mot_infanterie", "panzergrenadier",
                   "fallschirmjaeger", "panzer", "panzerabwehr",
                   "luftabwehr", "aufklaerung", "panzeraufklaerung",
                   "artillerie", "moerser", "pioniere", "heeresflieger",
                   "uav"],
    "logistik": ["logistik", "transport", "instandsetzung", "munition"],
    "sanitaet": ["sanitaet"],
    "THW": ["bergung", "ortung", "raeumen", "pumpen", "beleuchtung",
            "fuehrung", "logistik", "sanitaet"],
}

# Kategorien mit eigener Rahmenform (Symbology Guide: aerial entity =
# unten offener Bogen, surface entity = Kreis)
DOMAIN_ROLES = {
    "luft": ["flugzeug", "bomber", "transportflugzeug", "hubschrauber",
             "uav"],
    "see": ["flugzeugtraeger", "kriegsschiff", "kreuzer", "zerstoerer",
            "fregatte", "uboot", "boot"],
}

ROLE_NAMES = {
    "fuehrung": "Führungsstelle",
    "fernmelde": "Fernmelde",
    "infanterie": "Infanterie",
    "mot_infanterie": "Infanterie (motorisiert)",
    "panzergrenadier": "Panzergrenadiere",
    "fallschirmjaeger": "Fallschirmjäger",
    "panzer": "Panzer",
    "panzerabwehr": "Panzerabwehr",
    "luftabwehr": "Luftabwehr",
    "aufklaerung": "Aufklärung",
    "panzeraufklaerung": "Panzeraufklärung",
    "artillerie": "Artillerie",
    "moerser": "Mörser",
    "pioniere": "Pioniere",
    "heeresflieger": "Heeresflieger",
    "uav": "UAV / Drohne",
    "instandsetzung": "Instandsetzung",
    "munition": "Munition",
    "feldjaeger": "Feldjäger",
    "flugzeug": "Kampfflugzeug",
    "bomber": "Bomber",
    "transportflugzeug": "Transportflugzeug",
    "hubschrauber": "Hubschrauber",
    "flugzeugtraeger": "Flugzeugträger",
    "kriegsschiff": "Kriegsschiff",
    "kreuzer": "Kreuzer",
    "zerstoerer": "Zerstörer",
    "fregatte": "Fregatte",
    "uboot": "U-Boot",
    "boot": "Boot",
    "logistik": "Logistik",
    "transport": "Transport",
    "sanitaet": "Sanität",
    "bergung": "Bergung",
    "ortung": "Ortung",
    "raeumen": "Räumen",
    "pumpen": "Pumpen / Wasserschaden",
    "beleuchtung": "Beleuchtung",
}

AFFILIATION_NAMES = {
    "freund": "eigene Kräfte",
    "feind": "feindliche Kräfte",
    "neutral": "neutral",
    "unbekannt": "unbekannt",
}


# ----------------------------------------------------------------------
# Ereignis-/Gefahrensymbole (BOS-Lagen: rahmenlose Zeichen)
# ----------------------------------------------------------------------
def _event_brand() -> str:
    # Flamme (rot, BOS: Brandstelle)
    return ('<path d="M 100 30 C 128 62, 148 88, 142 124 C 138 152, '
            '118 170, 100 170 C 78 170, 60 150, 58 124 C 56 96, 80 66, '
            '100 30 Z" fill="#d02020" stroke="#901010" stroke-width="4"/>'
            '<path d="M 100 82 C 112 100, 120 110, 117 128 C 115 144, '
            '108 152, 100 152 C 90 152, 83 143, 82 128 C 81 114, 92 98, '
            '100 82 Z" fill="#ffb020"/>')


def _event_explosion() -> str:
    # Explosionsstern
    points = []
    import math as _m
    for i in range(16):
        r = 78 if i % 2 == 0 else 34
        angle = _m.pi * i / 8
        points.append(f"{100 + r * _m.cos(angle):.0f},"
                      f"{100 + r * _m.sin(angle):.0f}")
    return (f'<polygon points="{" ".join(points)}" fill="#e03030" '
            f'stroke="#901010" stroke-width="4"/>')


def _event_ueberschwemmung() -> str:
    waves = []
    for y in (78, 108, 138):
        waves.append(
            f'<path d="M 30 {y} Q 55 {y - 22}, 80 {y} T 130 {y} T 180 {y}" '
            f'fill="none" stroke="#1060c0" stroke-width="7"/>')
    return "".join(waves)


def _event_truemmer() -> str:
    # Teilzerstörung/Trümmer: geborstenes Gebäude
    return ('<g stroke="#606060" stroke-width="5" fill="#c8c8c8">'
            '<path d="M 45 160 L 45 80 L 90 80 L 96 110 L 120 104 '
            'L 118 70 L 155 70 L 155 160 Z"/></g>'
            '<path d="M 70 160 L 84 124 L 100 140 L 116 118 L 130 160" '
            'fill="none" stroke="#606060" stroke-width="5"/>')


def _event_gefahrgut() -> str:
    # Gefahr durch Gefahrstoffe: Warnraute mit Ausrufezeichen
    return ('<path d="M 100 30 L 170 100 L 100 170 L 30 100 Z" '
            'fill="#ff9800" stroke="#a05000" stroke-width="5"/>'
            '<rect x="93" y="62" width="14" height="52" rx="6" '
            'fill="#000000"/>'
            '<circle cx="100" cy="136" r="9" fill="#000000"/>')


def _event_stromausfall() -> str:
    # Ausfall Elektrizität: durchgestrichener Blitz
    return ('<polygon points="115,25 62,110 95,110 82,175 140,85 105,85" '
            'fill="#f0c020" stroke="#806000" stroke-width="4"/>'
            '<line x1="40" y1="160" x2="160" y2="40" stroke="#000000" '
            'stroke-width="10" stroke-linecap="round"/>')


EVENTS = {
    "brand": ("Brand", _event_brand),
    "explosion": ("Explosion", _event_explosion),
    "ueberschwemmung": ("Überschwemmung", _event_ueberschwemmung),
    "truemmer": ("Trümmer / Teilzerstörung", _event_truemmer),
    "gefahrgut": ("Gefahrstoffe", _event_gefahrgut),
    "stromausfall": ("Ausfall Elektrizität", _event_stromausfall),
}


def build_event_svg(event: str) -> str:
    """Erzeugt das SVG eines Ereignis-/Gefahrensymbols (rahmenlos)."""
    _name, builder = EVENTS[event]
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" '
        f'height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">'
        f"{builder()}</svg>"
    )


def build_symbol_svg(role: str, affiliation: str = "freund",
                     domain: str = "land") -> str:
    """Erzeugt das SVG eines taktischen Zeichens (ohne Echelon).

    ``domain`` wählt die Rahmenform: "land" (Rechteck/Raute/…),
    "luft" (unten offener Bogen) oder "see" (Kreis). Die
    Größenkennzeichnung wird zur Laufzeit vom Editor gemäß gewählter
    Konvention ergänzt (Festlegung 10.6), nicht in die Symboldatei
    eingebrannt.
    """
    aff = AFFILIATIONS[affiliation]
    if domain == "luft":
        frame_svg, box = _frame_air(affiliation)
    elif domain == "see":
        frame_svg, box = _frame_sea(affiliation)
    else:
        frame_svg, box = FRAMES[aff["frame"]]()
    frame_svg = frame_svg.format(fill=aff["fill"], stroke=aff["stroke"])
    icon_svg = _icon(role, box, aff["stroke"])
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" '
        f'height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">'
        f"{frame_svg}{icon_svg}</svg>"
    )


# ----------------------------------------------------------------------
# BOS-Einheiten und -Fahrzeuge (vgl. DV 102: Feuerwehr rot, THW blau,
# Polizei grün, Rettungswesen weiß, Führung gelb, Katastrophenschutz
# orange; Grundzeichen: Einheit = Rechteck, Kraftfahrzeug = Rechteck
# mit nach unten gewölbter Unterseite)
# ----------------------------------------------------------------------
BOS_UNITS = {
    "feuerwehr": ("Feuerwehr", "#c00000", "#f8d0d0", "", "einheit"),
    "polizei": ("Polizei", "#006e3c", "#cfe8d9", "", "einheit"),
    "rettungsdienst": ("Rettungsdienst", "#404040", "#ffffff", "kreuz",
                       "einheit"),
    "wasserrettung": ("Wasserrettung / DLRG", "#0060a0", "#ffffff",
                      "wellen", "einheit"),
    "bos_fuehrung": ("Führung (BOS)", "#8a7000", "#f5e97a", "flagge",
                     "einheit"),
    "katastrophenschutz": ("Katastrophenschutz", "#c05000", "#fbdfc4", "",
                           "einheit"),
    "seg": ("Schnelleinsatzgruppe (SEG)", "#404040", "#ffffff",
            "kreuz+SEG", "einheit"),
    "seg_verpflegung": ("SEG Verpflegung", "#404040", "#ffffff",
                        "topf+SEG", "einheit"),
    "seg_drohne": ("SEG Drohne", "#404040", "#ffffff",
                   "drohne+SEG", "einheit"),
    "lf": ("Löschfahrzeug (LF)", "#c00000", "#f8d0d0", "text:LF",
           "fahrzeug"),
    "tlf": ("Tanklöschfahrzeug (TLF)", "#c00000", "#f8d0d0", "text:TLF",
            "fahrzeug"),
    "hlf": ("Hilfeleistungslöschfahrzeug (HLF)", "#c00000", "#f8d0d0",
            "text:HLF", "fahrzeug"),
    "dlk": ("Drehleiter (DLK)", "#c00000", "#f8d0d0", "text:DLK",
            "fahrzeug"),
    "gw": ("Gerätewagen (GW)", "#c00000", "#f8d0d0", "text:GW",
           "fahrzeug"),
    "mtw": ("Mannschaftstransportwagen (MTW)", "#c00000", "#f8d0d0",
            "text:MTW", "fahrzeug"),
    "rtw": ("Rettungswagen (RTW)", "#404040", "#ffffff", "kreuz+RTW",
            "fahrzeug"),
    "ktw": ("Krankentransportwagen (KTW)", "#404040", "#ffffff",
            "kreuz+KTW", "fahrzeug"),
    "nef": ("Notarzteinsatzfahrzeug (NEF)", "#404040", "#ffffff",
            "kreuz+NEF", "fahrzeug"),
    "elw": ("Einsatzleitwagen (ELW)", "#c00000", "#f8d0d0",
            "flagge+ELW", "fahrzeug"),
}


def _cross_white_red(cx: float, cy: float, a: float) -> str:
    """Weißes Kreuz mit rotem Rahmen (Rettungswesen)."""
    t = a * 0.34
    pts = [(cx - t, cy - a), (cx + t, cy - a), (cx + t, cy - t),
           (cx + a, cy - t), (cx + a, cy + t), (cx + t, cy + t),
           (cx + t, cy + a), (cx - t, cy + a), (cx - t, cy + t),
           (cx - a, cy + t), (cx - a, cy - t), (cx - t, cy - t)]
    d = "M " + " L ".join(f"{px:.1f} {py:.1f}" for px, py in pts) + " Z"
    return (f'<path d="{d}" fill="#ffffff" stroke="#c00000" '
            f'stroke-width="{STROKE * 0.9}"/>')


def build_bos_svg(unit: str) -> str:
    """Erzeugt das SVG einer BOS-Einheit bzw. eines BOS-Fahrzeugs."""
    _name, stroke, fill, icon, form = BOS_UNITS[unit]
    x, y, w, h = 30.0, 55.0, 140.0, 90.0
    cx, cy = x + w / 2, y + h / 2
    if form == "fahrzeug":
        # Kraftfahrzeug: Rechteck mit gewölbter Unterseite
        parts = [f'<path d="M {x} {y} L {x + w} {y} L {x + w} {y + h * 0.8} '
                 f'Q {cx} {y + h * 1.25}, {x} {y + h * 0.8} Z" '
                 f'fill="{fill}" stroke="{stroke}" stroke-width="{STROKE}"/>']
    else:
        parts = [f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
                 f'fill="{fill}" stroke="{stroke}" '
                 f'stroke-width="{STROKE}"/>']

    text = ""
    if "+" in icon:
        icon, text = icon.split("+", 1)
    elif icon.startswith("text:"):
        icon, text = "", icon[5:]

    if icon == "kreuz":
        a = h * 0.24 if text else h * 0.28
        kcy = cy - h * 0.08 if text else cy
        parts.append(_cross_white_red(cx, kcy, a))
    elif icon == "topf":
        # Verpflegung: Kochtopf mit Deckel
        r = w * 0.14
        kcy = cy - h * 0.10
        parts.append(
            f'<path d="M {cx - r} {kcy - r * 0.3} L {cx - r} {kcy + r * 0.2} '
            f'A {r} {r * 0.8} 0 0 0 {cx + r} {kcy + r * 0.2} '
            f'L {cx + r} {kcy - r * 0.3} Z" fill="none" stroke="{stroke}" '
            f'stroke-width="{STROKE * 0.9}"/>'
            f'<line x1="{cx - r * 1.35}" y1="{kcy - r * 0.3}" '
            f'x2="{cx + r * 1.35}" y2="{kcy - r * 0.3}" stroke="{stroke}" '
            f'stroke-width="{STROKE * 0.9}"/>')
    elif icon == "drohne":
        # Drohne: abgewinkelte Tragfläche (UAV-Zeichen)
        kcy = cy - h * 0.10
        parts.append(
            f'<path d="M {cx - w * 0.18} {kcy - h * 0.08} L {cx} '
            f'{kcy + h * 0.10} L {cx + w * 0.18} {kcy - h * 0.08}" '
            f'fill="none" stroke="{stroke}" '
            f'stroke-width="{STROKE * 1.4}"/>')
    elif icon == "flagge":
        fx = x + w * 0.16 if text else cx
        parts.append(f'<path d="M {fx} {y + h * 0.15} L {fx} '
                     f'{y + h * 0.75} M {fx} {y + h * 0.15} '
                     f'L {fx + w * 0.18} {y + h * 0.28} L {fx} '
                     f'{y + h * 0.41}" stroke="{stroke}" '
                     f'stroke-width="{STROKE}" fill="none"/>')
    elif icon == "wellen":
        for dy in (-h * 0.10, h * 0.14):
            parts.append(
                f'<path d="M {x + w * 0.18} {cy + dy} '
                f'Q {x + w * 0.31} {cy + dy - h * 0.16}, '
                f'{x + w * 0.44} {cy + dy} T {x + w * 0.70} {cy + dy} '
                f'T {x + w * 0.86} {cy + dy}" fill="none" '
                f'stroke="{stroke}" stroke-width="{STROKE}"/>')

    if text:
        if icon in ("kreuz", "topf", "drohne"):
            tx, ty, size = cx, y + h * 0.80, h * 0.26
        elif icon == "flagge":
            tx, ty, size = cx + w * 0.14, cy + h * 0.05, h * 0.34
        else:
            tx, ty, size = cx, cy, h * 0.40
        parts.append(f'<text x="{tx:.0f}" y="{ty:.0f}" '
                     f'font-family="sans-serif" font-size="{size:.0f}" '
                     f'font-weight="bold" fill="{stroke}" '
                     f'text-anchor="middle" '
                     f'dominant-baseline="central">{text}</text>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" '
        f'height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">'
        f'{"".join(parts)}</svg>'
    )


# ----------------------------------------------------------------------
# Windrichtungspfeile mit meteorologischen Fiedern je Windstärke
# (halbe Fieder ≈ 5 kn, ganze Fieder ≈ 10 kn, Wimpel ≈ 50 kn)
# ----------------------------------------------------------------------
BFT_KNOTS = {1: 2, 2: 5, 3: 10, 4: 15, 5: 20, 6: 25, 7: 30, 8: 35,
             9: 45, 10: 50, 11: 55, 12: 65}


def build_wind_svg(bft: int) -> str:
    """Windpfeil mit Fiedern für die angegebene Windstärke (Bft).

    Pfeilspitze zeigt in die Richtung, in die der Wind weht; die
    Fiedern sitzen am Schaftende (Luv-Seite). Im Editor wird der
    Pfeil über die Drehung auf die tatsächliche Windrichtung gestellt.
    """
    kn = BFT_KNOTS[max(1, min(12, bft))]
    pennants, rest = divmod(kn, 50)
    fulls, rest = divmod(rest, 10)
    half = rest >= 5

    y = 100.0
    parts = [
        f'<line x1="28" y1="{y}" x2="176" y2="{y}" stroke="#000000" '
        f'stroke-width="6"/>',
        f'<polygon points="170,{y - 14:.0f} 194,{y:.0f} 170,{y + 14:.0f}" '
        f'fill="#000000"/>',
    ]
    bx = 28.0
    for _ in range(pennants):
        parts.append(f'<polygon points="{bx:.0f},{y:.0f} '
                     f'{bx + 9:.0f},{y - 34:.0f} {bx + 20:.0f},{y:.0f}" '
                     f'fill="#000000"/>')
        bx += 24
    for _ in range(fulls):
        parts.append(f'<line x1="{bx:.0f}" y1="{y:.0f}" '
                     f'x2="{bx + 11:.0f}" y2="{y - 34:.0f}" '
                     f'stroke="#000000" stroke-width="5"/>')
        bx += 15
    if half:
        if fulls == 0 and pennants == 0:
            bx += 10   # halbe Fieder nie ganz am Schaftende
        parts.append(f'<line x1="{bx:.0f}" y1="{y:.0f}" '
                     f'x2="{bx + 6:.0f}" y2="{y - 18:.0f}" '
                     f'stroke="#000000" stroke-width="5"/>')
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W:.0f}" '
        f'height="{H:.0f}" viewBox="0 0 {W:.0f} {H:.0f}">'
        f'{"".join(parts)}</svg>'
    )


def generate_set(target: str | Path) -> int:
    """Erzeugt den Startersatz in der Lastenheft-Ordnerstruktur (Kap. 8).

    Liefert die Anzahl erzeugter Symboldateien.
    """
    target = Path(target)
    count = 0
    for category, roles in ROLES.items():
        cat_dir = target / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        for role in roles:
            for affiliation in AFFILIATIONS:
                # THW-Ordner: nur eigene Kräfte (BOS-Lagen)
                if category == "THW" and affiliation != "freund":
                    continue
                stem = f"{role}_{affiliation}"
                (cat_dir / f"{stem}.svg").write_text(
                    build_symbol_svg(role, affiliation), encoding="utf-8")
                meta = {
                    "name": f"{ROLE_NAMES[role]} ({AFFILIATION_NAMES[affiliation]})",
                    "kategorie": category,
                    "standardgroesse": "",
                }
                (cat_dir / f"{stem}.json").write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2),
                    encoding="utf-8")
                count += 1

    # Luft- und Seefahrzeuge (eigene Rahmenformen)
    for domain, roles in DOMAIN_ROLES.items():
        cat_dir = target / domain
        cat_dir.mkdir(parents=True, exist_ok=True)
        for role in roles:
            for affiliation in AFFILIATIONS:
                stem = f"{role}_{affiliation}"
                (cat_dir / f"{stem}.svg").write_text(
                    build_symbol_svg(role, affiliation, domain),
                    encoding="utf-8")
                meta = {
                    "name": f"{ROLE_NAMES[role]} ({AFFILIATION_NAMES[affiliation]})",
                    "kategorie": domain,
                    "standardgroesse": "",
                }
                (cat_dir / f"{stem}.json").write_text(
                    json.dumps(meta, ensure_ascii=False, indent=2),
                    encoding="utf-8")
                count += 1

    # BOS-Einheiten (Feuerwehr, Polizei, Rettungsdienst usw.)
    bos_dir = target / "BOS"
    bos_dir.mkdir(parents=True, exist_ok=True)
    for unit, (name, *_style) in BOS_UNITS.items():
        (bos_dir / f"{unit}.svg").write_text(
            build_bos_svg(unit), encoding="utf-8")
        meta = {"name": name, "kategorie": "BOS", "standardgroesse": ""}
        (bos_dir / f"{unit}.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8")
        count += 1

    # Ereignis-/Gefahrensymbole (rahmenlos, für BOS-/THW-Lagen)
    event_dir = target / "ereignisse"
    event_dir.mkdir(parents=True, exist_ok=True)
    for event, (name, _builder) in EVENTS.items():
        (event_dir / f"{event}.svg").write_text(
            build_event_svg(event), encoding="utf-8")
        meta = {"name": name, "kategorie": "Ereignisse",
                "standardgroesse": ""}
        (event_dir / f"{event}.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8")
        count += 1

    # Windrichtungspfeile mit Fiedern je Windstärke (1–12 Bft)
    for bft in range(1, 13):
        stem = f"wind_{bft:02d}bft"
        (event_dir / f"{stem}.svg").write_text(
            build_wind_svg(bft), encoding="utf-8")
        meta = {"name": f"Windrichtung ({bft} Bft)",
                "kategorie": "Ereignisse", "standardgroesse": ""}
        (event_dir / f"{stem}.json").write_text(
            json.dumps(meta, ensure_ascii=False, indent=2),
            encoding="utf-8")
        count += 1
    return count


def main() -> int:
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "symbole"
    count = generate_set(target)
    print(f"{count} Symbole nach {target}/ erzeugt.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
