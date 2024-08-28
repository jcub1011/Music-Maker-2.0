import queue
import threading
from typing import List

import PyQt6
import pytube
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QListWidget, \
    QProgressBar, QFormLayout

import AppDataHandler
from CustomWidgets import LabeledCheckbox
from DownloadHandler import DownloadRequest


class StreamViewer(QWidget):
    def __init__(self):
        super().__init__()

        print("Init stream viewer.")

        self.output_path: str = ""
        self.on_cancel_callback = []
        self.on_start_downloads_callback = []
        self.video_list_gen_thread = None
        self.stop_video_list_generation_event = threading.Event()
        self.progress_bar = QProgressBar()
        self.video_queue = queue.Queue()
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.check_messages)

        # Buttons
        self.cancel_btn = QPushButton("Return To Home")
        self.cancel_btn.setStyleSheet("padding: 5px")
        self.cancel_btn.clicked.connect(self.on_cancel)

        self.begin_btn = QPushButton("Start Downloading")
        self.begin_btn.setStyleSheet("padding: 5px")
        self.begin_btn.setEnabled(False)
        self.begin_btn.clicked.connect(self.on_start_downloads)

        self.audio_only_toggle = LabeledCheckbox("Audio Only?", True)
        audio_only_initial_state = AppDataHandler.DataHandler.get_config_file_info()[AppDataHandler.DataHandler.audio_only_key]
        if audio_only_initial_state is not None:
            self.audio_only_toggle.check_box.setChecked(audio_only_initial_state)
        self.audio_only_toggle.setDisabled(True)

        self.audio_only_toggle.check_box.stateChanged.connect( lambda:
            AppDataHandler.DataHandler.update_config_file(
                AppDataHandler.DataHandler.audio_only_key,
                self.audio_only_toggle.check_box.isChecked()))

        self.select_toggle = QPushButton("Toggle Select")
        self.select_toggle.setStyleSheet("padding: 5px")
        self.select_toggle.clicked.connect(self.toggle_select)

        self.stream_list_view = QListWidget()
        self.stream_list_view.setSelectionMode(PyQt6.QtWidgets.QAbstractItemView.SelectionMode.MultiSelection)
        self.stream_id_youtube_map = {}

        # Layout
        column_2 = QVBoxLayout()
        column_2.addWidget(self.cancel_btn)
        column_2.addWidget(self.begin_btn)

        row_1 = QHBoxLayout()
        row_1.addWidget(QLabel("To Download"))
        row_1.addWidget(self.audio_only_toggle)
        row_1.addWidget(self.select_toggle)
        row_1.addWidget(self.cancel_btn)

        column_1 = QVBoxLayout()
        column_1.addLayout(row_1)
        column_1.addWidget(self.stream_list_view)
        column_1.addWidget(self.progress_bar)

        layout = QFormLayout()
        layout.addRow(column_1)
        layout.addRow(self.begin_btn)
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
        self.stop_video_list_generation_event.set()
        self.update_timer.stop()

        if self.video_list_gen_thread.is_alive():
            self.video_list_gen_thread.join()

        for callback in self.on_cancel_callback:
            callback()

    def on_start_downloads(self):
        print("Beginning downloads.")

        # Create download list.
        download_list: List[DownloadRequest] = []
        for selected_item in self.stream_list_view.selectedItems():
            video_id = int(selected_item.text().split('.', maxsplit = 1)[0])
            video = self.stream_id_youtube_map[video_id]
            audio_only = self.audio_only_toggle.get_value()
            output_path = self.output_path

            download_list.append(DownloadRequest(video_id, video, audio_only, output_path))

        for callback in self.on_start_downloads_callback:
            callback(download_list)

    def toggle_select(self):
        print("Toggling select.")

        if len(self.stream_list_view.selectedItems()) > 0:
            print("Removing selections.")
            self.stream_list_view.clearSelection()
        else:
            self.stream_list_view.selectAll()

    def set_video_list(self, videos: List[pytube.YouTube], output_path: str):
        print("Setting url list.")
        self.begin_btn.setEnabled(False)
        self.output_path = output_path

        while not self.video_queue.empty():
            self.video_queue.get()

        self.update_timer.stop()
        self.stop_video_list_generation_event.clear()
        self.progress_bar.setValue(0)
        self.stream_id_youtube_map = {}
        self.stream_list_view.clear()
        self.video_list_gen_thread = threading.Thread(target=self.populate_video_list, args=(videos, self.video_queue))
        self.video_list_gen_thread.daemon = True
        self.video_list_gen_thread.start()
        self.update_timer.start(100)

    def check_messages(self):
        while not self.video_queue.empty():
            self.on_message_received(self.video_queue.get())

    def on_message_received(self, message: dict):
        if "Stop Message" in message.keys():
            # perform cleanup
            print("Received stop message.")
            if message["Stop Message"] == "Finished":
                self.stream_list_view.selectAll()
                self.begin_btn.setEnabled(True)
            return

        self.stream_id_youtube_map[message["ID"]] = message["YouTube"]
        self.stream_list_view.addItem(f"{message["ID"]}. {message["Title"]} - {message["Author"]}")
        self.progress_bar.setValue(message["Progress"])

    def populate_video_list(self, videos: List[pytube.YouTube], result_queue: queue):
        print("Beginning population.")

        video_count = 1
        total_videos = len(videos)
        print(total_videos)
        for video in videos:
            if self.stop_video_list_generation_event.is_set():
                print("Stopping video retrieval.")
                result_queue.put({
                    "Stop Message": "Canceled"
                })
                return
            print(f"Adding {video.title} to list.")

            message = {
                "ID": video_count,
                "YouTube": video,
                "Title": video.title,
                "Author": video.author,
                "Progress": int(video_count / total_videos * 100)
            }
            result_queue.put(message)
            video_count += 1

        result_queue.put({
            "Stop Message": "Finished"
        })