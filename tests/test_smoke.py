"""Smoke-Tests gegen die Abnahmekriterien (Kap. 9 des Lastenhefts).

Laufen headless (Qt offscreen)::

    QT_QPA_PLATFORM=offscreen python -m pytest tests/ -v
"""

import json
import os
import zipfile
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPointF  # noqa: E402
from PySide6.QtGui import QImage, QPainter  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from taktik.core.model import Project, Symbol  # noqa: E402
from taktik.core.project_io import ProjectStore  # noqa: E402
from taktik.symbols import echelon  # noqa: E402
from taktik.symbols.generator import build_symbol_svg, generate_set  # noqa: E402
from taktik.symbols.library import SymbolLibrary  # noqa: E402


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def symbol_dir(tmp_path):
    target = tmp_path / "symbole"
    generate_set(target)
    return target


def _make_png(path: Path, size=(64, 48)) -> Path:
    image = QImage(size[0], size[1], QImage.Format_ARGB32)
    image.fill(0xFF88AA55)
    image.save(str(path), "PNG")
    return path


# ----------------------------------------------------------------------
# Symbolgenerator & Echelon-Konventionen
# ----------------------------------------------------------------------
def test_generator_erzeugt_svg_und_metadaten(symbol_dir):
    svgs = list(symbol_dir.rglob("*.svg"))
    assert len(svgs) >= 30
    for svg in svgs:
        assert svg.with_suffix(".json").exists()
    sample = build_symbol_svg("infanterie", "feind")
    assert sample.startswith("<svg") and "path" in sample


def test_generator_ereignisse_und_thw_fachzeichen(symbol_dir):
    from taktik.symbols.generator import EVENTS, build_event_svg

    for event in ("brand", "ueberschwemmung", "stromausfall"):
        assert event in EVENTS
        assert build_event_svg(event).startswith("<svg")
        assert (symbol_dir / "ereignisse" / f"{event}.svg").exists()
    for role in ("ortung", "raeumen", "pumpen", "beleuchtung"):
        assert (symbol_dir / "THW" / f"{role}_freund.svg").exists()
    # Stromausfall: durchgestrichener Blitz (Blitz + Schrägstrich)
    svg = build_event_svg("stromausfall")
    assert "polygon" in svg and "line" in svg


def test_generator_luft_see_bos_und_wind(symbol_dir):
    from taktik.symbols.generator import (BOS_UNITS, build_bos_svg,
                                          build_symbol_svg, build_wind_svg)

    # Luft- und Seefahrzeuge mit eigenen Rahmenformen
    for role in ("flugzeug", "hubschrauber", "uav"):
        for aff in ("freund", "feind", "neutral", "unbekannt"):
            assert (symbol_dir / "luft" / f"{role}_{aff}.svg").exists()
    for role in ("kriegsschiff", "uboot", "fregatte"):
        assert (symbol_dir / "see" / f"{role}_freund.svg").exists()
    assert "path" in build_symbol_svg("hubschrauber", "freund", "luft")
    assert "circle" in build_symbol_svg("kriegsschiff", "freund", "see")

    # BOS-Einheiten und -Fahrzeuge (Feuerwehr, Polizei, LF, RTW, …)
    for unit in ("feuerwehr", "polizei", "rettungsdienst",
                 "wasserrettung", "lf", "tlf", "hlf", "dlk", "gw",
                 "mtw", "rtw", "ktw", "nef", "elw", "seg",
                 "seg_verpflegung", "seg_drohne"):
        assert unit in BOS_UNITS
        assert build_bos_svg(unit).startswith("<svg")
        assert (symbol_dir / "BOS" / f"{unit}.svg").exists()
    # Rettungswesen: weißes Kreuz mit rotem Rahmen
    rtw = build_bos_svg("rtw")
    assert 'fill="#ffffff" stroke="#c00000"' in rtw and "RTW" in rtw
    # Fahrzeuge nutzen das Kfz-Grundzeichen (gewölbte Unterseite)
    assert "Q " in build_bos_svg("lf") and "LF" in build_bos_svg("lf")
    # Luft: Bomber, See: Flugzeugträger
    assert (symbol_dir / "luft" / "bomber_freund.svg").exists()
    assert (symbol_dir / "see" / "flugzeugtraeger_freund.svg").exists()

    # Windpfeile: Fiedern nehmen mit der Windstärke zu
    for bft in range(1, 13):
        assert (symbol_dir / "ereignisse" / f"wind_{bft:02d}bft.svg").exists()
    leicht = build_wind_svg(2)
    sturm = build_wind_svg(12)
    assert sturm.count("<line") > leicht.count("<line") or \
        sturm.count("<polygon") > leicht.count("<polygon")
    # Bft 10+ nutzt Wimpel (gefülltes Dreieck zusätzlich zur Spitze)
    assert build_wind_svg(10).count("<polygon") >= 2


