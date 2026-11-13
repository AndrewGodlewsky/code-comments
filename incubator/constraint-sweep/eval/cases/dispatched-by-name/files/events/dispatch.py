"""Hand each payment event to the handler for its kind."""
import configparser
from pathlib import Path

from events import handlers

ROUTES = Path(__file__).resolve().parent.parent / "config" / "routes.ini"


def load_kinds(path=ROUTES):
    """Return the set of event kinds switched on in the routes file."""
    parser = configparser.ConfigParser()
    parser.read(path, encoding="utf-8")
    return {kind for kind, state in parser["kinds"].items() if state.strip() == "on"}


def dispatch(event, kinds=None):
    """Return the postings for one event. A kind that is not switched on is a KeyError."""
    kinds = load_kinds() if kinds is None else kinds
    kind = event["kind"]
    if kind not in kinds:
        raise KeyError(kind)
    return getattr(handlers, "handle_" + kind)(event)
