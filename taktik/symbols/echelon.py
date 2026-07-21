"""Größenkennzeichnungen (Echelons) nach BW- und THW-Konvention.

Festlegung 10.6 im Lastenheft: Es gibt zwei getrennte, im UI
umschaltbare Konventionssätze. Die Kennzeichnung wird mittig
oberhalb des taktischen Zeichens ergänzt.

Der BW-Satz folgt der NATO-APP-6-Echelon-Leiter (vgl. den im
Lastenheft referenzierten Military Symbology Guide):

    Trupp/Team Ø · Gruppe ● · Staffel ●● · Zug ●●● · Kompanie I ·
    Bataillon II · Regiment III · Brigade X · Division XX ·
    Korps XXX · Armee XXXX · Heeresgruppe XXXXX

Die Zuordnung ist bewusst datengetrieben gehalten, damit sie ohne
Codeänderung an dienstliche Vorgaben angepasst werden kann. Jede
Kennzeichnung ist eine Folge von Elementen:

* ``dot``       – ausgefüllter Punkt
* ``ring``      – nicht ausgefüllter Kreis
* ``ringslash`` – durchgestrichener Kreis Ø (NATO: Trupp/Team)
* ``bar``       – senkrechter Strich
* ``x``         – Andreaskreuz (X)
"""

from __future__ import annotations

from taktik.core.model import ECHELON_ALIASES

# NATO APP-6 / Bundeswehr
BW = {
    "Trupp": ["ringslash"],
    "Gruppe": ["dot"],
    "Staffel": ["dot", "dot"],
    "Zug": ["dot", "dot", "dot"],
    "Kompanie / Einheit": ["bar"],
    "Bataillon": ["bar", "bar"],
    "Regiment": ["bar", "bar", "bar"],
    "Brigade": ["x"],
    "Division": ["x", "x"],
    "Korps": ["x", "x", "x"],
    "Armee": ["x", "x", "x", "x"],
    "Heeresgruppe": ["x", "x", "x", "x", "x"],
    "Theater / Region": ["x", "x", "x", "x", "x", "x"],
}

# THW / BOS (Punkte für Teileinheiten, Striche für Einheiten/Verbände).
# Standardbelegung, per Datenpflege anpassbar; militärische
# Verbandsebenen oberhalb fallen auf den BW-Satz zurück.
THW = {
    "Trupp": ["dot"],
    "Staffel": ["dot", "dot"],
    "Gruppe": ["dot", "dot", "dot"],
    "Zug": ["bar"],
    "Kompanie / Einheit": ["bar", "bar"],
    "Bataillon": ["bar", "bar", "bar"],
    "Regiment": ["bar", "bar", "bar"],
    "Brigade": ["x"],
}

CONVENTION_SETS = {"BW": BW, "THW": THW}


def marks_for(convention: str, echelon: str) -> list[str]:
    """Liefert die Zeichenfolge der Kennzeichnung (leer = keine).

    Lastenheft-Namen („Verband“, „Großverband“) und ältere
    Projektdateien werden über Aliasse aufgelöst; im THW-Satz nicht
    definierte Ebenen fallen auf den BW-/NATO-Satz zurück.
    """
    echelon = ECHELON_ALIASES.get(echelon, echelon)
    marks = CONVENTION_SETS.get(convention, BW).get(echelon)
    if marks is None:
        marks = BW.get(echelon, [])
    return marks


def echelon_svg_fragment(marks: list[str], center_x: float, baseline_y: float,
                         unit: float = 10.0, stroke: str = "#000000") -> str:
    """SVG-Fragment einer Kennzeichnung, zentriert über ``center_x``.

    ``baseline_y`` ist die vertikale Mitte der Kennzeichnung,
    ``unit`` skaliert die Elementgröße.
    """
    if not marks:
        return ""
    spacing = unit * 1.6
    total = spacing * (len(marks) - 1)
    x = center_x - total / 2.0
    parts: list[str] = []
    for mark in marks:
        if mark == "dot":
            parts.append(
                f'<circle cx="{x:.1f}" cy="{baseline_y:.1f}" r="{unit * 0.45:.1f}" '
                f'fill="{stroke}"/>')
        elif mark in ("ring", "ringslash"):
            r = unit * 0.45
            parts.append(
                f'<circle cx="{x:.1f}" cy="{baseline_y:.1f}" r="{r:.1f}" '
                f'fill="none" stroke="{stroke}" stroke-width="{unit * 0.18:.1f}"/>')
            if mark == "ringslash":
                d = r * 1.35
                parts.append(
                    f'<line x1="{x - d:.1f}" y1="{baseline_y + d:.1f}" '
                    f'x2="{x + d:.1f}" y2="{baseline_y - d:.1f}" '
                    f'stroke="{stroke}" stroke-width="{unit * 0.18:.1f}"/>')
        elif mark == "bar":
            parts.append(
                f'<line x1="{x:.1f}" y1="{baseline_y - unit * 0.7:.1f}" '
                f'x2="{x:.1f}" y2="{baseline_y + unit * 0.7:.1f}" '
                f'stroke="{stroke}" stroke-width="{unit * 0.22:.1f}"/>')
        elif mark == "x":
            d = unit * 0.6
            parts.append(
                f'<path d="M {x - d:.1f} {baseline_y - d:.1f} '
                f'L {x + d:.1f} {baseline_y + d:.1f} '
                f'M {x - d:.1f} {baseline_y + d:.1f} '
                f'L {x + d:.1f} {baseline_y - d:.1f}" '
                f'stroke="{stroke}" stroke-width="{unit * 0.22:.1f}" fill="none"/>')
        x += spacing
    return "".join(parts)
