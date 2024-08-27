import os
import threading
import time
import traceback
from typing import NamedTuple, Final
from multiprocessing import Manager
from enum import Enum

import pytube
from ffmpeg import ffmpeg, FFmpegError
from mutagen.mp4 import MP4Cover, MP4
from pytube import Stream, StreamQuery

from AppDataHandler import DataHandler


class Metadata(NamedTuple):
    title: str
    author: str
    album: str
    year: str
    cover: MP4Cover


class DownloadErrorCode(Enum):
    NONE = 0
    ERROR = 1
    CANCELED = 2


class DownloadRequestArgs(NamedTuple):
    """
    Attributes
    ----------
    message_check_frequency : int
        In milliseconds.
    output_queue : Manager.Queue
        Queue to send progress and update messages to.
    output_folder : str
        Folder to put downloaded files in.
    audio_only : bool
        True if you want to download the audio only, otherwise it will download audio and video.
    metadata : Metadata
        The metadata to apply to the downloaded file.
    stop_event : threading.Event
        The flag to listen to for stop requests.
    streams : list[Stream]
        The fmt_streams from a YouTube object.
    uuid : str
        Identifier for the download request.
    """
    message_check_frequency: int
    output_queue: Manager.Queue
    output_folder: str
    audio_only: bool
    metadata: Metadata
    stop_event: threading.Event
    streams: list[Stream]
    uuid: str


class DownloadProgressMessage(NamedTuple):
    """
    Attributes
    ----------
    type : str
        The message type. ["event", "progress", "error"]
    value : [str, int]
        The value associated with the message. Event and Error types are string
        while Progress types are int.
    uuid : str
        Unique identifier for the download request.
    """
    type: str
    value: [str, int]
    uuid: str


def convert_to_file_name(name: str):
    """
    Replaces illegal characters in the string with spaces.
    :param name: String to clean.
    :return: The cleaned string.
    """
    # Characters that can't be in Windows directories.
    FORBIDDEN_CHARS: Final[list[str]] = [
        ">",
        "<",
        ":",
        '"',
        "\\",
        "/",
        "|",
        "?",
        "*",
        "."
    ]

    cleaned_name = ""
    for char in name:
        if char not in FORBIDDEN_CHARS:
            cleaned_name += char
        else:
            cleaned_name += " "

    return cleaned_name


def download_with_progress(self, ars: DownloadRequestArgs) -> None:
    """
    Attempts to download a YouTube video with the ability to send progress reports and receive pause/cancel requests.
    :return: None
    """
    print(f"Beginning to download {ars.metadata.title}.")
    ars.output_queue.put(DownloadProgressMessage(
        type="event",
        value="thread started",
        uuid=ars.uuid
    ))

    file_system_safe_name: str = convert_to_file_name(f"{ars.metadata.title} - {ars.metadata.author}")
    temporary_file_path_a: str = os.path.join(ars.output_folder, f"{ars.uuid}-a.mp4")
    temporary_file_path_v: str = os.path.join(ars.output_folder, f"{ars.uuid}-v.mp4")
    update_interval_ns: int = ars.message_check_frequency * 1000000

    try:
        if not ars.audio_only:
            raise NotImplementedError("Video download is currently unsupported.")

        if ars.stop_event.is_set():
            return

        # Get streams.
        audio_stream = StreamQuery(ars.streams).get_audio_only()
        if not ars.audio_only:
            video_stream = StreamQuery(ars.streams).filter(
                mime_type="video/mp4", adaptive=True).order_by("resolution").desc().first()
        else:
            video_stream = None

        # Download streams.
        ars.output_queue.put(DownloadProgressMessage(
            type="event",
            value="started download",
            uuid=ars.uuid
        ))
        if temporary_file_path_a:
            download_stream_with_progress(audio_stream, temporary_file_path_a, ars.output_queue, ars.uuid,
                                          ars.stop_event, update_interval_ns)
        if temporary_file_path_v:
            download_stream_with_progress(video_stream, temporary_file_path_v, ars.output_queue, ars.uuid,
                                          ars.stop_event, update_interval_ns)
        ars.output_queue.put(DownloadProgressMessage(
            type="event",
            value="completed download",
            uuid=ars.uuid
        ))

        # Process downloads.
        ars.output_queue.put(DownloadProgressMessage(
            type="event",
            value="started processing",
            uuid=ars.uuid
        ))

        if ars.audio_only:
            extension = ".m4a"
        else:
            extension = ".mp4"

        remux_output_file: str = os.path.join(ars.output_folder, file_system_safe_name + extension)
        attempts: int = 0
        MAX_ATTEMPTS: int = 5

        # Get valid location.
        while os.path.exists(remux_output_file):
            if attempts >= MAX_ATTEMPTS:
                raise FileExistsError(f"Too many files with the name '{file_system_safe_name + extension}'.")
            else:
                remux_output_file: str = os.path.join(ars.output_folder,
                                                      f"{file_system_safe_name}({str(attempts)}){extension}")

        try:
            # Attempt to process downloads.
            if ars.audio_only:
                mpeg = (
                    ffmpeg.FFmpeg(DataHandler.get_config_file_info()[DataHandler.ffmpeg_key])
                    .option("y").input(temporary_file_path_a).output(
                        remux_output_file,
                        codec="copy"
                    )
                )
                mpeg.execute()
                add_metadata_mp4(remux_output_file, ars.metadata)

        except:
            print(traceback.format_exc())

            # Cleanup.
            if os.path.exists(remux_output_file):
                os.remove(remux_output_file)

        finally:
            ars.output_queue.put(DownloadProgressMessage(
                type="event",
                value="completed processing",
                uuid=ars.uuid
            ))

    except:
        print(traceback.print_exc())

    finally:
        # Delete temporary files.
        if os.path.exists(temporary_file_path_a):
            os.remove(temporary_file_path_a)
        if os.path.exists(temporary_file_path_v):
            os.remove(temporary_file_path_v)

        ars.output_queue.put(DownloadProgressMessage(
            type="event",
            value="thread finished",
            uuid=ars.uuid
        ))


