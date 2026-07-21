"""Speichern und Laden des nativen Projektformats ``.taktik``.

Festlegung 10.2 im Lastenheft: Ein ``.taktik``-Projekt ist ein
ZIP-Container mit einer ``project.json`` (Szene, Objekte,
Transformationen) und den eingebetteten Karten- und Symboldateien
unter ``assets/``. Das Paket ist damit selbsttragend und portabel.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from pathlib import Path

from taktik.core.model import Project

PROJECT_JSON = "project.json"
ASSET_DIR = "assets"


class ProjectStore:
    """Verwaltet ein Projekt samt Arbeitsverzeichnis für Assets.

    Assets (Karten, Symbole) werden beim Hinzufügen in ein temporäres
    Arbeitsverzeichnis kopiert und beim Speichern in den ZIP-Container
    eingebettet. Beim Laden wird der Container dorthin entpackt.
    """

    def __init__(self) -> None:
        self.project = Project()
        self.path: Path | None = None      # zuletzt gespeicherte/geladene Datei
        self._workdir = Path(tempfile.mkdtemp(prefix="taktik-"))
        (self._workdir / ASSET_DIR).mkdir(exist_ok=True)

    # ------------------------------------------------------------------
    # Assets
    # ------------------------------------------------------------------
    @property
    def workdir(self) -> Path:
        return self._workdir

    def asset_path(self, asset: str) -> Path:
        """Absoluter Pfad eines Projekt-Assets im Arbeitsverzeichnis."""
        return self._workdir / asset

    def import_asset(self, source: str | Path) -> str:
        """Kopiert eine Datei ins Projekt und liefert den Asset-Pfad.

        Namenskollisionen werden durch Anhängen eines Zählers gelöst,
        damit unterschiedliche Dateien gleichen Namens koexistieren.
        """
        source = Path(source)
        target_dir = self._workdir / ASSET_DIR
        target = target_dir / source.name
        counter = 1
        while target.exists() and not _same_file(source, target):
            target = target_dir / f"{source.stem}_{counter}{source.suffix}"
            counter += 1
        if not target.exists():
            shutil.copy2(source, target)
        return f"{ASSET_DIR}/{target.name}"

    # ------------------------------------------------------------------
    # Speichern / Laden
    # ------------------------------------------------------------------
    def save(self, path: str | Path) -> None:
        """Schreibt das Projekt als ZIP-Container (.taktik)."""
        path = Path(path)
        used_assets = {m.asset for m in self.project.maps}
        used_assets |= {s.asset for s in self.project.symbols}
        used_assets.discard("")

        # Erst in eine temporäre Datei schreiben, dann atomar ersetzen,
        # damit ein Abbruch kein bestehendes Projekt zerstört.
        tmp = path.with_suffix(path.suffix + ".tmp")
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr(PROJECT_JSON, json.dumps(
                self.project.to_dict(), ensure_ascii=False, indent=2))
            for asset in sorted(used_assets):
                source = self.asset_path(asset)
                if source.exists():
                    zf.write(source, asset)
        tmp.replace(path)
        self.path = path

    def load(self, path: str | Path) -> None:
        """Lädt ein Projekt aus einem ZIP-Container (.taktik)."""
        path = Path(path)
        with zipfile.ZipFile(path) as zf:
            data = json.loads(zf.read(PROJECT_JSON).decode("utf-8"))
            for name in zf.namelist():
                # Nur reguläre Asset-Einträge entpacken (Zip-Slip vermeiden).
                if not name.startswith(f"{ASSET_DIR}/"):
                    continue
                rel = Path(name)
                if rel.is_absolute() or ".." in rel.parts:
                    continue
                target = self._workdir / rel
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(name) as src, open(target, "wb") as dst:
                    shutil.copyfileobj(src, dst)
        self.project = Project.from_dict(data)
        self.path = path

    def new(self) -> None:
        """Setzt auf ein leeres Projekt zurück."""
        self.project = Project()
        self.path = None

    def cleanup(self) -> None:
        shutil.rmtree(self._workdir, ignore_errors=True)


def _same_file(a: Path, b: Path) -> bool:
    try:
        return a.stat().st_size == b.stat().st_size and \
            a.read_bytes() == b.read_bytes()
    except OSError:
        return False
