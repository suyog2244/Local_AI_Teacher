from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget


class ChatView(QWidget):
    def __init__(self, parent) -> None:
        super().__init__(parent)
