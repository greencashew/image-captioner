import argparse
import logging
import sys
import textwrap
import traceback

from imagecaptioner.captioner import ImageCaptioner
from imagecaptioner.metatags import Metags
from imagecaptioner.utils import get_logging_handler


def create_parser():
    parser = argparse.ArgumentParser(usage='%(prog)s path caption_expression [options]', add_help=True,
                                     allow_abbrev=True,
                                     exit_on_error=True,
                                     formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=textwrap.dedent("""Examples:
    > imagecaptioner 20190116_111115.jpg -c "Party, ##DateTime - Captured with phone ##Make ##Model"
    > imagecaptioner images/ --output=captioned_images
    > imagecaptioner 20190116_111115.jpg -p --font=fonts/Lato-Regular.ttf --size=120 --color=#030360 --bold=3
    > imagecaptioner 20190116_111115.jpg -r -dateformat "%H:%M" --output=captioned.jpg
    
    Show metatags:
    > imagecaptioner 20190116_111115.jpg -m
    > imagecaptioner images/ -m
                                     """)
                                     )
    parser.add_argument("path", type=str, help="File or directory location")
    parser.add_argument("-c", "--caption", type=str,
                        help="Caption with variables support taken from metatags. To access variable in caption use e.g. ##DateTime",
                        default='##DateTime')
    parser.add_argument("-m", "--metatags", action="count", help="Show file metatags")
    parser.add_argument("-df", "--dateformat", type=str, help="Date time format", default="%Y/%m/%d, %H:%M")
    parser.add_argument("-o", "--output", type=str,
                        help="Output file or directory, by default adds 'captioned_' prefix")
    parser.add_argument("-r", "--overwrite", action="count", help="Overwrite already captioned photo with new one")
    parser.add_argument("-p", "--preview", action="count",
                        help="Preview mode. Show only mode instead of save. Useful for testing. Only for specific file.")
    parser.add_argument("--font", type=str, help="Font type")
    parser.add_argument("--size", type=int, help="Font size, by default automatically chosen.")
    parser.add_argument("--color", type=str, help="Font color", default="blue")
    parser.add_argument("--bold", type=int, help="Font bold", default=1)
    parser.add_argument("--singlethread", action="count", help="Use single thread (only works for directory)")
    parser.add_argument('-v', '--verbose', help="Increase logging severity", action="store_const", dest="loglevel",
                        const=logging.INFO)
    return parser


def exception_handler(exception_type, value, track_back):
    print(f"{exception_type}: {value} \n {traceback.extract_tb(track_back)}")


def main():
    sys.excepthook = exception_handler

    args = create_parser().parse_args()
    logging.basicConfig(level=args.loglevel, handlers=[get_logging_handler()])

    if args.metatags:
        Metags.get_metatags(args=args)
    else:
        ImageCaptioner.add_captions(
            path=args.path,
            caption=args.caption,
            dateformat=args.dateformat,
            output=args.output,
            overwrite=args.overwrite,
            preview=args.preview,
            font=args.font,
            size=args.size,
            color=args.color,
            bold=args.bold,
            singlethread=args.singlethread,
        )
