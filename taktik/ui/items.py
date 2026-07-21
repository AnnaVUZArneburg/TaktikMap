"""QGraphics-Items der Kartenszene: Karten und taktische Zeichen.

Jedes Item hält eine Referenz auf sein Modellobjekt
(:class:`~taktik.core.model.MapImage` bzw.
:class:`~taktik.core.model.Symbol`) und synchronisiert Position und
Transformation dorthin, sodass Speichern jederzeit den aktuellen
Zustand erfasst.
"""

from __future__ import annotations

from pathlib import Path

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (QBrush, QColor, QImageReader, QPainter,
                           QPainterPath, QPainterPathStroker, QPen,
                           QPixmap, QPolygonF)
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import QGraphicsItem, QGraphicsSimpleTextItem

from taktik.core.model import Area, Arrow, MapImage, Symbol
from taktik.symbols import echelon as echelon_mod

# Einheitliche Zielgröße neu platzierter Symbole (Szeneneinheiten)
SYMBOL_TARGET_SIZE = 64.0


def load_pixmap(path: Path) -> QPixmap:
    """Lädt PNG/JPG/TIFF; nutzt QImageReader für große Formate."""
    reader = QImageReader(str(path))
    reader.setAutoTransform(True)
    image = reader.read()
    if image.isNull():
        return QPixmap()
    return QPixmap.fromImage(image)


class _BaseItem(QGraphicsItem):
    """Gemeinsame Basis: Auswahl, Bewegen, Modell-Synchronisation."""

    def __init__(self) -> None:
        super().__init__()
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange:
            scene = self.scene()
            snap = getattr(scene, "snap_to_grid", None)
            if snap:
                value = snap(value)
        elif change == QGraphicsItem.ItemPositionHasChanged:
            self.sync_model()
            scene = self.scene()
            if scene is not None and hasattr(scene, "item_moved"):
                scene.item_moved.emit(self)
        return super().itemChange(change, value)

    def sync_model(self) -> None:  # pragma: no cover - überschrieben
        raise NotImplementedError

    def _paint_selection(self, painter: QPainter, rect: QRectF) -> None:
        if self.isSelected():
            pen = QPen(QColor("#0078d7"), 0, Qt.DashLine)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(rect)


class MapItem(_BaseItem):
    """Hintergrundkarte (PNG/JPG/TIFF als Pixmap, SVG als Renderer).

    Die Drehung ist nicht-destruktiv: Sie wird nur als
    ``rotation``-Transformation gehalten (Festlegung 10.5).
    """

    def __init__(self, model: MapImage, file_path: Path) -> None:
        super().__init__()
        self.model = model
        self._renderer: QSvgRenderer | None = None
        self._pixmap: QPixmap | None = None

        if file_path.suffix.lower() == ".svg":
            self._renderer = QSvgRenderer(str(file_path))
            self._size = self._renderer.defaultSize()
        else:
            self._pixmap = load_pixmap(file_path)
            self._size = self._pixmap.size()

        # Drehung um den Kartenmittelpunkt
        self.setTransformOriginPoint(self._size.width() / 2,
                                     self._size.height() / 2)
        self.setPos(model.x, model.y)
        self.setRotation(model.rotation)
        self.setScale(model.scale)
        self.setZValue(model.z)

    @property
    def is_valid(self) -> bool:
        if self._renderer is not None:
            return self._renderer.isValid()
        return self._pixmap is not None and not self._pixmap.isNull()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._size.width(), self._size.height())

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        if self._renderer is not None:
            self._renderer.render(painter, self.boundingRect())
        elif self._pixmap is not None:
            painter.drawPixmap(0, 0, self._pixmap)
        self._paint_selection(painter, self.boundingRect())

    def sync_model(self) -> None:
        pos = self.pos()
        self.model.x, self.model.y = pos.x(), pos.y()
        self.model.rotation = self.rotation()
        self.model.scale = self.scale()

    def set_rotation_deg(self, degrees: float) -> None:
        self.setRotation(degrees % 360.0)
        self.sync_model()


