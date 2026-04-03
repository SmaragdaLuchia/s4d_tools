from __future__ import annotations

from typing import Any, Dict, Optional, Union

import pandas as pd

from .apt_pricematrix_normalization import price_matrix_from_any_apt_shape
from .standradized_schema import (
    STANDARDIZED_PRICING_COLUMNS,
    STANDARDIZED_HEADER_COLUMNS,
    STANDARDIZED_MACHINE_COLUMNS,
    STANDARDIZED_OBJECTS_COLUMNS,
    STANDARDIZED_PRODUCTS_COLUMNS,
    STANDARDIZED_SPECIES_GROUPS_COLUMNS,
    STANDARDIZED_STATISTICS_COLUMNS,
    STANDARDIZED_STEMS_COLUMNS,
    META_HAS_PRI,
    META_SOURCE_TYPE,
    empty_standardized_report,
    empty_standardized_table,
)

# --- HELPER FUNCTIONS ---

def _ensure_columns(df: pd.DataFrame, columns: list, fill_value: Any = "") -> pd.DataFrame:
    """Uses Pandas reindex for fast, memory-efficient column ensuring."""
    return df.reindex(columns=columns, fill_value=fill_value)

def _format_table(df_dict: Dict[str, pd.DataFrame], key: str, columns: list) -> pd.DataFrame:
    """Helper to check for empty tables and apply _ensure_columns to reduce boilerplate."""
    df = df_dict.get(key)
    if df is None or df.empty:
        return empty_standardized_table(columns)
    return _ensure_columns(df.copy(), columns)

def _merge_first_row(primary_df: pd.DataFrame, secondary_df: pd.DataFrame) -> pd.DataFrame:
    """Safely merges primary and secondary row data without using .iloc mutation."""
    if primary_df.empty or secondary_df.empty:
        return primary_df

    primary_nan = primary_df.replace("", pd.NA)
    secondary_nan = secondary_df.replace("", pd.NA)
    
    merged = primary_nan.combine_first(secondary_nan)
    return merged.fillna("")

