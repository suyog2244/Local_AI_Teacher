from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ChatView(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.user_label = QLabel()
        self.user_label.setWordWrap(True)

        self.teacher_label = QLabel()
        self.teacher_label.setWordWrap(True)

        self.user_label.setText("You\n")
        self.teacher_label.setText("AI Teacher\n")

        layout.addWidget(self.user_label)
        layout.addWidget(self.teacher_label)

        layout.addStretch()

    def add_user_message(self, message: str):
        self.user_label.setText(f"<b>You</b><br>{message}")

    def add_teacher_message(self, message: str):
        self.teacher_label.setText(f"<b>AI Teacher</b><br>{message}")
