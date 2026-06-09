APP_STYLE = """
* {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
}

QMainWindow {
    background: #f8fafc;
}

QWidget#central {
    background: #f8fafc;
}

QWidget#left_sidebar {
    background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
    border-right: 1px solid #e2e8f0;
}

QWidget#logo_container {
    background: #ffffff;
    border-bottom: 1px solid #e2e8f0;
}

QLabel#app_title {
    color: #1e293b;
    font-size: 20px;
    font-weight: 800;
    letter-spacing: 0.5px;
}

QLabel#app_subtitle {
    color: #64748b;
    font-size: 14px;
    font-weight: 600;
}

QLabel#nav_section_label {
    color: #94a3b8;
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 1px;
    padding: 4px 4px;
}

QLabel#nav_button {
    color: #334155;
    font-size: 14px;
    font-weight: 600;
    padding: 12px 16px;
    border-radius: 10px;
    background: transparent;
}

QLabel#nav_button:hover {
    background: #eff6ff;
    color: #1d4ed8;
}

QLabel#nav_button[selected="true"] {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #60a5fa, stop: 1 #3b82f6);
    color: #ffffff;
    font-weight: 700;
}

QLabel#nav_group_button {
    color: #1e293b;
    font-size: 15px;
    font-weight: 700;
    padding: 12px 16px;
    border-radius: 10px;
    background: #f1f5f9;
}

QLabel#nav_group_button:hover {
    background: #e2e8f0;
    color: #1e293b;
}

QLabel#nav_group_button[selected="true"] {
    background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1, stop: 0 #3b82f6, stop: 1 #2563eb);
    color: #ffffff;
    font-weight: 700;
}

QLabel#nav_sub_button {
    color: #475569;
    font-size: 13px;
    font-weight: 500;
    padding: 10px 16px 10px 32px;
    border-radius: 8px;
    background: transparent;
}

QLabel#nav_sub_button:hover {
    background: #eff6ff;
    color: #1d4ed8;
}

QLabel#nav_sub_button[selected="true"] {
    background: #dbeafe;
    color: #1d4ed8;
    font-weight: 700;
    border-left: 3px solid #3b82f6;
}

QLabel#help_title {
    color: #334155;
    font-size: 14px;
    font-weight: 700;
}

QLabel#help_desc {
    color: #64748b;
    font-size: 12px;
}

QLabel#help_desc a {
    color: #3b82f6;
    text-decoration: none;
}

QLabel#help_desc a:hover {
    color: #2563eb;
    text-decoration: underline;
}

QWidget#right_content {
    background: #f8fafc;
}

QWidget#header_bar {
    background: #ffffff;
    border-bottom: 1px solid #e2e8f0;
}

QLabel#module_title {
    color: #1e293b;
    font-size: 18px;
    font-weight: 700;
}

QWidget#left_panel_container {
    background: #ffffff;
}

QFrame#divider {
    background: #e2e8f0;
    border: none;
}

QLabel#section_title {
    color: #334155;
    font-size: 14px;
    font-weight: 700;
    padding-bottom: 4px;
}

QLabel#info_text {
    color: #64748b;
    font-size: 13px;
    line-height: 1.6;
}

QLineEdit {
    background: #ffffff;
    border: 2px solid #cbd5e1;
    border-radius: 10px;
    padding: 12px 14px;
    color: #1e293b;
    font-size: 14px;
    font-weight: 500;
}

QLineEdit:hover {
    border-color: #94a3b8;
    background: #ffffff;
}

QLineEdit:focus {
    border-color: #60a5fa;
    background: #ffffff;
    outline: none;
}

QLineEdit::placeholder {
    color: #94a3b8;
    font-weight: 400;
}

QPushButton {
    background: #ffffff;
    color: #334155;
    border: 2px solid #cbd5e1;
    border-radius: 10px;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 600;
}

QPushButton:hover {
    background: #f1f5f9;
    border-color: #64748b;
    color: #1e293b;
}

QPushButton:pressed {
    background: #e2e8f0;
}

QPushButton#primary_btn {
    background: #3b82f6;
    color: #ffffff;
    border: none;
    padding: 14px 20px;
    font-size: 14px;
    font-weight: 700;
}

QPushButton#primary_btn:hover {
    background: #2563eb;
}

QPushButton#primary_btn:pressed {
    background: #1d4ed8;
}

QPushButton#primary_btn:disabled {
    background: #93c5fd;
    color: #ffffff;
}

QPushButton#secondary_btn {
    background: #ffffff;
    color: #475569;
    border: 2px solid #e2e8f0;
    border-radius: 10px;
    padding: 10px 20px;
    font-size: 14px;
    font-weight: 600;
    min-width: 100px;
}

QPushButton#secondary_btn:hover {
    background: #f8fafc;
    border-color: #cbd5e1;
    color: #334155;
}

QPushButton#secondary_btn:pressed {
    background: #f1f5f9;
}

QPushButton#action_btn {
    background: #f1f5f9;
    border: 2px solid #cbd5e1;
    padding: 9px 14px;
    font-size: 12px;
    font-weight: 700;
    color: #334155;
}

QPushButton#action_btn:hover {
    background: #eff6ff;
    border-color: #60a5fa;
    color: #1d4ed8;
}

QPushButton#oauth_btn {
    background: #60a5fa;
    color: #ffffff;
    border: none;
    padding: 13px 20px;
    font-size: 14px;
    font-weight: 700;
}

QPushButton#oauth_btn:hover {
    background: #3b82f6;
}

QPushButton#oauth_btn:disabled {
    background: #bfdbfe;
    color: #ffffff;
}

QPushButton#cookie_auto_btn {
    background: #10b981;
    color: #ffffff;
    border: none;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 700;
}

QPushButton#cookie_auto_btn:hover {
    background: #34d399;
}

QPushButton#cookie_auto_btn:disabled {
    background: #6ee7b7;
    color: #ffffff;
}

QPushButton#cookie_confirm_btn {
    background: #60a5fa;
    color: #ffffff;
    border: none;
    padding: 10px 16px;
    font-size: 13px;
    font-weight: 700;
}

QPushButton#cookie_confirm_btn:hover {
    background: #3b82f6;
}

QPushButton#cookie_confirm_btn:disabled {
    background: #bfdbfe;
    color: #ffffff;
}

QPushButton#clear_btn {
    background: #fee2e2;
    color: #dc2626;
    border: 2px solid #fca5a5;
    padding: 8px 12px;
    font-size: 12px;
    font-weight: 700;
}

QPushButton#clear_btn:hover {
    background: #fecaca;
    border-color: #f87171;
    color: #b91c1c;
}

QTabWidget::pane {
    border: none;
    background: transparent;
}

QTabWidget::tab-bar {
    alignment: left;
}

QTabBar::tab {
    background: transparent;
    color: #64748b;
    padding: 12px 20px;
    font-size: 13px;
    font-weight: 700;
    border-bottom: 3px solid transparent;
    margin-right: 4px;
}

QTabBar::tab:selected {
    color: #60a5fa;
    border-bottom: 3px solid #60a5fa;
}

QTabBar::tab:hover:!selected {
    color: #334155;
    background: #f1f5f9;
}

QTextEdit {
    background: #ffffff;
    border: 2px solid #cbd5e1;
    border-radius: 12px;
    padding: 16px;
    color: #1e293b;
    font-family: 'SF Mono', Monaco, 'Fira Code', Consolas, 'Courier New', monospace;
    font-size: 13px;
    line-height: 1.7;
}

QTextEdit:focus {
    border-color: #60a5fa;
}

QScrollBar:vertical {
    border: none;
    background: #f1f5f9;
    width: 10px;
    border-radius: 5px;
    margin: 4px;
}

QScrollBar::handle:vertical {
    background: #94a3b8;
    border-radius: 5px;
    min-height: 25px;
}

QScrollBar::handle:vertical:hover {
    background: #64748b;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar:horizontal {
    border: none;
    background: #f1f5f9;
    height: 10px;
    border-radius: 5px;
    margin: 4px;
}

QScrollBar::handle:horizontal {
    background: #94a3b8;
    border-radius: 5px;
    min-width: 25px;
}

QScrollBar::handle:horizontal:hover {
    background: #64748b;
}

QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {
    width: 0px;
}

QCheckBox {
    color: #334155;
    font-size: 13px;
    font-weight: 700;
    spacing: 10px;
}

QCheckBox::indicator {
    width: 20px;
    height: 20px;
    border: 2px solid #cbd5e1;
    border-radius: 6px;
    background: #ffffff;
}

QCheckBox::indicator:checked {
    background: #60a5fa;
    border: 2px solid #60a5fa;
}

QCheckBox::indicator:hover {
    border-color: #60a5fa;
}

QCheckBox::indicator:disabled {
    opacity: 0.4;
}

QFrame#search_container {
    background: #ffffff;
    border: 2px solid #cbd5e1;
    border-radius: 12px;
}

QFrame#search_container:focus-within {
    border-color: #60a5fa;
}

QPushButton#nav_btn {
    background: #f1f5f9;
    border: none;
    color: #64748b;
    font-size: 12px;
    border-radius: 8px;
    padding: 6px 10px;
}

QPushButton#nav_btn:hover {
    background: #eff6ff;
    color: #60a5fa;
}

QPushButton#nav_btn:disabled {
    color: #cbd5e1;
}

QMessageBox {
    background: #ffffff;
}

QMessageBox QLabel {
    color: #334155;
    font-size: 14px;
}

QMessageBox QPushButton {
    min-width: 80px;
    padding: 8px 24px;
}
"""
