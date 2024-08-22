from typing import List

from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QLineEdit, \
    QVBoxLayout, QFileDialog, QHBoxLayout, QSpinBox, QWidget, QListWidget
from CustomWidgets import LabeledSpinbox, ErrorDialog, LabeledCheckbox
import pytube


class StreamViewer(QWidget):
    def __init__(self):
        super(StreamViewer, self).__init__()

        self.url_list = []

        self.on_cancel_callback = []
        self.on_start_downloads_callback = []

        # Buttons
        self.cancel_btn = QPushButton("Return To Home")
        self.cancel_btn.setStyleSheet("padding: 5px")
        self.cancel_btn.clicked.connect(self.on_cancel)

        self.begin_btn = QPushButton("Start Downloading")
        self.begin_btn.setStyleSheet("padding: 5px")
        self.begin_btn.clicked.connect(self.on_start_downloads)

        self.audio_only_toggle = LabeledCheckbox("Audio Only?", True)

        self.stream_list_view = QListWidget()

        # Layout
        column_2 = QVBoxLayout()
        column_2.addWidget(self.cancel_btn)
        column_2.addWidget(self.begin_btn)
        column_2_widget = QWidget()
        column_2_widget.setLayout(column_2)

        row_1 = QHBoxLayout()
        row_1.addWidget(QLabel("To Download"))
        row_1.addWidget(self.audio_only_toggle)
        row_1_widget = QWidget()
        row_1_widget.setLayout(row_1)

        column_1 = QVBoxLayout()
        column_1.addWidget(row_1_widget)
        column_1.addWidget(self.stream_list_view)
        column_1_widget = QWidget()
        column_1_widget.setLayout(column_1)

        layout = QHBoxLayout()
        layout.addWidget(column_1_widget)
        layout.addWidget(column_2_widget)
        self.setLayout(layout)

    def add_on_cancel_callback(self, callback):
        print("Adding on cancel callback.")
        self.on_cancel_callback.append(callback)

    def add_on_start_downloads_callback(self, callback):
        """Callback requires parameters (urls: List[str], audio_only: bool)."""
        print("Adding on start downloads callback.")
        self.on_start_downloads_callback.append(callback)

    def on_cancel(self):
        print("Returning to home.")
        for callback in self.on_cancel_callback:
            callback()

    def on_start_downloads(self):
        print("Beginning downloads.")
        for callback in self.on_start_downloads_callback:
            callback([], self.audio_only_toggle.get_value())

    def set_url_list(self, urls: List[str]):
        print("Setting url list.")
        self.url_list = urls
