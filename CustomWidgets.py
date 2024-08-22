import sys
import typing

from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QLineEdit, \
    QVBoxLayout, QFileDialog, QHBoxLayout, QSpinBox, QWidget, QDialog, QDialogButtonBox


class LabeledSpinbox(QWidget):
    def __init__(self, text: str, range_min: int = 1, range_max: int = 2147483647):
        super().__init__()
        if range_max > 2147483647:
            range_max = 2147483647
        elif range_max < -2147483646:
            range_max = -2147483646

        if range_min > 2147483647:
            range_min = 2147483647
        elif range_min < -2147483646:
            range_min = -2147483646

        # Swap
        if range_min > range_max:
            raise ValueError("The min must not be greater than the max.")

        layout = QVBoxLayout()

        self.label = QLabel(text)
        self.spin_box = QSpinBox()
        self.spin_box.setRange(range_min, range_max)

        layout.addWidget(self.label)
        layout.addWidget(self.spin_box)

        super().setLayout(layout)

    def setLayout(self, a0: typing.Optional['QLayout']) -> None:
        print(f"Set layout is unsupported in custom widget '{self}'")

    def set_text(self, text: str):
        self.label.setText(text)

    def get_text(self) -> str:
        return self.label.text()

    def set_value(self, value: int):
        self.spin_box.setValue(value)

    def get_value(self) -> int:
        return self.spin_box.value()


class ErrorDialog(QDialog):
    def __init__(self, title: str, msg: str):
        super().__init__()

        self.setWindowTitle(title)

        self.layout = QVBoxLayout()
        self.layout.addWidget(QLabel(msg))

        # Close button definition.
        close_btn = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        close_btn.clicked.connect(lambda: self.close())
        self.layout.addWidget(close_btn)

        self.setLayout(self.layout)