def download_stream_with_progress(stream: Stream, output_file: str, output_queue: Manager.Queue, uuid: str,
                                  stop_event: threading.Event, update_interval: int) -> DownloadErrorCode:
    """
    Downloads the provided stream at the provided file location.
    :param update_interval: How often to check and receive messages and event flags. (nanoseconds)
    :param stop_event: The stop flag to look for.
    :param uuid: Download request uuid.
    :param output_queue: Queue to send progress messages.
    :param stream: The stream to download.
    :param output_file: The location to store the download.
    :return: None
    """
    try:
        if stop_event.is_set():
            return DownloadErrorCode.CANCELED
        else:
            time_of_last_update = time.monotonic_ns()

        with open(output_file, 'wb') as file:
            stream_chunks = pytube.streams.request.stream(stream.url)
            file_size: int = stream.filesize
            downloaded: float = 0.0
            output_queue.put(DownloadProgressMessage(
                type="event",
                value="started stream",
                uuid=uuid
            ))

            while True:
                # Send and receive messages.
                if time.monotonic_ns() - time_of_last_update > update_interval:
                    time_of_last_update = time.monotonic_ns()

                    if stop_event.is_set():
                        return DownloadErrorCode.CANCELED

                    output_queue.put(DownloadProgressMessage(
                        type="progress",
                        value=int(downloaded / file_size * 100),
                        uuid=uuid
                    ))

                # Retrieve data.
                chunk = next(stream_chunks, None)
                if chunk:
                    file.write(chunk)
                    downloaded += len(chunk)
                else:
                    output_queue.put(DownloadProgressMessage(
                        type="event",
                        value="completed stream",
                        uuid=uuid
                    ))
                    return DownloadErrorCode.NONE

    except Exception as exe:
        print(traceback.format_exc())
        return DownloadErrorCode.ERROR


def add_metadata_mp4(file_path: str, metadata: Metadata):
    """
    Embeds the metadata to the provided mp4/m4a file.
    :param file_path: Path to the file.
    :param metadata: Metadata to embed.
    :return: None
    """
    tags = MP4(file_path)

    tags["\xa9nam"] = metadata.title
    tags["\xa9ART"] = metadata.author
    tags["\xa9alb"] = metadata.album
    tags["\xa9day"] = metadata.year
    tags["covr"] = metadata.cover

    tags.save()



