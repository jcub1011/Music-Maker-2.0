import os
import threading
import traceback
from enum import Enum
from multiprocessing.queues import Queue
from tempfile import SpooledTemporaryFile
from typing import NamedTuple, Final

import pytube
from ffmpeg import ffmpeg
from pytube import Stream, StreamQuery, YouTube

from AppDataHandler import DataHandler
from MetadataScraper import add_metadata_mp4, get_metadata_mp4


class DownloadErrorCode(Enum):
    NONE = 0
    ERROR = 1
    CANCELED = 2


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


class DownloadRequestArgs(NamedTuple):
    """
    Attributes
    ----------
    message_check_frequency : int
        In milliseconds.
    output_queue : Manager.Queue
        Queue that DownloadProgressMessages are sent to.
    output_folder : str
        Folder to put downloaded files in.
    audio_only : bool
        True if you want to download the audio only, otherwise it will download audio and video.
    video : YouTube
        The video to download.
    stop_event : threading.Event
        The flag to listen to for stop requests.
    uuid : str
        Identifier for the download request.
    """
    message_check_frequency: int
    output_queue: Queue
    output_folder: str
    audio_only: bool
    stop_event: threading.Event
    uuid: str
    video: YouTube


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


def download_stream(link: str):
    print(f"Downloading {link}.")


def download_stream(stream: Stream, output_file: SpooledTemporaryFile, output_queue: Queue, uuid: str,
                    stop_event: threading.Event) -> DownloadErrorCode:
    """
    Downloads the provided stream at the provided file location.
    :param stop_event: The stop flag to look for.
    :param uuid: Download request uuid.
    :param output_queue: Queue to send progress messages.
    :param stream: The stream to download.
    :param output_file: The location to store the download.
    :return: The error code.
    """
    try:
        if stop_event.is_set():
            return DownloadErrorCode.CANCELED

        output_queue.put(DownloadProgressMessage(
            type="event",
            value="started stream",
            uuid=uuid
        ))
        output_queue.put(DownloadProgressMessage(
            type="progress",
            value=0,
            uuid=uuid
        ))

        file_size: int = stream.filesize
        downloaded: float = 0.0

        for chunk in pytube.streams.request.stream(stream.url):
            if stop_event.is_set():
                return DownloadErrorCode.CANCELED

            # Retrieve data.
            output_file.write(chunk)
            downloaded += len(chunk)

            output_queue.put(DownloadProgressMessage(
                type="progress",
                value=int(downloaded / file_size * 95),
                uuid=uuid
            ))

        output_queue.put(DownloadProgressMessage(
            type="event",
            value="completed stream",
            uuid=uuid
        ))
        return DownloadErrorCode.NONE

    except Exception as exe:
        print(traceback.format_exc())
        return DownloadErrorCode.ERROR


def download_with_progress(ars: DownloadRequestArgs) -> None:
    """
    Attempts to download a YouTube video with the ability to send progress reports and receive pause/cancel requests.
    :return: None
    """
    print(f"Beginning to download {ars.video.title}.")
    ars.output_queue.put(DownloadProgressMessage(
        type="event",
        value="thread started",
        uuid=ars.uuid
    ))

    metadata = get_metadata_mp4(ars.video)

    # https://docs.python.org/3/library/tempfile.html#tempfile.NamedTemporaryFile
    audio_temp_file = SpooledTemporaryFile(max_size=25000000, mode='wb+', suffix=".mp4")

    if not ars.audio_only:
        video_temp_file = SpooledTemporaryFile(max_size=25000000, mode='wb+', suffix=".mp4")
    else:
        video_temp_file = None

    file_system_safe_name: str = convert_to_file_name(f"{metadata.title} - {metadata.author}")

    try:
        ars.output_queue.put(DownloadProgressMessage(
            type="event",
            value="finding streams",
            uuid=ars.uuid
        ))

        if not ars.audio_only:
            raise NotImplementedError("Video download is currently unsupported.")

        if ars.stop_event.is_set():
            ars.output_queue.put(DownloadProgressMessage(
                type="event",
                value="canceled",
                uuid=ars.uuid
            ))
            return

        # Get streams.
        audio_stream = StreamQuery(ars.video.streams).get_audio_only()
        if not ars.audio_only:
            video_stream = StreamQuery(ars.video.fmt_streams).get_highest_resolution()
        else:
            video_stream = None

        # Start stream downloads.
        ars.output_queue.put(DownloadProgressMessage(
            type="event",
            value="started download",
            uuid=ars.uuid
        ))

        # Get audio.
        if audio_temp_file and audio_stream:
            error_code = download_stream(audio_stream, audio_temp_file, ars.output_queue, ars.uuid,
                                         ars.stop_event)
            if error_code == DownloadErrorCode.CANCELED:
                ars.output_queue.put(DownloadProgressMessage(
                    type="event",
                    value="canceled",
                    uuid=ars.uuid
                ))
                return
            if error_code == DownloadErrorCode.ERROR:
                ars.output_queue.put(DownloadProgressMessage(
                    type="event",
                    value="error",
                    uuid=ars.uuid
                ))
                return

        # Get video.
        if video_temp_file and video_stream:
            error_code = download_stream(video_stream, video_temp_file, ars.output_queue, ars.uuid,
                                         ars.stop_event)
            if error_code == DownloadErrorCode.CANCELED:
                ars.output_queue.put(DownloadProgressMessage(
                    type="event",
                    value="canceled",
                    uuid=ars.uuid
                ))
                return
            if error_code == DownloadErrorCode.ERROR:
                ars.output_queue.put(DownloadProgressMessage(
                    type="event",
                    value="error",
                    uuid=ars.uuid
                ))
                return

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
            attempts += 1
            if attempts >= MAX_ATTEMPTS:
                raise FileExistsError(f"Too many files with the name '{file_system_safe_name + extension}'.")
            else:
                remux_output_file: str = os.path.join(ars.output_folder,
                                                      f"{file_system_safe_name} ({str(attempts)}){extension}")

        try:
            # Attempt to process downloads.
            if ars.audio_only:
                mpeg = (
                    ffmpeg.FFmpeg(DataHandler.get_config_file_info()[DataHandler.ffmpeg_key])
                    .option("y").input("pipe:0").output(
                        remux_output_file,
                        codec="copy"
                    )
                )

                audio_temp_file.seek(0)
                mpeg.execute(stream=audio_temp_file.read())
                add_metadata_mp4(remux_output_file, metadata)
                ars.output_queue.put(DownloadProgressMessage(
                    type="event",
                    value="completed processing",
                    uuid=ars.uuid
                ))

        except:
            print(traceback.format_exc())
            ars.output_queue.put(DownloadProgressMessage(
                type="event",
                value="error",
                uuid=ars.uuid
            ))

            # Cleanup.
            if os.path.exists(remux_output_file):
                os.remove(remux_output_file)

    except:
        print(traceback.print_exc())
        ars.output_queue.put(DownloadProgressMessage(
            type="event",
            value="error",
            uuid=ars.uuid
        ))

    finally:
        # Delete temporary files.
        if audio_temp_file is not None:
            audio_temp_file.close()
        if video_temp_file is not None:
            video_temp_file.close()

        ars.output_queue.put(DownloadProgressMessage(
            type="event",
            value="thread finished",
            uuid=ars.uuid
        ))
