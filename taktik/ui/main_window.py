"""Hauptfenster: Menüleiste, Werkzeugleiste, Kartenansicht, Docks.

Deutschsprachige Oberfläche mit den im Lastenheft (Kap. 6) geforderten
Bereichen: Menüleiste, Werkzeugleiste, Kartenansicht, Symbolbibliothek,
Eigenschaftenfenster, Ebenenverwaltung.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QSettings, Qt
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtPrintSupport import QPrintDialog, QPrinter
from PySide6.QtWidgets import (QDockWidget, QFileDialog, QLabel, QMainWindow,
                               QMessageBox, QToolBar)

from taktik import APP_NAME
from taktik.core.model import Area, Arrow, Symbol, new_id
from taktik.core.project_io import ProjectStore
from taktik.symbols.library import SymbolLibrary
from taktik.ui import export as export_mod
from taktik.ui.commands import (AddAreaCommand, AddArrowCommand,
                                AddSymbolCommand, RemoveItemsCommand)
from taktik.ui.items import AreaItem, ArrowItem, MapItem, SymbolItem
from taktik.ui.layers_panel import LayersPanel
from taktik.ui.map_view import MapView
from taktik.ui.properties_panel import PropertiesPanel
from taktik.ui.scene import MapScene
from taktik.ui.symbol_panel import SymbolPanel

MAP_FILE_FILTER = (
    "Kartendateien (*.png *.jpg *.jpeg *.tif *.tiff *.svg);;"
    "Rasterbilder (*.png *.jpg *.jpeg *.tif *.tiff);;"
    "Vektorgrafiken (*.svg);;Alle Dateien (*)")
PROJECT_FILTER = "Taktik-Projekte (*.taktik)"


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1400, 900)

        from taktik.ui.tutorial import guide_icon
        self.setWindowIcon(guide_icon())

        self.store = ProjectStore()
        self.scene = MapScene(self.store)
        self.view = MapView(self.scene)
        self.setCentralWidget(self.view)

        self.library = SymbolLibrary()
        self.symbol_panel = SymbolPanel(self.library)
        self.properties_panel = PropertiesPanel(self.scene, self.library)
        self.layers_panel = LayersPanel(self.scene)

        self._dirty = False
        self._settings = QSettings()

        self._build_docks()
        self._build_actions()
        self._build_menus()
        self._build_toolbar()
        self._build_statusbar()
        self._connect()
        self._restore_symbol_dir()
        self._update_title()

    # ==================================================================
    # Aufbau
    # ==================================================================
    def _build_docks(self) -> None:
        def dock(title: str, widget, area) -> QDockWidget:
            d = QDockWidget(title, self)
            d.setObjectName(title)
            d.setWidget(widget)
            self.addDockWidget(area, d)
            return d

        self._symbol_dock = dock("Symbolbibliothek", self.symbol_panel,
                                 Qt.LeftDockWidgetArea)
        self._props_dock = dock("Eigenschaften", self.properties_panel,
                                Qt.RightDockWidgetArea)
        self._layers_dock = dock("Ebenen", self.layers_panel,
                                 Qt.RightDockWidgetArea)

    def _build_actions(self) -> None:
        def act(text: str, slot, shortcut=None) -> QAction:
            action = QAction(text, self)
            if shortcut:
                action.setShortcut(shortcut)
            action.triggered.connect(slot)
            return action

        self.act_new = act("&Neu", self.new_project, QKeySequence.New)
        self.act_open = act("Ö&ffnen …", self._open_dialog,
                            QKeySequence.Open)
        self.act_save = act("&Speichern", self.save_project,
                            QKeySequence.Save)
        self.act_save_as = act("Speichern &unter …", self._save_as_dialog,
                               QKeySequence.SaveAs)
        self.act_import_map = act("&Karte importieren …", self._import_map,
                                  "Ctrl+I")
        self.act_symbol_dir = act("S&ymbolordner öffnen …",
                                  self._choose_symbol_dir, "Ctrl+Shift+O")
        self.act_export_png = act("Als &PNG exportieren …", self._export_png,
                                  "Ctrl+E")
        self.act_export_svg = act("Als S&VG exportieren …", self._export_svg)
        self.act_print = act("&Drucken …", self._print, QKeySequence.Print)
        self.act_quit = act("&Beenden", self.close, QKeySequence.Quit)

        self.act_undo = self.scene.undo_stack.createUndoAction(
            self, "&Rückgängig")
        self.act_undo.setShortcut(QKeySequence.Undo)
        self.act_redo = self.scene.undo_stack.createRedoAction(
            self, "&Wiederholen")
        self.act_redo.setShortcut(QKeySequence.Redo)
        self.act_delete = act("&Löschen", self._delete_selection,
                              QKeySequence.Delete)
        self.act_duplicate = act("&Duplizieren", self._duplicate_selection,
                                 "Ctrl+D")

        # Zeichenwerkzeuge: Pfeile und Flächen
        self.act_arrow = QAction("&Pfeil zeichnen", self, checkable=True)
        self.act_arrow.setShortcut("P")
        self.act_arrow.setToolTip(
            "Pfeil einzeichnen: Punkte anklicken (oder in einem Zug "
            "ziehen), Doppelklick/Rechtsklick schließt ab, Esc bricht ab")
        self.act_arrow.toggled.connect(
            lambda on: self.view.set_draw_mode("arrow" if on else ""))
        self.act_line = QAction("&Linie zeichnen", self, checkable=True)
        self.act_line.setShortcut("L")
        self.act_line.setToolTip(
            "Linie einzeichnen (ohne Pfeilspitze): Punkte anklicken (oder "
            "in einem Zug ziehen), Doppelklick/Rechtsklick schließt ab. "
            "Muster (Zinnen/Welle) und Pfeilspitze über die Eigenschaften.")
        self.act_line.toggled.connect(
            lambda on: self.view.set_draw_mode("line" if on else ""))
        self.act_area = QAction("&Fläche zeichnen", self, checkable=True)
        self.act_area.setShortcut("F")
        self.act_area.setToolTip(
            "Fläche (Einsatzabschnitt/Schadensgebiet) einzeichnen: "
            "Eckpunkte anklicken, Doppelklick/Rechtsklick schließt ab, "
            "Esc bricht ab")
        self.act_area.toggled.connect(
            lambda on: self.view.set_draw_mode("area" if on else ""))

        self.act_grid = QAction("&Raster anzeigen", self, checkable=True)
        self.act_grid.setShortcut("Ctrl+G")
        self.act_grid.toggled.connect(self._toggle_grid)
        self.act_snap = QAction("Am Raster &fangen", self, checkable=True)
        self.act_snap.setShortcut("Ctrl+Shift+G")
        self.act_snap.toggled.connect(self._toggle_snap)
        self.act_zoom_fit = act("Auf &Inhalt zoomen", self._zoom_fit,
                                "Ctrl+0")
        self.act_zoom_reset = act("Zoom &zurücksetzen", self._zoom_reset,
                                  "Ctrl+1")

        # Konventionsumschaltung BW/THW (Festlegung 10.6)
        self.convention_group = QActionGroup(self)
        self.act_conv_bw = QAction("Bundeswehr (APP-6)", self, checkable=True)
        self.act_conv_thw = QAction("THW / BOS", self, checkable=True)
        for action in (self.act_conv_bw, self.act_conv_thw):
            self.convention_group.addAction(action)
        self.act_conv_bw.setChecked(True)
        self.act_conv_bw.triggered.connect(
            lambda: self.scene.set_convention("BW"))
        self.act_conv_thw.triggered.connect(
            lambda: self.scene.set_convention("THW"))

    def _build_menus(self) -> None:
        bar = self.menuBar()

        m_file = bar.addMenu("&Datei")
        for action in (self.act_new, self.act_open, self.act_save,
                       self.act_save_as):
            m_file.addAction(action)
        m_file.addSeparator()
        m_file.addAction(self.act_import_map)
        m_file.addAction(self.act_symbol_dir)
        m_file.addSeparator()
        m_file.addAction(self.act_export_png)
        m_file.addAction(self.act_export_svg)
        m_file.addAction(self.act_print)
        m_file.addSeparator()
        m_file.addAction(self.act_quit)

        m_edit = bar.addMenu("&Bearbeiten")
        for action in (self.act_undo, self.act_redo):
            m_edit.addAction(action)
        m_edit.addSeparator()
        m_edit.addAction(self.act_arrow)
        m_edit.addAction(self.act_line)
        m_edit.addAction(self.act_area)
        m_edit.addAction(self.act_duplicate)
        m_edit.addAction(self.act_delete)

        m_view = bar.addMenu("&Ansicht")
        m_view.addAction(self.act_grid)
        m_view.addAction(self.act_snap)
        m_view.addSeparator()
        m_view.addAction(self.act_zoom_fit)
        m_view.addAction(self.act_zoom_reset)
        m_view.addSeparator()
        for dock in (self._symbol_dock, self._props_dock, self._layers_dock):
            m_view.addAction(dock.toggleViewAction())

        m_conv = bar.addMenu("&Konvention")
        m_conv.addAction(self.act_conv_bw)
        m_conv.addAction(self.act_conv_thw)

        m_help = bar.addMenu("&Hilfe")
        m_help.addAction(QAction(
            "&Tutorial", self, triggered=self._show_tutorial))
        m_help.addSeparator()
        m_help.addAction(QAction(
            "Über &Taktik", self,
            triggered=lambda: QMessageBox.about(
                self, "Über Taktik",
                "Taktik – Python-Tool zur taktischen Lagekarte\n\n"
                "Darstellung von Einsatzlagen nach BW-/THW-Konventionen.")))

    def _build_toolbar(self) -> None:
        toolbar = QToolBar("Werkzeuge", self)
        toolbar.setObjectName("Werkzeuge")
        self.addToolBar(toolbar)
        for action in (self.act_new, self.act_open, self.act_save):
            toolbar.addAction(action)
        toolbar.addSeparator()
        toolbar.addAction(self.act_import_map)
        toolbar.addAction(self.act_export_png)
        toolbar.addSeparator()
        toolbar.addAction(self.act_arrow)
        toolbar.addAction(self.act_line)
        toolbar.addAction(self.act_area)
        toolbar.addSeparator()
        for action in (self.act_undo, self.act_redo, self.act_duplicate,
                       self.act_delete):
            toolbar.addAction(action)
        toolbar.addSeparator()
        toolbar.addAction(self.act_grid)
        toolbar.addAction(self.act_snap)
        toolbar.addAction(self.act_zoom_fit)

    def _build_statusbar(self) -> None:
        self._status_zoom = QLabel("Zoom: 100 %")
        self._status_rotation = QLabel("")
        self.statusBar().addPermanentWidget(self._status_rotation)
        self.statusBar().addPermanentWidget(self._status_zoom)
        self.statusBar().showMessage(
            "Karte importieren (Strg+I) und Zeichen aus der Bibliothek "
            "auf die Karte ziehen.")

    def _connect(self) -> None:
        self.scene.selectionChanged.connect(self._on_selection_changed)
        self.scene.item_moved.connect(
            lambda _item: self.properties_panel.sync_from_item())
        self.scene.project_changed.connect(self._mark_dirty)
        self.scene.undo_stack.indexChanged.connect(
            lambda _i: (self._mark_dirty(),
                        self.properties_panel.sync_from_item()))
        self.view.symbol_dropped.connect(self._insert_symbol_at)
        self.view.shape_drawn.connect(self._insert_shape)
        self.view.draw_mode_changed.connect(self._on_draw_mode_changed)
        self.view.zoom_changed.connect(
            lambda z: self._status_zoom.setText(f"Zoom: {z * 100:.0f} %"))
        self.symbol_panel.symbol_activated.connect(self._insert_symbol_center)
        self.layers_panel.layers_changed.connect(
            self.properties_panel.refresh_layers)

    # ==================================================================
    # Projekt
    # ==================================================================
    def new_project(self) -> None:
        if not self._confirm_discard():
            return
        self.store.new()
        self.scene.rebuild_from_project()
        self.layers_panel.refresh()
        self.properties_panel.set_item(None)
        self._set_convention_ui()
        self._dirty = False
        self._update_title()

    def open_project(self, path: str) -> None:
        try:
            self.store.load(path)
        except Exception as exc:  # defekte/fremde Datei sauber melden
            QMessageBox.critical(self, "Öffnen fehlgeschlagen",
                                 f"Projekt konnte nicht geladen werden:\n{exc}")
            return
        self.scene.rebuild_from_project()
        self.layers_panel.refresh()
        self.properties_panel.set_item(None)
        self._set_convention_ui()
        self._zoom_fit()
        self._dirty = False
        self._update_title()

    def _open_dialog(self) -> None:
        if not self._confirm_discard():
            return
        path, _ = QFileDialog.getOpenFileName(
            self, "Projekt öffnen", "", PROJECT_FILTER)
        if path:
            self.open_project(path)

    def save_project(self) -> bool:
        if self.store.path is None:
            return self._save_as_dialog()
        return self._do_save(self.store.path)

    def _save_as_dialog(self) -> bool:
        path, _ = QFileDialog.getSaveFileName(
            self, "Projekt speichern", "lagekarte.taktik", PROJECT_FILTER)
        if not path:
            return False
        if not path.endswith(".taktik"):
            path += ".taktik"
        return self._do_save(Path(path))

    def _do_save(self, path) -> bool:
        try:
            self.store.save(path)
        except Exception as exc:
            QMessageBox.critical(self, "Speichern fehlgeschlagen", str(exc))
            return False
        self._dirty = False
        self._update_title()
        self.statusBar().showMessage(f"Gespeichert: {path}", 5000)
        return True

    def _confirm_discard(self) -> bool:
        if not self._dirty:
            return True
        answer = QMessageBox.question(
            self, "Ungespeicherte Änderungen",
            "Das Projekt enthält ungespeicherte Änderungen. Speichern?",
            QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
        if answer == QMessageBox.Save:
            return self.save_project()
        return answer == QMessageBox.Discard

    def closeEvent(self, event) -> None:
        if self._confirm_discard():
            self.store.cleanup()
            event.accept()
        else:
            event.ignore()

    # ==================================================================
    # Karten / Symbole
    # ==================================================================
    def _import_map(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, "Karte importieren", "", MAP_FILE_FILTER)
        if not path:
            return
        item = self.scene.add_map_from_file(path)
        if item is None:
            QMessageBox.warning(self, "Karte importieren",
                                "Die Datei konnte nicht geladen werden.")
            return
        self._zoom_fit()
        self.statusBar().showMessage(
            "Karte geladen. Drehung über das Eigenschaftenfenster "
            "(Nordausrichtung).", 8000)

    def _choose_symbol_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(
            self, "Symbolordner wählen",
            str(self.library.root or Path.cwd()))
        if path:
            self._load_symbol_dir(path)

    def _load_symbol_dir(self, path: str) -> None:
        count = self.library.scan(path)
        self.symbol_panel.refresh_categories()
        self._settings.setValue("symbol_dir", path)
        self.statusBar().showMessage(
            f"{count} Symbole aus {path} geladen.", 5000)

    def _restore_symbol_dir(self) -> None:
        # Zuletzt genutzten Ordner oder mitgelieferten Startersatz laden
        stored = self._settings.value("symbol_dir", "")
        if stored and Path(stored).is_dir():
            self._load_symbol_dir(str(stored))
            return
        from taktik import resource_path
        bundled = resource_path("symbole")
        if bundled.is_dir():
            self._load_symbol_dir(str(bundled))

    # ------------------------------------------------------------------
    # Tutorial (Guide „Safety")
    # ------------------------------------------------------------------
    def _show_tutorial(self) -> None:
        from taktik.ui.tutorial import TutorialDialog

        dialog = TutorialDialog(self)
        dialog.chk_startup.setChecked(
            self._settings.value("show_tutorial", True, type=bool))
        dialog.exec()
        self._settings.setValue("show_tutorial", dialog.show_on_startup())

    def maybe_show_tutorial(self) -> None:
        """Zeigt das Tutorial beim Start, sofern nicht abgewählt."""
        if self._settings.value("show_tutorial", True, type=bool):
            self._show_tutorial()

    def _insert_symbol_at(self, key: str, scene_pos: QPointF) -> None:
        entry = self.symbol_panel.entry_by_key(key)
        if entry is None:
            return
        item = self.scene.create_symbol_item(entry, scene_pos)
        if item is None:
            QMessageBox.warning(self, "Symbol einfügen",
                                "Das Symbol konnte nicht geladen werden.")
            return
        self.scene.undo_stack.push(AddSymbolCommand(self.scene, item))

    def _insert_symbol_center(self, key: str) -> None:
        center = self.view.mapToScene(self.view.viewport().rect().center())
        self._insert_symbol_at(key, center)

    def _insert_shape(self, mode: str, points: list) -> None:
        if mode == "arrow":
            item = self.scene.create_arrow_item(points)
            self.scene.undo_stack.push(AddArrowCommand(self.scene, item))
        elif mode == "line":
            item = self.scene.create_arrow_item(
                points, color="#0060a0", head="keine")
            self.scene.undo_stack.push(AddArrowCommand(self.scene, item))
        elif mode == "area":
            item = self.scene.create_area_item(points)
            self.scene.undo_stack.push(AddAreaCommand(self.scene, item))

    def _on_draw_mode_changed(self, mode: str) -> None:
        for action, name in ((self.act_arrow, "arrow"),
                             (self.act_line, "line"),
                             (self.act_area, "area")):
            if action.isChecked() != (mode == name):
                action.setChecked(mode == name)
        messages = {
            "arrow": "Pfeilmodus: Punkte anklicken (oder in einem Zug "
                     "ziehen). Doppelklick/Rechtsklick/Enter schließt ab, "
                     "Esc bricht ab.",
            "line": "Linienmodus: Punkte anklicken (oder in einem Zug "
                    "ziehen). Doppelklick/Rechtsklick/Enter schließt ab, "
                    "Esc bricht ab. Muster/Spitze über die Eigenschaften.",
            "area": "Flächenmodus: Eckpunkte anklicken. Doppelklick/"
                    "Rechtsklick/Enter schließt die Fläche, Esc bricht ab.",
        }
        if mode in messages:
            self.statusBar().showMessage(messages[mode])
        else:
            self.statusBar().clearMessage()

    def _delete_selection(self) -> None:
        items = [i for i in self.scene.selectedItems()
                 if isinstance(i, (MapItem, SymbolItem, ArrowItem,
                                   AreaItem))]
        if items:
            self.scene.undo_stack.push(RemoveItemsCommand(self.scene, items))
            self.properties_panel.set_item(None)

    def _duplicate_selection(self) -> None:
        for item in list(self.scene.selectedItems()):
            if isinstance(item, SymbolItem):
                model = Symbol.from_dict(item.model.to_dict())
                model.id = new_id()
                model.x += 30.0
                model.y += 30.0
                clone = SymbolItem(model, self.store.asset_path(model.asset),
                                   self.store.project.convention)
                self.scene.undo_stack.push(
                    AddSymbolCommand(self.scene, clone))
            elif isinstance(item, ArrowItem):
                model = Arrow.from_dict(item.model.to_dict())
                model.id = new_id()
                model.points = [[x + 30.0, y + 30.0]
                                for x, y in model.points]
                self.scene.undo_stack.push(
                    AddArrowCommand(self.scene, ArrowItem(model)))
            elif isinstance(item, AreaItem):
                model = Area.from_dict(item.model.to_dict())
                model.id = new_id()
                model.points = [[x + 30.0, y + 30.0]
                                for x, y in model.points]
                self.scene.undo_stack.push(
                    AddAreaCommand(self.scene, AreaItem(model)))

    # ==================================================================
    # Ansicht / Export
    # ==================================================================
    def _toggle_grid(self, checked: bool) -> None:
        self.scene.grid_visible = checked
        self.view.viewport().update()

    def _toggle_snap(self, checked: bool) -> None:
        self.scene.snap_enabled = checked

    def _zoom_fit(self) -> None:
        rect = self.scene.content_rect()
        if not rect.isEmpty():
            self.view.fitInView(rect.adjusted(-20, -20, 20, 20),
                                Qt.KeepAspectRatio)
            self.view.zoom_changed.emit(self.view.transform().m11())

    def _zoom_reset(self) -> None:
        self.view.resetTransform()
        self.view.zoom_changed.emit(1.0)

    def _export_png(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Als PNG exportieren", "lagekarte.png", "PNG-Bild (*.png)")
        if not path:
            return
        if export_mod.export_png(self.scene, path, scale=2.0):
            self.statusBar().showMessage(f"Exportiert: {path}", 5000)
        else:
            QMessageBox.critical(self, "Export", "PNG-Export fehlgeschlagen.")

    def _export_svg(self) -> None:
        path, _ = QFileDialog.getSaveFileName(
            self, "Als SVG exportieren", "lagekarte.svg",
            "SVG-Grafik (*.svg)")
        if not path:
            return
        export_mod.export_svg(self.scene, path)
        self.statusBar().showMessage(f"Exportiert: {path}", 5000)

    def _print(self) -> None:
        printer = QPrinter(QPrinter.HighResolution)
        dialog = QPrintDialog(printer, self)
        if dialog.exec() == QPrintDialog.Accepted:
            export_mod.print_scene(self.scene, printer)

    # ==================================================================
    # Sonstiges
    # ==================================================================
    def _on_selection_changed(self) -> None:
        try:
            selected = self.scene.selectedItems()
        except RuntimeError:
            return   # Szene bereits zerstört (z. B. beim Beenden)
        items = [i for i in selected
                 if isinstance(i, (MapItem, SymbolItem, ArrowItem,
                                   AreaItem))]
        item = items[0] if len(items) == 1 else None
        self.properties_panel.set_item(item)
        if isinstance(item, (MapItem, SymbolItem)):
            self._status_rotation.setText(
                f"Drehung: {item.rotation():.1f} °")
        else:
            self._status_rotation.setText("")

    def _set_convention_ui(self) -> None:
        if self.store.project.convention == "THW":
            self.act_conv_thw.setChecked(True)
        else:
            self.act_conv_bw.setChecked(True)

    def _mark_dirty(self) -> None:
        self._dirty = True
        try:
            self._update_title()
        except RuntimeError:
            pass   # Fenster bereits zerstört (z. B. beim Beenden)

    def _update_title(self) -> None:
        name = self.store.path.name if self.store.path else "Unbenannt"
        marker = " *" if self._dirty else ""
        self.setWindowTitle(f"{name}{marker} – {APP_NAME}")