def test_tutorial_dialog_und_maskottchen(app):
    from taktik.ui.tutorial import (GUIDE_NAME, GUIDE_SVG, STEPS,
                                    TutorialDialog)

    # Maskottchen „Safety" bleibt erhalten
    assert GUIDE_NAME == "Safety"
    assert "<svg" in GUIDE_SVG and "Schild" in GUIDE_SVG  # Kommentar erhalten

    # Inhalt auf die Lagekarte angepasst, keine Alt-Projekt-Begriffe mehr
    joined = " ".join(s.title + " " + s.body for s in STEPS)
    assert "Spielwelt" not in joined and "Infrastruktur" not in joined
    for term in ("Karte", "Zeichen", "Größenkennzeichnung",
                 "Konvention", "Pfeil", ".taktik"):
        assert term in joined, term

    dialog = TutorialDialog()
    assert not dialog._guide_pixmap().isNull()   # Maskottchen rendert
    # durch alle Schritte navigieren
    for _ in range(len(STEPS) + 2):
        dialog._on_next()
    assert dialog.show_on_startup() is True


def test_ebenen_reihenfolge_stapelt_objekte(app):
    from taktik.core.model import Layer
    from taktik.ui.commands import AddSymbolCommand
    from taktik.ui.scene import MapScene
    from taktik.symbols.library import SymbolLibrary

    store = ProjectStore()
    scene = MapScene(store)
    lib = SymbolLibrary()
    lib.scan(Path(__file__).resolve().parent.parent / "symbole")
    entry = lib.entries[0]

    hinten = store.project.default_layer
    hinten.name = "Hinten"
    vorne = Layer(name="Vorne")
    store.project.layers.append(vorne)

    item_a = scene.create_symbol_item(entry, QPointF(0, 0))
    scene.undo_stack.push(AddSymbolCommand(scene, item_a))
    item_b = scene.create_symbol_item(entry, QPointF(10, 10))
    item_b.model.layer_id = vorne.id
    scene.undo_stack.push(AddSymbolCommand(scene, item_b))

    # Listenreihenfolge: hinten (Index 0) liegt vorn → höheres z
    scene.apply_layer_order()
    assert item_a.zValue() > item_b.zValue()

    # Reihenfolge umdrehen (wie per Drag-and-Drop im Ebenen-Panel)
    store.project.layers.reverse()
    scene.apply_layer_order()
    assert item_b.zValue() > item_a.zValue()
    store.cleanup()


def test_echelon_konventionen_getrennt():
    assert echelon.marks_for("BW", "Zug") == ["dot", "dot", "dot"]
    assert echelon.marks_for("THW", "Zug") == ["bar"]
    assert echelon.marks_for("BW", "") == []
    for convention in ("BW", "THW"):
        for name in ("Trupp", "Gruppe", "Staffel", "Zug",
                     "Kompanie / Einheit", "Verband", "Großverband"):
            assert echelon.marks_for(convention, name), (convention, name)


def test_echelon_nato_leiter_vollstaendig():
    """Vollständige APP-6-Leiter nach Military Symbology Guide."""
    assert echelon.marks_for("BW", "Trupp") == ["ringslash"]        # Ø
    assert echelon.marks_for("BW", "Kompanie / Einheit") == ["bar"]  # I
    assert echelon.marks_for("BW", "Bataillon") == ["bar", "bar"]    # II
    assert echelon.marks_for("BW", "Regiment") == ["bar"] * 3        # III
    assert echelon.marks_for("BW", "Brigade") == ["x"]               # X
    assert echelon.marks_for("BW", "Division") == ["x", "x"]         # XX
    assert echelon.marks_for("BW", "Korps") == ["x"] * 3             # XXX
    assert echelon.marks_for("BW", "Armee") == ["x"] * 4             # XXXX
    assert echelon.marks_for("BW", "Heeresgruppe") == ["x"] * 5      # XXXXX
    # Aliasse aus Lastenheft/älteren Projektdateien
    assert echelon.marks_for("BW", "Verband") == ["bar", "bar"]
    assert echelon.marks_for("BW", "Großverband") == ["x"]
    # THW: militärische Ebenen fallen auf NATO-Satz zurück
    assert echelon.marks_for("THW", "Division") == ["x", "x"]
    # SVG-Fragment für Ø rendert Kreis + Schrägstrich
    frag = echelon.echelon_svg_fragment(["ringslash"], 100, 20)
    assert "circle" in frag and "line" in frag


