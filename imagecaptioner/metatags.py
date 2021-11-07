import os

from PIL import Image

from imagecaptioner.utils import Utils


class Metags:
    @staticmethod
    def get_metatags(args: {}):
        if not os.path.exists(args.path):
            raise ValueError(f"Unable to find image or directory under path: {args.path}")

        if os.path.isdir(args.path):
            image_paths = Utils.gather_images_from_path(args.path)
            if len(image_paths) == 0:
                raise ValueError(f"Unable to find any image under directory: {args.path}")

            for image_path in image_paths:
                image = Image.open(image_path)
                exif_data = Utils.extract_exif_data(image)
                print(f"{image_path} => {exif_data}")
        else:
            image = Image.open(args.path)
            exif_data = Utils.extract_exif_data(image)
            print(f"{args.path} => {exif_data}")
