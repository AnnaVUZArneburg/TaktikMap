"""Einheitliches Erscheinungsbild: dezentes, helles Grau.

Die Anwendung nutzt bewusst nicht das System-Farbschema (unter
dunklen Desktops würde die Oberfläche sonst schwarz), sondern eine
eigene, einsatzorientierte Grau-Palette auf Basis des Fusion-Stils –
plattformübergreifend identisch.
"""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

# Abgestimmte Grautöne
WINDOW = "#d6d8da"        # Fensterflächen, Panels
PANEL = "#cfd1d3"         # Schaltflächen
BASE = "#f2f3f4"          # Eingabefelder, Listen
ALT_BASE = "#e6e8ea"      # alternierende Zeilen
TEXT = "#26282a"          # Text
DISABLED = "#8a8d90"      # deaktivierte Elemente
BORDER = "#b2b5b8"        # Rahmenlinien
HIGHLIGHT = "#4a6d96"     # Auswahl (gedecktes Stahlblau)
MAP_BACKGROUND = "#a8abae"  # Fläche um die Karte


def apply_theme(app: QApplication) -> None:
    """Wendet die Grau-Palette auf die gesamte Anwendung an."""
    app.setStyle("Fusion")

    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(WINDOW))
    palette.setColor(QPalette.WindowText, QColor(TEXT))
    palette.setColor(QPalette.Base, QColor(BASE))
    palette.setColor(QPalette.AlternateBase, QColor(ALT_BASE))
    palette.setColor(QPalette.Text, QColor(TEXT))
    palette.setColor(QPalette.PlaceholderText, QColor(DISABLED))
    palette.setColor(QPalette.Button, QColor(PANEL))
    palette.setColor(QPalette.ButtonText, QColor(TEXT))
    palette.setColor(QPalette.ToolTipBase, QColor(BASE))
    palette.setColor(QPalette.ToolTipText, QColor(TEXT))
    palette.setColor(QPalette.Highlight, QColor(HIGHLIGHT))
    palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
    palette.setColor(QPalette.Light, QColor("#e8eaec"))
    palette.setColor(QPalette.Midlight, QColor("#dcdee0"))
    palette.setColor(QPalette.Mid, QColor(BORDER))
    palette.setColor(QPalette.Dark, QColor("#9a9da0"))
    palette.setColor(QPalette.Shadow, QColor("#6e7174"))
    palette.setColor(QPalette.Link, QColor(HIGHLIGHT))
    for role in (QPalette.WindowText, QPalette.Text, QPalette.ButtonText):
        palette.setColor(QPalette.Disabled, role, QColor(DISABLED))
    palette.setColor(QPalette.Disabled, QPalette.Base, QColor(ALT_BASE))
    app.setPalette(palette)

    # Dezente Feinabstimmung einzelner Bereiche
    app.setStyleSheet(f"""
        QToolBar {{
            background: {WINDOW};
            border-bottom: 1px solid {BORDER};
            spacing: 2px;
            padding: 2px;
        }}
        QMenuBar {{
            background: {WINDOW};
            border-bottom: 1px solid {BORDER};
        }}
        QStatusBar {{
            background: {WINDOW};
            border-top: 1px solid {BORDER};
        }}
        QDockWidget::title {{
            background: {PANEL};
            padding: 4px 6px;
            border: 1px solid {BORDER};
        }}
        QToolTip {{
            background: {BASE};
            color: {TEXT};
            border: 1px solid {BORDER};
            padding: 3px;
        }}
    """)