def _compute_hpr_statistics(hpr_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Computes statistics using vectorized groupby and merge instead of iterrows."""
    stems_df = hpr_data.get("stems", pd.DataFrame())
    logs_df = hpr_data.get("logs", pd.DataFrame())
    species_df = hpr_data.get("species_groups", pd.DataFrame())

    if stems_df.empty:
        return pd.DataFrame([{
            "total_stems": 0, "species_names": [], 
            "stems_per_species": [], "volume_per_species": []
        }])

    # 1. Stems per species
    stems_counts = stems_df.groupby("species_group_key").size().reset_index(name="stems_count")

    # 2. Volume per species
    if not logs_df.empty and "stem_key" in logs_df.columns:
        logs_merged = logs_df.merge(stems_df[["stem_key", "species_group_key"]], on="stem_key", how="left")
        logs_merged["volume_sob_m3"] = pd.to_numeric(logs_merged["volume_sob_m3"].replace("", "0"), errors="coerce").fillna(0)
        logs_merged["volume"] = (logs_merged["volume_sob_m3"] * 100).astype(int)
        vol_counts = logs_merged.groupby("species_group_key")["volume"].sum().reset_index()
    else:
        vol_counts = pd.DataFrame(columns=["species_group_key", "volume"])

    # 3. Compile final statistics
    if not species_df.empty:
        stats_df = species_df[["species_group_key", "species_group_name"]].copy()
        stats_df["species_group_name"] = stats_df["species_group_name"].replace("", pd.NA).fillna(stats_df["species_group_key"])
    else:
        stats_df = stems_counts[["species_group_key"]].copy()
        stats_df["species_group_name"] = stats_df["species_group_key"]

    stats_df = stats_df.merge(stems_counts, on="species_group_key", how="left").fillna({"stems_count": 0})
    stats_df = stats_df.merge(vol_counts, on="species_group_key", how="left").fillna({"volume": 0})

    return pd.DataFrame([{
        "total_stems": len(stems_df),
        "species_names": stats_df["species_group_name"].tolist(),
        "stems_per_species": stats_df["stems_count"].astype(int).tolist(),
        "volume_per_species": stats_df["volume"].astype(int).tolist(),
    }])


def _standardized_pricing_matrix(
    apt_parse_result: Optional[Union[Dict[str, Any], pd.DataFrame]],
) -> pd.DataFrame:
    """Classic APT parse output → standardized long-form ``pricing_matrix``; empty table if no APT."""
    if apt_parse_result is None:
        return empty_standardized_table(STANDARDIZED_PRICING_COLUMNS)
    return _ensure_columns(
        price_matrix_from_any_apt_shape(apt_parse_result).copy(),
        STANDARDIZED_PRICING_COLUMNS,
    )


# --- TRANSFORMATION FUNCTIONS ---

def transform_prd_to_standardized(
    prd_data: Dict[str, pd.DataFrame],
    apt_parse_result: Optional[Union[Dict[str, Any], pd.DataFrame]] = None,
) -> Dict[str, Any]:
    apt_df = _standardized_pricing_matrix(apt_parse_result)
    return {
        "header": _format_table(prd_data, "header", STANDARDIZED_HEADER_COLUMNS),
        "machine": _format_table(prd_data, "machine", STANDARDIZED_MACHINE_COLUMNS),
        "objects": _format_table(prd_data, "objects", STANDARDIZED_OBJECTS_COLUMNS),
        "species_groups": _format_table(prd_data, "species_groups", STANDARDIZED_SPECIES_GROUPS_COLUMNS),
        "products": _format_table(prd_data, "products", STANDARDIZED_PRODUCTS_COLUMNS),
        "statistics": _format_table(prd_data, "statistics", STANDARDIZED_STATISTICS_COLUMNS),
        "stems": empty_standardized_table(STANDARDIZED_STEMS_COLUMNS),
        "logs": pd.DataFrame(),  # PRD has no logs; keep parser shape (empty)
        "pricing_matrix": apt_df,
        META_SOURCE_TYPE: "classic_prd",
        META_HAS_PRI: False,
    }


def transform_hpr_to_standardized(
    hpr_data: Dict[str, pd.DataFrame],
    apt_parse_result: Optional[Union[Dict[str, Any], pd.DataFrame]] = None,
) -> Dict[str, Any]:
    
    # Process objects separately because it requires custom mapping before ensuring columns
    objects_df = hpr_data.get("objects", pd.DataFrame())
    if not objects_df.empty:
        ob = objects_df.copy()
        if "object_name" not in ob.columns:
            ob["object_name"] = ob.get("sub_object_name", "")
        if "contract_number" not in ob.columns:
            ob["contract_number"] = ""
        objects_out = _ensure_columns(ob, STANDARDIZED_OBJECTS_COLUMNS)
    else:
        objects_out = empty_standardized_table(STANDARDIZED_OBJECTS_COLUMNS)

    # Process stems separately to retain extra un-standardized columns
    stems = hpr_data.get("stems", pd.DataFrame())
    if not stems.empty:
        stems_out = _ensure_columns(stems.copy(), STANDARDIZED_STEMS_COLUMNS)
        extra = [c for c in stems.columns if c not in STANDARDIZED_STEMS_COLUMNS]
        if extra:
            stems_out = pd.concat([stems_out, stems[extra]], axis=1)
    else:
        stems_out = empty_standardized_table(STANDARDIZED_STEMS_COLUMNS)

    # Compute statistics
    statistics = _compute_hpr_statistics(hpr_data)
    statistics = _ensure_columns(statistics, STANDARDIZED_STATISTICS_COLUMNS)

    apt_df = _standardized_pricing_matrix(apt_parse_result)

    return {
        "header": _format_table(hpr_data, "header", STANDARDIZED_HEADER_COLUMNS),
        "machine": _format_table(hpr_data, "machine", STANDARDIZED_MACHINE_COLUMNS),
        "objects": objects_out,
        "species_groups": _format_table(hpr_data, "species_groups", STANDARDIZED_SPECIES_GROUPS_COLUMNS),
        "products": _format_table(hpr_data, "products", STANDARDIZED_PRODUCTS_COLUMNS),
        "statistics": statistics,
        "stems": stems_out,
        "logs": hpr_data.get("logs", pd.DataFrame()).copy() if not hpr_data.get("logs", pd.DataFrame()).empty else pd.DataFrame(),
        "pricing_matrix": apt_df,
        META_SOURCE_TYPE: "stanford_2010_hpr",
        META_HAS_PRI: False,
    }


def transform_pin_to_standardized(
    pin_data: Dict[str, pd.DataFrame],
) -> Dict[str, Any]:
    out = empty_standardized_report("stanford_2010_pin", False)

    products_in = pin_data.get("products", pd.DataFrame())
    if not products_in.empty:
        products = products_in.copy()
        if "product_key" not in products.columns:
            products["product_key"] = products.get("product_user_id", "")
        if "product_name" not in products.columns:
            products["product_name"] = ""
        out["products"] = _ensure_columns(products, STANDARDIZED_PRODUCTS_COLUMNS)

    matrix_in = pin_data.get("price_matrices", pd.DataFrame())
    if not matrix_in.empty:
        pm = matrix_in.copy()

        # Join species data using pd.merge instead of mapping dicts
        if not products_in.empty:
            if "product_user_id" in pm.columns and "species_group_user_id" in products_in.columns:
                mapping = products_in[["product_user_id", "species_group_user_id"]].dropna().drop_duplicates("product_user_id")
                pm = pm.merge(mapping, on="product_user_id", how="left")
                pm["Species_Name"] = pm["species_group_user_id"].fillna("")
            elif "product_name" in pm.columns and "species_group_user_id" in products_in.columns:
                mapping = products_in[["product_name", "species_group_user_id"]].dropna().drop_duplicates("product_name")
                pm = pm.merge(mapping, on="product_name", how="left")
                pm["Species_Name"] = pm["species_group_user_id"].fillna("")
            else:
                pm["Species_Name"] = ""
        else:
            pm["Species_Name"] = ""

        pm["Assortment_Name"] = pm.get("product_name", "")
        pm["Allowed_Grades_Bitmask"] = 0
        pm["Diameter_Lower_mm"] = pd.to_numeric(pm.get("diameter_class_lower_limit", ""), errors="coerce").fillna(0).astype(int)
        d_lim = pd.to_numeric(pm.get("diameter_class_limit", ""), errors="coerce")
        pm["Diameter_Limit_mm"] = d_lim.fillna(pm["Diameter_Lower_mm"]).astype(int)
        pm["Length_Lower_cm"] = pd.to_numeric(pm.get("length_class_lower_limit", ""), errors="coerce").fillna(0).astype(int)
        l_lim = pd.to_numeric(pm.get("length_class_limit", ""), errors="coerce")
        pm["Length_Limit_cm"] = l_lim.fillna(pm["Length_Lower_cm"]).astype(int)
        pm["Relative_Value"] = pd.to_numeric(pm.get("price", ""), errors="coerce").fillna(0)

        out["pricing_matrix"] = _ensure_columns(pm, STANDARDIZED_PRICING_COLUMNS)

    return out


def merge_pin_into_standardized(
    standardized: Dict[str, Any], pin_data: Dict[str, pd.DataFrame],
) -> Dict[str, Any]:
    result = {k: v for k, v in standardized.items()}
    pin_std = transform_pin_to_standardized(pin_data)
    if not pin_std["pricing_matrix"].empty:
        result["pricing_matrix"] = pin_std["pricing_matrix"]
    if not pin_std["products"].empty:
        existing = result.get("products", pd.DataFrame())
        if existing.empty:
            result["products"] = pin_std["products"]
    return result


def merge_pri_into_standardized(
    standardized: Dict[str, Any], pri_data: Dict[str, pd.DataFrame]
) -> Dict[str, Any]:
    result = {k: v for k, v in standardized.items() if k in (META_SOURCE_TYPE, META_HAS_PRI)}
    result[META_HAS_PRI] = True

    for key in (
        "header", "machine", "objects", "species_groups", 
        "products", "statistics", "stems", "logs", "pricing_matrix"
    ):
        if key in standardized:
            result[key] = standardized[key].copy() if standardized[key] is not None else standardized[key]

    # Use the safe combine_first helper for replacing missing values
    result["header"] = _merge_first_row(result["header"], pri_data.get("header", pd.DataFrame()))
    result["machine"] = _merge_first_row(result["machine"], pri_data.get("machine", pd.DataFrame()))
    result["objects"] = _merge_first_row(result["objects"], pri_data.get("objects", pd.DataFrame()))

    # Add PRI specific keys
    for key in (
        "buyer_vendor", "calibration", "apt_history", "price_matrices",
        "operators", "production_statistics", "log_codes", "tree_codes", "additional_info"
    ):
        if key in pri_data:
            result[key] = pri_data[key]

    if not pri_data.get("logs", pd.DataFrame()).empty:
        pri_logs = pri_data["logs"].copy()
        if result["logs"].empty:
            result["logs"] = pri_logs
        else:
            result["logs_pri"] = pri_logs
    else:
        if "logs_pri" in result:
            del result["logs_pri"]

    return result


def merge_apt_into_standardized(
    standardized: Dict[str, Any],
    apt_parse_result: Union[Dict[str, Any], pd.DataFrame],
) -> Dict[str, Any]:
    result = {k: v for k, v in standardized.items()}
    result["pricing_matrix"] = _standardized_pricing_matrix(apt_parse_result)
    return result


def transform_apt_to_standardized(
    apt_parse_result: Union[Dict[str, Any], pd.DataFrame],
) -> Dict[str, Any]:
    out = empty_standardized_report("classic_apt", False)
    out["pricing_matrix"] = _standardized_pricing_matrix(apt_parse_result)
    return out