class EchelonItem(QGraphicsItem):
    """Zeichnet die Größenkennzeichnung mittig über dem Symbol."""

    UNIT = 12.0

    def __init__(self, parent: QGraphicsItem) -> None:
        super().__init__(parent)
        self._marks: list[str] = []

    def set_marks(self, marks: list[str]) -> None:
        self.prepareGeometryChange()
        self._marks = marks
        self.update()

    def boundingRect(self) -> QRectF:
        if not self._marks:
            return QRectF()
        u = self.UNIT
        width = u * 1.6 * (len(self._marks) - 1) + u * 1.6
        return QRectF(-width / 2, -u, width, u * 2)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        if not self._marks:
            return
        painter.setRenderHint(QPainter.Antialiasing, True)
        u = self.UNIT
        pen = QPen(QColor("black"), u * 0.2)
        spacing = u * 1.6
        x = -spacing * (len(self._marks) - 1) / 2.0
        for mark in self._marks:
            painter.setPen(pen)
            if mark == "dot":
                painter.setBrush(QColor("black"))
                painter.drawEllipse(QPointF(x, 0), u * 0.45, u * 0.45)
            elif mark in ("ring", "ringslash"):
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(x, 0), u * 0.45, u * 0.45)
                if mark == "ringslash":
                    d = u * 0.6
                    painter.drawLine(QPointF(x - d, d), QPointF(x + d, -d))
            elif mark == "bar":
                painter.drawLine(QPointF(x, -u * 0.7), QPointF(x, u * 0.7))
            elif mark == "x":
                d = u * 0.6
                painter.drawLine(QPointF(x - d, -d), QPointF(x + d, d))
                painter.drawLine(QPointF(x - d, d), QPointF(x + d, -d))
            x += spacing


class SymbolItem(_BaseItem):
    """Taktisches Zeichen mit Größenkennzeichnung und Beschriftung."""

    def __init__(self, model: Symbol, file_path: Path,
                 convention: str = "BW") -> None:
        super().__init__()
        self.model = model
        self._convention = convention
        self._renderer: QSvgRenderer | None = None
        self._pixmap: QPixmap | None = None

        if file_path.suffix.lower() == ".svg":
            self._renderer = QSvgRenderer(str(file_path))
            self._size = self._renderer.defaultSize()
        else:
            self._pixmap = load_pixmap(file_path)
            self._size = self._pixmap.size()

        self.setTransformOriginPoint(self._size.width() / 2,
                                     self._size.height() / 2)

        self._echelon_item = EchelonItem(self)
        self._label_item = QGraphicsSimpleTextItem(self)
        font = self._label_item.font()
        font.setPointSizeF(14.0)
        self._label_item.setFont(font)

        self.setPos(model.x, model.y)
        self.setRotation(model.rotation)
        self.setScale(model.scale)
        self.setZValue(model.z)
        self.refresh_decorations()

    @property
    def is_valid(self) -> bool:
        if self._renderer is not None:
            return self._renderer.isValid()
        return self._pixmap is not None and not self._pixmap.isNull()

    def boundingRect(self) -> QRectF:
        return QRectF(0, 0, self._size.width(), self._size.height())

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)
        painter.setRenderHint(QPainter.Antialiasing, True)
        if self._renderer is not None:
            self._renderer.render(painter, self.boundingRect())
        elif self._pixmap is not None:
            painter.drawPixmap(
                0, 0,
                self._pixmap.scaled(self._size, Qt.KeepAspectRatio,
                                    Qt.SmoothTransformation))
        self._paint_selection(painter, self.boundingRect())

    def sync_model(self) -> None:
        pos = self.pos()
        self.model.x, self.model.y = pos.x(), pos.y()
        self.model.rotation = self.rotation()
        self.model.scale = self.scale()

    # ------------------------------------------------------------------
    # Größenkennzeichnung / Beschriftung
    # ------------------------------------------------------------------
    def set_convention(self, convention: str) -> None:
        self._convention = convention
        self.refresh_decorations()

    def refresh_decorations(self) -> None:
        """Positioniert Echelon (mittig oberhalb) und Beschriftung
        (unterhalb) gemäß Konvention (Anforderung 3.5)."""
        marks = echelon_mod.marks_for(self._convention, self.model.echelon)
        self._echelon_item.set_marks(marks)
        w = self._size.width()
        h = self._size.height()
        self._echelon_item.setPos(w / 2, -EchelonItem.UNIT * 1.4)

        self._label_item.setText(self.model.label)
        if self.model.label:
            text_rect = self._label_item.boundingRect()
            self._label_item.setPos((w - text_rect.width()) / 2, h + 4)
        self.update()

    def apply_model_transform(self) -> None:
        """Übernimmt Transformationen aus dem Modell (z. B. nach Undo)."""
        self.setPos(self.model.x, self.model.y)
        self.setRotation(self.model.rotation)
        self.setScale(self.model.scale)
        self.refresh_decorations()

    def reload_asset(self, file_path: Path) -> None:
        """Tauscht die Symboldatei aus (z. B. andere Windstärke)."""
        self.prepareGeometryChange()
        if file_path.suffix.lower() == ".svg":
            self._renderer = QSvgRenderer(str(file_path))
            self._pixmap = None
            self._size = self._renderer.defaultSize()
        else:
            self._pixmap = load_pixmap(file_path)
            self._renderer = None
            self._size = self._pixmap.size()
        self.setTransformOriginPoint(self._size.width() / 2,
                                     self._size.height() / 2)
        self.refresh_decorations()
        self.update()


