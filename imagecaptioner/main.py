import logging
import multiprocessing
import os
import argparse
import sys
import textwrap
import traceback
from datetime import datetime
from string import Template

from PIL import Image, ImageDraw, ImageFont, ImageOps
from PIL.ExifTags import TAGS

from imagecaptioner.logger import CustomFormatter


def create_parser():
    parser = argparse.ArgumentParser(usage='%(prog)s path caption_expression [options]', add_help=True,
                                     allow_abbrev=True,
                                     exit_on_error=True,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=textwrap.dedent("""Examples:
    > icaptioner 20190116_111115.jpg -c "Party, ##DateTime - Captured with phone ##Make ##Model"
    > icaptioner images/ --output=captioned_images
    > icaptioner 20190116_111115.jpg -p --font=fonts/Lato-Regular.ttf --size=120 --color=#030360 --bold=3
    > icaptioner 20190116_111115.jpg -r -dateformat "%H:%M" --output=captioned.jpg
    
    Show metatags:
    > icaptioner 20190116_111115.jpg -m
    > icaptioner images/ -m
                                     """)
                                     )
    parser.add_argument("path", type=str, help="File or directory location")
    parser.add_argument("-c", "--caption", type=str,
                        help="Caption with variables support taken from metatags. To access in caption e.g. ##DateTime",
                        default='##DateTime')
    parser.add_argument("-m", "--metatags", action="count", help="Show file metatags")
    parser.add_argument("-df", "--dateformat", type=str, help="Date time format", default="%Y/%m/%d, %H:%M")
    parser.add_argument("-o", "--output", type=str, help="Output file or directory, by default adds 'captioned_' prefix")
    parser.add_argument("-r", "--overwrite", action="count", help="Overwrite current photo with new one")
    parser.add_argument("-p", "--preview", action="count",
                        help="Preview mode. Show only mode instead of writing. Useful for testing. Only for specific file.")
    parser.add_argument("--font", type=str, help="Font type")
    parser.add_argument("--size", type=int, help="Font size, by default automatically chosen.")
    parser.add_argument("--color", type=str, help="Font color", default="blue")
    parser.add_argument("--bold", type=int, help="Font bold", default=1)
    parser.add_argument("--singlethread", action="count", help="Use single thread (only works for directory)")
    parser.add_argument('-v', '--verbose', help="Increase logging severity", action="store_const", dest="loglevel",
                        const=logging.DEBUG)
    return parser


def exception_handler(exception_type, value, track_back):
    logger.error(f"{exception_type}: {value} \n {traceback.extract_tb(track_back)}")


def gather_images_from_path(path: str) -> []:
    images = []
    valid_images = [".jpg", ".gif", ".png", ".tga"]
    for file in os.listdir(path):
        extension = os.path.splitext(file)[1]
        if extension.lower() not in valid_images:
            continue
        images.append(os.path.join(path, file))
    return images


def extract_exif_data(image: Image) -> {}:
    map_tag_dict = {}
    exif_data = image.getexif()
    for tag_id in exif_data:
        tag = TAGS.get(tag_id, tag_id)
        data = exif_data.get(tag_id)
        map_tag_dict[tag] = data
    return map_tag_dict


class MyTemplate(Template):
    delimiter = '##'


def find_font_size(text, font, image):
    tested_font_size = 64

    if image.width > image.height:
        target_width_ratio = 0.3
    else:
        target_width_ratio = 0.5

    tested_font = ImageFont.truetype(font, tested_font_size)
    fit_image = Image.new('RGB', (image.width, image.height))
    draw = ImageDraw.Draw(fit_image)
    observed_width, observed_height = draw.textsize(text, tested_font)
    estimated_font_size = tested_font_size / (observed_width / image.width) * target_width_ratio

    return round(estimated_font_size)


def draw_image(image: Image, output_filename, caption, font_type, font_color, font_size, stroke_width, preview,
               overwrite):
    if not overwrite and os.path.exists(output_filename):
        raise FileExistsError(f"File {output_filename} already exists. To overwrite use --overwrite flag.")

    draw = ImageDraw.Draw(image)
    width, height = image.size
    try:
        calculated_font_size = font_size or find_font_size(caption, font_type, image)
    except ZeroDivisionError as error:
        logger.warning(f"Unable to calculate font size. Picking up default one: {64}. Error: {error}")
        calculated_font_size = 64

    font = ImageFont.truetype(font_type, calculated_font_size)

    draw.text(xy=(width / 15 + 25, height - (80 + calculated_font_size)), text=caption, fill=font_color, font=font,
              align="left",
              stroke_width=stroke_width)

    if preview:
        image.show()
    else:
        image.save(output_filename)


