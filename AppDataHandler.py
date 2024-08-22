import os
from os.path import pathsep

import appdirs
import json

class DataHandler:
    application_name = "Music Maker"
    author = "Jocwae"
    file_name = "preferences.json"

    # Identifiers
    folder_key = "FOLDER"
    url_key = "URL"
    sim_download_key = "SIMULTANEOUS_DOWNLOADS"
    sim_process_key = "SIMULTANEOUS_DOWNLOADS"


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
            if not os.path.exists(path):
                print(f"No config file exists at '{path}'.")
                return {}
            else:
                with open(path, "r") as file:
                    print(f"Found config file at '{path}'")
                    return json.load(file)
        except json.JSONDecodeError:
            print("Unable to parse config file.")
            return {}

    @classmethod
    def update_config_file(cls, key: str, value):
        """Updates or adds a value in the configuration file."""
        path = cls.get_file_path()

        existing_json = cls.get_config_file_info()
        existing_json[key] = value

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
