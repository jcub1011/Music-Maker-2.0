import queue
import threading
from typing import List

import PyQt6
import pytube
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QApplication, QPushButton, QLabel, QVBoxLayout, QHBoxLayout, QWidget, QListWidget, \
    QProgressBar

from CustomWidgets import LabeledCheckbox


class StreamViewer(QWidget):
    def __init__(self):
        super(StreamViewer, self).__init__()

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
        column_1.addWidget(self.progress_bar)
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
        self.stop_video_list_generation_event.set()
        self.update_timer.stop()

        if self.video_list_gen_thread.is_alive():
            self.video_list_gen_thread.join()

        for callback in self.on_cancel_callback:
            callback()

    def on_start_downloads(self):
        print("Beginning downloads.")
        for callback in self.on_start_downloads_callback:
            callback([], self.audio_only_toggle.get_value())

    def toggle_select(self):
        print("Toggling select.")

        if len(self.stream_list_view.selectedItems()) > 0:
            print("Removing selections.")
            self.stream_list_view.clearSelection()
        else:
            self.stream_list_view.selectAll()

    def set_video_list(self, videos: List[pytube.YouTube]):
        print("Setting url list.")

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
                    "Stop Message": None
                })
                return
            print(f"Adding {video.title} to list.")
            # self.stream_id_youtube_map[video_count] = video
            # self.stream_list_view.addItem(f"{video_count}. {video.title} - {video.author}")
            # percent = int(video_count / total_videos * 100)
            # print(percent)
            # if self.progress_bar.value() != percent:
            #     self.progress_bar.setValue(percent)

            message = {
                "ID": video_count,
                "YouTube": video,
                "Title": video.title,
                "Author": video.author,
                "Progress": int(video_count / total_videos * 100)
            }
            result_queue.put(message)

            video_count += 1

        self.stream_list_view.selectAll()

#
# class VideoListRetriever(QRunnable):
#     def __init__(self, video_list: List[YouTube]):
#         super(VideoListRetriever, self).__init__()
#
#         self.signals = VideoListRetrieverSignals()
#         self.video_list = video_list
#
#     @pyqtSlot()
#     def run(self):
#         video_index = 1
#         total_videos = len(self.video_list)
#
#         for video in self.video_list:
#             if self.stop_video_list_generation_event.is_set():
#                 print("Stopping video retrieval.")
#                 return
#             print(f"Adding {video.title} to list.")
#             self.stream_id_youtube_map[video_index] = video
#             self.stream_list_view.addItem(f"{video_index}. {video.title} - {video.author}")
#
#             percent = int(video_index / total_videos * 100)
#             print(percent)
#             if self.progress_bar.value() != percent:
#                 self.progress_bar.setValue(percent)
#
#             video_index += 1
#
#         self.stream_list_view.selectAll()
#
# class VideoListRetrieverSignals(QObject):
#     """
#     finished
#         no data
#     error
#         err msg
#     received_next_YouTube
#         (YouTube, "(video num). title - author")
#     progress_updated
#         integer (0 to 100)
#     """
#     finished = pyqtSignal()
#     error = pyqtSignal(str)
#     received_next_YouTube = pyqtSignal(tuple)
#     progress_updated = pyqtSignal(int)
