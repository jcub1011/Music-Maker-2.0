import os
import threading
import time
import traceback
import urllib.request
from io import BytesIO
from urllib.request import urlopen

import requests
import urllib3
from PIL import Image
from multiprocessing.queues import Queue
from typing import NamedTuple, Final
from multiprocessing import Manager
from enum import Enum

import pytube
from ffmpeg import ffmpeg, FFmpegError
from mutagen.mp4 import MP4Cover, MP4
from pytube import Stream, StreamQuery, YouTube
from requests import request

from AppDataHandler import DataHandler


class Metadata(NamedTuple):
    title: str
    author: str
    album: str
    year: str
    cover_url: str


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
    file_system_safe_name: str = convert_to_file_name(f"{metadata.title} - {metadata.author}")
    temporary_file_path_a: str = os.path.join(ars.output_folder, f"{ars.uuid}-a.mp4")
    temporary_file_path_v: str = os.path.join(ars.output_folder, f"{ars.uuid}-v.mp4")
    update_interval_ns: int = ars.message_check_frequency * 1000000

    try:
        if not ars.audio_only:
            raise NotImplementedError("Video download is currently unsupported.")

        if ars.stop_event.is_set():
            return

        # Get streams.
        audio_stream = StreamQuery(ars.video.fmt_streams).get_audio_only()
        if not ars.audio_only:
            video_stream = StreamQuery(ars.video.fmt_streams).filter(
                mime_type="video/mp4", adaptive=True).order_by("resolution").desc().first()
        else:
            video_stream = None

        # Download streams.
        ars.output_queue.put(DownloadProgressMessage(
            type="event",
            value="started download",
            uuid=ars.uuid
        ))
        if temporary_file_path_a and audio_stream:
            download_stream_with_progress(audio_stream, temporary_file_path_a, ars.output_queue, ars.uuid,
                                          ars.stop_event, update_interval_ns)
        if temporary_file_path_v and video_stream:
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
                    .option("y").input(temporary_file_path_a).output(
                        remux_output_file,
                        codec="copy"
                    )
                )
                mpeg.execute()
                add_metadata_mp4(remux_output_file, metadata)

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


def download_stream_with_progress(stream: Stream, output_file: str, output_queue: Queue, uuid: str,
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
            output_queue.put(DownloadProgressMessage(
                type="progress",
                value=0,
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

    http_req = urlopen(metadata.cover_url)
    file = http_req.read()
    http_req.close()
    tags["covr"] = [MP4Cover(file, imageformat=MP4Cover.FORMAT_JPEG)]

    tags.save()


def get_metadata_mp4(video: YouTube):
    """
    Attempts to scrape relevant metadata from the provided video.
    :param video:
    :return:
    """
    text = video.description
    if text is not None:
        lines = text.split('\n')
    else:
        lines = [""]

    # Checks if the description was generated by YouTube.
    if lines[-1] == "Auto-generated by YouTube.":
        print("Description was auto generated.")

        # Parse details.
        title, artist = lines[2].split(' · ', 1)
        album = lines[4]
        year = ""

        # Finds the release year if it exists.
        for line in lines:
            if line.find('Released on: ') != -1:
                year = line.split(': ')[1].split('-', 1)[0]
                break

        # If the release year wasn't found.
        if year == "":
            year = str(video.publish_date.year)

    else:
        title = video.title
        artist = video.author
        year = str(video.publish_date.year)
        album = ""


    # Fix artist formatting.
    artist = artist.replace(' · ', "; ")

    return Metadata(
        title=title,
        author=artist,
        album=album,
        year=year,
        cover_url=video.thumbnail_url
    )
