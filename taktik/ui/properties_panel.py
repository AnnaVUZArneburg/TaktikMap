"""Eigenschaftenfenster: Transformationen, Größenkennzeichnung,
Beschriftung des ausgewählten Objekts (Anforderungen 3.3, 3.5, 3.6)."""

from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox,
                               QFormLayout, QLabel, QLineEdit, QPushButton,
                               QSpinBox, QWidget)

from taktik.core.model import ECHELONS
from taktik.ui.commands import (ArrowStyleCommand, SymbolPropertyCommand,
                                TransformCommand, WindStrengthCommand)

WIND_PATTERN = re.compile(r"wind_(\d{2})bft\.svg$")
from taktik.ui.items import AreaItem, ArrowItem, MapItem, SymbolItem
from taktik.ui.scene import MapScene

ARROW_COLORS = [
    ("Blau (eigene Kräfte)", "#0060a0"),
    ("Rot (feindlich / Gefahr)", "#c00000"),
    ("Grün (neutral)", "#00a000"),
    ("Orange (Abschnitt)", "#e07000"),
    ("Schwarz", "#000000"),
]

ARROW_SHAPES = [
    ("Linie", "linie"),
    ("Breiter Pfeil (Umriss)", "breit"),
]

LINE_PATTERNS = [
    ("glatt", "glatt"),
    ("Zinnen (Kastenmuster)", "zinnen"),
    ("Welle", "welle"),
    ("Striche oben", "striche_oben"),
    ("Striche unten", "striche_unten"),
    ("Igel (T-Striche)", "igel"),
]

ARROW_HEADS = [
    ("mit Pfeilspitze", "spitze"),
    ("ohne (nur Linie)", "keine"),
]