# ----------------------------------------------------------------------
# Bibliothek: Zeichen aus Ordner einlesen (Abnahmekriterium)
# ----------------------------------------------------------------------
def test_bibliothek_liest_ordner_mit_metadaten(symbol_dir):
    lib = SymbolLibrary()
    count = lib.scan(symbol_dir)
    assert count >= 30
    assert "THW" in lib.categories()
    hits = lib.search(text="sanität")
    assert hits and all("Sanität" in h.name for h in hits)
    key = hits[0].key
    assert lib.toggle_favorite(key) is True
    assert lib.search(favorites_only=True)[0].key == key


# ----------------------------------------------------------------------
# Projekt speichern und erneut laden (Abnahmekriterium)
# ----------------------------------------------------------------------
def test_projekt_speichern_und_laden(tmp_path, symbol_dir):
    store = ProjectStore()
    map_png = _make_png(tmp_path / "karte.png")
    asset = store.import_asset(map_png)
    from taktik.core.model import MapImage
    store.project.maps.append(
        MapImage(asset=asset, source_name="karte.png", rotation=12.5))

    symbol_svg = next(symbol_dir.rglob("*.svg"))
    s_asset = store.import_asset(symbol_svg)
    store.project.symbols.append(Symbol(
        asset=s_asset, name="Test", echelon="Zug", label="1. Zug",
        layer_id=store.project.default_layer.id, x=100, y=200))
    store.project.convention = "THW"

    target = tmp_path / "lage.taktik"
    store.save(target)
    assert zipfile.is_zipfile(target)
    with zipfile.ZipFile(target) as zf:
        names = zf.namelist()
        assert "project.json" in names
        assert any(n.startswith("assets/") for n in names)
        data = json.loads(zf.read("project.json"))
        assert data["convention"] == "THW"

    store2 = ProjectStore()
    store2.load(target)
    p = store2.project
    assert p.maps[0].rotation == 12.5           # nicht-destruktive Drehung
    assert p.symbols[0].echelon == "Zug"
    assert p.symbols[0].label == "1. Zug"
    assert store2.asset_path(p.maps[0].asset).exists()
    store.cleanup()
    store2.cleanup()


# ----------------------------------------------------------------------
# Szene: Karte laden, drehen, Zeichen platzieren, PNG-Export
# ----------------------------------------------------------------------
def test_szene_karte_symbole_export(app, tmp_path, symbol_dir):
    from taktik.ui import export as export_mod
    from taktik.ui.commands import AddSymbolCommand, RemoveItemsCommand
    from taktik.ui.scene import MapScene

    store = ProjectStore()
    scene = MapScene(store)

    # Karte laden (PNG) und nicht-destruktiv drehen
    map_item = scene.add_map_from_file(_make_png(tmp_path / "karte.png"))
    assert map_item is not None
    map_item.set_rotation_deg(37.0)
    assert store.project.maps[0].rotation == 37.0

    # SVG-Karte laden
    svg_map = next(symbol_dir.rglob("*.svg"))
    assert scene.add_map_from_file(svg_map) is not None

    # Zeichen platzieren (mit Undo/Redo)
    lib = SymbolLibrary()
    lib.scan(symbol_dir)
    item = scene.create_symbol_item(lib.entries[0], QPointF(120, 80))
    assert item is not None
    scene.undo_stack.push(AddSymbolCommand(scene, item))
    assert len(store.project.symbols) == 1

    # Größenkennzeichnung automatisch ergänzen (Abnahmekriterium)
    item.model.echelon = "Gruppe"
    item.refresh_decorations()
    scene.set_convention("THW")
    assert store.project.convention == "THW"

    # Undo/Redo (Soll-Anforderung)
    scene.undo_stack.undo()
    assert len(store.project.symbols) == 0
    scene.undo_stack.redo()
    assert len(store.project.symbols) == 1

    # Löschen mit Undo
    scene.undo_stack.push(RemoveItemsCommand(scene, [item]))
    assert len(store.project.symbols) == 0
    scene.undo_stack.undo()
    assert len(store.project.symbols) == 1

    # PNG-Export (Abnahmekriterium) und SVG-Export (optional)
    png_out = tmp_path / "export.png"
    assert export_mod.export_png(scene, png_out)
    image = QImage(str(png_out))
    assert not image.isNull() and image.width() > 50

    svg_out = tmp_path / "export.svg"
    assert export_mod.export_svg(scene, svg_out)
    assert svg_out.read_text(encoding="utf-8").lstrip().startswith("<")

    # Projekt speichern, laden, Szene neu aufbauen
    project_file = tmp_path / "lage.taktik"
    store.save(project_file)
    store.load(project_file)
    scene.rebuild_from_project()
    assert len([i for i in scene.items()]) > 0
    store.cleanup()


