"""Taktik – Python-Tool zur taktischen Lagekarte.

Desktop-Anwendung zur Darstellung und Bearbeitung taktischer Lagen
auf Karten nach Bundeswehr- und THW-Konventionen.
"""

import sys
from pathlib import Path

__version__ = "0.1.0"
APP_NAME = "Taktik – Taktische Lagekarte"


def resource_path(relative: str) -> Path:
    """Pfad zu einer mitgelieferten Ressource (z. B. ``symbole``).

    Funktioniert sowohl bei normaler Ausführung als auch im
    PyInstaller-Bundle: dort werden mitgelieferte Dateien beim Start
    nach ``sys._MEIPASS`` entpackt.
    """
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / relative
    # Quellbaum: Ressourcen liegen neben dem Paketverzeichnis
    return Path(__file__).resolve().parent.parent / relative