class PropertiesPanel(QWidget):
    """Zeigt und ändert Eigenschaften des ausgewählten Objekts."""

    def __init__(self, scene: MapScene, library=None, parent=None) -> None:
        super().__init__(parent)
        self._scene = scene
        self._library = library
        self._item: MapItem | SymbolItem | None = None
        self._updating = False

        self._type_label = QLabel("–")

        self._rotation = QDoubleSpinBox()
        self._rotation.setRange(-360.0, 360.0)
        self._rotation.setSuffix(" °")
        self._rotation.setDecimals(1)
        self._rotation.setSingleStep(1.0)
        self._rotation.setKeyboardTracking(False)

        self._north_button = QPushButton("Nach Norden ausrichten (0°)")

        self._scale = QDoubleSpinBox()
        self._scale.setRange(0.01, 100.0)
        self._scale.setDecimals(2)
        self._scale.setSingleStep(0.1)
        self._scale.setKeyboardTracking(False)

        self._echelon = QComboBox()
        for value in ECHELONS:
            self._echelon.addItem(value if value else "(keine)", value)

        self._label = QLineEdit()
        self._label.setPlaceholderText("Beschriftung …")

        self._layer = QComboBox()

        # Pfeil-/Flächen-Eigenschaften
        self._arrow_color = QComboBox()
        for name, value in ARROW_COLORS:
            self._arrow_color.addItem(name, value)
        self._arrow_width = QDoubleSpinBox()
        self._arrow_width.setRange(1.0, 30.0)
        self._arrow_width.setDecimals(1)
        self._arrow_width.setSingleStep(1.0)
        self._arrow_width.setKeyboardTracking(False)
        self._arrow_dashed = QCheckBox("gestrichelt (geplant)")
        self._arrow_shape = QComboBox()
        for name, value in ARROW_SHAPES:
            self._arrow_shape.addItem(name, value)
        self._arrow_curved = QCheckBox("gebogene Linienführung")
        self._line_pattern = QComboBox()
        for name, value in LINE_PATTERNS:
            self._line_pattern.addItem(name, value)
        self._arrow_head = QComboBox()
        for name, value in ARROW_HEADS:
            self._arrow_head.addItem(name, value)

        # Windstärke (nur für Windrichtungspfeile)
        self._wind = QSpinBox()
        self._wind.setRange(1, 12)
        self._wind.setSuffix(" Bft")
        self._wind.setKeyboardTracking(False)

        form = QFormLayout(self)
        form.setContentsMargins(6, 6, 6, 6)
        form.addRow("Objekt:", self._type_label)
        form.addRow("Drehung:", self._rotation)
        form.addRow("", self._north_button)
        form.addRow("Skalierung:", self._scale)
        form.addRow("Größe:", self._echelon)
        form.addRow("Windstärke:", self._wind)
        form.addRow("Beschriftung:", self._label)
        form.addRow("Farbe:", self._arrow_color)
        form.addRow("Linienbreite:", self._arrow_width)
        form.addRow("Pfeilform:", self._arrow_shape)
        form.addRow("Muster:", self._line_pattern)
        form.addRow("Abschluss:", self._arrow_head)
        form.addRow("", self._arrow_curved)
        form.addRow("", self._arrow_dashed)
        form.addRow("Ebene:", self._layer)

        self._rotation.valueChanged.connect(self._on_rotation)
        self._north_button.clicked.connect(lambda: self._rotation.setValue(0.0))
        self._scale.valueChanged.connect(self._on_scale)
        self._echelon.currentIndexChanged.connect(self._on_echelon)
        self._label.editingFinished.connect(self._on_label)
        self._layer.currentIndexChanged.connect(self._on_layer)
        self._arrow_color.currentIndexChanged.connect(self._on_arrow_color)
        self._arrow_width.valueChanged.connect(self._on_arrow_width)
        self._arrow_dashed.toggled.connect(self._on_arrow_dashed)
        self._arrow_shape.currentIndexChanged.connect(self._on_arrow_shape)
        self._arrow_curved.toggled.connect(self._on_arrow_curved)
        self._line_pattern.currentIndexChanged.connect(self._on_line_pattern)
        self._arrow_head.currentIndexChanged.connect(self._on_arrow_head)
        self._wind.valueChanged.connect(self._on_wind)

        self.set_item(None)

    # ------------------------------------------------------------------
    def refresh_layers(self) -> None:
        self._layer.blockSignals(True)
        self._layer.clear()
        for layer in self._scene.store.project.layers:
            self._layer.addItem(layer.name, layer.id)
        self._layer.blockSignals(False)
        if isinstance(self._item, (SymbolItem, ArrowItem, AreaItem)):
            index = self._layer.findData(self._item.model.layer_id)
            self._layer.blockSignals(True)
            self._layer.setCurrentIndex(max(index, 0))
            self._layer.blockSignals(False)

    def set_item(self, item) -> None:
        self._item = item
        self._updating = True
        is_symbol = isinstance(item, SymbolItem)
        is_map = isinstance(item, MapItem)
        is_arrow = isinstance(item, ArrowItem)
        is_area = isinstance(item, AreaItem)

        for widget in (self._rotation, self._scale, self._north_button):
            widget.setEnabled(is_symbol or is_map)
        self._echelon.setEnabled(is_symbol)
        self._label.setEnabled(is_symbol or is_arrow or is_area)
        self._layer.setEnabled(is_symbol or is_arrow or is_area)
        for widget in (self._arrow_color, self._arrow_width,
                       self._arrow_dashed):
            widget.setEnabled(is_arrow or is_area)
        for widget in (self._arrow_shape, self._arrow_curved,
                       self._line_pattern, self._arrow_head):
            widget.setEnabled(is_arrow)

        is_line = is_arrow and item.model.head == "keine"
        if is_map:
            self._type_label.setText(f"Karte: {item.model.source_name}")
        elif is_symbol:
            self._type_label.setText(f"Zeichen: {item.model.name}")
        elif is_arrow:
            self._type_label.setText("Linie" if is_line else "Pfeil")
        elif is_area:
            self._type_label.setText("Fläche")
        else:
            self._type_label.setText("–")

        if item is not None and not (is_arrow or is_area):
            self._rotation.setValue(item.rotation())
            self._scale.setValue(item.scale())
        wind_match = None
        if is_symbol:
            wind_match = WIND_PATTERN.search(item.model.source_name or "")
        self._wind.setEnabled(bool(wind_match))
        if wind_match:
            self._wind.blockSignals(True)
            self._wind.setValue(int(wind_match.group(1)))
            self._wind.blockSignals(False)

        if is_symbol:
            index = self._echelon.findData(item.model.echelon)
            self._echelon.setCurrentIndex(max(index, 0))
            self._label.setText(item.model.label)
            self.refresh_layers()
        elif is_arrow or is_area:
            index = self._arrow_color.findData(item.model.color)
            self._arrow_color.setCurrentIndex(max(index, 0))
            self._arrow_width.setValue(item.model.width)
            self._arrow_dashed.setChecked(item.model.dashed)
            if is_arrow:
                index = self._arrow_shape.findData(item.model.style)
                self._arrow_shape.setCurrentIndex(max(index, 0))
                self._arrow_curved.setChecked(item.model.curved)
                index = self._line_pattern.findData(item.model.pattern)
                self._line_pattern.setCurrentIndex(max(index, 0))
                index = self._arrow_head.findData(item.model.head)
                self._arrow_head.setCurrentIndex(max(index, 0))
            self._label.setText(item.model.label)
            self.refresh_layers()
        else:
            self._label.clear()
        self._updating = False

    def sync_from_item(self) -> None:
        """Aktualisiert die Anzeige nach externen Änderungen (Undo …)."""
        try:
            if self._item is not None and self._item.scene() is self._scene:
                self.set_item(self._item)
        except RuntimeError:
            # C++-Objekt bereits zerstört (z. B. beim Beenden)
            self._item = None

    # ------------------------------------------------------------------
    def _on_rotation(self, value: float) -> None:
        if self._updating or self._item is None:
            return
        old = self._item.rotation()
        if abs(old - value) < 1e-6:
            return
        self._scene.undo_stack.push(TransformCommand(
            self._item, "rotation", old, value, "Drehen"))

    def _on_scale(self, value: float) -> None:
        if self._updating or self._item is None:
            return
        old = self._item.scale()
        if abs(old - value) < 1e-6:
            return
        self._scene.undo_stack.push(TransformCommand(
            self._item, "scale", old, value, "Skalieren"))

    def _on_echelon(self) -> None:
        if self._updating or not isinstance(self._item, SymbolItem):
            return
        new = self._echelon.currentData()
        old = self._item.model.echelon
        if new != old:
            self._scene.undo_stack.push(SymbolPropertyCommand(
                self._item, "echelon", old, new, "Größenkennzeichnung"))

    def _on_label(self) -> None:
        if self._updating:
            return
        new = self._label.text()
        if isinstance(self._item, SymbolItem):
            old = self._item.model.label
            if new != old:
                self._scene.undo_stack.push(SymbolPropertyCommand(
                    self._item, "label", old, new, "Beschriften"))
        elif isinstance(self._item, (ArrowItem, AreaItem)):
            old = self._item.model.label
            if new != old:
                self._scene.undo_stack.push(ArrowStyleCommand(
                    self._item, "label", old, new, "Beschriften"))

    def _on_layer(self) -> None:
        if self._updating or \
                not isinstance(self._item, (SymbolItem, ArrowItem,
                                            AreaItem)):
            return
        layer_id = self._layer.currentData()
        if layer_id and layer_id != self._item.model.layer_id:
            self._item.model.layer_id = layer_id
            self._scene.apply_layer_visibility()
            self._scene.apply_layer_order()
            self._scene.project_changed.emit()

    def _on_arrow_color(self) -> None:
        if self._updating or \
                not isinstance(self._item, (ArrowItem, AreaItem)):
            return
        new = self._arrow_color.currentData()
        old = self._item.model.color
        if new != old:
            self._scene.undo_stack.push(ArrowStyleCommand(
                self._item, "color", old, new, "Farbe"))

    def _on_arrow_width(self, value: float) -> None:
        if self._updating or \
                not isinstance(self._item, (ArrowItem, AreaItem)):
            return
        old = self._item.model.width
        if abs(old - value) > 1e-6:
            self._scene.undo_stack.push(ArrowStyleCommand(
                self._item, "width", old, value, "Linienbreite"))

    def _on_arrow_dashed(self, checked: bool) -> None:
        if self._updating or \
                not isinstance(self._item, (ArrowItem, AreaItem)):
            return
        old = self._item.model.dashed
        if old != checked:
            self._scene.undo_stack.push(ArrowStyleCommand(
                self._item, "dashed", old, checked, "Strichelung"))

    def _on_arrow_shape(self) -> None:
        if self._updating or not isinstance(self._item, ArrowItem):
            return
        new = self._arrow_shape.currentData()
        old = self._item.model.style
        if new != old:
            self._scene.undo_stack.push(ArrowStyleCommand(
                self._item, "style", old, new, "Pfeilform"))

    def _on_line_pattern(self) -> None:
        if self._updating or not isinstance(self._item, ArrowItem):
            return
        new = self._line_pattern.currentData()
        old = self._item.model.pattern
        if new != old:
            self._scene.undo_stack.push(ArrowStyleCommand(
                self._item, "pattern", old, new, "Linienmuster"))

    def _on_arrow_head(self) -> None:
        if self._updating or not isinstance(self._item, ArrowItem):
            return
        new = self._arrow_head.currentData()
        old = self._item.model.head
        if new != old:
            self._scene.undo_stack.push(ArrowStyleCommand(
                self._item, "head", old, new, "Linienabschluss"))
            self._type_label.setText(
                "Linie" if new == "keine" else "Pfeil")

    def _on_wind(self, bft: int) -> None:
        if self._updating or not isinstance(self._item, SymbolItem) \
                or self._library is None:
            return
        if not WIND_PATTERN.search(self._item.model.source_name or ""):
            return
        wanted = f"wind_{bft:02d}bft.svg"
        for entry in self._library.entries:
            if entry.path.name == wanted:
                self._scene.undo_stack.push(WindStrengthCommand(
                    self._item, self._scene.store, entry.path, entry.name))
                return

    def _on_arrow_curved(self, checked: bool) -> None:
        if self._updating or not isinstance(self._item, ArrowItem):
            return
        old = self._item.model.curved
        if old != checked:
            self._scene.undo_stack.push(ArrowStyleCommand(
                self._item, "curved", old, checked, "Linienführung"))
