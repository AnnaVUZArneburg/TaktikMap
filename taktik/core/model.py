"""Datenmodell der Lagekarte (Qt-frei).

Trennung von UI und Kartenlogik: Dieses Modul beschreibt den
serialisierbaren Zustand eines Projekts. Die UI-Schicht
(:mod:`taktik.ui`) bildet diese Objekte auf QGraphicsItems ab.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field


def new_id() -> str:
    return uuid.uuid4().hex


# Vollständige Echelon-Leiter nach NATO APP-6 (vgl. Military Symbology
# Guide); umfasst die im Lastenheft (3.5) geforderten Stufen Trupp bis
# Großverband sowie die ausgeschriebenen Verbandsebenen.
ECHELONS = [
    "",  # keine Kennzeichnung
    "Trupp",
    "Gruppe",
    "Staffel",
    "Zug",
    "Kompanie / Einheit",
    "Bataillon",
    "Regiment",
    "Brigade",
    "Division",
    "Korps",
    "Armee",
    "Heeresgruppe",
    "Theater / Region",
]

# Aliasse der Lastenheft-Namen (und älterer Projektdateien) auf die
# ausgeschriebenen Ebenen.
ECHELON_ALIASES = {
    "Verband": "Bataillon",
    "Großverband": "Brigade",
}

CONVENTIONS = ["BW", "THW"]


@dataclass
class Layer:
    """Eine Ebene der Lagekarte."""

    id: str = field(default_factory=new_id)
    name: str = "Ebene"
    visible: bool = True

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "visible": self.visible}

    @classmethod
    def from_dict(cls, d: dict) -> "Layer":
        return cls(id=d["id"], name=d.get("name", "Ebene"),
                   visible=d.get("visible", True))


@dataclass
class MapImage:
    """Eine als Hintergrund geladene Karte (PNG/JPG/TIFF/SVG).

    Die Drehung wird nicht-destruktiv als Winkel gespeichert
    (Festlegung 10.5 im Lastenheft); die Quelldatei bleibt unverändert.
    """

    id: str = field(default_factory=new_id)
    asset: str = ""            # Pfad innerhalb des Projekts (assets/...)
    source_name: str = ""      # ursprünglicher Dateiname (Anzeige)
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0      # Grad, im Uhrzeigersinn
    scale: float = 1.0
    z: float = -100.0          # Karten liegen unter den Zeichen

    def to_dict(self) -> dict:
        return {
            "id": self.id, "asset": self.asset, "source_name": self.source_name,
            "x": self.x, "y": self.y, "rotation": self.rotation,
            "scale": self.scale, "z": self.z,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MapImage":
        return cls(id=d["id"], asset=d["asset"],
                   source_name=d.get("source_name", ""),
                   x=d.get("x", 0.0), y=d.get("y", 0.0),
                   rotation=d.get("rotation", 0.0),
                   scale=d.get("scale", 1.0), z=d.get("z", -100.0))


@dataclass
class Symbol:
    """Ein auf der Karte platziertes taktisches Zeichen."""

    id: str = field(default_factory=new_id)
    asset: str = ""            # Pfad innerhalb des Projekts (assets/...)
    source_name: str = ""
    name: str = ""             # Anzeigename (aus Metadaten oder Dateiname)
    layer_id: str = ""
    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    scale: float = 1.0
    z: float = 0.0
    echelon: str = ""          # Größenkennzeichnung, siehe ECHELONS
    label: str = ""            # freie Beschriftung

    def to_dict(self) -> dict:
        return {
            "id": self.id, "asset": self.asset, "source_name": self.source_name,
            "name": self.name, "layer_id": self.layer_id,
            "x": self.x, "y": self.y, "rotation": self.rotation,
            "scale": self.scale, "z": self.z,
            "echelon": self.echelon, "label": self.label,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Symbol":
        return cls(id=d["id"], asset=d["asset"],
                   source_name=d.get("source_name", ""),
                   name=d.get("name", ""), layer_id=d.get("layer_id", ""),
                   x=d.get("x", 0.0), y=d.get("y", 0.0),
                   rotation=d.get("rotation", 0.0), scale=d.get("scale", 1.0),
                   z=d.get("z", 0.0), echelon=d.get("echelon", ""),
                   label=d.get("label", ""))


ARROW_STYLES = ["linie", "breit"]
# Linienmuster: glatt, Zinnen (Kastenmuster, z. B. Stellung/Grenze),
# Welle (z. B. Gewässer/Sperre) sowie Strichmuster mit Querstrichen
# im Verhältnis Abstand : Länge = 1:1 (einseitig oben/unten bzw.
# „Igel" mit T-Strichen)
LINE_PATTERNS = ["glatt", "zinnen", "welle",
                 "striche_oben", "striche_unten", "igel"]


@dataclass
class Arrow:
    """Ein Pfeil auf der Karte (Bewegungs-/Angriffsrichtung usw.).

    Definiert durch eine Punktfolge in Szenenkoordinaten (mindestens
    zwei Punkte); alle Stützpunkte sind im Editor einzeln verschiebbar.
    ``curved`` glättet die Linienführung, ``style`` "breit" zeichnet
    einen breiten Umrisspfeil (Angriffs-/Vorstoßrichtung).
    """

    id: str = field(default_factory=new_id)
    layer_id: str = ""
    points: list = field(default_factory=lambda: [[0.0, 0.0], [100.0, 0.0]])
    color: str = "#0060a0"     # Standard: blau (eigene Kräfte)
    width: float = 4.0
    dashed: bool = False       # gestrichelt z. B. für geplante Bewegung
    curved: bool = False       # glatte Kurve durch die Stützpunkte
    style: str = "linie"       # "linie" oder "breit" (Umrisspfeil)
    pattern: str = "glatt"     # Linienmuster, siehe LINE_PATTERNS
    head: str = "spitze"       # "spitze" (Pfeilspitze) oder "keine" (Linie)
    label: str = ""
    z: float = 10.0            # Pfeile über den Zeichen

    def to_dict(self) -> dict:
        return {
            "id": self.id, "layer_id": self.layer_id,
            "points": [[float(x), float(y)] for x, y in self.points],
            "color": self.color, "width": self.width,
            "dashed": self.dashed, "curved": self.curved,
            "style": self.style, "pattern": self.pattern, "head": self.head,
            "label": self.label, "z": self.z,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Arrow":
        if "points" in d:
            points = [[float(x), float(y)] for x, y in d["points"]]
        else:
            # Abwärtskompatibilität: frühere Version mit x1/y1/x2/y2
            points = [[d.get("x1", 0.0), d.get("y1", 0.0)],
                      [d.get("x2", 100.0), d.get("y2", 0.0)]]
        style = d.get("style", "linie")
        if style not in ARROW_STYLES:
            style = "linie"
        pattern = d.get("pattern", "glatt")
        if pattern not in LINE_PATTERNS:
            pattern = "glatt"
        head = d.get("head", "spitze")
        if head not in ("spitze", "keine"):
            head = "spitze"
        return cls(id=d["id"], layer_id=d.get("layer_id", ""),
                   points=points, color=d.get("color", "#0060a0"),
                   width=d.get("width", 4.0), dashed=d.get("dashed", False),
                   curved=d.get("curved", False), style=style,
                   pattern=pattern, head=head,
                   label=d.get("label", ""), z=d.get("z", 10.0))


@dataclass
class Area:
    """Eine Flächenmarkierung (Schadenskonto, Einsatzabschnitt usw.).

    Geschlossenes Polygon in Szenenkoordinaten mit transparenter
    Füllung; alle Eckpunkte sind im Editor einzeln verschiebbar.
    """

    id: str = field(default_factory=new_id)
    layer_id: str = ""
    points: list = field(default_factory=list)
    color: str = "#c00000"     # Standard: rot (Schadensgebiet)
    width: float = 3.0         # Randbreite
    dashed: bool = True        # BOS-üblich: gestrichelte Begrenzung
    label: str = ""
    z: float = -50.0           # Flächen zwischen Karte und Zeichen

    def to_dict(self) -> dict:
        return {
            "id": self.id, "layer_id": self.layer_id,
            "points": [[float(x), float(y)] for x, y in self.points],
            "color": self.color, "width": self.width,
            "dashed": self.dashed, "label": self.label, "z": self.z,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Area":
        return cls(id=d["id"], layer_id=d.get("layer_id", ""),
                   points=[[float(x), float(y)] for x, y in
                           d.get("points", [])],
                   color=d.get("color", "#c00000"),
                   width=d.get("width", 3.0), dashed=d.get("dashed", True),
                   label=d.get("label", ""), z=d.get("z", -50.0))


@dataclass
class Project:
    """Gesamtzustand eines Lagekarten-Projekts."""

    version: int = 1
    title: str = "Neue Lagekarte"
    convention: str = "BW"     # "BW" oder "THW" (Festlegung 10.6)
    maps: list[MapImage] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)
    arrows: list[Arrow] = field(default_factory=list)
    areas: list[Area] = field(default_factory=list)
    layers: list[Layer] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.layers:
            self.layers.append(Layer(name="Lage"))

    @property
    def default_layer(self) -> Layer:
        return self.layers[0]

    def layer_by_id(self, layer_id: str) -> Layer | None:
        for layer in self.layers:
            if layer.id == layer_id:
                return layer
        return None

    def to_dict(self) -> dict:
        return {
            "version": self.version,
            "title": self.title,
            "convention": self.convention,
            "layers": [l.to_dict() for l in self.layers],
            "maps": [m.to_dict() for m in self.maps],
            "symbols": [s.to_dict() for s in self.symbols],
            "arrows": [a.to_dict() for a in self.arrows],
            "areas": [a.to_dict() for a in self.areas],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Project":
        project = cls(
            version=d.get("version", 1),
            title=d.get("title", "Lagekarte"),
            convention=d.get("convention", "BW"),
            layers=[Layer.from_dict(x) for x in d.get("layers", [])],
            maps=[MapImage.from_dict(x) for x in d.get("maps", [])],
            symbols=[Symbol.from_dict(x) for x in d.get("symbols", [])],
            arrows=[Arrow.from_dict(x) for x in d.get("arrows", [])],
            areas=[Area.from_dict(x) for x in d.get("areas", [])],
        )
        if project.convention not in CONVENTIONS:
            project.convention = "BW"
        return project
