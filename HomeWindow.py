from os import path
from typing import List

import pytube
from PyQt6.QtWidgets import QMainWindow, QPushButton, QLabel, QLineEdit, \
    QVBoxLayout, QFileDialog, QHBoxLayout, QWidget, QStackedWidget

from CustomWidgets import LabeledSpinbox, ErrorDialog
from StreamViewer import StreamViewer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Music Maker 2.0")
        self.setMinimumWidth(500)

        self.central_widget = QStackedWidget()
        self.setCentralWidget(self.central_widget)
        self.home = HomeWindow()
        self.stream_viewer = StreamViewer()
        self.stream_viewer.add_on_cancel_callback(self.open_home)
        self.home.add_get_streams_callback(self.open_stream_viewer)
        self.central_widget.addWidget(self.home)
        self.central_widget.addWidget(self.stream_viewer)

        self.open_home()

    def open_stream_viewer(self, urls: List[str]):
        print("Opening stream viewer.")
        self.setWindowTitle("Music Maker 2.0 - Stream Viewer")
        self.central_widget.setCurrentWidget(self.stream_viewer)
        self.stream_viewer.set_video_list(urls)

    def open_home(self):
        self.setWindowTitle("Music Maker 2.0 - Home")
        self.central_widget.setCurrentWidget(self.home)


class HomeWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.on_get_streams_callbacks = []

        # Start button.
        self.getStreamsButton = QPushButton("Get Streams")
        self.getStreamsButton.setStyleSheet("padding: 5px")
        self.getStreamsButton.clicked.connect(self.get_streams)

        # URL input field.
        self.urlInputLabel = QLabel("YouTube Link (Playlist or Video Link)")
        self.urlInput = QLineEdit(self)

        # Folder input field.
        self.selectedFolderLabel = QLabel("Selected Folder")
        self.selectedFolder = QLineEdit(self)
        self.selectedFolder.setReadOnly(True)
        self.selectedFolder.setText("No folder selected")
        self.selectFolderButton = QPushButton("Select Output Folder")
        self.selectFolderButton.setStyleSheet("padding: 5px")
        self.selectFolderButton.clicked.connect(self.select_folder)

        # Footer selectors.
        self.simultaneousDownloads = LabeledSpinbox("Simultaneous Downloads")
        self.simultaneousProcesses = LabeledSpinbox("Simultaneous Processes")

        # Layout
        v_box = QVBoxLayout(self)
        v_box.addWidget(self.urlInputLabel)
        v_box.addWidget(self.urlInput)

        v_box.addWidget(self.selectedFolderLabel)
        folder_h_box = QHBoxLayout(self)
        folder_h_box.addWidget(self.selectedFolder)
        folder_h_box.addWidget(self.selectFolderButton)
        select_folder_widget = QWidget()
        select_folder_widget.setLayout(folder_h_box)
        v_box.addWidget(select_folder_widget)

        footer_h_box = QHBoxLayout(self)
        footer_h_box.addWidget(self.simultaneousDownloads)
        footer_h_box.addWidget(self.simultaneousProcesses)
        footer_h_box.addWidget(self.getStreamsButton)
        footer_h_box_widget = QWidget()
        footer_h_box_widget.setLayout(footer_h_box)
        v_box.addWidget(footer_h_box_widget)

        self.setLayout(v_box)

    def get_streams(self):
        """Opens the streams window."""
        print("Validating inputs.")

        err_msg = self.validate_inputs()
        if err_msg is not None and err_msg != "":
            print(f"Unable to get streams.\n{err_msg}")
            ErrorDialog("Error", err_msg).exec()
            return

        print("Getting streams.")
        self.raise_get_streams_callback()

    def select_folder(self):
        """Prompts the user to select a folder."""
        print("Selecting folder.")

        # Start from folder that was selected previously.
        if path.exists(self.selectedFolder.text()):
            start_folder = self.selectedFolder.text()
        else:
            start_folder = "/home"

        folder = str(QFileDialog.getExistingDirectory(self, "Select Directory", directory=start_folder))
        if path.exists(folder):
            self.selectedFolder.setText(folder)
            print(f"Output folder set to '{self.selectedFolder.text()}'.")
        else:
            print(f"Invalid folder '{folder}'.")

    def validate_inputs(self) -> str:
        """Returns an error message if any of the inputs are invalid, otherwise it is an empty string."""

        # Check if folder exists.
        if not path.exists(self.selectedFolder.text()):
            return f"Invalid folder path '{self.selectedFolder.text()}'."

        print("Completed folder validation.")

        # Check if video/playlist exists.
        try:
            print(f"Playlist ID: {pytube.Playlist(self.urlInput.text()).playlist_id}")

        except KeyError:
            print("Link is not a playlist.")

            try:
                length = pytube.YouTube(self.urlInput.text()).length
                print(f"Valid video link. {length}s")
            except:
                return "Invalid video link. (Link may be mistyped, the video may be private or otherwise unavailable.)"

        except:
            return "Unknown error."

        finally:
            print("Completed link validation.")

        # Completed checks.
        return ""

    def add_get_streams_callback(self, callback):
        """Callback requires a List[str] parameter."""

        self.on_get_streams_callbacks.append(callback)

    def raise_get_streams_callback(self):
        try:
            playlist = pytube.Playlist(self.urlInput.text())
            print(playlist.playlist_id)
            videos = playlist.videos
        except KeyError:
            videos = [pytube.YouTube(self.urlInput.text())]
        except:
            print(f"Unable to get video or playlist from url '{self.urlInput.text()}'.")
            return

        for callback in self.on_get_streams_callbacks:
            callback(videos)
