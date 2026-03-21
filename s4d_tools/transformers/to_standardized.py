from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from .standradized_schema import (
    STANDARDIZED_HEADER_COLUMNS,
    STANDARDIZED_MACHINE_COLUMNS,
    STANDARDIZED_OBJECTS_COLUMNS,
    STANDARDIZED_PRODUCTS_COLUMNS,
    STANDARDIZED_SPECIES_GROUPS_COLUMNS,
    STANDARDIZED_STATISTICS_COLUMNS,
    STANDARDIZED_STEMS_COLUMNS,
    META_HAS_PRI,
    META_SOURCE_TYPE,
    empty_standardized_table,
)


def _ensure_columns(df: pd.DataFrame, columns: list, fill_value: Any = "") -> pd.DataFrame:
    for c in columns:
        if c not in df.columns:
            df = df.copy()
            df[c] = fill_value
    existing = [c for c in columns if c in df.columns]
    return df[existing]


def _compute_hpr_statistics(hpr_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    stats = {
        "total_stems": 0,
        "species_names": [],
        "stems_per_species": [],
        "volume_per_species": [],
    }
    stems_df = hpr_data.get("stems")
    logs_df = hpr_data.get("logs")
    species_df = hpr_data.get("species_groups")

    if stems_df is None or stems_df.empty:
        return pd.DataFrame([stats])

    total_stems = len(stems_df)
    stats["total_stems"] = total_stems

    stems_per_species_counts = stems_df.groupby("species_group_key").size()

    if species_df is not None and not species_df.empty:
        species_names = []
        stems_counts = []
        volume_per_species = []

        logs_with_stems = None
        if logs_df is not None and not logs_df.empty and "stem_key" in logs_df.columns:
            logs_with_stems = logs_df.merge(
                stems_df[["stem_key", "species_group_key"]],
                on="stem_key",
                how="left",
            )

        for _, row in species_df.iterrows():
            sk = row.get("species_group_key", "")
            if not sk:
                continue
            name = row.get("species_group_name", "") or sk
            species_names.append(name)
            stems_counts.append(int(stems_per_species_counts.get(sk, 0)))

            vol = 0
            if logs_with_stems is not None and "volume_sob_m3" in logs_with_stems.columns:
                subset = logs_with_stems[logs_with_stems["species_group_key"] == sk]
                if not subset.empty:
                    vol_series = pd.to_numeric(subset["volume_sob_m3"].replace("", "0"), errors="coerce").fillna(0)
                    vol = int(vol_series.sum() * 100)  # raw units like PRD
            volume_per_species.append(vol)

        stats["species_names"] = species_names
        stats["stems_per_species"] = stems_counts
        stats["volume_per_species"] = volume_per_species
    else:
        for sk in stems_per_species_counts.index:
            if sk:
                stats["species_names"].append(sk)
                stats["stems_per_species"].append(int(stems_per_species_counts.get(sk, 0)))
                stats["volume_per_species"].append(0)

    return pd.DataFrame([stats])


def transform_prd_to_standardized(prd_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    out = {
        "header": _ensure_columns(prd_data["header"].copy(), STANDARDIZED_HEADER_COLUMNS)
        if not prd_data["header"].empty
        else empty_standardized_table(STANDARDIZED_HEADER_COLUMNS),
        "machine": _ensure_columns(prd_data["machine"].copy(), STANDARDIZED_MACHINE_COLUMNS)
        if not prd_data["machine"].empty
        else empty_standardized_table(STANDARDIZED_MACHINE_COLUMNS),
        "objects": _ensure_columns(prd_data["objects"].copy(), STANDARDIZED_OBJECTS_COLUMNS)
        if not prd_data["objects"].empty
        else empty_standardized_table(STANDARDIZED_OBJECTS_COLUMNS),
        "species_groups": _ensure_columns(
            prd_data["species_groups"].copy(), STANDARDIZED_SPECIES_GROUPS_COLUMNS
        )
        if not prd_data["species_groups"].empty
        else empty_standardized_table(STANDARDIZED_SPECIES_GROUPS_COLUMNS),
        "products": _ensure_columns(prd_data["products"].copy(), STANDARDIZED_PRODUCTS_COLUMNS)
        if not prd_data["products"].empty
        else empty_standardized_table(STANDARDIZED_PRODUCTS_COLUMNS),
        "statistics": _ensure_columns(
            prd_data["statistics"].copy(), STANDARDIZED_STATISTICS_COLUMNS
        )
        if not prd_data["statistics"].empty
        else empty_standardized_table(STANDARDIZED_STATISTICS_COLUMNS),
        "stems": empty_standardized_table(STANDARDIZED_STEMS_COLUMNS),
        "logs": pd.DataFrame(),  # PRD has no logs; keep parser shape (empty)
        META_SOURCE_TYPE: "classic_prd",
        META_HAS_PRI: False,
    }
    return out


def transform_hpr_to_standardized(hpr_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    header = hpr_data["header"].copy() if not hpr_data["header"].empty else pd.DataFrame()
    header = _ensure_columns(header, STANDARDIZED_HEADER_COLUMNS) if not header.empty else empty_standardized_table(STANDARDIZED_HEADER_COLUMNS)

    objects_df = hpr_data["objects"]
    if not objects_df.empty:
        ob = objects_df.copy()
        if "object_name" not in ob.columns:
            ob["object_name"] = ob.get("sub_object_name", "")
        if "contract_number" not in ob.columns:
            ob["contract_number"] = ""
        objects_out = _ensure_columns(ob, STANDARDIZED_OBJECTS_COLUMNS)
    else:
        objects_out = empty_standardized_table(STANDARDIZED_OBJECTS_COLUMNS)

    species = (
        _ensure_columns(hpr_data["species_groups"].copy(), STANDARDIZED_SPECIES_GROUPS_COLUMNS)
        if not hpr_data["species_groups"].empty
        else empty_standardized_table(STANDARDIZED_SPECIES_GROUPS_COLUMNS)
    )

    products = (
        _ensure_columns(hpr_data["products"].copy(), STANDARDIZED_PRODUCTS_COLUMNS)
        if not hpr_data["products"].empty
        else empty_standardized_table(STANDARDIZED_PRODUCTS_COLUMNS)
    )

    statistics = _compute_hpr_statistics(hpr_data)
    statistics = _ensure_columns(statistics, STANDARDIZED_STATISTICS_COLUMNS)

    stems = hpr_data["stems"]
    if not stems.empty:
        stems_out = _ensure_columns(stems.copy(), STANDARDIZED_STEMS_COLUMNS)
        extra = [c for c in stems.columns if c not in STANDARDIZED_STEMS_COLUMNS]
        if extra:
            stems_out = pd.concat([stems_out, stems[extra]], axis=1)
    else:
        stems_out = empty_standardized_table(STANDARDIZED_STEMS_COLUMNS)

    logs_out = hpr_data["logs"].copy() if not hpr_data["logs"].empty else pd.DataFrame()

    machine = (
        _ensure_columns(hpr_data["machine"].copy(), STANDARDIZED_MACHINE_COLUMNS)
        if not hpr_data["machine"].empty
        else empty_standardized_table(STANDARDIZED_MACHINE_COLUMNS)
    )

    return {
        "header": header,
        "machine": machine,
        "objects": objects_out,
        "species_groups": species,
        "products": products,
        "statistics": statistics,
        "stems": stems_out,
        "logs": logs_out,
        META_SOURCE_TYPE: "stanford_2010_hpr",
        META_HAS_PRI: False,
    }


def merge_pri_into_standardized(
    standardized: Dict[str, Any], pri_data: Dict[str, pd.DataFrame]
) -> Dict[str, Any]:
    result = {k: v for k, v in standardized.items() if k in (META_SOURCE_TYPE, META_HAS_PRI)}
    result[META_HAS_PRI] = True

    for key in ("header", "machine", "objects", "species_groups", "products", "statistics", "stems", "logs"):
        result[key] = standardized[key].copy() if standardized[key] is not None else standardized[key]

    if not pri_data["header"].empty and not result["header"].empty:
        prd_row = result["header"].iloc[0]
        pri_row = pri_data["header"].iloc[0]
        for col in result["header"].columns:
            if col in pri_row.index and (pd.isna(prd_row.get(col)) or prd_row.get(col) == ""):
                result["header"].iloc[0][col] = pri_row[col]
    if not pri_data["machine"].empty and not result["machine"].empty:
        prd_row = result["machine"].iloc[0]
        pri_row = pri_data["machine"].iloc[0]
        for col in result["machine"].columns:
            if col in pri_row.index and (pd.isna(prd_row.get(col)) or prd_row.get(col) == ""):
                result["machine"].iloc[0][col] = pri_row[col]
    if not pri_data["objects"].empty and not result["objects"].empty:
        prd_row = result["objects"].iloc[0]
        pri_row = pri_data["objects"].iloc[0]
        for col in result["objects"].columns:
            if col in pri_row.index and (pd.isna(prd_row.get(col)) or prd_row.get(col) == ""):
                result["objects"].iloc[0][col] = pri_row[col]

    for key in (
        "buyer_vendor",
        "calibration",
        "apt_history",
        "price_matrices",
        "operators",
        "production_statistics",
        "log_codes",
        "tree_codes",
        "additional_info",
    ):
        if key in pri_data:
            result[key] = pri_data[key]

    if not pri_data["logs"].empty:
        pri_logs = pri_data["logs"].copy()
        if result["logs"].empty:
            result["logs"] = pri_logs
        else:
            result["logs_pri"] = pri_logs
    else:
        if "logs_pri" in result:
            del result["logs_pri"]

    return result


def transform_prd_to_canonical(prd_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Backward-compatible alias for transform_prd_to_standardized()."""
    return transform_prd_to_standardized(prd_data)


def transform_hpr_to_canonical(hpr_data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Backward-compatible alias for transform_hpr_to_standardized()."""
    return transform_hpr_to_standardized(hpr_data)


def merge_pri_into_canonical(
    canonical: Dict[str, Any], pri_data: Dict[str, pd.DataFrame]
) -> Dict[str, Any]:
    """Backward-compatible alias for merge_pri_into_standardized()."""
    return merge_pri_into_standardized(canonical, pri_data)