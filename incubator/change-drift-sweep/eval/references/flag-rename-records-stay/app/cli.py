"""Command line for the reporting service."""

import argparse
import sys

from app.export import export_rows


def build_parser():
    parser = argparse.ArgumentParser(prog="reportctl")
    commands = parser.add_subparsers(dest="command", required=True)
    export = commands.add_parser("export", help="Write order rows as CSV.")
    export.add_argument("source", help="CSV of orders with a `changed` column (YYYY-MM-DD).")
    export.add_argument("--after", metavar="DATE",
                        help="Only rows changed on or after DATE (YYYY-MM-DD).")
    export.add_argument("--output", default="-", help="File to write, or - for stdout.")
    return parser


def main(argv=None, stdout=None):
    args = build_parser().parse_args(argv)
    if args.command == "export":
        return export_rows(args.source, since=args.after, output=args.output,
                           stdout=stdout or sys.stdout)
    return 2