def draw_caption_on_image(args: {}, image_path: str, output_filename: str):
    logger.debug(f"Going to add caption '{args.caption}' to file '{output_filename}'")
    image = ImageOps.exif_transpose(Image.open(image_path))

    tag_dict = extract_exif_data(image)
    logger.debug(f"Image metatags: {tag_dict}")

    if not args.font:
        args.font = os.path.join(os.path.dirname(__file__), "fonts/Lato-Regular.ttf")

    try:
        tag_dict['DateTime'] = datetime.strptime(tag_dict['DateTime'], "%Y:%m:%d %H:%M:%S").strftime(
            args.dateformat)
        logger.debug(f"Update DateTime metatag: {tag_dict['DateTime']}")
    except ValueError as err:
        tag_dict['DateTime'] = ""
        logger.warning(f"Unable to parse DateTime {err} for file {image_path}. Filled with empty string.")
    except KeyError as err:
        tag_dict['DateTime'] = ""
        logger.warning(f"{err} variable is missing for file {image_path}. Filled with empty string.")

    try:
        caption = MyTemplate(args.caption).safe_substitute(tag_dict)
        draw_image(image=image, output_filename=output_filename, caption=caption, font_type=args.font,
                   font_color=args.color, font_size=args.size, stroke_width=args.bold, preview=args.preview,
                   overwrite=args.overwrite)

        logger.info(f"Caption '{caption}' added to file '{output_filename}'")
    except KeyError as e:
        logger.error(
            f"Missed variable {e} given in caption for {args.path}. List of available variables: {tag_dict}")


def add_captions(args: {}):
    if os.path.isdir(args.path):
        image_paths = gather_images_from_path(args.path)

        if args.preview:
            raise AttributeError("Preview mode is not supported for directory.")

        if len(image_paths) == 0:
            raise ValueError(f"Unable to find any image under directory: {args.path}")

        output = args.output or "captioned"
        if os.path.exists(output):
            if not args.overwrite:
                raise FileExistsError(f"Directory '{output}' already exists. To overwrite use --overwrite flag.")
        else:
            os.mkdir(output)

        if args.singlethread:
            for image_path in image_paths:
                draw_caption_on_image(args, image_path, os.path.join(output, os.path.basename(image_path)))
        else:
            pool = multiprocessing.Pool(multiprocessing.cpu_count())
            pool.starmap_async(draw_caption_on_image,
                               [(args, image_path, os.path.join(output, os.path.basename(image_path))) for image_path in
                                image_paths]).get()
            pool.close()
        logger.info("SUCCESS Captions added.")
    else:
        output_filename = args.output or os.path.join(os.path.dirname(args.path),
                                                      "captioned_" + os.path.basename(args.path))
        draw_caption_on_image(args, args.path, output_filename)
        logger.info("SUCCESS Caption added.")


def get_metatags(args: {}):
    if os.path.isdir(args.path):
        image_paths = gather_images_from_path(args.path)
        if len(image_paths) == 0:
            raise ValueError(f"Unable to find any image under directory: {args.path}")

        for image_path in image_paths:
            image = Image.open(image_path)
            exif_data = extract_exif_data(image)
            print(f"{image_path} => {exif_data}")
    else:
        image = Image.open(args.path)
        exif_data = extract_exif_data(image)
        print(f"{args.path} => {exif_data}")


def init_logger(log_level):
    logger = logging.getLogger(__name__)
    logger.setLevel(level=log_level or logging.INFO)
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(CustomFormatter())
    logger.addHandler(stream_handler)
    return logger

logger = logging.getLogger(__name__)

def main():
    sys.excepthook = exception_handler

    args = create_parser().parse_args()
    logger = init_logger(args.loglevel)
    logger.debug(f"Input arguments: {args}")

    if not os.path.exists(args.path):
        raise ValueError(f"Unable to find image or directory under path: {args.path}")

    if args.metatags:
        get_metatags(args=args)
    else:
        add_captions(args=args)
