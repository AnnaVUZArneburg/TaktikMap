"""Kartenszene: verbindet Projektmodell und QGraphics-Items."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, Signal
from PySide6.QtGui import QUndoStack
from PySide6.QtWidgets import QGraphicsItem, QGraphicsScene

from taktik.core.model import Area, Arrow, MapImage, Symbol
from taktik.core.project_io import ProjectStore
from taktik.symbols.library import SymbolEntry
from taktik.ui.items import (SYMBOL_TARGET_SIZE, AreaItem, ArrowItem,
                             MapItem, SymbolItem)

MAP_SUFFIXES = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".svg"}


class MapScene(QGraphicsScene):
    """Szene der Lagekarte mit Raster-/Fangfunktion und Undo-Stack."""

    item_moved = Signal(QGraphicsItem)
    project_changed = Signal()

    GRID_SIZE = 50.0

    def __init__(self, store: ProjectStore, parent=None) -> None:
        super().__init__(parent)
        self.store = store
        self.undo_stack = QUndoStack(self)
        self.grid_visible = False
        self.snap_enabled = False
        self.setSceneRect(-5000, -5000, 10000, 10000)

    # ------------------------------------------------------------------
    # Raster / Fang (Soll-Anforderung)
    # ------------------------------------------------------------------
    def snap_to_grid(self, pos: QPointF) -> QPointF:
        if not self.snap_enabled:
            return pos
        g = self.GRID_SIZE
        return QPointF(round(pos.x() / g) * g, round(pos.y() / g) * g)

    # ------------------------------------------------------------------
    # Karten
    # ------------------------------------------------------------------
    def add_map_from_file(self, file_path: str | Path) -> MapItem | None:
        """Importiert eine Kartendatei ins Projekt (Anforderung 3.2)."""
        file_path = Path(file_path)
        if file_path.suffix.lower() not in MAP_SUFFIXES:
            return None
        asset = self.store.import_asset(file_path)
        model = MapImage(asset=asset, source_name=file_path.name)
        item = MapItem(model, self.store.asset_path(asset))
        if not item.is_valid:
            return None
        self.store.project.maps.append(model)
        self.addItem(item)
        self.project_changed.emit()
        return item

    # ------------------------------------------------------------------
    # Symbole
    # ------------------------------------------------------------------
    def create_symbol_item(self, entry: SymbolEntry,
                           scene_pos: QPointF) -> SymbolItem | None:
        """Erzeugt ein Symbol-Item aus einem Bibliothekseintrag
        (noch ohne Undo-Registrierung)."""
        asset = self.store.import_asset(entry.path)
        model = Symbol(
            asset=asset,
            source_name=entry.path.name,
            name=entry.name,
            layer_id=self.store.project.default_layer.id,
            echelon=entry.default_echelon,
        )
        item = SymbolItem(model, self.store.asset_path(asset),
                          self.store.project.convention)
        if not item.is_valid:
            return None
        # Auf einheitliche Zielgröße skalieren
        w = item.boundingRect().width()
        if w > 0:
            item.setScale(SYMBOL_TARGET_SIZE / w)
        pos = self.snap_to_grid(scene_pos - QPointF(
            item.boundingRect().width() * item.scale() / 2,
            item.boundingRect().height() * item.scale() / 2))
        item.setPos(pos)
        item.sync_model()
        return item

    def attach_symbol(self, item: SymbolItem) -> None:
        """Fügt ein Symbol in Szene und Modell ein (für Undo/Redo)."""
        if item.model not in self.store.project.symbols:
            self.store.project.symbols.append(item.model)
        if item.scene() is not self:
            self.addItem(item)
        self._apply_layer_visibility(item)
        self.apply_layer_order()
        self.project_changed.emit()

    def detach_symbol(self, item: SymbolItem) -> None:
        """Entfernt ein Symbol aus Szene und Modell (für Undo/Redo)."""
        if item.model in self.store.project.symbols:
            self.store.project.symbols.remove(item.model)
        if item.scene() is self:
            self.removeItem(item)
        self.project_changed.emit()

    def detach_map(self, item: MapItem) -> None:
        if item.model in self.store.project.maps:
            self.store.project.maps.remove(item.model)
        if item.scene() is self:
            self.removeItem(item)
        self.project_changed.emit()

    def attach_map(self, item: MapItem) -> None:
        if item.model not in self.store.project.maps:
            self.store.project.maps.append(item.model)
        if item.scene() is not self:
            self.addItem(item)
        self.project_changed.emit()

    # ------------------------------------------------------------------
    # Pfeile und Flächen (Bewegungsrichtungen, Einsatzabschnitte usw.)
    # ------------------------------------------------------------------
    def _snapped_points(self, points: list[QPointF]) -> list[list[float]]:
        snapped = [self.snap_to_grid(p) for p in points]
        return [[p.x(), p.y()] for p in snapped]

    def create_arrow_item(self, points: list[QPointF],
                          color: str = "#0060a0", head: str = "spitze",
                          pattern: str = "glatt") -> ArrowItem:
        model = Arrow(
            points=self._snapped_points(points),
            color=color,
            head=head,
            pattern=pattern,
            layer_id=self.store.project.default_layer.id,
        )
        return ArrowItem(model)

    def create_area_item(self, points: list[QPointF],
                         color: str = "#c00000") -> AreaItem:
        model = Area(
            points=self._snapped_points(points),
            color=color,
            layer_id=self.store.project.default_layer.id,
        )
        return AreaItem(model)

    def attach_arrow(self, item: ArrowItem) -> None:
        if item.model not in self.store.project.arrows:
            self.store.project.arrows.append(item.model)
        if item.scene() is not self:
            self.addItem(item)
        self._apply_item_layer_visibility(item)
        self.apply_layer_order()
        self.project_changed.emit()

    def detach_arrow(self, item: ArrowItem) -> None:
        if item.model in self.store.project.arrows:
            self.store.project.arrows.remove(item.model)
        if item.scene() is self:
            self.removeItem(item)
        self.project_changed.emit()

    def attach_area(self, item: AreaItem) -> None:
        if item.model not in self.store.project.areas:
            self.store.project.areas.append(item.model)
        if item.scene() is not self:
            self.addItem(item)
        self._apply_item_layer_visibility(item)
        self.apply_layer_order()
        self.project_changed.emit()

    def detach_area(self, item: AreaItem) -> None:
        if item.model in self.store.project.areas:
            self.store.project.areas.remove(item.model)
        if item.scene() is self:
            self.removeItem(item)
        self.project_changed.emit()

    # ------------------------------------------------------------------
    # Konvention / Ebenen
    # ------------------------------------------------------------------
    def set_convention(self, convention: str) -> None:
        self.store.project.convention = convention
        for item in self.items():
            if isinstance(item, SymbolItem):
                item.set_convention(convention)
        self.project_changed.emit()

    def _apply_layer_visibility(self, item) -> None:
        self._apply_item_layer_visibility(item)

    def _apply_item_layer_visibility(self, item) -> None:
        layer = self.store.project.layer_by_id(item.model.layer_id)
        item.setVisible(layer.visible if layer else True)

    def apply_layer_visibility(self) -> None:
        """Blendet Objekte gemäß Ebenen-Sichtbarkeit ein/aus."""
        for item in self.items():
            if isinstance(item, (SymbolItem, ArrowItem, AreaItem)):
                self._apply_item_layer_visibility(item)

    def apply_layer_order(self) -> None:
        """Stapelt Objekte gemäß Ebenen-Reihenfolge.

        Die oberste Ebene der Ebenenliste liegt vorn; innerhalb einer
        Ebene liegen Flächen hinter Zeichen, Pfeile davor. Karten
        bleiben immer im Hintergrund.
        """
        project = self.store.project
        rank_of = {layer.id: len(project.layers) - 1 - i
                   for i, layer in enumerate(project.layers)}
        for item in self.items():
            if isinstance(item, AreaItem):
                offset = -50.0
            elif isinstance(item, ArrowItem):
                offset = 10.0
            elif isinstance(item, SymbolItem):
                offset = 0.0
            else:
                continue
            rank = rank_of.get(item.model.layer_id, 0)
            item.model.z = rank * 200.0 + offset
            item.setZValue(item.model.z)

    # ------------------------------------------------------------------
    # Projekt neu aufbauen (nach Laden)
    # ------------------------------------------------------------------
    def rebuild_from_project(self) -> None:
        self.clear()
        self.undo_stack.clear()
        project = self.store.project
        for map_model in project.maps:
            item = MapItem(map_model, self.store.asset_path(map_model.asset))
            if item.is_valid:
                self.addItem(item)
        for symbol_model in project.symbols:
            item = SymbolItem(symbol_model,
                              self.store.asset_path(symbol_model.asset),
                              project.convention)
            if item.is_valid:
                self.addItem(item)
        for arrow_model in project.arrows:
            self.addItem(ArrowItem(arrow_model))
        for area_model in project.areas:
            self.addItem(AreaItem(area_model))
        self.apply_layer_visibility()
        self.apply_layer_order()
        self.project_changed.emit()

    def content_rect(self):
        """Umschließendes Rechteck aller Objekte (für Export/Druck)."""
        return self.itemsBoundingRect()
