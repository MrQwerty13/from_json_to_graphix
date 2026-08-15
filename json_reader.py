import json
from typing import Any


def read_json(path: str) -> Any:
    """Read a JSON file and return the parsed object.

    Args:
        path: Path to the JSON file.

    Returns:
        Parsed JSON (dict/list).
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_json_from_fileobj(fileobj) -> Any:
    """Read JSON from a file-like object (e.g., Werkzeug upload)."""
    return json.load(fileobj)
