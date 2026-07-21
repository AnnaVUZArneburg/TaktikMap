"""Symbolbibliothek-Panel: Anzeige, Suche, Favoriten, Drag-and-Drop."""

from __future__ import annotations

from PySide6.QtCore import QMimeData, QSize, Qt, Signal
from PySide6.QtGui import QDrag, QIcon
from PySide6.QtWidgets import (QCheckBox, QComboBox, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMenu,
                               QVBoxLayout, QWidget)

from taktik.symbols.library import SymbolEntry, SymbolLibrary
from taktik.ui.map_view import SYMBOL_MIME


class _SymbolList(QListWidget):
    """Liste mit Drag-Unterstützung (eigener MIME-Typ)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setViewMode(QListWidget.IconMode)
        self.setIconSize(QSize(48, 48))
        self.setResizeMode(QListWidget.Adjust)
        self.setDragEnabled(True)
        self.setSpacing(6)
        self.setWordWrap(True)

    def startDrag(self, actions) -> None:
        item = self.currentItem()
        if item is None:
            return
        mime = QMimeData()
        mime.setData(SYMBOL_MIME,
                     item.data(Qt.UserRole).encode("utf-8"))
        drag = QDrag(self)
        drag.setMimeData(mime)
        icon = item.icon()
        if not icon.isNull():
            drag.setPixmap(icon.pixmap(48, 48))
        drag.exec(Qt.CopyAction)


class SymbolPanel(QWidget):
    """Bibliothek der taktischen Zeichen (Anforderungen 3.4, Kann: Suche,
    Favoriten)."""

    symbol_activated = Signal(str)   # Bibliotheksschlüssel (Doppelklick)

    def __init__(self, library: SymbolLibrary, parent=None) -> None:
        super().__init__(parent)
        self.library = library

        self._search = QLineEdit()
        self._search.setPlaceholderText("Symbol suchen …")
        self._search.setClearButtonEnabled(True)

        self._category = QComboBox()
        self._favorites_only = QCheckBox("Nur Favoriten")

        self._list = _SymbolList()
        self._list.setContextMenuPolicy(Qt.CustomContextMenu)

        self._hint = QLabel(
            "Kein Symbolordner geladen.\n"
            "Datei → Symbolordner öffnen …")
        self._hint.setAlignment(Qt.AlignCenter)
        self._hint.setWordWrap(True)

        filter_row = QHBoxLayout()
        filter_row.addWidget(self._category, 1)
        filter_row.addWidget(self._favorites_only)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self._search)
        layout.addLayout(filter_row)
        layout.addWidget(self._hint)
        layout.addWidget(self._list, 1)

        self._search.textChanged.connect(self.refresh)
        self._category.currentIndexChanged.connect(self.refresh)
        self._favorites_only.toggled.connect(self.refresh)
        self._list.itemDoubleClicked.connect(self._on_double_click)
        self._list.customContextMenuRequested.connect(self._on_context_menu)

        self.refresh_categories()

    # ------------------------------------------------------------------
    def refresh_categories(self) -> None:
        current = self._category.currentText()
        self._category.blockSignals(True)
        self._category.clear()
        self._category.addItem("Alle Kategorien", "")
        for cat in self.library.categories():
            self._category.addItem(cat, cat)
        index = self._category.findText(current)
        if index >= 0:
            self._category.setCurrentIndex(index)
        self._category.blockSignals(False)
        self.refresh()

    def refresh(self) -> None:
        self._list.clear()
        entries = self.library.search(
            text=self._search.text(),
            category=self._category.currentData() or "",
            favorites_only=self._favorites_only.isChecked(),
        )
        self._hint.setVisible(not self.library.entries)
        for entry in entries:
            item = QListWidgetItem(QIcon(str(entry.path)), entry.name)
            item.setData(Qt.UserRole, entry.key)
            tooltip = f"{entry.name}\nKategorie: {entry.category}"
            if entry.default_echelon:
                tooltip += f"\nStandardgröße: {entry.default_echelon}"
            if entry.key in self.library.favorites:
                tooltip += "\n★ Favorit"
            item.setToolTip(tooltip)
            self._list.addItem(item)

    def entry_by_key(self, key: str) -> SymbolEntry | None:
        for entry in self.library.entries:
            if entry.key == key:
                return entry
        return None

    # ------------------------------------------------------------------
    def _on_double_click(self, item: QListWidgetItem) -> None:
        self.symbol_activated.emit(item.data(Qt.UserRole))

    def _on_context_menu(self, pos) -> None:
        item = self._list.itemAt(pos)
        if item is None:
            return
        key = item.data(Qt.UserRole)
        menu = QMenu(self)
        is_fav = key in self.library.favorites
        action = menu.addAction(
            "Aus Favoriten entfernen" if is_fav else "Zu Favoriten hinzufügen")
        insert = menu.addAction("In Karte einfügen")
        chosen = menu.exec(self._list.mapToGlobal(pos))
        if chosen is action:
            self.library.toggle_favorite(key)
            self.refresh()
        elif chosen is insert:
            self.symbol_activated.emit(key)
