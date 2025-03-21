from typing import NamedTuple
from urllib.request import urlopen

from mutagen.mp4 import MP4Cover, MP4
from pytube import YouTube


class Metadata(NamedTuple):
    title: str
    author: str
    album: str
    year: str
    cover_url: str


def get_description(yt: YouTube):
    """
    Thanks https://github.com/pytube/pytube/issues/1626#issuecomment-1775501965
    :param yt:
    :return:
    """
    for n in range(6):
        try:
            description =  yt.initial_data["engagementPanels"][n]["engagementPanelSectionListRenderer"]["content"]["structuredDescriptionContentRenderer"]["items"][1]["expandableVideoDescriptionBodyRenderer"]["attributedDescriptionBodyText"]["content"]
            return description
        except:
            continue
    return False


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


def get_metadata_mp4(video: YouTube) -> Metadata:
    """
    Attempts to scrape relevant metadata from the provided video.
    :param video: The video to scrape the metadata from.
    :return: The scraped metadata.
    """
    text = get_description(video)
    if text is not None or False:
        lines = text.split('\n')
    else:
        lines = [""]

    # Checks if the description was generated by YouTube.
    if lines[-1].find("Auto-generated by YouTube.") != -1:
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

    meta = Metadata(
        title=title,
        author=artist,
        album=album,
        year=year,
        cover_url=video.thumbnail_url
    )
    print("Detected metadata:", meta)
    return meta
