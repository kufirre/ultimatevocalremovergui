import sys
import os
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QIODevice, QTextStream
from PySide6.QtGui import QFontDatabase

from . import resources_rc
from .ui.main_window_view import MainWindowView
from .core import app_constants as ac
from .core.logger_utils import UVRLogger, get_logger

# Configure logging early
UVRLogger.configure_logging()
logger = get_logger("main")


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

    # Load fonts from QRC
    try:
        font_id = QFontDatabase.addApplicationFont(ac.QRC_CENTURY_GOTHIC_PATH)
        if font_id != -1:
            logger.info(f"Successfully loaded font from QRC: {ac.CENTURY_GOTHIC_FONT} (from {ac.QRC_CENTURY_GOTHIC_PATH})")
        else:
            logger.warning(f"Failed to load font from QRC: {ac.QRC_CENTURY_GOTHIC_PATH}")
    except Exception as e:
        logger.error(f"Error loading Century Gothic font: {e}")

    try:
        font_id = QFontDatabase.addApplicationFont(ac.QRC_MONTSERRAT_PATH)
        if font_id != -1:
            logger.info(f"Successfully loaded font from QRC: {ac.MONTSERRAT_FONT} (from {ac.QRC_MONTSERRAT_PATH})")
        else:
            logger.warning(f"Failed to load font from QRC: {ac.QRC_MONTSERRAT_PATH}")
    except Exception as e:
        logger.error(f"Error loading Montserrat font: {e}")

    # Load main stylesheet from QRC
    try:
        qss_file = QFile(ac.QRC_MAIN_STYLESHEET_PATH)
        if qss_file.open(QIODevice.ReadOnly | QIODevice.Text):
            stream = QTextStream(qss_file)
            app.setStyleSheet(stream.readAll())
            logger.info(f"Successfully loaded stylesheet from QRC: {ac.QRC_MAIN_STYLESHEET_PATH}")
        else:
            logger.warning(f"Failed to open stylesheet file: {ac.QRC_MAIN_STYLESHEET_PATH}")
    except Exception as e:
        logger.error(f"Error loading main stylesheet: {e}")

    # Load progress bar stylesheet from QRC
    try:
        progress_qss_file = QFile(ac.QRC_PROGRESS_STYLESHEET_PATH)
        if progress_qss_file.open(QIODevice.ReadOnly | QIODevice.Text):
            stream = QTextStream(progress_qss_file)
            progress_stylesheet = stream.readAll()
            # Append to existing stylesheet
            app.setStyleSheet(app.styleSheet() + "\n" + progress_stylesheet)
            logger.info(f"Successfully loaded progress bar stylesheet from QRC: {ac.QRC_PROGRESS_STYLESHEET_PATH}")
        else:
            logger.warning(f"Failed to open progress stylesheet file: {ac.QRC_PROGRESS_STYLESHEET_PATH}")
    except Exception as e:
        logger.error(f"Error loading progress bar stylesheet: {e}")

    window = MainWindowView()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run()
