"""
Shared helpers for StanForD Classic tilde-separated files (PRD, PRI, APT, etc.).

Each segment after splitting on ``~`` is parsed as::

    <group_id> <variable_id> [<rest>]

Repeated (group_id, variable_id) blocks are merged into a list (PRI-style),
which matches production-individual files and is a safe superset for PRD.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple, Union

from ..constants import BLOCK_SEPARATOR, DEFAULT_ENCODING

RawBlockMap = Dict[Tuple[int, int], Any]


def load_raw_data(
    file_path: Union[str, Path],
    encoding: str = DEFAULT_ENCODING,
    *,
    merge_duplicate_keys: bool = True,
) -> RawBlockMap:
    path = Path(file_path)
    with open(path, "r", encoding=encoding) as f:
        content = f.read()

    data_dict: RawBlockMap = {}
    for data_item in content.split(BLOCK_SEPARATOR):
        parts = data_item.strip().split(maxsplit=2)
        if len(parts) < 2:
            continue
        try:
            group_id = int(parts[0])
            variable_id = int(parts[1])
        except ValueError:
            continue

        value = parts[2] if len(parts) > 2 else None
        key = (group_id, variable_id)

        if merge_duplicate_keys:
            if key in data_dict:
                if not isinstance(data_dict[key], list):
                    data_dict[key] = [data_dict[key]]
                data_dict[key].append(value)
            else:
                data_dict[key] = value
        else:
            data_dict[key] = value

    return data_dict


def get_value(
    raw_data: RawBlockMap,
    group_id: int,
    variable_id: int,
    default: Any = None,
) -> Any:
   return raw_data.get((group_id, variable_id), default)


def normalize_value(value: Any, *, list_join: str = "\n") -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return list_join.join(str(x) for x in value if x is not None)
    return str(value)


def parse_list(
    value: Any,
    type_func: type = int,
) -> List[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        value = " ".join(str(x) for x in value if x is not None)
    if not isinstance(value, str) or not value.strip():
        return []
    try:
        return [type_func(x.strip()) for x in value.split() if x.strip()]
    except (ValueError, TypeError):
        return []


def parse_multiline_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        out: List[str] = []
        for chunk in value:
            if chunk is None:
                continue
            for line in str(chunk).split("\n"):
                s = line.strip()
                if s:
                    out.append(s)
        return out
    if not isinstance(value, str):
        value = str(value)
    return [line.strip() for line in value.split("\n") if line.strip()]


__all__ = [
    "RawBlockMap",
    "load_raw_data",
    "get_value",
    "normalize_value",
    "parse_list",
    "parse_multiline_list",
]
