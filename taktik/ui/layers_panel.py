"""Ebenenverwaltung (Soll-Anforderung: Layer, Ein-/Ausblenden)."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QInputDialog, QListWidget,
                               QListWidgetItem, QMessageBox, QPushButton,
                               QVBoxLayout, QWidget)

from taktik.core.model import Layer
from taktik.ui.scene import MapScene


class LayersPanel(QWidget):
    """Liste der Ebenen mit Sichtbarkeits-Häkchen."""

    layers_changed = Signal()

    def __init__(self, scene: MapScene, parent=None) -> None:
        super().__init__(parent)
        self._scene = scene

        self._list = QListWidget()
        self._list.setDragDropMode(QListWidget.InternalMove)
        self._list.setToolTip(
            "Ziehen zum Sortieren – die oberste Ebene liegt vorn")
        self._add_button = QPushButton("Neu")
        self._rename_button = QPushButton("Umbenennen")
        self._remove_button = QPushButton("Löschen")

        buttons = QHBoxLayout()
        buttons.addWidget(self._add_button)
        buttons.addWidget(self._rename_button)
        buttons.addWidget(self._remove_button)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self._list, 1)
        layout.addLayout(buttons)

        self._list.itemChanged.connect(self._on_item_changed)
        self._list.model().rowsMoved.connect(self._on_reordered)
        self._add_button.clicked.connect(self._on_add)
        self._rename_button.clicked.connect(self._on_rename)
        self._remove_button.clicked.connect(self._on_remove)

        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self._list.blockSignals(True)
        self._list.clear()
        for layer in self._scene.store.project.layers:
            item = QListWidgetItem(layer.name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked if layer.visible else Qt.Unchecked)
            item.setData(Qt.UserRole, layer.id)
            self._list.addItem(item)
        self._list.blockSignals(False)

    def current_layer(self) -> Layer | None:
        item = self._list.currentItem()
        if item is None:
            return None
        return self._scene.store.project.layer_by_id(item.data(Qt.UserRole))

    # ------------------------------------------------------------------
    def _on_item_changed(self, item: QListWidgetItem) -> None:
        layer = self._scene.store.project.layer_by_id(item.data(Qt.UserRole))
        if layer is not None:
            layer.visible = item.checkState() == Qt.Checked
            self._scene.apply_layer_visibility()
            self._scene.project_changed.emit()

    def _on_reordered(self, *args) -> None:
        """Übernimmt die per Drag-and-Drop geänderte Reihenfolge."""
        project = self._scene.store.project
        id_order = [self._list.item(i).data(Qt.UserRole)
                    for i in range(self._list.count())]
        project.layers.sort(key=lambda layer: id_order.index(layer.id))
        self._scene.apply_layer_order()
        self.layers_changed.emit()
        self._scene.project_changed.emit()

    def _on_add(self) -> None:
        name, ok = QInputDialog.getText(self, "Neue Ebene", "Name der Ebene:")
        if ok and name.strip():
            self._scene.store.project.layers.append(Layer(name=name.strip()))
            self.refresh()
            self.layers_changed.emit()
            self._scene.project_changed.emit()

    def _on_rename(self) -> None:
        layer = self.current_layer()
        if layer is None:
            return
        name, ok = QInputDialog.getText(self, "Ebene umbenennen",
                                        "Neuer Name:", text=layer.name)
        if ok and name.strip():
            layer.name = name.strip()
            self.refresh()
            self.layers_changed.emit()
            self._scene.project_changed.emit()

    def _on_remove(self) -> None:
        layer = self.current_layer()
        project = self._scene.store.project
        if layer is None:
            return
        if len(project.layers) <= 1:
            QMessageBox.information(
                self, "Ebenen", "Die letzte Ebene kann nicht gelöscht werden.")
            return
        used = any(o.layer_id == layer.id for o in
                   (*project.symbols, *project.arrows, *project.areas))
        if used:
            answer = QMessageBox.question(
                self, "Ebene löschen",
                f"Die Ebene „{layer.name}“ enthält Zeichen. Diese werden in "
                "die erste Ebene verschoben. Fortfahren?")
            if answer != QMessageBox.Yes:
                return
        project.layers.remove(layer)
        fallback = project.default_layer.id
        for obj in (*project.symbols, *project.arrows, *project.areas):
            if obj.layer_id == layer.id:
                obj.layer_id = fallback
        self._scene.apply_layer_visibility()
        self.refresh()
        self.layers_changed.emit()
        self._scene.project_changed.emit()
