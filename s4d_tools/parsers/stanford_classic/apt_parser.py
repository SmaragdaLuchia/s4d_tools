from __future__ import annotations

from typing import Any, Dict, Tuple, Union

from .utils.helpers import (
    get_value,
    load_raw_data,
    normalize_value,
    parse_list,
    parse_multiline_list,
)


class APTParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self._raw_data = None

    def _load_raw_data(self):
        if self._raw_data is None:
            self._raw_data = load_raw_data(self.file_path, merge_duplicate_keys=True)
        return self._raw_data

    def _get_value(self, group_id, variable_id, default=None):
        if self._raw_data is None:
            self._load_raw_data()
        return get_value(self._raw_data, group_id, variable_id, default)

    def parse_raw_blocks(self) -> Dict[Tuple[int, int], str]:
        self._load_raw_data()
        return {
            k: normalize_value(v, list_join="")
            for k, v in self._raw_data.items()
        }

    def parse_price_matrix(self) -> Dict[str, Any]:
        self._load_raw_data()
        return {
            "total_tree_species_count": parse_list(self._get_value(111, 1), int),
            "assortments_per_species": parse_list(self._get_value(116, 1), int),
            "diameter_classes_per_matrix": parse_list(self._get_value(117, 1), int),
            "length_classes_per_matrix": parse_list(self._get_value(118, 1), int),
            "tree_species_names": parse_multiline_list(self._get_value(120, 1)),
            "assortment_names": parse_multiline_list(self._get_value(121, 1)),
            "diameter_class_limits_mm": parse_list(self._get_value(131, 1), int),
            "length_class_limits": parse_list(self._get_value(132, 1), int),
            "permitted_quality_grade_bitmasks": parse_list(self._get_value(141, 1), int),
            "relative_price_value_matrix_flat": parse_list(self._get_value(162, 2), int),
        }

    def parse(self) -> Dict[str, Any]:
        return {"price_matrix": self.parse_price_matrix()}


__all__ = ["APTParser"]
