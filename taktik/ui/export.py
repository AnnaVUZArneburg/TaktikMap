"""Export der fertigen Lagekarte als PNG/SVG sowie Druck (3.7, Soll)."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtSvg import QSvgGenerator

from taktik.ui.scene import MapScene

EXPORT_MARGIN = 20.0
MAX_EXPORT_PIXELS = 8192


def _export_rect(scene: MapScene) -> QRectF:
    rect = scene.content_rect()
    if rect.isEmpty():
        rect = QRectF(0, 0, 800, 600)
    return rect.adjusted(-EXPORT_MARGIN, -EXPORT_MARGIN,
                         EXPORT_MARGIN, EXPORT_MARGIN)


def _render(scene: MapScene, painter: QPainter, source: QRectF,
            target: QRectF) -> None:
    # Auswahl-Markierungen nicht mit exportieren
    selected = scene.selectedItems()
    scene.clearSelection()
    try:
        scene.render(painter, target, source)
    finally:
        for item in selected:
            item.setSelected(True)


def export_png(scene: MapScene, path: str | Path, scale: float = 1.0) -> bool:
    """Exportiert die Lagekarte als PNG (Abnahmekriterium)."""
    source = _export_rect(scene)
    width = min(int(source.width() * scale), MAX_EXPORT_PIXELS)
    height = min(int(source.height() * scale), MAX_EXPORT_PIXELS)
    image = QImage(QSize(max(width, 1), max(height, 1)),
                   QImage.Format_ARGB32)
    image.fill(Qt.white)
    painter = QPainter(image)
    painter.setRenderHints(QPainter.Antialiasing
                           | QPainter.SmoothPixmapTransform)
    _render(scene, painter, source, QRectF(0, 0, width, height))
    painter.end()
    return image.save(str(path), "PNG")


def export_svg(scene: MapScene, path: str | Path) -> bool:
    """Exportiert die Lagekarte als SVG (optionales Kriterium)."""
    source = _export_rect(scene)
    generator = QSvgGenerator()
    generator.setFileName(str(path))
    generator.setSize(QSize(int(source.width()), int(source.height())))
    generator.setViewBox(QRectF(0, 0, source.width(), source.height()))
    generator.setTitle("Taktische Lagekarte")
    painter = QPainter(generator)
    _render(scene, painter, source,
            QRectF(0, 0, source.width(), source.height()))
    painter.end()
    return True


def print_scene(scene: MapScene, printer) -> None:
    """Druckt die Lagekarte seitenfüllend (Soll-Anforderung)."""
    source = _export_rect(scene)
    painter = QPainter(printer)
    page = painter.viewport()
    factor = min(page.width() / source.width(),
                 page.height() / source.height())
    target = QRectF(0, 0, source.width() * factor,
                    source.height() * factor)
    _render(scene, painter, source, target)
    painter.end()
