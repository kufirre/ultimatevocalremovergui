import sys
from PySide6.QtWidgets import QApplication
# We use a relative import here because it's within the same package
from .ui.main_window_view import MainWindowView


def run():
    """Initializes and runs the PySide6 application."""
    # print("Starting UVR PySide6 GUI...") # Removed unprofessional comment
    app = QApplication(sys.argv)

    # You might want to apply a style or theme here later
    # For example: app.setStyle("Fusion")

    main_window = MainWindowView()
    main_window.show()

    # print("Main window shown. Entering event loop.") # Removed unprofessional comment
    sys.exit(app.exec())


if __name__ == "__main__":
    run()
