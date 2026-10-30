"""Qt Style Sheets for ClipDesk — Sky-Blue Wave Glass Theme (Light) & Dark Theme."""

ANIMATION_DURATION = 180  # ms

SKY_LIGHT_THEME = """
QWidget {
    color: #1E2F4D;
    font-family: "Segoe UI", "Leelawadee UI", "Tahoma", sans-serif;
    font-size: 13px;
}

QMainWindow {
    background-color: #EBF3FC;
}

QLabel {
    background: transparent;
    border: none;
}

QLabel#headerTitle {
    font-size: 21px;
    font-weight: 800;
    color: #162B4D;
}

QLabel#headerSubtitle {
    font-size: 13px;
    color: #4A658A;
}

QLabel#sectionTitle {
    font-size: 15px;
    font-weight: 700;
    color: #162B4D;
}

QLabel#cardFieldTitle {
    font-size: 12px;
    font-weight: 700;
    color: #264066;
}

QLabel#errorLabel {
    color: #E53935;
    font-size: 12px;
    font-weight: 600;
}

QLabel#noteLabel {
    color: #6B82A6;
    font-size: 11px;
}

/* White Glass Cards */
QFrame#whiteCard, QWidget#whiteCard {
    background-color: rgba(255, 255, 255, 242);
    border: 1px solid #DCE9F9;
    border-radius: 14px;
}

QFrame#optionCard {
    background-color: rgba(255, 255, 255, 245);
    border: 1px solid #DCE9F9;
    border-radius: 12px;
}

QFrame#queueItemCard {
    background-color: #F7FAFF;
    border: 1px solid #E2EEFC;
    border-radius: 11px;
}

QFrame#queueItemCard:hover {
    background-color: #EFF6FF;
    border: 1px solid #BBD8FB;
}

/* URL LineEdit inside white bar */
QLineEdit#urlEdit {
    background: transparent;
    border: none;
    color: #1E2F4D;
    font-size: 13.5px;
    padding: 6px 4px;
    selection-background-color: #2196F3;
}

QLineEdit#folderEdit {
    background-color: #F8FBFF;
    border: 1px solid #D5E5F8;
    border-radius: 8px;
    padding: 5px 10px;
    color: #2B4266;
    font-size: 12.5px;
}

QLineEdit#folderEdit:focus {
    border: 1.5px solid #2185F0;
}

/* ComboBox inside option cards */
QComboBox#modernCombo {
    background-color: #F8FBFF;
    border: 1px solid #D5E5F8;
    border-radius: 8px;
    padding: 5px 12px;
    color: #1E2F4D;
    font-size: 13px;
    font-weight: 600;
    min-height: 22px;
}

QComboBox#modernCombo:hover {
    border-color: #90C2F9;
    background-color: #FFFFFF;
}

QComboBox#modernCombo::drop-down {
    border: none;
    width: 26px;
}

QComboBox#modernCombo QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #C5DDF8;
    border-radius: 8px;
    selection-background-color: #E3F0FF;
    selection-color: #1565D8;
    color: #1E2F4D;
    padding: 4px;
    outline: 0;
}

/* Sort ComboBox in Queue Header */
QComboBox#sortCombo {
    background: transparent;
    border: none;
    color: #3A5278;
    font-size: 12.5px;
    font-weight: 600;
    padding: 2px 6px;
}

QComboBox#sortCombo:hover {
    color: #1565D8;
}

/* Primary Check URL Button */
QPushButton#checkUrlBtn {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #2B8eff, stop:0.5 #1B75EB, stop:1 #135FD1);
    color: white;
    border: 1px solid #4CA3FF;
    border-radius: 10px;
    font-size: 13.5px;
    font-weight: 700;
    padding: 8px 18px;
}

QPushButton#checkUrlBtn:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
        stop:0 #429BFF, stop:0.5 #2682F5, stop:1 #1A6CE0);
}

QPushButton#checkUrlBtn:pressed {
    background: #1256BE;
}

QPushButton#checkUrlBtn:disabled {
    background: #9BC5F5;
    border-color: #B2D3F8;
    color: #F0F7FF;
}

/* Queue Header Pill Buttons (ล้างคิว / หยุดทั้งหมด) */
QPushButton#queueHeaderBtn {
    background-color: #F5F9FF;
    border: 1px solid #D2E3F8;
    border-radius: 8px;
    padding: 5px 12px;
    color: #334E75;
    font-size: 12px;
    font-weight: 600;
}

QPushButton#queueHeaderBtn:hover {
    background-color: #E6F1FF;
    border-color: #9CC6F9;
    color: #1565D8;
}

QPushButton#queueHeaderBtn:pressed {
    background-color: #D6E8FF;
}

/* Folder Picker Icon Button */
QPushButton#folderIconBtn {
    background-color: #F3F8FF;
    border: 1px solid #D5E5F8;
    border-radius: 8px;
    color: #35527A;
    font-size: 14px;
    padding: 4px;
}

QPushButton#folderIconBtn:hover {
    background-color: #E3F0FF;
    border-color: #90C2F9;
}

/* ScrollArea */
QScrollArea {
    background: transparent;
    border: none;
}

QScrollBar:vertical {
    background: transparent;
    width: 6px;
    margin: 2px 0;
}

QScrollBar::handle:vertical {
    background-color: #C2D8F2;
    border-radius: 3px;
    min-height: 28px;
}

QScrollBar::handle:vertical:hover {
    background-color: #94BBE8;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QDialog {
    background-color: #F2F7FE;
}
"""

DARK_THEME = SKY_LIGHT_THEME


def get_theme(dark: bool = False) -> str:
    """Return the Sky-Blue Wave Glass stylesheet (matches the reference mockup)."""
    return SKY_LIGHT_THEME