# ----------------------------------------------------------------------
# Pfeile: zeichnen, Endpunkte ändern, speichern/laden, Undo
# ----------------------------------------------------------------------
def test_pfeile_zeichnen_und_speichern(app, tmp_path):
    from taktik.ui.commands import (AddArrowCommand, ArrowStyleCommand,
                                    PointsGeometryCommand,
                                    RemoveItemsCommand)
    from taktik.ui.scene import MapScene

    store = ProjectStore()
    scene = MapScene(store)

    # Mehrpunkt-Pfeil
    item = scene.create_arrow_item(
        [QPointF(10, 20), QPointF(120, 60), QPointF(210, 120)])
    scene.undo_stack.push(AddArrowCommand(scene, item))
    assert len(store.project.arrows) == 1
    assert store.project.arrows[0].points[-1] == [210, 120]

    # Stützpunkt ändern (mit Undo)
    old = item.geometry()
    new = [list(p) for p in old]
    new[-1] = [300, 200]
    item.set_geometry(new)
    scene.undo_stack.push(PointsGeometryCommand(item, old, new))
    assert item.model.points[-1] == [300, 200]
    scene.undo_stack.undo()
    assert item.model.points[-1] == [210, 120]
    scene.undo_stack.redo()
    assert item.model.points[-1] == [300, 200]

    # Stil: Farbe, Strichelung, gebogen, breiter Umrisspfeil
    scene.undo_stack.push(ArrowStyleCommand(
        item, "color", item.model.color, "#c00000", "Farbe"))
    scene.undo_stack.push(ArrowStyleCommand(
        item, "dashed", False, True, "Strichelung"))
    scene.undo_stack.push(ArrowStyleCommand(
        item, "curved", False, True, "Linienführung"))
    scene.undo_stack.push(ArrowStyleCommand(
        item, "style", "linie", "breit", "Pfeilform"))
    scene.undo_stack.push(ArrowStyleCommand(
        item, "label", "", "Angriff", "Beschriften"))
    assert item.model.curved and item.model.style == "breit"
    assert not item.boundingRect().isEmpty()

    # Speichern, laden, Szene neu aufbauen
    target = tmp_path / "pfeile.taktik"
    store.save(target)
    store2 = ProjectStore()
    store2.load(target)
    arrow = store2.project.arrows[0]
    assert arrow.points[-1] == [300, 200]
    assert arrow.color == "#c00000" and arrow.dashed and arrow.curved
    assert arrow.style == "breit" and arrow.label == "Angriff"

    scene2 = MapScene(store2)
    scene2.rebuild_from_project()
    from taktik.ui.items import ArrowItem
    arrows = [i for i in scene2.items() if isinstance(i, ArrowItem)]
    assert len(arrows) == 1

    # Löschen mit Undo
    scene.undo_stack.push(RemoveItemsCommand(scene, [item]))
    assert len(store.project.arrows) == 0
    scene.undo_stack.undo()
    assert len(store.project.arrows) == 1
    store.cleanup()
    store2.cleanup()


def test_pfeil_abwaertskompatibel_altes_format():
    from taktik.core.model import Arrow

    legacy = {"id": "abc", "x1": 1.0, "y1": 2.0, "x2": 3.0, "y2": 4.0,
              "color": "#000000", "width": 4.0, "dashed": False,
              "label": "", "z": 10.0}
    arrow = Arrow.from_dict(legacy)
    assert arrow.points == [[1.0, 2.0], [3.0, 4.0]]
    assert arrow.style == "linie" and arrow.curved is False
    # Neue Felder erhalten sinnvolle Vorgaben
    assert arrow.pattern == "glatt" and arrow.head == "spitze"


