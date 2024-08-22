from typing import List

import PyQt6
from PyQt6.QtWidgets import QApplication, QMainWindow, QPushButton, QLabel, QLineEdit, \
    QVBoxLayout, QFileDialog, QHBoxLayout, QSpinBox, QWidget, QListWidget, QListView, QAbstractItemView

from CustomWidgets import LabeledSpinbox, ErrorDialog, LabeledCheckbox
import pytube


class StreamViewer(QWidget):
    def __init__(self):
        super(StreamViewer, self).__init__()

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
        self.select_toggle = QPushButton("Toggle Select")
        self.select_toggle.clicked.connect(self.toggle_select)

        self.stream_list_view = QListWidget()
        self.stream_list_view.setSelectionMode(PyQt6.QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        self.stream_id_youtube_map = {}

        # Layout
        column_2 = QVBoxLayout()
        column_2.addWidget(self.cancel_btn)
        column_2.addWidget(self.begin_btn)
        column_2_widget = QWidget()
        column_2_widget.setLayout(column_2)

        row_1 = QHBoxLayout()
        row_1.addWidget(QLabel("To Download"))
        row_1.addWidget(self.audio_only_toggle)
        row_1.addWidget(self.select_toggle)
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

    def set_video_list(self, videos: List[pytube.YouTube]):
        print("Setting url list.")
        self.stream_id_youtube_map = {}
        self.stream_list_view.clear()

        video_count = 1
        for video in videos:
            print(f"Adding {video.title} to list.")
            self.stream_id_youtube_map[video_count] = video
            self.stream_list_view.addItem(f"{video_count}. {video.title} - {video.author}")
            video_count += 1

        self.stream_list_view.selectAll()

    def toggle_select(self):
        print("Toggling select.")

        if len(self.stream_list_view.selectedItems()) > 0:
            print("Removing selections.")
            self.stream_list_view.clearSelection()
        else:
            self.stream_list_view.selectAll()

