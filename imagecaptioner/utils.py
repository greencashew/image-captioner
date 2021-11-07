import logging
import os

from PIL import Image
from PIL.ExifTags import TAGS


class Utils:
    @staticmethod
    def extract_exif_data(image: Image) -> {}:
        map_tag_dict = {}
        exif_data = image.getexif()
        for tag_id in exif_data:
            tag = TAGS.get(tag_id, tag_id)
            data = exif_data.get(tag_id)
            map_tag_dict[tag] = data
        return map_tag_dict

    @staticmethod
    def gather_images_from_path(path: str) -> []:
        images = []
        valid_images = [".jpg", ".gif", ".png", ".tga"]
        for file in os.listdir(path):
            extension = os.path.splitext(file)[1]
            if extension.lower() not in valid_images:
                continue
            images.append(os.path.join(path, file))
        return images


class CustomFormatter(logging.Formatter):
    grey = "\x1b[38;21m"
    yellow = "\x1b[33;21m"
    red = "\x1b[31;21m"
    blue = "\x1b[34m"
    bold_red = "\x1b[31;1m"
    reset = "\x1b[0m"
    format = "[%(filename)s:%(lineno)d] %(levelname)s: %(message)s "

    FORMATS = {
        logging.DEBUG: blue + format + reset,
        logging.INFO: grey + format + reset,
        logging.WARNING: yellow + format + reset,
        logging.ERROR: red + format + reset,
        logging.CRITICAL: bold_red + format + reset
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def get_logging_handler():
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(CustomFormatter())
    return stream_handler
