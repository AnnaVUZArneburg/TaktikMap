"""Symbolbibliothek: liest taktische Zeichen aus einem frei wählbaren Ordner.

Anforderung 3.4 des Lastenhefts: PNG- und SVG-Zeichen aus einer
Ordnerstruktur (Kap. 8) einlesen; optionale JSON-Metadaten je Symbol::

    {
      "name": "Führungsstelle",
      "kategorie": "Führung",
      "standardgroesse": "Zug"
    }

Dieses Modul ist Qt-frei; die Anzeige übernimmt
:mod:`taktik.ui.symbol_panel`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

SYMBOL_SUFFIXES = {".png", ".svg"}


@dataclass
class SymbolEntry:
    """Ein Symbol der Bibliothek."""

    path: Path
    name: str
    category: str
    default_echelon: str = ""

    @property
    def key(self) -> str:
        return str(self.path)


@dataclass
class SymbolLibrary:
    """Gescannte Symbolbibliothek mit Suche und Favoriten."""

    root: Path | None = None
    entries: list[SymbolEntry] = field(default_factory=list)
    favorites: set[str] = field(default_factory=set)

    def scan(self, root: str | Path) -> int:
        """Liest alle PNG/SVG-Symbole unterhalb von ``root`` ein.

        Die Kategorie ergibt sich aus dem Unterordner (oder den
        JSON-Metadaten); liefert die Anzahl gefundener Symbole.
        """
        self.root = Path(root)
        self.entries = []
        if not self.root.is_dir():
            return 0
        for path in sorted(self.root.rglob("*")):
            if path.suffix.lower() not in SYMBOL_SUFFIXES:
                continue
            meta = self._read_metadata(path)
            rel = path.relative_to(self.root)
            category = meta.get("kategorie") or (
                rel.parts[0] if len(rel.parts) > 1 else "Allgemein")
            self.entries.append(SymbolEntry(
                path=path,
                name=meta.get("name") or path.stem.replace("_", " "),
                category=category,
                default_echelon=meta.get("standardgroesse", ""),
            ))
        return len(self.entries)

    @staticmethod
    def _read_metadata(symbol_path: Path) -> dict:
        meta_path = symbol_path.with_suffix(".json")
        if meta_path.exists():
            try:
                data = json.loads(meta_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    return data
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    # ------------------------------------------------------------------
    # Suche / Kategorien / Favoriten
    # ------------------------------------------------------------------
    def categories(self) -> list[str]:
        return sorted({e.category for e in self.entries})

    def search(self, text: str = "", category: str = "",
               favorites_only: bool = False) -> list[SymbolEntry]:
        text = text.strip().lower()
        result = []
        for entry in self.entries:
            if category and entry.category != category:
                continue
            if favorites_only and entry.key not in self.favorites:
                continue
            if text and text not in entry.name.lower() \
                    and text not in entry.category.lower():
                continue
            result.append(entry)
        return result

    def toggle_favorite(self, key: str) -> bool:
        """Schaltet den Favoritenstatus um; liefert den neuen Zustand."""
        if key in self.favorites:
            self.favorites.discard(key)
            return False
        self.favorites.add(key)
        return True
