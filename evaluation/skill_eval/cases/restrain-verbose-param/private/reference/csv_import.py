import csv


def read_rows(path, delimiter=","):
    with open(path, newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def read_emails(path, delimiter=","):
    return [row["email"].strip().lower() for row in read_rows(path, delimiter) if row.get("email")]


def count_rows(path, delimiter=","):
    return len(read_rows(path, delimiter))
