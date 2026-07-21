"""Kartenansicht: Zoom, Pan, Rasteranzeige, Drag-and-Drop von Symbolen."""

from __future__ import annotations

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QBrush, QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QGraphicsView

from taktik.ui.commands import MoveItemsCommand
from taktik.ui.items import MapItem, SymbolItem
from taktik.ui.scene import MapScene

SYMBOL_MIME = "application/x-taktik-symbol"


class MapView(QGraphicsView):
    """Ansicht der Lagekarte (Anforderung 6: Kartenansicht)."""

    symbol_dropped = Signal(str, QPointF)   # Bibliotheksschlüssel, Szenenpos.
    shape_drawn = Signal(str, list)         # Modus, Punktliste (Szene)
    draw_mode_changed = Signal(str)         # "arrow" | "line" | "area" | ""
    zoom_changed = Signal(float)

    def __init__(self, scene: MapScene, parent=None) -> None:
        super().__init__(scene, parent)
        self.setRenderHints(QPainter.Antialiasing
                            | QPainter.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setAcceptDrops(True)
        # Neutraler grauer Hintergrund (unabhängig vom Systemtheme)
        from taktik.ui.theme import MAP_BACKGROUND
        self.setBackgroundBrush(QBrush(QColor(MAP_BACKGROUND)))
        # ViewportUpdate auf Vollmodus, damit Auswahl-Rahmen sauber zeichnen
        self.setViewportUpdateMode(QGraphicsView.BoundingRectViewportUpdate)
        self._move_origin: dict = {}
        self._draw_mode = ""                # "" | "arrow" | "line" | "area"
        self._draw_points: list[QPointF] = []
        self._preview = None

    # ------------------------------------------------------------------
    # Zeichenmodi: Pfeile (Mehrpunkt) und Flächen (Polygon)
    # ------------------------------------------------------------------
    def set_draw_mode(self, mode: str) -> None:
        """Aktiviert einen Zeichenmodus ("arrow", "line", "area") oder ""."""
        if mode == self._draw_mode:
            return
        self._cancel_drawing()
        self._draw_mode = mode
        self.setDragMode(QGraphicsView.NoDrag if mode
                         else QGraphicsView.RubberBandDrag)
        self.viewport().setCursor(Qt.CrossCursor if mode
                                  else Qt.ArrowCursor)
        self.draw_mode_changed.emit(mode)

    def _cancel_drawing(self) -> None:
        if self._preview is not None:
            self.scene().removeItem(self._preview)
            self._preview = None
        self._draw_points = []

    def _min_points(self) -> int:
        return 3 if self._draw_mode == "area" else 2

    def _update_preview(self, cursor: QPointF | None = None) -> None:
        if not self._draw_points:
            return
        points = list(self._draw_points)
        if cursor is not None:
            points.append(cursor)
        path = QPainterPath(points[0])
        for p in points[1:]:
            path.lineTo(p)
        if self._draw_mode == "area" and len(points) > 2:
            path.closeSubpath()
        if self._preview is None:
            color = QColor({"area": "#c00000", "line": "#0060a0"}.get(
                self._draw_mode, "#0060a0"))
            pen = QPen(color, 2, Qt.DashLine)
            self._preview = self.scene().addPath(path, pen)
            if self._draw_mode == "area":
                fill = QColor(color)
                fill.setAlpha(30)
                self._preview.setBrush(QBrush(fill))
            self._preview.setZValue(1000)
        else:
            self._preview.setPath(path)

    def _finish_drawing(self, extra: QPointF | None = None) -> None:
        points = list(self._draw_points)
        if extra is not None:
            points.append(extra)
        mode = self._draw_mode
        self._cancel_drawing()
        # Doppelte Schlusspunkte (Doppelklick) entfernen
        while len(points) >= 2 and \
                (points[-1] - points[-2]).manhattanLength() < 4:
            points.pop()
        if len(points) >= self._min_points():
            self.shape_drawn.emit(mode, points)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key_Escape and self._draw_mode:
            if self._draw_points:
                self._cancel_drawing()      # erst Zeichnung abbrechen …
            else:
                self.set_draw_mode("")      # … dann Modus verlassen
            return
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and \
                self._draw_points:
            self._finish_drawing()
            return
        super().keyPressEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:
        if self._draw_mode and event.button() == Qt.LeftButton \
                and self._draw_points:
            self._finish_drawing()
            event.accept()
            return
        super().mouseDoubleClickEvent(event)

    # ------------------------------------------------------------------
    # Zoom (Mausrad) und Pan (mittlere Maustaste)
    # ------------------------------------------------------------------
    def wheelEvent(self, event) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        current = self.transform().m11()
        if 0.02 < current * factor < 50.0:
            self.scale(factor, factor)
            self.zoom_changed.emit(self.transform().m11())

    def mousePressEvent(self, event) -> None:
        if self._draw_mode:
            if event.button() == Qt.LeftButton:
                pos = self.mapToScene(event.position().toPoint())
                self._draw_points.append(pos)
                self._update_preview(pos)
                event.accept()
                return
            if event.button() == Qt.RightButton and self._draw_points:
                self._finish_drawing()      # Rechtsklick schließt ab
                event.accept()
                return
        if event.button() == Qt.MiddleButton:
            self.setDragMode(QGraphicsView.ScrollHandDrag)
            # Weiterreichen als linker Klick, damit das Ziehen startet
            fake = event.__class__(event.type(), event.position(),
                                   Qt.LeftButton, Qt.LeftButton,
                                   event.modifiers())
            super().mousePressEvent(fake)
            return
        if event.button() == Qt.LeftButton:
            # Ausgangspositionen für Undo des Verschiebens merken
            self._move_origin = {
                item: item.pos()
                for item in self.scene().selectedItems()
                if isinstance(item, (MapItem, SymbolItem))
            }
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._draw_mode and self._draw_points:
            cursor = self.mapToScene(event.position().toPoint())
            self._update_preview(cursor)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._draw_mode and event.button() == Qt.LeftButton \
                and self._draw_points:
            # Schnellmodus für einfache Pfeile/Linien: Ziehen in einem Zug
            release = self.mapToScene(event.position().toPoint())
            if self._draw_mode in ("arrow", "line") \
                    and len(self._draw_points) == 1 \
                    and (release - self._draw_points[0]).manhattanLength() > 12:
                self._finish_drawing(release)
            event.accept()
            return
        if self.dragMode() == QGraphicsView.ScrollHandDrag:
            self.setDragMode(QGraphicsView.RubberBandDrag)
        super().mouseReleaseEvent(event)
        if event.button() == Qt.LeftButton and self._move_origin:
            moves = []
            for item, old_pos in self._move_origin.items():
                if item.scene() is self.scene() and item.pos() != old_pos:
                    moves.append((item, old_pos, item.pos()))
            if moves:
                scene: MapScene = self.scene()
                scene.undo_stack.push(MoveItemsCommand(moves))
            self._move_origin = {}

    # ------------------------------------------------------------------
    # Drag-and-Drop aus der Symbolbibliothek (Anforderung 3.4)
    # ------------------------------------------------------------------
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasFormat(SYMBOL_MIME):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event) -> None:
        if event.mimeData().hasFormat(SYMBOL_MIME):
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event) -> None:
        if event.mimeData().hasFormat(SYMBOL_MIME):
            key = bytes(event.mimeData().data(SYMBOL_MIME)).decode("utf-8")
            scene_pos = self.mapToScene(event.position().toPoint())
            self.symbol_dropped.emit(key, scene_pos)
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

    # ------------------------------------------------------------------
    # Rasteranzeige (Soll-Anforderung)
    # ------------------------------------------------------------------
    def drawBackground(self, painter: QPainter, rect) -> None:
        super().drawBackground(painter, rect)
        scene: MapScene = self.scene()
        if not getattr(scene, "grid_visible", False):
            return
        g = scene.GRID_SIZE
        pen = QPen(QColor(0, 0, 0, 40), 0)
        painter.setPen(pen)
        left = int(rect.left() // g) * g
        top = int(rect.top() // g) * g
        x = left
        while x < rect.right():
            painter.drawLine(QPointF(x, rect.top()),
                             QPointF(x, rect.bottom()))
            x += g
        y = top
        while y < rect.bottom():
            painter.drawLine(QPointF(rect.left(), y),
                             QPointF(rect.right(), y))
            y += g
