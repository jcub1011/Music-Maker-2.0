import os

import appdirs
import json


class DataHandler:
    application_name = "Music Maker"
    author = "Jocwae"
    file_name = "preferences.json"
    cache_name = "cache.json"

    # Identifiers
    folder_key = "FOLDER"
    url_key = "URL"
    ffmpeg_key = "FFMPEG"
    sim_download_key = "SIMULTANEOUS_DOWNLOADS"
    sim_process_key = "SIMULTANEOUS_PROCESSES"
    audio_only_key = "AUDIO_ONLY"
    stream_limit_key = "STREAM_LIMIT"

    __default_application_settings = {
        url_key: "",
        folder_key: "",
        ffmpeg_key: "",
        sim_download_key: 1,
        sim_process_key: 1,
        audio_only_key: True,
        stream_limit_key: 0
    }

    # Cached data.
    __cached_data_updated = False
    __cached_application_settings = {
        url_key: "",
        folder_key: "",
        ffmpeg_key: "",
        sim_download_key: 1,
        sim_process_key: 1,
        audio_only_key: True,
        stream_limit_key: 0
    }

    @classmethod
    def get_file_path(cls) -> str:
        return (os.path.join(
            appdirs.user_data_dir(cls.application_name, cls.author),
            cls.file_name))

    @classmethod
    def get_config_file_info(cls) -> dict:
        """Gets the json in the configuration file."""
        path = cls.get_file_path()

        try:
            if cls.__cached_data_updated:
                return cls.__cached_application_settings

            elif not os.path.exists(path):
                print(f"No config file exists at '{path}'.")
                return cls.__default_application_settings

            else:
                with open(path, "r") as file:
                    print(f"Found config file at '{path}'")
                    settings = json.load(file)

                    has_missing_keys = False
                    for key in cls.__default_application_settings.keys():
                        if key not in settings.keys():
                            settings[key] = cls.__default_application_settings[key]
                            has_missing_keys = True

                    cls.__cached_application_settings = settings
                    cls.__cached_data_updated = True

                # Add missing keys.
                if has_missing_keys:
                    with open(path, "w") as file:
                        json.dump(settings, file)

                return settings

        except json.JSONDecodeError:
            print("Unable to parse config file.")
            return cls.__default_application_settings

    @classmethod
    def get_cache_path(cls) -> str:
        return (os.path.join(
            appdirs.user_cache_dir(cls.application_name, cls.author),
            cls.cache_name))

    @classmethod
    def get_cache_file_info(cls) -> dict:
        """Gets the json in the configuration file."""
        path = cls.get_cache_path()

        try:
            if not os.path.exists(path):
                print(f"No cache file exists at '{path}'.")
                return {}
            else:
                with open(path, "r") as file:
                    print(f"Found cache file at '{path}'")
                    return json.load(file)
        except json.JSONDecodeError:
            print("Unable to parse cache file.")
            return {}

    @classmethod
    def update_config_file(cls, key: str, value):
        """Updates or adds a value in the configuration file."""
        path = cls.get_file_path()

        existing_json = cls.get_config_file_info()
        existing_json[key] = value
        cls.__cached_application_settings = existing_json
        cls.__cached_data_updated = True

        if not os.path.exists(path):
            os.makedirs(appdirs.user_data_dir(cls.application_name, cls.author), exist_ok=True)
            with open(path, "w") as file:
                file.write("{}")

        with open(path, "w") as file:
            json.dump(existing_json, file)

    @classmethod
    def retrieve_config_file_info(cls, key: str):
        """Retrieves information from the configuration file.
        Returns None if the key does not exist."""
        file_info = cls.get_config_file_info()

        if key not in file_info:
            return None
        else:
            return file_info[key]

    @classmethod
    def update_cache_file(cls, key: str, value):
        """Adds or updates the value in the cache file."""
        path = cls.get_cache_path()

        existing_json = cls.get_cache_file_info()
        existing_json[key] = value

        with open(path, "w") as file:
            json.dump(existing_json, file)

    @classmethod
    def retrieve_cache_file_info(cls, key: str):
        """Retrieves information from the cache file.
        Returns None if the key does not exist."""
        file_info = cls.get_cache_file_info()

        if key not in file_info:
            return None
        else:
            return file_info[key]
