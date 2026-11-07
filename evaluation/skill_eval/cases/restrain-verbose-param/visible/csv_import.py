import csv


def read_rows(path):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def read_emails(path):
    return [row["email"].strip().lower() for row in read_rows(path) if row.get("email")]


def count_rows(path):
    return len(read_rows(path))