class _PointsItem(_BaseItem):
    """Basis für Objekte aus einer Punktfolge (Pfeile, Flächen).

    Item-Ursprung ist der erste Punkt; alle Stützpunkte lassen sich
    bei ausgewähltem Objekt einzeln mit der Maus verschieben.
    """

    HANDLE_RADIUS = 9.0

    def __init__(self, model) -> None:
        super().__init__()
        self.model = model
        self._drag_index: int | None = None
        self._drag_old: list | None = None
        if model.points:
            self.setPos(model.points[0][0], model.points[0][1])
        self.setZValue(model.z)

    # ------------------------------------------------------------------
    def _local_points(self) -> list[QPointF]:
        if not self.model.points:
            return [QPointF(0, 0)]
        x0, y0 = self.model.points[0]
        return [QPointF(x - x0, y - y0) for x, y in self.model.points]

    def geometry(self) -> list:
        return [list(p) for p in self.model.points]

    def set_geometry(self, points: list) -> None:
        self.prepareGeometryChange()
        self.model.points = [list(p) for p in points]
        # setPos löst itemChange/sync_model aus; Werte sind konsistent.
        self.setPos(points[0][0], points[0][1])
        self.update()

    def sync_model(self) -> None:
        if not self.model.points:
            return
        pos = self.pos()
        dx = pos.x() - self.model.points[0][0]
        dy = pos.y() - self.model.points[0][1]
        if dx or dy:
            self.model.points = [[x + dx, y + dy]
                                 for x, y in self.model.points]

    def refresh_style(self) -> None:
        self.prepareGeometryChange()
        self.update()

    def _paint_handles(self, painter: QPainter) -> None:
        painter.setPen(QPen(QColor("#0078d7"), 1))
        painter.setBrush(QColor(255, 255, 255, 220))
        for point in self._local_points():
            painter.drawEllipse(point, self.HANDLE_RADIUS,
                                self.HANDLE_RADIUS)

    # ------------------------------------------------------------------
    # Stützpunkte mit der Maus verschieben
    # ------------------------------------------------------------------
    def _point_index_at(self, pos: QPointF) -> int | None:
        grab = self.HANDLE_RADIUS * 1.6
        for index, point in enumerate(self._local_points()):
            if math.hypot(pos.x() - point.x(), pos.y() - point.y()) <= grab:
                return index
        return None

    def mousePressEvent(self, event) -> None:
        if self.isSelected() and event.button() == Qt.LeftButton:
            index = self._point_index_at(event.pos())
            if index is not None:
                self._drag_index = index
                self._drag_old = self.geometry()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._drag_index is not None:
            scene_pos = event.scenePos()
            snap = getattr(self.scene(), "snap_to_grid", None)
            if snap:
                scene_pos = snap(scene_pos)
            points = self.geometry()
            points[self._drag_index] = [scene_pos.x(), scene_pos.y()]
            self.set_geometry(points)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._drag_index is not None:
            old, new = self._drag_old, self.geometry()
            self._drag_index = None
            self._drag_old = None
            if old != new:
                scene = self.scene()
                if scene is not None and hasattr(scene, "undo_stack"):
                    from taktik.ui.commands import PointsGeometryCommand
                    scene.undo_stack.push(
                        PointsGeometryCommand(self, old, new))
            event.accept()
            return
        super().mouseReleaseEvent(event)


