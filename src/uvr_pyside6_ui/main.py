import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QIODevice, QTextStream
from PySide6.QtGui import QFontDatabase

from . import resources_rc
from .ui.main_window_view import MainWindowView
from .core import app_constants as ac


def run():
    """Initializes and runs the PySide6 application."""
    # Determine the base path of the application
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle, use PyInstaller's _MEIPASS
        BASE_PATH = sys._MEIPASS
    else:
        # If run as a script, use the directory of this file
        BASE_PATH = os.path.dirname(os.path.abspath(__file__))

    # Change the current working directory to the base path
    os.chdir(BASE_PATH)

    app = QApplication(sys.argv)
    app.setStyle(ac.FUSION_STYLE)

    # Load custom fonts from QRC
    fonts_to_load_qrc = {
        ac.CENTURY_GOTHIC_FONT: ac.QRC_CENTURY_GOTHIC_PATH,
        ac.MONTSERRAT_FONT: ac.QRC_MONTSERRAT_PATH,
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

    # Load main QSS stylesheet from QRC
    qss_file = QFile(ac.QRC_MAIN_STYLESHEET_PATH)
    if not qss_file.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
        print(f"Warning: Could not open style.qss from QRC: {ac.QRC_MAIN_STYLESHEET_PATH}. Error: {qss_file.errorString()}")
    else:
        stream = QTextStream(qss_file)
        main_stylesheet = stream.readAll()
        qss_file.close()
        print(f"Successfully loaded stylesheet from QRC: {ac.QRC_MAIN_STYLESHEET_PATH}")
    
    # Load progress bar stylesheet from QRC
    progress_qss_file = QFile(ac.QRC_PROGRESS_STYLESHEET_PATH)
    progress_stylesheet = ""
    
    if not progress_qss_file.open(QIODevice.OpenModeFlag.ReadOnly | QIODevice.OpenModeFlag.Text):
        print(f"Warning: Could not open progress_bars.qss from QRC: {ac.QRC_PROGRESS_STYLESHEET_PATH}. Error: {progress_qss_file.errorString()}")
    else:
        stream = QTextStream(progress_qss_file)
        progress_stylesheet = stream.readAll()
        progress_qss_file.close()
        print(f"Successfully loaded progress bar stylesheet from QRC: {ac.QRC_PROGRESS_STYLESHEET_PATH}")
        
    # Apply combined stylesheets
    app.setStyleSheet(main_stylesheet + "\n" + progress_stylesheet)

    main_window = MainWindowView()
    main_window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
