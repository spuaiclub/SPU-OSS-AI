import json
import sys

import markdown
import requests
from PyQt6.QtCore import (
    QEvent,
    QPoint,
    QRect,
    QSettings,
    QSize,
    Qt,
    QThread,
    pyqtSignal,
)
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPalette,
    QTextCursor,
    QTextDocument,
)
from PyQt6.QtWidgets import (
    QAbstractScrollArea,
    QApplication,
    QComboBox,
    QDialog,
    QFormLayout,
    QFrame,
    QGraphicsDropShadowEffect,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

# -----------------------------------------------------------------------------
# CONFIGURATION & THEME
# -----------------------------------------------------------------------------
APP_NAME = "SPU-OSS AI"
DEFAULT_FONT = "Inter, Segoe UI, Helvetica Neue, sans-serif"

# Minimalist Color Palette
COLOR_BG_MAIN = "#FFFFFF"
COLOR_BG_SIDEBAR = "#F9F9FB"
COLOR_TEXT_MAIN = "#1A1A1A"
COLOR_USER_BUBBLE = "#F2F2F2"
COLOR_BORDER = "#E5E5E5"

STYLESHEET = f"""
QMainWindow {{
    background-color: {COLOR_BG_MAIN};
}}
QWidget {{
    font-family: "{DEFAULT_FONT}";
    font-size: 14px;
    color: {COLOR_TEXT_MAIN};
}}
/* Sidebar */
QFrame#sidebar {{
    background-color: {COLOR_BG_SIDEBAR};
    border-right: 1px solid {COLOR_BORDER};
}}
QLabel#sidebarTitle {{
    font-weight: 800;
    font-size: 18px;
    color: #000;
    padding: 10px 0;
}}
/* Chat Area */
QScrollArea {{
    border: none;
    background-color: {COLOR_BG_MAIN};
}}
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 6px;
    margin: 0px 2px 0px 0px;
}}
QScrollBar::handle:vertical {{
    background: #D1D1D1;
    border-radius: 3px;
    min-height: 20px;
}}
/* Input Field */
QLineEdit {{
    border: 1px solid #E0E0E0;
    border-radius: 20px;
    padding: 12px 20px;
    background-color: #FFFFFF;
    font-size: 15px;
}}
QLineEdit:focus {{
    border: 1px solid #333333;
    background-color: #FFFFFF;
}}
/* Buttons */
QPushButton {{
    border: none;
    border-radius: 6px;
    padding: 8px 12px;
    text-align: left;
    color: #444;
}}
QPushButton:hover {{
    background-color: #EAEAEA;
    color: #000;
}}
QPushButton#newChatBtn {{
    background-color: #1A1A1A;
    color: #FFFFFF;
    border-radius: 8px;
    font-weight: 600;
    text-align: center;
    padding: 10px;
    margin-bottom: 15px;
}}
QPushButton#newChatBtn:hover {{
    background-color: #333333;
}}
QComboBox {{
    border: 1px solid {COLOR_BORDER};
    border-radius: 6px;
    padding: 5px 10px;
    background-color: #FFFFFF;
    color: #333;
}}
QComboBox::drop-down {{
    border: none;
}}
"""

PROVIDERS = {
    "OpenAI": {
        "url": "https://api.openai.com/v1/chat/completions",
        "model": "gpt-4o-mini",
        "style": "openai",
    },
    "Gemini (Google)": {
        "url": "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent",
        "model": "gemini-2.5-flash",
        "style": "google",
    },
    "DeepSeek": {
        "url": "https://api.deepseek.com/chat/completions",
        "model": "deepseek-chat",
        "style": "openai",
    },
    "Perplexity": {
        "url": "https://api.perplexity.ai/chat/completions",
        "model": "llama-3.1-sonar-small-128k-online",
        "style": "openai",
    },
}


# -----------------------------------------------------------------------------
# BACKEND LOGIC
# -----------------------------------------------------------------------------
class APIWorker(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, api_key, messages, provider_name):
        super().__init__()
        self.api_key = api_key
        self.messages = messages
        self.provider_config = PROVIDERS.get(provider_name)

    def run(self):
        if not self.provider_config:
            self.error.emit("Unknown Provider")
            return

        url = self.provider_config["url"]
        style = self.provider_config["style"]
        model = self.provider_config["model"]
        headers = {"Content-Type": "application/json"}
        data = {}

        if style == "openai":
            headers["Authorization"] = f"Bearer {self.api_key}"
            data = {"model": model, "messages": self.messages, "temperature": 0.7}
        elif style == "google":
            url = f"{url}?key={self.api_key}"
            contents = []
            for msg in self.messages:
                role = "user" if msg["role"] == "user" else "model"
                if msg["role"] == "system":
                    continue
                contents.append({"role": role, "parts": [{"text": msg["content"]}]})
            if not contents:
                contents.append({"role": "user", "parts": [{"text": "Hello"}]})
            data = {"contents": contents}

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            if response.status_code == 200:
                result = response.json()
                content = ""
                if style == "openai":
                    content = result["choices"][0]["message"]["content"]
                elif style == "google":
                    try:
                        content = result["candidates"][0]["content"]["parts"][0]["text"]
                    except:
                        content = "(No text returned)"
                self.finished.emit(content)
            else:
                self.error.emit(f"Error {response.status_code}: {response.text}")
        except Exception as e:
            self.error.emit(str(e))


# -----------------------------------------------------------------------------
# UI COMPONENTS
# -----------------------------------------------------------------------------
class MinimalChatBubble(QFrame):
    def __init__(self, text, is_user=False, parent=None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.is_user = is_user

        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(20, 10, 20, 10)

        # Content Container
        self.content_widget = QFrame()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setContentsMargins(15, 12, 15, 12)

        # Text Browser (Rich Text)
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setFrameShape(QFrame.Shape.NoFrame)
        self.text_browser.setVerticalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.text_browser.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )
        self.text_browser.setStyleSheet("background: transparent;")

        # Markdown to HTML
        html_content = markdown.markdown(text, extensions=["fenced_code", "codehilite"])

        # Styling
        if is_user:
            text_color = "#111"
            bg_color = COLOR_USER_BUBBLE
            align_style = "border-radius: 18px; border-bottom-right-radius: 4px;"
            self.layout.addStretch()
            self.layout.addWidget(self.content_widget)
        else:
            text_color = "#000"
            bg_color = "transparent"
            align_style = ""

            # AI Avatar Icon
            ai_label = QLabel("AI")
            ai_label.setFixedSize(28, 28)
            ai_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ai_label.setStyleSheet("""
                background-color: #000; color: #fff;
                border-radius: 14px; font-weight: bold; font-size: 10px;
            """)
            self.layout.addWidget(ai_label, 0, Qt.AlignmentFlag.AlignTop)
            self.layout.addWidget(self.content_widget)
            self.layout.addStretch()

        self.content_widget.setStyleSheet(
            f"background-color: {bg_color}; {align_style}"
        )

        # Internal HTML CSS
        css = f"""
        <style>
            body {{ font-family: '{DEFAULT_FONT}'; font-size: 15px; color: {text_color}; margin: 0; line-height: 1.6; }}
            p {{ margin-bottom: 8px; }}
            code {{ background-color: #F4F4F4; padding: 2px 5px; border-radius: 4px; font-family: Consolas; color: #D63384; }}
            pre {{ background-color: #F8F9FA; padding: 12px; border-radius: 6px; border: 1px solid #E9ECEF; overflow-x: auto; }}
            a {{ color: #0066CC; text-decoration: none; font-weight: 500; }}
            h1, h2, h3 {{ font-weight: 700; margin-top: 15px; margin-bottom: 8px; color: #000; }}
            li {{ margin-bottom: 4px; }}
        </style>
        """
        self.text_browser.setHtml(css + html_content)

        self.content_layout.addWidget(self.text_browser)

        # Initial sizing
        self.content_widget.setMaximumWidth(750)
        self.text_browser.setMaximumWidth(720)
        self.adjust_height()

    def adjust_height(self):
        """Calculate accurate height for text content"""
        doc = self.text_browser.document()
        # Set text width to allow word wrapping calculation
        doc.setTextWidth(self.text_browser.width())
        height = doc.size().height()
        self.text_browser.setFixedHeight(int(height) + 10)

    def resizeEvent(self, event):
        """Re-calculate height when window is resized"""
        self.text_browser.setMaximumWidth(min(720, self.width() - 100))
        self.adjust_height()
        super().resizeEvent(event)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("API Settings")
        self.setFixedSize(420, 380)
        self.setStyleSheet(f"background-color: #FFFFFF; font-family: '{DEFAULT_FONT}';")

        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.addWidget(QLabel("<b>API Keys Management</b>"))

        self.inputs = {}
        self.settings = QSettings("SPU_OSS", "AI_Chat_App_Minimal")

        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        for name in PROVIDERS.keys():
            inp = QLineEdit()
            inp.setEchoMode(QLineEdit.EchoMode.Password)
            inp.setPlaceholderText(f"sk-...")
            inp.setText(self.settings.value(f"api_key_{name}", ""))
            inp.setStyleSheet(
                "border: 1px solid #DDD; padding: 8px; border-radius: 6px;"
            )
            form_layout.addRow(f"{name}:", inp)
            self.inputs[name] = inp

        layout.addLayout(form_layout)
        layout.addStretch()

        save_btn = QPushButton("Save Keys")
        save_btn.setStyleSheet(
            "background-color: #000; color: #fff; padding: 10px; border-radius: 6px; font-weight: bold;"
        )
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self.save_settings)
        layout.addWidget(save_btn)

    def save_settings(self):
        for name, inp in self.inputs.items():
            self.settings.setValue(f"api_key_{name}", inp.text().strip())
        self.accept()


