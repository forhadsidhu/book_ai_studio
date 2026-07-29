import sys
import os

# Ensure local imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt6.QtWidgets import QApplication, QSplashScreen, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QPixmap, QColor

from ui.main_window import MainWindow
from ui.styles import DARK_THEME


def show_splash(app: QApplication) -> QSplashScreen:
    splash_pix = QPixmap(500, 300)
    splash_pix.fill(QColor("#0f0f1a"))
    splash = QSplashScreen(splash_pix)
    splash.setStyleSheet("color: #e2e8f0; font-family: 'Segoe UI'; font-size: 14px;")
    splash.showMessage(
        "📚 BookAI Studio\n\nLoading...",
        Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom,
        QColor("#a78bfa")
    )
    splash.show()
    app.processEvents()
    return splash


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("BookAI Studio")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("BookAI")
    app.setStyleSheet(DARK_THEME)

    font = QFont("Segoe UI", 10)
    app.setFont(font)

    splash = show_splash(app)

    window = MainWindow()
    QTimer.singleShot(1500, splash.close)
    QTimer.singleShot(1500, window.show)

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
