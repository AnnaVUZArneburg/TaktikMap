"""Startpunkt: ``python -m taktik``."""

import sys


def main() -> int:
    from PySide6.QtWidgets import QApplication

    from taktik import APP_NAME
    from taktik.ui.main_window import MainWindow
    from taktik.ui.theme import apply_theme
    from taktik.ui.tutorial import guide_icon

    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setOrganizationName("Taktik")
    apply_theme(app)
    app.setWindowIcon(guide_icon())      # Maskottchen „Safety" als App-Icon

    window = MainWindow()
    window.show()

    # Optional: Projektdatei als Argument öffnen
    opened = False
    for arg in sys.argv[1:]:
        if arg.endswith(".taktik"):
            window.open_project(arg)
            opened = True
            break

    # Tutorial beim ersten Start (bzw. bis abgewählt) anzeigen
    if not opened:
        window.maybe_show_tutorial()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
