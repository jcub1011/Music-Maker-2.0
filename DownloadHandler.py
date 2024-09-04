import queue
import threading
from concurrent.futures.thread import ThreadPoolExecutor
from typing import NamedTuple, List
from uuid import uuid4

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QScrollArea, QFormLayout
from pytube import YouTube

import DownloadHelpers
from AppDataHandler import DataHandler
from CustomWidgets import DownloadListItem
from DownloadHelpers import download_with_progress, DownloadRequestArgs


class DownloadRequest(NamedTuple):
    video_number: int
    video: YouTube
    audio_only: bool
    output_path: str


class DownloadViewer(QWidget):
    def __init__(self):
        super(DownloadViewer, self).__init__()

        print("Init download viewer.")
        self.output_queue = queue.Queue()
        self.stop_download_event = threading.Event()
        self.pause_download_event = threading.Event()
        self.message_check_timer = QTimer(self)
        self.message_check_timer.timeout.connect(self.check_for_messages)
        self.threads_finished = 0
        self.total_threads_to_finish = 0
        self.thread_pool: ThreadPoolExecutor = None
        self.go_back_callback = []
        self.uuid_list_item_map: dict[str, DownloadListItem] = {}

        # Top Bar
        top_bar = QHBoxLayout()
        self.return_button = QPushButton("Go Back")
        self.return_button.pressed.connect(self.on_go_back_pressed)
        self.stop_button = QPushButton("Stop")
        self.stop_button.pressed.connect(self.on_stop_pressed)
        top_bar.addWidget(QLabel("Downloads"))
        top_bar.addWidget(self.stop_button)
        top_bar.addWidget(self.return_button)

        self.download_list_view = QScrollArea()
        self.download_list_view.setWidgetResizable(True)

        layout = QVBoxLayout()
        layout.addLayout(top_bar)
        layout.addWidget(self.download_list_view)
        self.setLayout(layout)

    def on_stop_pressed(self):
        print("Stopping downloads.")
        self.stop_download_event.set()
        self.stop_button.setDisabled(True)

    def on_go_back_pressed(self):
        print("Going back.")
        for callback in self.go_back_callback:
            callback()

    def register_go_back_callback(self, callback):
        self.go_back_callback.append(callback)

    def set_download_list(self, download_list: List[DownloadRequest]):
        print(f"Setting download list: {len(download_list)} items.")
        self.return_button.setDisabled(True)
        self.stop_button.setDisabled(False)

        self.pause_download_event.clear()
        self.stop_download_event.clear()
        self.message_check_timer.start(100)
        self.threads_finished = 0
        self.total_threads_to_finish = len(download_list)
        print(f"Total threads to complete: {self.total_threads_to_finish}")

        thread_count = DataHandler.get_config_file_info()[DataHandler.sim_download_key]
        audio_only = DataHandler.get_config_file_info()[DataHandler.audio_only_key]
        print(f"Using {thread_count} threads.\nAudio Only: {audio_only}")

        progress_bar_list = []
        self.thread_pool = ThreadPoolExecutor(max_workers=thread_count)
        for request in download_list:
            identifier = str(uuid4())
            item = DownloadListItem(f"{request.video_number}. {request.video.title}")
            self.uuid_list_item_map[identifier] = item
            progress_bar_list.append(item)

            args = DownloadRequestArgs(
                message_check_frequency=100,
                output_queue=self.output_queue,
                output_folder=request.output_path,
                audio_only=request.audio_only,
                stop_event=self.stop_download_event,
                uuid=identifier,
                video=request.video
            )
            self.thread_pool.submit(download_with_progress, args)

        scroll_layout = QFormLayout()
        scroll_layout.setVerticalSpacing(0)
        for item in progress_bar_list:
            scroll_layout.addRow(item)

        container = QWidget()
        container.setLayout(scroll_layout)
        self.download_list_view.setWidget(container)

    def check_for_messages(self):
        while not self.output_queue.empty():
            self.on_progress_message_received(self.output_queue.get())

    def on_progress_message_received(self, message: DownloadHelpers.DownloadProgressMessage):
        print(f"Received message: {message}")

        if message.type == "event":
            if message.value == "thread finished":
                self.threads_finished += 1
                print(f"Current completed thread count: {self.threads_finished}")

                if self.threads_finished >= self.total_threads_to_finish:
                    self.return_button.setDisabled(False)
                    self.stop_button.setDisabled(True)
                    self.message_check_timer.stop()

                    print("Shutting down thread pool.")
                    if self.thread_pool is not None:
                        self.thread_pool.shutdown()
            elif message.value == "finding streams":
                self.uuid_list_item_map[message.uuid].update_status("Getting Streams")
            elif message.value == "thread started":
                self.uuid_list_item_map[message.uuid].update_status("Ready")
            elif message.value == "started download":
                self.uuid_list_item_map[message.uuid].update_status("Downloading")
            elif message.value == "started processing":
                self.uuid_list_item_map[message.uuid].update_status("Processing")
            elif message.value == "completed processing":
                self.uuid_list_item_map[message.uuid].update_status("Finished")
                self.uuid_list_item_map[message.uuid].update_progress(100)
            elif message.value == "canceled":
                self.uuid_list_item_map[message.uuid].update_status("Canceled")
            elif message.value == "error":
                self.uuid_list_item_map[message.uuid].update_status("Encountered Error")

        elif message.type == "progress":
            self.uuid_list_item_map[message.uuid].update_progress(message.value)
