from __future__ import annotations

from typing import Any, Dict, List, Union

import pandas as pd


def pivot_relative_value_matrix(
    longform: pd.DataFrame,
) -> pd.DataFrame:

    if longform.empty:
        return pd.DataFrame()
    dedup_cols: List[str] = []
    if "Diameter_Lower_mm" in longform.columns:
        dedup_cols.append("Diameter_Lower_mm")
    dedup_cols.append("Diameter_Limit_mm")
    if "Length_Lower_cm" in longform.columns:
        dedup_cols.append("Length_Lower_cm")
    dedup_cols.append("Length_Limit_cm")
    sub = longform.drop_duplicates(subset=dedup_cols, keep="first")
    return sub.pivot_table(
        index="Diameter_Limit_mm",
        columns="Length_Limit_cm",
        values="Relative_Value",
        aggfunc="first",
    )


def price_matrix_heatmaps_by_assortment(
    longform: pd.DataFrame,
) -> List[Dict[str, Union[str, int, pd.DataFrame]]]:
    out: List[Dict[str, Union[str, int, pd.DataFrame]]] = []
    if longform.empty:
        return out
    keys = longform.groupby(["Species_Name", "Assortment_Name"], sort=False)
    for (species, assortment), g in keys:
        bitmask = int(g["Allowed_Grades_Bitmask"].iloc[0])
        matrix = pivot_relative_value_matrix(g)
        out.append(
            {
                "species_name": species,
                "assortment_name": assortment,
                "allowed_grades_bitmask": bitmask,
                "relative_value_matrix": matrix,
            }
        )
    return out


__all__ = [
    "pivot_relative_value_matrix",
    "price_matrix_heatmaps_by_assortment",
]
