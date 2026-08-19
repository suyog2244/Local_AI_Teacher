from PyQt6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget


class StandardSelector(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        standard_label = QLabel("Standard:")
        self.standard_combo = QComboBox()

        for standard in range(1, 13):
            self.standard_combo.addItem(f"Class {standard}", standard)

        subject_label = QLabel("Subject:")
        self.subject_combo = QComboBox()

        self.subject_combo.addItems(
            [
                "Mathematics",
                "Science",
                "English",
                "Social Science",
            ]
        )

        layout.addWidget(standard_label)
        layout.addWidget(self.standard_combo)

        layout.addSpacing(20)

        layout.addWidget(subject_label)
        layout.addWidget(self.subject_combo)

        layout.addStretch()
