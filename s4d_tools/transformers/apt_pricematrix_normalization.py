from __future__ import annotations

from typing import Any, Dict, List, Union

import pandas as pd

from .standradized_schema import STANDARDIZED_PRICING_COLUMNS


def _standardized_pricing_columns() -> List[str]:
    return list(STANDARDIZED_PRICING_COLUMNS)


def _is_classic_apt_price_matrix_dict(d: Dict[str, Any]) -> bool:
    return isinstance(d, dict) and "relative_price_value_matrix_flat" in d


def expand_classic_apt_price_matrix(pm: Dict[str, Any]) -> pd.DataFrame:
    """
    Expand StanForD Classic APT ``parse_price_matrix()`` output into standardized long-form rows.
    """
    flat = pm.get("relative_price_value_matrix_flat") or []
    dc = pm.get("diameter_classes_per_matrix") or []
    lc = pm.get("length_classes_per_matrix") or []
    d_mm = pm.get("diameter_class_limits_mm") or []
    l_cm = pm.get("length_class_limits") or []
    species_names = pm.get("tree_species_names") or []
    assortment_names = pm.get("assortment_names") or []
    aps = pm.get("assortments_per_species") or []
    bitmasks = pm.get("permitted_quality_grade_bitmasks") or []

    if not flat or not dc or not lc:
        return pd.DataFrame(columns=_standardized_pricing_columns())

    n_mat = min(len(dc), len(lc))
    rows: List[Dict[str, Any]] = []
    flat_off = 0
    d_lim_off = 0
    l_lim_off = 0

    def species_for_matrix(m: int) -> str:
        if not aps or not species_names:
            return ""
        start = 0
        for si, cnt in enumerate(aps):
            if m < start + cnt:
                return str(species_names[si]) if si < len(species_names) else ""
            start += cnt
        return str(species_names[-1]) if species_names else ""

    for m in range(n_mat):
        d_c = int(dc[m])
        l_c = int(lc[m])
        cells = d_c * l_c
        if flat_off + cells > len(flat):
            break
        n_d_bounds = d_c + 1
        n_l_bounds = l_c + 1
        if d_lim_off + n_d_bounds > len(d_mm) or l_lim_off + n_l_bounds > len(l_cm):
            break
        d_bounds = d_mm[d_lim_off : d_lim_off + n_d_bounds]
        l_bounds = l_cm[l_lim_off : l_lim_off + n_l_bounds]
        d_lim_off += n_d_bounds
        l_lim_off += n_l_bounds

        asm_name = str(assortment_names[m]) if m < len(assortment_names) else ""
        sp_name = species_for_matrix(m)
        bitmask = int(bitmasks[m]) if m < len(bitmasks) else 0

        for i in range(d_c):
            for j in range(l_c):
                k = flat_off + i * l_c + j
                rel = int(flat[k]) if k < len(flat) else 0
                rows.append(
                    {
                        "Species_Name": sp_name,
                        "Assortment_Name": asm_name,
                        "Allowed_Grades_Bitmask": bitmask,
                        "Diameter_Lower_mm": int(d_bounds[i]),
                        "Diameter_Limit_mm": int(d_bounds[i + 1]),
                        "Length_Lower_cm": int(l_bounds[j]),
                        "Length_Limit_cm": int(l_bounds[j + 1]),
                        "Relative_Value": rel,
                    }
                )
        flat_off += cells

    return build_relative_price_longform(rows)


def build_relative_price_longform(rows: Union[List[Dict[str, Any]], pd.DataFrame]) -> pd.DataFrame:
    df = rows.copy() if isinstance(rows, pd.DataFrame) else pd.DataFrame(rows or [])
    cols = _standardized_pricing_columns()

    defaults = {
        "Allowed_Grades_Bitmask": 0,
        "Diameter_Lower_mm": 0,
        "Diameter_Limit_mm": 0,
        "Length_Lower_cm": 0,
        "Length_Limit_cm": 0,
        "Relative_Value": 0,
    }

    df = df.reindex(columns=cols)
    df = df.fillna(defaults).fillna("")

    return df


def price_matrix_from_any_apt_shape(
    apt_parse_result: Union[Dict[str, Any], pd.DataFrame, None],
) -> pd.DataFrame:
    """
    Normalize common APT parse output shapes into standardized long-form matrix rows.
    """
    if apt_parse_result is None:
        return pd.DataFrame(columns=_standardized_pricing_columns())

    if isinstance(apt_parse_result, pd.DataFrame):
        return build_relative_price_longform(apt_parse_result)

    if isinstance(apt_parse_result, dict):
        for key in ("pricing_matrix", "apt_pricing_matrix"):
            value = apt_parse_result.get(key)
            if isinstance(value, pd.DataFrame):
                return build_relative_price_longform(value)
            if isinstance(value, dict) and _is_classic_apt_price_matrix_dict(value):
                return expand_classic_apt_price_matrix(value)

        if "fields" in apt_parse_result and isinstance(apt_parse_result["fields"], dict):
            inner = apt_parse_result["fields"].get("price_matrix")
            if isinstance(inner, pd.DataFrame):
                return build_relative_price_longform(inner)
            if isinstance(inner, list):
                return build_relative_price_longform(inner)
            if isinstance(inner, dict) and _is_classic_apt_price_matrix_dict(inner):
                return expand_classic_apt_price_matrix(inner)
            if isinstance(inner, dict):
                return build_relative_price_longform([inner])

        if "price_matrix" in apt_parse_result:
            value = apt_parse_result["price_matrix"]
            if value is None:
                pass
            elif isinstance(value, pd.DataFrame):
                return build_relative_price_longform(value)
            elif isinstance(value, list):
                return build_relative_price_longform(value)
            elif isinstance(value, dict) and _is_classic_apt_price_matrix_dict(value):
                return expand_classic_apt_price_matrix(value)
            elif isinstance(value, dict):
                return build_relative_price_longform([value])

        if _is_classic_apt_price_matrix_dict(apt_parse_result):
            return expand_classic_apt_price_matrix(apt_parse_result)

        return build_relative_price_longform(apt_parse_result)


__all__ = [
    "build_relative_price_longform",
    "expand_classic_apt_price_matrix",
    "price_matrix_from_any_apt_shape",
]
