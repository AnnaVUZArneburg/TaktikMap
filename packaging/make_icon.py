"""Erzeugt das Windows-Icon der Anwendung aus dem Maskottchen „Safety".

Rendert das SVG (``taktik.ui.tutorial.GUIDE_SVG``) in mehreren
Auflösungen und schreibt eine Multi-Resolution-``.ico`` sowie ein
256×256-PNG. Aufruf::

    python packaging/make_icon.py

Die erzeugte ``packaging/taktik.ico`` wird von ``taktik.spec`` als
EXE-Icon eingebunden.
"""

from __future__ import annotations

import os
import struct
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))       # Repo-Root für 'import taktik'

from PySide6.QtCore import QBuffer, QIODevice  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402
SIZES = [16, 24, 32, 48, 64, 128, 256]


def _png_bytes(pixmap) -> bytes:
    buffer = QBuffer()
    buffer.open(QIODevice.WriteOnly)
    pixmap.save(buffer, "PNG")
    return bytes(buffer.data())


def build_ico(target: Path) -> None:
    from taktik.ui.tutorial import guide_pixmap

    images = [(size, _png_bytes(guide_pixmap(size))) for size in SIZES]

    # ICONDIR-Header
    header = struct.pack("<HHH", 0, 1, len(images))
    entries = b""
    offset = 6 + 16 * len(images)
    payload = b""
    for size, data in images:
        dim = 0 if size >= 256 else size          # 0 bedeutet 256 im ICO
        entries += struct.pack(
            "<BBBBHHII", dim, dim, 0, 0, 1, 32, len(data), offset)
        payload += data
        offset += len(data)
    target.write_bytes(header + entries + payload)

    # Zusätzlich ein PNG (praktisch für README/Store-Listing)
    (target.with_suffix(".png")).write_bytes(images[-1][1])


def main() -> int:
    app = QApplication(sys.argv)  # noqa: F841 - für QPixmap nötig
    target = HERE / "taktik.ico"
    build_ico(target)
    print(f"Icon geschrieben: {target} ({target.stat().st_size} Bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
