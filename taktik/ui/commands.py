"""Undo/Redo-Kommandos (Soll-Anforderung des Lastenhefts)."""

from __future__ import annotations

from PySide6.QtCore import QPointF
from PySide6.QtGui import QUndoCommand

from taktik.ui.items import AreaItem, ArrowItem, MapItem, SymbolItem
from taktik.ui.scene import MapScene


class AddArrowCommand(QUndoCommand):
    def __init__(self, scene: MapScene, item: ArrowItem) -> None:
        super().__init__("Pfeil zeichnen")
        self._scene = scene
        self._item = item

    def redo(self) -> None:
        self._scene.attach_arrow(self._item)

    def undo(self) -> None:
        self._scene.detach_arrow(self._item)


class AddAreaCommand(QUndoCommand):
    def __init__(self, scene: MapScene, item: AreaItem) -> None:
        super().__init__("Fläche zeichnen")
        self._scene = scene
        self._item = item

    def redo(self) -> None:
        self._scene.attach_area(self._item)

    def undo(self) -> None:
        self._scene.detach_area(self._item)


class PointsGeometryCommand(QUndoCommand):
    """Verschieben eines Stützpunkts (Pfeil oder Fläche)."""

    def __init__(self, item, old: list, new: list) -> None:
        super().__init__("Stützpunkt verschieben")
        self._item = item
        self._old = old
        self._new = new
        self._first = True

    def redo(self) -> None:
        if self._first:
            self._first = False
            return
        self._item.set_geometry(self._new)

    def undo(self) -> None:
        self._item.set_geometry(self._old)


class ArrowStyleCommand(QUndoCommand):
    """Änderung einer Stil-Eigenschaft (Pfeil oder Fläche)."""

    def __init__(self, item, attribute: str, old, new, text: str) -> None:
        super().__init__(text)
        self._item = item
        self._attribute = attribute   # color/width/dashed/curved/style/label
        self._old = old
        self._new = new

    def _apply(self, value) -> None:
        setattr(self._item.model, self._attribute, value)
        self._item.refresh_style()

    def redo(self) -> None:
        self._apply(self._new)

    def undo(self) -> None:
        self._apply(self._old)


class AddSymbolCommand(QUndoCommand):
    def __init__(self, scene: MapScene, item: SymbolItem) -> None:
        super().__init__(f"Zeichen „{item.model.name}“ einfügen")
        self._scene = scene
        self._item = item

    def redo(self) -> None:
        self._scene.attach_symbol(self._item)

    def undo(self) -> None:
        self._scene.detach_symbol(self._item)


class RemoveItemsCommand(QUndoCommand):
    def __init__(self, scene: MapScene, items: list) -> None:
        super().__init__("Objekte löschen")
        self._scene = scene
        self._items = items

    def redo(self) -> None:
        for item in self._items:
            if isinstance(item, SymbolItem):
                self._scene.detach_symbol(item)
            elif isinstance(item, MapItem):
                self._scene.detach_map(item)
            elif isinstance(item, ArrowItem):
                self._scene.detach_arrow(item)
            elif isinstance(item, AreaItem):
                self._scene.detach_area(item)

    def undo(self) -> None:
        for item in self._items:
            if isinstance(item, SymbolItem):
                self._scene.attach_symbol(item)
            elif isinstance(item, MapItem):
                self._scene.attach_map(item)
            elif isinstance(item, ArrowItem):
                self._scene.attach_arrow(item)
            elif isinstance(item, AreaItem):
                self._scene.attach_area(item)


class MoveItemsCommand(QUndoCommand):
    """Verschieben per Maus; alte/neue Positionen je Item."""

    def __init__(self, moves: list[tuple[object, QPointF, QPointF]]) -> None:
        super().__init__("Verschieben")
        self._moves = moves
        self._first = True

    def redo(self) -> None:
        if self._first:      # erste Ausführung: Items liegen schon am Ziel
            self._first = False
            return
        for item, _old, new in self._moves:
            item.setPos(new)
            item.sync_model()

    def undo(self) -> None:
        for item, old, _new in self._moves:
            item.setPos(old)
            item.sync_model()


class TransformCommand(QUndoCommand):
    """Änderung von Drehung oder Skalierung eines Items."""

    def __init__(self, item, attribute: str, old: float, new: float,
                 text: str) -> None:
        super().__init__(text)
        self._item = item
        self._attribute = attribute   # "rotation" | "scale"
        self._old = old
        self._new = new

    def _apply(self, value: float) -> None:
        if self._attribute == "rotation":
            self._item.setRotation(value)
        else:
            self._item.setScale(value)
        self._item.sync_model()

    def redo(self) -> None:
        self._apply(self._new)

    def undo(self) -> None:
        self._apply(self._old)


class WindStrengthCommand(QUndoCommand):
    """Wechselt die Windstärke eines Windpfeils (tauscht das Asset)."""

    def __init__(self, item: SymbolItem, store, new_source_path,
                 new_name: str) -> None:
        super().__init__("Windstärke")
        self._item = item
        self._store = store
        self._old = (item.model.asset, item.model.source_name,
                     item.model.name)
        asset = store.import_asset(new_source_path)
        self._new = (asset, new_source_path.name, new_name)

    def _apply(self, state: tuple) -> None:
        asset, source_name, name = state
        model = self._item.model
        model.asset = asset
        model.source_name = source_name
        model.name = name
        self._item.reload_asset(self._store.asset_path(asset))

    def redo(self) -> None:
        self._apply(self._new)

    def undo(self) -> None:
        self._apply(self._old)


class SymbolPropertyCommand(QUndoCommand):
    """Änderung von Echelon oder Beschriftung eines Symbols."""

    def __init__(self, item: SymbolItem, attribute: str,
                 old: str, new: str, text: str) -> None:
        super().__init__(text)
        self._item = item
        self._attribute = attribute   # "echelon" | "label"
        self._old = old
        self._new = new

    def _apply(self, value: str) -> None:
        setattr(self._item.model, self._attribute, value)
        self._item.refresh_decorations()

    def redo(self) -> None:
        self._apply(self._new)

    def undo(self) -> None:
        self._apply(self._old)