class ArrowItem(_PointsItem):
    """Pfeil für Bewegungs-/Angriffsrichtungen (Erweiterung 3.6).

    Unterstützt mehrere Stützpunkte, glatte Kurvenführung (``curved``)
    und einen breiten Umrisspfeil (``style`` "breit").
    """

    def __init__(self, model: Arrow) -> None:
        super().__init__(model)

    # ------------------------------------------------------------------
    def _head_size(self) -> float:
        if self.model.style == "breit":
            return self._body_width() * 1.7
        return max(self.model.width * 3.5, 12.0)

    def _body_width(self) -> float:
        return max(self.model.width * 4.0, 18.0)

    def _center_path(self, trim_head: bool = False) -> QPainterPath:
        """Linienführung durch die Stützpunkte (Polyline oder Kurve)."""
        pts = self._local_points()
        end = pts[-1]
        if trim_head and len(pts) >= 2:
            prev = pts[-2]
            vec = end - prev
            length = math.hypot(vec.x(), vec.y())
            if length > 1e-6:
                trim = min(self._head_size() * 0.8, length)
                end = QPointF(end.x() - vec.x() / length * trim,
                              end.y() - vec.y() / length * trim)
        path = QPainterPath(pts[0])
        if self.model.curved and len(pts) > 2:
            # Glatte Kurve: Stützpunkte als Kontrollpunkte, Übergänge
            # an den Segmentmitten
            for i in range(1, len(pts) - 1):
                nxt = end if i + 1 == len(pts) - 1 else pts[i + 1]
                mid = QPointF((pts[i].x() + nxt.x()) / 2,
                              (pts[i].y() + nxt.y()) / 2)
                path.quadTo(pts[i], mid)
            path.lineTo(end)
        else:
            for p in pts[1:-1]:
                path.lineTo(p)
            path.lineTo(end)
        return path

    def _head_polygon(self) -> QPolygonF:
        pts = self._local_points()
        if len(pts) < 2:
            return QPolygonF()
        tip, prev = pts[-1], pts[-2]
        angle = math.atan2(tip.y() - prev.y(), tip.x() - prev.x())
        head = self._head_size()
        spread = math.radians(24 if self.model.style == "linie" else 30)
        p1 = QPointF(tip.x() - head * math.cos(angle - spread),
                     tip.y() - head * math.sin(angle - spread))
        p2 = QPointF(tip.x() - head * math.cos(angle + spread),
                     tip.y() - head * math.sin(angle + spread))
        return QPolygonF([tip, p1, p2])

    def _pattern_amplitude(self) -> float:
        return max(self.model.width * 2.2, 9.0)

    def _pattern_period(self) -> float:
        return max(self.model.width * 5.0, 26.0)

    def _walk_geometry(self):
        """Bogenlängen-Geometrie der Polylinie.

        Liefert ``(total, at)``: Gesamtlänge und eine Funktion, die zu
        einer Bogenlänge Punkt und Normale ``(x, y, nx, ny)`` liefert –
        oder ``(0, None)``, wenn keine Linie vorhanden ist.
        """
        pts = self._local_points()
        segs = []
        total = 0.0
        for a, b in zip(pts, pts[1:]):
            d = math.hypot(b.x() - a.x(), b.y() - a.y())
            if d < 1e-9:
                continue
            segs.append((a, b, d, total))
            total += d
        if total < 1e-6 or not segs:
            return 0.0, None

        def at(dist: float):
            dist = max(0.0, min(total, dist))
            for a, b, d, start in segs:
                if dist <= start + d:
                    t = (dist - start) / d
                    ux, uy = (b.x() - a.x()) / d, (b.y() - a.y()) / d
                    return (a.x() + (b.x() - a.x()) * t,
                            a.y() + (b.y() - a.y()) * t, -uy, ux)
            a, b, d, start = segs[-1]
            ux, uy = (b.x() - a.x()) / d, (b.y() - a.y()) / d
            return b.x(), b.y(), -uy, ux

        return total, at

    def _tick_lines(self) -> list[tuple[QPointF, QPointF, QPointF | None]]:
        """Querstriche für die Strichmuster (A/B/Igel).

        Teilung Abstand : Strichlänge = 1:1; liefert je Strich
        ``(fuß, spitze, t_balken_richtung|None)``.
        """
        total, at = self._walk_geometry()
        if at is None:
            return []
        length = self._pattern_amplitude() * 1.6
        spacing = length            # 1:1
        side = -1.0 if self.model.pattern in ("striche_oben", "igel") \
            else 1.0
        ticks = []
        s = spacing
        while s < total - spacing * 0.25:
            px, py, nx, ny = at(s)
            foot = QPointF(px, py)
            tip = QPointF(px + nx * length * side,
                          py + ny * length * side)
            tee = None
            if self.model.pattern == "igel":
                # Richtung des T-Balkens = Tangente (senkrecht zur Normale)
                tee = QPointF(-ny, nx)
            ticks.append((foot, tip, tee))
            s += spacing * 2        # Mittenabstand: Länge + Lücke (1:1)
        return ticks

    def _decorated_path(self) -> QPainterPath:
        """Muster-Linienzug (Zinnen/Welle) entlang der Stützpunkte.

        Das Muster folgt der Polylinie und läuft über die Eckpunkte
        hinweg durch (gemeinsame Bogenlänge). Bei „glatt" wird die
        normale Linienführung zurückgegeben.
        """
        pts = self._local_points()
        if self.model.pattern == "glatt" or len(pts) < 2:
            return self._center_path()
        total, at = self._walk_geometry()
        if at is None:
            return self._center_path()

        amp = self._pattern_amplitude()
        period = self._pattern_period()
        path = QPainterPath()
        if self.model.pattern == "zinnen":
            half = period / 2
            px, py, nx, ny = at(0.0)
            path.moveTo(px + nx * amp, py + ny * amp)
            sign = 1
            s = 0.0
            while s < total - 1e-6:
                nxt = min(s + half, total)
                px, py, nx, ny = at(nxt)
                path.lineTo(px + nx * amp * sign, py + ny * amp * sign)
                if nxt < total - 1e-6:
                    path.lineTo(px + nx * amp * -sign, py + ny * amp * -sign)
                    sign = -sign
                s = nxt
        else:  # welle
            step = max(period / 10.0, 3.0)
            s = 0.0
            first = True
            while s <= total + 1e-6:
                px, py, nx, ny = at(s)
                off = amp * math.sin(2 * math.pi * s / period)
                point = QPointF(px + nx * off, py + ny * off)
                if first:
                    path.moveTo(point)
                    first = False
                else:
                    path.lineTo(point)
                s += step
        return path

    # ------------------------------------------------------------------
    def boundingRect(self) -> QRectF:
        rect = self._center_path().boundingRect()
        margin = self._head_size() + self.HANDLE_RADIUS + \
            self._body_width() / 2 + self._pattern_amplitude() * 1.7
        rect = rect.adjusted(-margin, -margin, margin, margin)
        if self.model.label:
            rect = rect.adjusted(-60, -30, 60, 10)
        return rect

    def shape(self) -> QPainterPath:
        stroker = QPainterPathStroker()
        width = self._body_width() if self.model.style == "breit" \
            else max(self.model.width * 3, 14.0)
        stroker.setWidth(width)
        return stroker.createStroke(self._center_path())

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing, True)
        color = QColor(self.model.color)
        pts = self._local_points()

        if len(pts) >= 2:
            if self.model.style == "breit":
                # Breiter Umrisspfeil: Körper + Spitze als eine Kontur
                stroker = QPainterPathStroker()
                stroker.setWidth(self._body_width())
                stroker.setCapStyle(Qt.FlatCap)
                stroker.setJoinStyle(Qt.RoundJoin)
                body = stroker.createStroke(self._center_path(trim_head=True))
                head = QPainterPath()
                head.addPolygon(self._head_polygon())
                head.closeSubpath()
                outline = body.united(head)
                pen = QPen(color, max(self.model.width * 0.7, 2.5))
                if self.model.dashed:
                    pen.setStyle(Qt.DashLine)
                painter.setPen(pen)
                fill = QColor(color)
                fill.setAlpha(45)
                painter.setBrush(QBrush(fill))
                painter.drawPath(outline)
            else:
                has_head = self.model.head == "spitze"
                pen = QPen(color, self.model.width, Qt.SolidLine,
                           Qt.RoundCap, Qt.RoundJoin)
                if self.model.dashed:
                    pen.setStyle(Qt.DashLine)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                tick_pattern = self.model.pattern in (
                    "striche_oben", "striche_unten", "igel")
                if self.model.pattern == "glatt" or tick_pattern:
                    painter.drawPath(self._center_path(trim_head=has_head))
                else:
                    painter.drawPath(self._decorated_path())
                if tick_pattern:
                    tick_pen = QPen(color, max(self.model.width * 0.85, 2.0),
                                    Qt.SolidLine, Qt.RoundCap)
                    painter.setPen(tick_pen)
                    tee_half = self._pattern_amplitude() * 0.55
                    for foot, tip, tee in self._tick_lines():
                        painter.drawLine(foot, tip)
                        if tee is not None:
                            painter.drawLine(
                                QPointF(tip.x() - tee.x() * tee_half,
                                        tip.y() - tee.y() * tee_half),
                                QPointF(tip.x() + tee.x() * tee_half,
                                        tip.y() + tee.y() * tee_half))
                if has_head:
                    painter.setPen(QPen(color, 1))
                    painter.setBrush(QBrush(color))
                    painter.drawPolygon(self._head_polygon())

        if self.model.label:
            mid = self._center_path().pointAtPercent(0.5)
            painter.setPen(QPen(QColor("black"), 1))
            font = painter.font()
            font.setPointSizeF(13.0)
            painter.setFont(font)
            painter.drawText(QRectF(mid.x() - 100, mid.y() - 34, 200, 24),
                             Qt.AlignCenter, self.model.label)

        if self.isSelected():
            self._paint_handles(painter)


