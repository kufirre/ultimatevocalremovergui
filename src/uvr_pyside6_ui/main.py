import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QIODevice, QTextStream  # QFileDevice is in QtCore, but we don't need it here
from PySide6.QtGui import QFontDatabase
from pathlib import Path
# Import the generated resources module
from . import resources_rc # Assuming resources_rc.py is in the same directory
# We use a relative import here because it's within the same package
from .ui.main_window_view import MainWindowView


def run():
    """Initializes and runs the PySide6 application."""
    # resources_rc module is imported, so resources are registered.
    app = QApplication(sys.argv)

    app.setStyle("Fusion") # Apply Fusion style

    # Load custom fonts from QRC
    fonts_to_load_qrc = {
        "Century Gothic": ":/uvr/fonts/CenturyGothic.ttf",
        "Montserrat": ":/uvr/fonts/Montserrat.ttf",
    }

    for font_name, font_qrc_path in fonts_to_load_qrc.items():
        font_id = QFontDatabase.addApplicationFont(font_qrc_path)
        if font_id == -1:
            print(f"Warning: Failed to load font from QRC: {font_name} from {font_qrc_path}")
        else:
            loaded_font_families = QFontDatabase.applicationFontFamilies(font_id)
            if loaded_font_families:
                print(f"Successfully loaded font from QRC: {loaded_font_families[0]} (from {font_qrc_path})")
            else:
                print(f"Warning: Font loaded from QRC with ID {font_id} but no families found: {font_qrc_path}")

    # Load QSS stylesheet from QRC
    qss_file_path_qrc = ":/uvr/theme/style.qss"
    qss_file = QFile(qss_file_path_qrc)
    if not qss_file.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
        print(f"Warning: Could not open style.qss from QRC: {qss_file_path_qrc}. Error: {qss_file.errorString()}")
    else:
        stream = QTextStream(qss_file)
        app.setStyleSheet(stream.readAll())
        qss_file.close()
        print(f"Successfully loaded stylesheet from QRC: {qss_file_path_qrc}")

    main_window = MainWindowView()
    main_window.show()

    # Debug print removed
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
