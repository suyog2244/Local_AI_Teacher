from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                             QPushButton, QVBoxLayout, QWidget)

from .chat_view import ChatView
from .standard_selector import StandardSelector


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Local AI Teacher")
        self.resize(1100, 700)
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)
        # header
        title = QLabel("Local AI Teacher")
        title.setObjectName("title")

        subtitle = QLabel("Your private, offline AI learning assistant")
        subtitle.setObjectName("subtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # Standard / subject selection
        self.standard_selector = StandardSelector()
        main_layout.addWidget(self.standard_selector)

        # Chat
        self.chat_view = ChatView()
        main_layout.addWidget(self.chat_view, 1)

        # Input area
        input_layout = QHBoxLayout()

        self.question_input = QLineEdit()
        self.question_input.setPlaceholderText("Ask your question...")

        self.mic_button = QPushButton("🎤")
        self.send_button = QPushButton("Ask")

        input_layout.addWidget(self.mic_button)
        input_layout.addWidget(self.question_input, 1)
        input_layout.addWidget(self.send_button)

        main_layout.addLayout(input_layout)

        # Status
        self.status_label = QLabel("● Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)

        main_layout.addWidget(self.status_label)

        # Signals
        self.send_button.clicked.connect(self.send_question)
        self.question_input.returnPressed.connect(self.send_question)

        self.apply_styles()

    def send_question(self):
        question = self.question_input.text().strip()

        if not question:
            return

        self.chat_view.add_user_message(question)

        self.question_input.clear()

        # Temporary response.
        # This will later be replaced by LangGraph/Ollama.
        self.chat_view.add_teacher_message(
            "I'm ready to help! The AI pipeline will be connected next."
        )

    def apply_styles(self):
        self.setStyleSheet("""
            QMainWindow {
                background: #f7f7f8;
            }

            QLabel#title {
                font-size: 28px;
                font-weight: bold;
            }

            QLabel#subtitle {
                font-size: 14px;
                color: #666666;
            }

            QComboBox,
            QLineEdit {
                padding: 10px;
                border: 1px solid #cccccc;
                border-radius: 8px;
                background: white;
            }

            QPushButton {
                padding: 10px 18px;
                border-radius: 8px;
                font-weight: bold;
            }

            QLabel {
                font-size: 14px;
            }
            """)


def run_app():
    from PyQt6.QtWidgets import QApplication

    app = QApplication([])

    window = MainWindow()
    window.show()

    app.exec()