class AreaItem(_PointsItem):
    """Flächenmarkierung (Schadenskonto, Einsatzabschnitt usw.)."""

    def __init__(self, model: Area) -> None:
        super().__init__(model)

    def _polygon_path(self) -> QPainterPath:
        pts = self._local_points()
        path = QPainterPath(pts[0])
        for p in pts[1:]:
            path.lineTo(p)
        path.closeSubpath()
        return path

    def boundingRect(self) -> QRectF:
        margin = self.HANDLE_RADIUS + self.model.width
        rect = self._polygon_path().boundingRect()
        return rect.adjusted(-margin, -margin, margin, margin)

    def shape(self) -> QPainterPath:
        # Gesamte Fläche anklickbar (inklusive Inneres)
        return self._polygon_path()

    def paint(self, painter: QPainter, option, widget=None) -> None:
        painter.setRenderHint(QPainter.Antialiasing, True)
        color = QColor(self.model.color)
        pen = QPen(color, self.model.width)
        if self.model.dashed:
            pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        fill = QColor(color)
        fill.setAlpha(50)
        painter.setBrush(QBrush(fill))
        painter.drawPath(self._polygon_path())

        if self.model.label:
            center = self._polygon_path().boundingRect().center()
            painter.setPen(QPen(QColor("black"), 1))
            font = painter.font()
            font.setPointSizeF(14.0)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                QRectF(center.x() - 120, center.y() - 12, 240, 24),
                Qt.AlignCenter, self.model.label)

        if self.isSelected():
            self._paint_handles(painter)
