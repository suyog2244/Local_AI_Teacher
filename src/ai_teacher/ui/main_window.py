from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import(QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                            QPushButton, QVBoxLayout, QWidget)

from .chat_view import ChatView
from .standard_selector import StandardSelector

class MainWindow (QMainWindow):
    def __init__(self):