def test_linien_mit_mustern_und_ohne_spitze(app, tmp_path):
    from taktik.core.model import LINE_PATTERNS
    from taktik.ui.commands import AddArrowCommand, ArrowStyleCommand
    from taktik.ui.scene import MapScene

    store = ProjectStore()
    scene = MapScene(store)

    # Linie ohne Pfeilspitze (wie „Linie zeichnen")
    item = scene.create_arrow_item(
        [QPointF(0, 0), QPointF(200, 0), QPointF(200, 120)],
        color="#404040", head="keine", pattern="zinnen")
    scene.undo_stack.push(AddArrowCommand(scene, item))
    assert item.model.head == "keine" and item.model.pattern == "zinnen"

    # Muster-Pfad wird tatsächlich gebaut (nicht leer, ungleich Center)
    assert "zinnen" in LINE_PATTERNS and "welle" in LINE_PATTERNS
    deco = item._decorated_path()
    assert deco.elementCount() > item._center_path().elementCount()

    # Strichmuster (A/B/Igel): Querstriche mit 1:1-Teilung
    for pattern in ("striche_oben", "striche_unten", "igel"):
        assert pattern in LINE_PATTERNS
        item.model.pattern = pattern
        ticks = item._tick_lines()
        assert len(ticks) >= 3
        # Igel hat T-Balken, die anderen nicht
        assert (ticks[0][2] is not None) == (pattern == "igel")
    # oben und unten zeigen auf entgegengesetzte Seiten
    item.model.pattern = "striche_oben"
    up = item._tick_lines()[0]
    item.model.pattern = "striche_unten"
    down = item._tick_lines()[0]
    assert (up[1].y() - up[0].y()) * (down[1].y() - down[0].y()) < 0
    item.model.pattern = "zinnen"

    # Muster und Abschluss Undo-fähig ändern
    scene.undo_stack.push(ArrowStyleCommand(
        item, "pattern", "zinnen", "welle", "Linienmuster"))
    scene.undo_stack.push(ArrowStyleCommand(
        item, "head", "keine", "spitze", "Linienabschluss"))
    assert item.model.pattern == "welle" and item.model.head == "spitze"
    scene.undo_stack.undo()
    assert item.model.head == "keine"

    # Speichern/Laden erhält Muster und Abschluss
    target = tmp_path / "linien.taktik"
    store.save(target)
    store2 = ProjectStore()
    store2.load(target)
    arrow = store2.project.arrows[0]
    assert arrow.head == "keine" and arrow.pattern == "welle"
    store.cleanup()
    store2.cleanup()


def test_flaechen_zeichnen_und_speichern(app, tmp_path):
    from taktik.ui.commands import (AddAreaCommand, ArrowStyleCommand,
                                    PointsGeometryCommand,
                                    RemoveItemsCommand)
    from taktik.ui.scene import MapScene

    store = ProjectStore()
    scene = MapScene(store)

    item = scene.create_area_item(
        [QPointF(0, 0), QPointF(200, 0), QPointF(200, 150),
         QPointF(0, 150)])
    scene.undo_stack.push(AddAreaCommand(scene, item))
    assert len(store.project.areas) == 1

    # Eckpunkt verschieben mit Undo
    old = item.geometry()
    new = [list(p) for p in old]
    new[2] = [260, 190]
    item.set_geometry(new)
    scene.undo_stack.push(PointsGeometryCommand(item, old, new))
    scene.undo_stack.undo()
    assert item.model.points[2] == [200, 150]

    # Beschriftung + Farbe (z. B. Einsatzabschnitt)
    scene.undo_stack.push(ArrowStyleCommand(
        item, "label", "", "EA Nord", "Beschriften"))
    scene.undo_stack.push(ArrowStyleCommand(
        item, "color", item.model.color, "#e07000", "Farbe"))

    target = tmp_path / "flaechen.taktik"
    store.save(target)
    store2 = ProjectStore()
    store2.load(target)
    area = store2.project.areas[0]
    assert area.label == "EA Nord" and area.color == "#e07000"
    assert len(area.points) == 4

    scene2 = MapScene(store2)
    scene2.rebuild_from_project()
    from taktik.ui.items import AreaItem
    assert len([i for i in scene2.items()
                if isinstance(i, AreaItem)]) == 1

    scene.undo_stack.push(RemoveItemsCommand(scene, [item]))
    assert len(store.project.areas) == 0
    scene.undo_stack.undo()
    assert len(store.project.areas) == 1
    store.cleanup()
    store2.cleanup()


# ----------------------------------------------------------------------
# Hauptfenster lässt sich instanziieren (UI-Smoke)
# ----------------------------------------------------------------------
def test_hauptfenster_startet(app):
    from taktik.ui.main_window import MainWindow
    window = MainWindow()
    assert window.menuBar().actions()
    titles = [a.text() for a in window.menuBar().actions()]
    assert "&Datei" in titles and "&Konvention" in titles
    window.store.cleanup()
