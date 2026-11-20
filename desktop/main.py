"""
Parental Control Desktop — entry point.
Loads config, creates QApplication, shows the Dashboard window.
"""

import sys
import os

# Ensure the desktop package directory is on the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from config_manager import ConfigManager
from dashboard import DashboardWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Parental Control Dashboard")
    app.setStyle("Fusion")

    # Load shared config
    config = ConfigManager()

    # Create and show main window
    window = DashboardWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
