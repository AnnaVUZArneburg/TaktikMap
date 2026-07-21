"""Geführtes „How-To"-Tutorial für die taktische Lagekarte.

Ein mehrstufiger Dialog, in dem der Guide „Safety“ neue Nutzer:innen
durch die wichtigsten Funktionen des Editors führt: Karten laden und
ausrichten, taktische Zeichen platzieren, Größenkennzeichnungen setzen,
Pfeile und Flächen einzeichnen sowie speichern und exportieren. Das
Tutorial erscheint beim ersten Start und ist jederzeit über das
Hilfe-Menü erreichbar.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QPainter, QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

GUIDE_NAME = "Safety"

# Maskottchen „Safety" – die Guide-Figur: Roboter mit dunklem
# Bildschirmgesicht (rote Augen, roter Mund), silbernem Rahmen mit
# Ohr-Scheiben, weißen Handschuhen mit Zeigestock sowie rot-goldenem Schild
# mit Schloss. Bewusst ohne Uniform/Abzeichen (schlichter Overall).
# Wird unverändert aus dem Ursprungsprojekt übernommen.
GUIDE_SVG = """
<svg xmlns='http://www.w3.org/2000/svg' width='128' height='128' viewBox='0 0 128 128'>
  <!-- Zeigestock (hinter der Hand) -->
  <line x1='28' y1='62' x2='8' y2='32' stroke='#37474f' stroke-width='2.6'
        stroke-linecap='round'/>
  <circle cx='7.5' cy='31' r='2.8' fill='#eceff1' stroke='#b0bec5' stroke-width='0.8'/>
  <!-- Ohr-Scheiben -->
  <circle cx='27' cy='40' r='9' fill='#6d787e'/>
  <circle cx='27' cy='40' r='5' fill='#525c61'/>
  <circle cx='101' cy='40' r='9' fill='#6d787e'/>
  <circle cx='101' cy='40' r='5' fill='#525c61'/>
  <!-- Kopf: silberner Rahmen, obere Deckplatte -->
  <rect x='44' y='8' width='40' height='7' rx='3.5' fill='#6d787e'/>
  <rect x='30' y='13' width='68' height='54' rx='11' fill='#98a4ab'/>
  <rect x='30' y='13' width='68' height='10' rx='5' fill='#aab6bd'/>
  <!-- Bildschirmgesicht -->
  <rect x='36' y='19' width='56' height='42' rx='7' fill='#0b0f12'/>
  <!-- rote, halb geschlossene Augen -->
  <ellipse cx='51' cy='38' rx='9' ry='6.5' fill='#ff2d2d'/>
  <ellipse cx='77' cy='38' rx='9' ry='6.5' fill='#ff2d2d'/>
  <rect x='40' y='28' width='22' height='7' fill='#0b0f12'/>
  <rect x='66' y='28' width='22' height='7' fill='#0b0f12'/>
  <circle cx='54' cy='38.5' r='1.6' fill='#ff8a80'/>
  <circle cx='80' cy='38.5' r='1.6' fill='#ff8a80'/>
  <!-- roter Mund -->
  <rect x='56' y='51' width='16' height='3.6' rx='1.8' fill='#ff2d2d'/>
  <!-- Hals -->
  <rect x='58' y='67' width='12' height='6' fill='#556066'/>
  <!-- Arme (Overall-Farbe), hinter dem Rumpf angesetzt -->
  <path d='M46 80 L30 64' stroke='#5b7247' stroke-width='8' stroke-linecap='round'/>
  <path d='M82 80 L95 90' stroke='#5b7247' stroke-width='8' stroke-linecap='round'/>
  <!-- Rumpf: schlichter Overall -->
  <rect x='42' y='73' width='44' height='34' rx='8' fill='#5b7247'/>
  <rect x='63' y='73' width='2.5' height='22' fill='#4a5e3a'/>
  <!-- Gürtel mit S-Schnalle -->
  <rect x='42' y='95' width='44' height='7' fill='#4e342e'/>
  <rect x='57' y='93.5' width='14' height='10' rx='2' fill='#c62828'
        stroke='#ffc107' stroke-width='1.6'/>
  <path d='M66.5 95.8 q-2.5 -1.4 -4.6 0 q-1.6 1.3 0.2 2.5 l3.4 1.6
           q1.8 1.2 0.2 2.5 q-2.1 1.4 -4.6 0'
        fill='none' stroke='#ffd54f' stroke-width='1.7' stroke-linecap='round'/>
  <!-- weiße Handschuhe -->
  <circle cx='28' cy='62' r='6' fill='#ffffff' stroke='#cfd8dc' stroke-width='1'/>
  <circle cx='96' cy='91' r='6' fill='#ffffff' stroke='#cfd8dc' stroke-width='1'/>
  <!-- rot-goldenes Schild mit goldenem Schloss -->
  <path d='M103 84 l17 5.5 v11 q0 12 -17 16.5 q-17 -4.5 -17 -16.5 v-11 z'
        fill='#c62828' stroke='#ffc107' stroke-width='3'/>
  <path d='M99 99 v-4 a4 4 0 0 1 8 0 v4' fill='none'
        stroke='#ffc107' stroke-width='2.4'/>
  <rect x='96.5' y='99' width='13' height='10' rx='2' fill='#ffc107'/>
  <circle cx='103' cy='103.5' r='1.8' fill='#7a5600'/>
  <rect x='102.2' y='103.5' width='1.6' height='3.4' fill='#7a5600'/>
  <!-- Beine und schwarze Stiefel -->
  <rect x='50' y='107' width='10' height='9' fill='#5b7247'/>
  <rect x='68' y='107' width='10' height='9' fill='#5b7247'/>
  <rect x='46' y='114' width='16' height='8' rx='3' fill='#212121'/>
  <rect x='66' y='114' width='16' height='8' rx='3' fill='#212121'/>
  <rect x='44' y='120' width='19' height='4' rx='2' fill='#000000'/>
  <rect x='65' y='120' width='19' height='4' rx='2' fill='#000000'/>
