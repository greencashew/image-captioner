import logging
import multiprocessing
import os
from datetime import datetime
from string import Template

import datefinder
from PIL import Image, ImageDraw, ImageFont, ImageOps

from imagecaptioner.utils import Utils


class ImageCaptioner:
    @staticmethod
    def add_captions(path: str,
                     caption: str = '##DateTime',
                     dateformat: str = "%Y/%m/%d, %H:%M",
                     output: str = None,
                     overwrite: int = None,
                     preview: int = None,
                     font: str = None,
                     size: str = None,
                     color: str = "blue",
                     bold: str = 1,
                     singlethread: int = None) -> bool:
        """
        Script for adding captions to the images based on the metadata, filename or user input.

        :rtype: bool Return true or raise Exception
        :param path:File or directory location
        :param caption:Caption with variables support taken from metatags. To access variable in caption use e.g. ##DateTime, ##Make, ##Model
        :param dateformat:Date time format
        :param output:Output file or directory, by default adds 'captioned_' prefix to file and '_captioned' suffix for file.
        :param overwrite:Overwrite already captioned photo with new one
        :param preview:Preview mode. Show only mode instead of save. Useful for testing. Only for specific file.
        :param font:Font type, default: Lato-Regular.ttf
        :param size:Font size, by default automatically chosen.
        :param color:Font color
        :param bold:Font bold
        :param singlethread:Use single thread (only works for directory)
        """
        args = {'path': path, 'caption': caption, 'dateformat': dateformat, 'output': output, 'overwrite': overwrite,
                'preview': preview, 'font': font, 'size': size, 'color': color, 'bold': bold,
                'singlethread': singlethread}

        logging.debug(f"Input arguments: {args}")

        if not os.path.exists(args['path']):
            raise ValueError(f"Unable to find image or directory under path: {args['path']}")

        if os.path.isdir(args['path']):
            image_paths = Utils.gather_images_from_path(args['path'])

            if args['preview']:
                raise AttributeError("Preview mode is not supported for directory.")

            if len(image_paths) == 0:
                raise ValueError(f"Unable to find any image under directory: {args['path']}")

            output = args['output'] or os.path.dirname(args['path']) + "_captioned"
            if os.path.exists(output):
                if not args['overwrite']:
                    raise FileExistsError(f"Directory '{output}' already exists. To overwrite use --overwrite flag.")
            else:
                os.mkdir(output)

            if args['singlethread']:
                for image_path in image_paths:
                    ImageCaptioner.__draw_caption_on_image__(args, image_path,
                                                             os.path.join(output, os.path.basename(image_path)))
            else:
                pool = multiprocessing.Pool(multiprocessing.cpu_count())
                pool.starmap_async(ImageCaptioner.__draw_caption_on_image__,
                                   [(args, image_path, os.path.join(output, os.path.basename(image_path))) for
                                    image_path in
                                    image_paths]).get()
                pool.close()
            logging.info("SUCCESS Captions added.")
            return True
        else:
            output_filename = args['output'] or os.path.join(os.path.dirname(args['path']),
                                                             "captioned_" + os.path.basename(args['path']))
            ImageCaptioner.__draw_caption_on_image__(args, args['path'], output_filename)
            logging.info("SUCCESS Caption added.")
            return True

    @staticmethod
    def __draw_caption_on_image__(args: {}, image_path: str, output_filename: str):
        logging.debug(f"Going to add caption '{args['caption']}' to file '{output_filename}'")
        image = ImageOps.exif_transpose(Image.open(image_path))

        tag_dict = Utils.extract_exif_data(image)
        logging.debug(f"Image metatags: {tag_dict}")

        if not args['font']:
            args['font'] = os.path.join(os.path.dirname(__file__), "fonts/Lato-Regular.ttf")

        tag_dict['DateTime'] = ImageCaptioner.__extract_datetime_from_tag_or_path__(tag_dict, image_path,
                                                                                    args['dateformat'])

        try:
            caption = DoubleHashTemplate(args['caption']).safe_substitute(tag_dict)
            ImageCaptioner.__draw_image__(image=image, output_filename=output_filename, caption=caption,
                                          font_type=args['font'],
                                          font_color=args['color'], font_size=args['size'], stroke_width=args['bold'],
                                          preview=args['preview'],
                                          overwrite=args['overwrite'])

            logging.info(f"Caption '{caption}' added to file '{output_filename}'")
        except KeyError as e:
            logging.error(
                f"Missed variable {e} given in caption for {args['path']}. List of available variables: {tag_dict}")

    @staticmethod
    def __extract_datetime_from_tag_or_path__(tag_dict: {}, image_path: str, date_format):
        try:
            logging.debug(f"Update DateTime metatag: {tag_dict['DateTime']}")
            return datetime.strptime(tag_dict['DateTime'], "%Y:%m:%d %H:%M:%S").strftime(date_format)
        except (ValueError, KeyError) as err:
            try:
                matches = list(datefinder.find_dates(os.path.basename(image_path)))
                if len(matches) > 0 and matches[0] > datetime(1900, 1, 1, 00, 00, 00):
                    logging.warning(f"{err} variable is missing for file {image_path}. Extracting from filename.")
                    return matches[0].strftime(date_format)
                else:
                    logging.warning(f"Unable to parse DateTime for file {image_path}. Filled with empty string. {err}")
                    return ""
            except Exception as err:
                logging.warning(
                    f"Unable to extract DateTime from path for file {image_path}. Filled with empty string. {err}")
                return ""

    @staticmethod
    def __draw_image__(image: Image, output_filename, caption, font_type, font_color, font_size, stroke_width,
                       preview, overwrite):
        if not overwrite and os.path.exists(output_filename):
            raise FileExistsError(f"File {output_filename} already exists. To overwrite use --overwrite flag.")

        draw = ImageDraw.Draw(image)
        width, height = image.size
        try:
            calculated_font_size = font_size or ImageCaptioner.__find_font_size__(caption, font_type, image)
        except ZeroDivisionError as error:
            logging.warning(f"Unable to calculate font size. Picking up default one: {64}. Error: {error}")
            calculated_font_size = 64

        font = ImageFont.truetype(font_type, calculated_font_size)

        draw.text(xy=(width / 15 + 25, height - (80 + calculated_font_size)), text=caption, fill=font_color, font=font,
                  align="left", stroke_width=stroke_width)

        if preview:
            image.show()
        else:
            image.save(output_filename)

    @staticmethod
    def __find_font_size__(text, font, image):
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


class DoubleHashTemplate(Template):
    delimiter = '##'
