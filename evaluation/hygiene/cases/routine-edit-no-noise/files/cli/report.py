"""Command-line entry point for the sales report."""

import argparse
import csv
import sys


def build_parser():
    parser = argparse.ArgumentParser(prog="report")
    parser.add_argument("source", help="CSV file of sales rows")
    parser.add_argument("--output", default="summary.csv")
    # Region codes are upper case in the source data, so match that.
    parser.add_argument("--region", type=str.upper)
    return parser


def summarise(rows, region=None):
    totals = {}
    for row in rows:
        if region and row["region"] != region:
            continue
        totals[row["product"]] = totals.get(row["product"], 0) + int(row["units"])
    return totals


def main(argv=None, out=sys.stdout):
    args = build_parser().parse_args(argv)
    with open(args.source, newline="") as handle:
        totals = summarise(csv.DictReader(handle), args.region)
    with open(args.output, "w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["product", "units"])
        for product, units in sorted(totals.items()):
            writer.writerow([product, units])
    print(f"Wrote {len(totals)} rows to {args.output}", file=out)
    return 0