</svg>
"""



@dataclass
class Step:
    title: str
    body: str


# Die inhaltlichen Schritte des Tutorials – decken die Kernfunktionen ab.
STEPS: List[Step] = [
    Step(
        "Willkommen",
        "Hallo, ich bin Safety – Ihr Guide durch die taktische Lagekarte. "
        "Mit diesem Werkzeug stellen Sie Einsatzlagen nach den Konventionen "
        "von Bundeswehr und THW dar: Karten laden, taktische Zeichen "
        "platzieren, Lagen einzeichnen und exportieren.\n\n"
        "Ich führe Sie durch die wichtigsten Funktionen. Sie können mich "
        "jederzeit über „Hilfe → Tutorial“ erneut aufrufen.",
    ),
    Step(
        "1 · Karte laden",
        "Beginnen Sie mit „Karte importieren“ in der Werkzeugleiste (oder "
        "„Datei → Karte importieren…“). Geladen werden Rasterkarten und "
        "Luftbilder (PNG, JPG, TIFF) sowie Vektorkarten (SVG). Die Karte "
        "liegt als Hintergrund unter allen Zeichen.",
    ),
    Step(
        "2 · Karte ausrichten (norden)",
        "Wählen Sie die Karte aus und stellen Sie im Panel „Eigenschaften“ "
        "unter „Drehung“ den Winkel in Grad ein, bis die Karte genordet ist. "
        "Mit „Nach Norden ausrichten (0°)“ setzen Sie die Drehung zurück. "
        "Die Drehung ist verlustfrei – die Originaldatei bleibt unverändert.",
    ),
    Step(
        "3 · Symbolordner öffnen",
        "Über „Datei → Symbolordner öffnen…“ laden Sie Ihre taktischen "
        "Zeichen. Ein Startersatz (Führung, Infanterie, Logistik, Sanität, "
        "THW, BOS, Luft, See, Ereignisse) ist bereits enthalten. Nutzen Sie "
        "das Suchfeld und die Kategorien, um schnell das richtige Zeichen "
        "zu finden; per Rechtsklick vergeben Sie Favoriten.",
    ),
    Step(
        "4 · Zeichen platzieren",
        "Ziehen Sie ein Symbol aus der Bibliothek per Drag-and-Drop auf die "
        "Karte – oder ein Doppelklick fügt es in der Mitte ein. Ausgewählte "
        "Zeichen lassen sich verschieben, drehen, skalieren, duplizieren, "
        "beschriften und löschen (Menü „Bearbeiten“).",
    ),
    Step(
        "5 · Größe & Konvention",
        "Im Panel „Eigenschaften“ wählen Sie unter „Größe“ die "
        "Größenkennzeichnung (Trupp, Gruppe, Zug, Kompanie … bis "
        "Heeresgruppe). Sie wird automatisch über dem Zeichen ergänzt. "
        "Über das Menü „Konvention“ schalten Sie zwischen Bundeswehr (APP-6) "
        "und THW/BOS um. Bei Windpfeilen stellen Sie hier die Windstärke ein.",
    ),
    Step(
        "6 · Pfeile & Flächen",
        "Mit „Pfeil zeichnen“ (Taste P) markieren Sie Bewegungs- und "
        "Angriffsrichtungen: Punkte anklicken (oder in einem Zug ziehen), "
        "Doppelklick/Enter schließt ab. Wählbar sind gerade/gebogene und "
        "breite Pfeile. Mit „Fläche zeichnen“ (Taste F) markieren Sie "
        "Einsatzabschnitte oder Schadensgebiete als Polygon.",
    ),
    Step(
        "7 · Ebenen",
        "Das Panel „Ebenen“ blendet Ebenen ein/aus und ordnet sie per "
        "Drag-and-Drop. Die oberste Ebene liegt vorn. So trennen Sie z. B. "
        "eigene Kräfte, gegnerische Lage und Gefahren sauber voneinander.",
    ),
    Step(
        "8 · Speichern & Export",
        "Speichern Sie Ihr Projekt über „Datei → Speichern“ im "
        ".taktik-Format (enthält Karten und Symbole). Die fertige Lagekarte "
        "exportieren Sie über „Als PNG exportieren“ – wahlweise auch als SVG.",
    ),
    Step(
        "Fertig!",
        "Das waren die Grundlagen. Legen Sie los – und rufen Sie mich, "
        "Safety, bei Bedarf jederzeit erneut über das Hilfe-Menü. Viel "
        "Erfolg bei Ihrer Lagedarstellung!",
    ),
]


class TutorialDialog(QDialog):
    """Schrittweiser How-To-Dialog."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("How-To · Tutorial")
        self.resize(520, 360)
        self._index = 0

        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        avatar = QLabel()
        avatar.setPixmap(self._guide_pixmap())
        avatar.setFixedSize(72, 72)
        avatar.setScaledContents(True)
        header.addWidget(avatar)
        header.addWidget(QLabel(f"<b>{GUIDE_NAME}</b> · Ihr Guide"))
        header.addStretch()
        layout.addLayout(header)

        self._stack = QStackedWidget()
        for step in STEPS:
            self._stack.addWidget(self._make_page(step))
        layout.addWidget(self._stack, 1)

        self._progress = QLabel()
        layout.addWidget(self._progress)

        controls = QHBoxLayout()
        self.chk_startup = QCheckBox("Beim Start anzeigen")
        self.chk_startup.setChecked(True)
        controls.addWidget(self.chk_startup)
        controls.addStretch()
        self.btn_back = QPushButton("Zurück")
        self.btn_next = QPushButton("Weiter")
        self.btn_back.clicked.connect(lambda: self._go(-1))
        self.btn_next.clicked.connect(self._on_next)
        controls.addWidget(self.btn_back)
        controls.addWidget(self.btn_next)
        layout.addLayout(controls)

        self._update()

    @staticmethod
    def _guide_pixmap(size: int = 128) -> QPixmap:
        renderer = QSvgRenderer(QByteArray(GUIDE_SVG.encode("utf-8")))
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return pixmap

    def _make_page(self, step: Step) -> QWidget:
        page = QWidget()
        box = QVBoxLayout(page)
        title = QLabel(f"<h2>{step.title}</h2>")
        body = QLabel(step.body)
        body.setWordWrap(True)
        body.setTextFormat(Qt.PlainText)
        box.addWidget(title)
        box.addWidget(body, 1)
        return page

    def _go(self, delta: int) -> None:
        self._index = max(0, min(self._index + delta, len(STEPS) - 1))
        self._update()

    def _on_next(self) -> None:
        if self._index >= len(STEPS) - 1:
            self.accept()
        else:
            self._go(1)

    def _update(self) -> None:
        self._stack.setCurrentIndex(self._index)
        self._progress.setText(f"Schritt {self._index + 1} von {len(STEPS)}")
        self.btn_back.setEnabled(self._index > 0)
        self.btn_next.setText(
            "Fertig" if self._index == len(STEPS) - 1 else "Weiter"
        )

    def show_on_startup(self) -> bool:
        return self.chk_startup.isChecked()