# -----------------------------------------------------------------------------
# MAIN WINDOW
# -----------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self.resize(1100, 800)
        self.settings = QSettings("SPU_OSS", "AI_Chat_App_Minimal")

        # Central Widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # Main Horizontal Layout (Sidebar | Content)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ----------------------
        # 1. SIDEBAR (Left)
        # ----------------------
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(260)
        sidebar.setMinimumWidth(260)  # Fix collapse issue

        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(20, 25, 20, 25)
        sidebar_layout.setSpacing(10)

        # Title
        title = QLabel(APP_NAME)
        title.setObjectName("sidebarTitle")
        sidebar_layout.addWidget(title)

        # New Chat Button
        self.new_chat_btn = QPushButton("+ New Chat")
        self.new_chat_btn.setObjectName("newChatBtn")
        self.new_chat_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.new_chat_btn.clicked.connect(self.reset_chat)
        sidebar_layout.addWidget(self.new_chat_btn)

        # Provider Selector
        lbl_prov = QLabel("Model Provider:")
        lbl_prov.setStyleSheet(
            "color: #666; font-size: 13px; font-weight: 500; margin-top: 10px;"
        )
        sidebar_layout.addWidget(lbl_prov)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(PROVIDERS.keys())
        last_provider = self.settings.value("current_provider", "OpenAI")
        idx = self.provider_combo.findText(last_provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self.provider_combo.currentTextChanged.connect(self.change_provider)
        sidebar_layout.addWidget(self.provider_combo)

        sidebar_layout.addStretch()

        # Settings
        settings_btn = QPushButton("⚙️  API Settings")
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.clicked.connect(self.open_settings)
        sidebar_layout.addWidget(settings_btn)

        main_layout.addWidget(sidebar)

        # ----------------------
        # 2. CONTENT AREA (Right)
        # ----------------------
        content_area = QWidget()
        content_layout = QVBoxLayout(content_area)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        # A. Chat History (Scroll Area)
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(
            Qt.ScrollBarPolicy.ScrollBarAlwaysOff
        )

        self.chat_container = QWidget()
        self.chat_container.setStyleSheet(f"background-color: {COLOR_BG_MAIN};")

        # Vertical Layout for messages
        self.chat_layout = QVBoxLayout(self.chat_container)
        self.chat_layout.setSpacing(0)
        self.chat_layout.setContentsMargins(0, 20, 0, 20)
        self.chat_layout.addStretch()  # Push messages to bottom

        self.scroll_area.setWidget(self.chat_container)

        # Add Scroll Area with Stretch 1 (Takes all available space)
        content_layout.addWidget(self.scroll_area, 1)

        # B. Input Area (Fixed at bottom)
        input_container = QFrame()
        input_container.setStyleSheet(f"background-color: {COLOR_BG_MAIN};")

        input_layout_inner = QHBoxLayout(input_container)
        input_layout_inner.setContentsMargins(
            50, 10, 50, 30
        )  # Top margin separates from chat

        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText(f"Message {last_provider}...")
        self.input_field.returnPressed.connect(self.send_message)

        # Subtle shadow for input
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 15))
        shadow.setOffset(0, 5)
        self.input_field.setGraphicsEffect(shadow)

        input_layout_inner.addWidget(self.input_field)

        # Add Input Container with Stretch 0 (Fixed size)
        content_layout.addWidget(input_container, 0)

        main_layout.addWidget(content_area)

        # Loading Bar (Overlay)
        self.progress_bar = QProgressBar(content_area)
        self.progress_bar.setFixedHeight(3)
        self.progress_bar.setStyleSheet(
            "background: transparent; border: none; QProgressBar::chunk { background-color: #000; }"
        )
        self.progress_bar.setRange(0, 0)
        self.progress_bar.hide()

        # State
        self.messages = [{"role": "system", "content": "You are a helpful assistant."}]
        self.current_provider = last_provider

        # Welcome Message
        self.add_message(
            "**Welcome.**\nSelect a provider and start typing.", is_user=False
        )

    def resizeEvent(self, event):
        # Update progress bar width on resize
        self.progress_bar.resize(self.width() - 260, 3)
        super().resizeEvent(event)

    def open_settings(self):
        SettingsDialog(self).exec()

    def change_provider(self, text):
        self.current_provider = text
        self.settings.setValue("current_provider", text)
        self.input_field.setPlaceholderText(f"Message {text}...")
        self.reset_chat()

    def reset_chat(self):
        # Clear layout safely
        while self.chat_layout.count() > 1:
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self.messages = [{"role": "system", "content": "You are a helpful assistant."}]
        self.add_message(
            f"**New Chat** started with {self.current_provider}.", is_user=False
        )

    def add_message(self, text, is_user):
        bubble = MinimalChatBubble(text, is_user)
        self.chat_layout.addWidget(bubble)
        QApplication.processEvents()
        self.scroll_to_bottom()

    def scroll_to_bottom(self):
        vsb = self.scroll_area.verticalScrollBar()
        vsb.setValue(vsb.maximum())

    def send_message(self):
        text = self.input_field.text().strip()
        if not text:
            return

        api_key = self.settings.value(f"api_key_{self.current_provider}", "")
        if not api_key:
            QMessageBox.warning(
                self,
                "No API Key",
                f"Please add your API Key for {self.current_provider} in Settings.",
            )
            self.open_settings()
            return

        self.add_message(text, is_user=True)
        self.input_field.clear()
        self.messages.append({"role": "user", "content": text})

        self.input_field.setDisabled(True)
        self.progress_bar.show()

        self.worker = APIWorker(api_key, self.messages, self.current_provider)
        self.worker.finished.connect(self.handle_response)
        self.worker.error.connect(self.handle_error)
        self.worker.start()

    def handle_response(self, content):
        self.progress_bar.hide()
        self.input_field.setDisabled(False)
        self.input_field.setFocus()
        self.messages.append({"role": "assistant", "content": content})
        self.add_message(content, is_user=False)

    def handle_error(self, error_msg):
        self.progress_bar.hide()
        self.input_field.setDisabled(False)
        QMessageBox.critical(self, "Error", str(error_msg))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
