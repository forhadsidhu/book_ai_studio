DARK_THEME = """
QMainWindow, QDialog, QWidget {
    background-color: #0f0f1a;
    color: #e2e8f0;
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}
QMenuBar {
    background-color: #16162a;
    color: #e2e8f0;
    border-bottom: 1px solid #2d2d4e;
    padding: 2px;
}
QMenuBar::item:selected { background-color: #4f46e5; border-radius: 4px; }
QMenu { background-color: #1e1e38; border: 1px solid #2d2d4e; border-radius: 6px; }
QMenu::item { padding: 6px 20px; }
QMenu::item:selected { background-color: #4f46e5; border-radius: 4px; }
QToolBar {
    background-color: #16162a;
    border-bottom: 1px solid #2d2d4e;
    spacing: 4px;
    padding: 4px;
}
QStatusBar {
    background-color: #0a0a14;
    color: #475569;
    border-top: 1px solid #2d2d4e;
    font-size: 11px;
}
QSplitter::handle { background-color: #2d2d4e; width: 1px; }
QTextEdit, QPlainTextEdit {
    background-color: #16162a;
    color: #e2e8f0;
    border: 1px solid #2d2d4e;
    border-radius: 8px;
    padding: 10px;
    font-size: 14px;
    line-height: 1.6;
    selection-background-color: #4f46e5;
}
QTextEdit:focus, QPlainTextEdit:focus { border-color: #4f46e5; }
QLineEdit {
    background-color: #1e1e38;
    color: #e2e8f0;
    border: 1px solid #2d2d4e;
    border-radius: 6px;
    padding: 8px 12px;
    font-size: 13px;
}
QLineEdit:focus { border-color: #4f46e5; }
QPushButton {
    background-color: #1e1e38;
    color: #94a3b8;
    border: 1px solid #2d2d4e;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: 500;
}
QPushButton:hover { background-color: #2d2d4e; color: #e2e8f0; }
QPushButton:pressed { background-color: #4f46e5; color: white; }
QPushButton:disabled { opacity: 0.4; }
QPushButton#primary {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
    color: white;
    border: none;
    font-weight: 600;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4338ca, stop:1 #6d28d9);
}
QPushButton#danger {
    background-color: #7f1d1d;
    color: #fca5a5;
    border: 1px solid #991b1b;
}
QPushButton#danger:hover { background-color: #991b1b; }
QListWidget {
    background-color: #16162a;
    border: none;
    border-radius: 0px;
    outline: none;
}
QListWidget::item {
    padding: 8px 12px;
    border-radius: 6px;
    margin: 2px 4px;
    color: #94a3b8;
}
QListWidget::item:selected {
    background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4f46e5, stop:1 #7c3aed);
    color: white;
}
QListWidget::item:hover:!selected { background-color: #1e1e38; color: #e2e8f0; }
QTabWidget::pane {
    border: none;
    background-color: #0f0f1a;
}
QTabBar::tab {
    background-color: #16162a;
    color: #64748b;
    padding: 8px 18px;
    border-bottom: 2px solid transparent;
    font-weight: 500;
}
QTabBar::tab:selected { color: #a78bfa; border-bottom-color: #a78bfa; background-color: #1a1a2e; }
QTabBar::tab:hover:!selected { color: #94a3b8; }
QScrollBar:vertical {
    background-color: #16162a;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background-color: #2d2d4e;
    border-radius: 4px;
    min-height: 30px;
}
QScrollBar::handle:vertical:hover { background-color: #4f46e5; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QComboBox {
    background-color: #1e1e38;
    color: #e2e8f0;
    border: 1px solid #2d2d4e;
    border-radius: 6px;
    padding: 6px 12px;
}
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background-color: #1e1e38;
    color: #e2e8f0;
    border: 1px solid #2d2d4e;
    selection-background-color: #4f46e5;
}
QSpinBox, QDoubleSpinBox {
    background-color: #1e1e38;
    color: #e2e8f0;
    border: 1px solid #2d2d4e;
    border-radius: 6px;
    padding: 6px;
}
QLabel { color: #94a3b8; }
QLabel#title { color: #e2e8f0; font-size: 16px; font-weight: 700; }
QLabel#section { color: #64748b; font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 1px; }
QGroupBox {
    border: 1px solid #2d2d4e;
    border-radius: 8px;
    margin-top: 12px;
    padding: 12px;
    color: #64748b;
    font-weight: 600;
    font-size: 11px;
}
QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 8px; color: #64748b; }
QSlider::groove:horizontal {
    height: 4px;
    background-color: #2d2d4e;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background-color: #4f46e5;
    width: 14px;
    height: 14px;
    border-radius: 7px;
    margin: -5px 0;
}
QSlider::sub-page:horizontal { background-color: #4f46e5; border-radius: 2px; }
QProgressBar {
    background-color: #1e1e38;
    border: 1px solid #2d2d4e;
    border-radius: 4px;
    height: 8px;
    text-align: center;
    font-size: 10px;
}
QProgressBar::chunk { background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #4f46e5, stop:1 #a78bfa); border-radius: 4px; }
QFrame#card {
    background-color: #16162a;
    border: 1px solid #2d2d4e;
    border-radius: 10px;
    padding: 12px;
}
QFrame#sidebar {
    background-color: #16162a;
    border-right: 1px solid #2d2d4e;
}
"""
