import typing

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QHBoxLayout, QSpinBox, QWidget, QDialog, QDialogButtonBox, QCheckBox, \
    QListWidgetItem, QProgressBar


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


class LabeledCheckbox(QWidget):
    def __init__(self, text: str, default_state: bool = False):
        super(LabeledCheckbox, self).__init__()

        self.label = QLabel(text)
        self.check_box = QCheckBox()
        self.check_box.setChecked(default_state)

        layout = QHBoxLayout()
        layout.addWidget(self.label)
        layout.addWidget(self.check_box)
        self.setLayout(layout)

    def get_value(self) -> bool:
        return self.check_box.isChecked()


class DownloadListItem(QWidget):
    def __init__(self, text: str):
        super().__init__()

        self.label = QLabel(text)
        self.label.setFixedHeight(10)
        self.progress_bar = QProgressBar()

        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.addWidget(self.label)
        layout.addWidget(self.progress_bar)
        self.setLayout(layout)
        print(f"Created list item {text}")

    def update_progress(self, progress: int):
        self.progress_bar.setValue(progress)