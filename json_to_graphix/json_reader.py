import json
from typing import Any


def read_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def read_json_from_fileobj(fileobj) -> Any:
    return json.load(fileobj)
