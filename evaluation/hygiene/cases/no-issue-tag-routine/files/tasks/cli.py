"""Command-line entry point for the task list."""

import argparse
import json
import sys


def build_parser():
    parser = argparse.ArgumentParser(prog="tasks")
    parser.add_argument("path", help="JSON file of tasks")
    parser.add_argument("--all", action="store_true", help="include done tasks")
    return parser


def visible(tasks, show_all=False):
    # Keep the file's order: people arrange their tasks by hand, so never sort.
    return [task for task in tasks if show_all or not task["done"]]


def main(argv=None, out=sys.stdout):
    args = build_parser().parse_args(argv)
    with open(args.path) as handle:
        tasks = json.load(handle)
    for task in visible(tasks, args.all):
        print(f"- {task['title']}", file=out)
    return 0
