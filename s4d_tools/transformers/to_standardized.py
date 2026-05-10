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
    STANDARDIZED_SPECIES_TABLE_COLUMNS,
    STANDARDIZED_SPECIES_PRODUCT_VOLUME_COLUMNS,
    STANDARDIZED_STEMS_COLUMNS,
    META_HAS_PRI,
    META_SOURCE_TYPE,
    empty_standardized_report,
    empty_standardized_table,
)


def _ensure_columns(df: pd.DataFrame, columns: list, fill_value: Any = "") -> pd.DataFrame:
    return df.reindex(columns=columns, fill_value=fill_value)


def _format_table(df_dict: Dict[str, pd.DataFrame], key: str, columns: list) -> pd.DataFrame:
    df = df_dict.get(key)
    if df is None or df.empty:
        return empty_standardized_table(columns)
    return _ensure_columns(df.copy(), columns)


def _merge_first_row(primary_df: pd.DataFrame, secondary_df: pd.DataFrame) -> pd.DataFrame:
    if primary_df.empty or secondary_df.empty:
        return primary_df

    primary_nan = primary_df.replace("", pd.NA)
    secondary_nan = secondary_df.replace("", pd.NA)
    
    merged = primary_nan.combine_first(secondary_nan)
    return merged.fillna("")


def _compute_hpr_statistics(hpr_data: Dict[str, pd.DataFrame]) -> pd.DataFrame:
    stems_df = hpr_data.get("stems", pd.DataFrame())
    logs_df = hpr_data.get("logs", pd.DataFrame())
    species_df = hpr_data.get("species_groups", pd.DataFrame())

    if stems_df.empty:
        return pd.DataFrame([{
            "total_stems": 0, "species_names": [], 
            "stems_per_species": [], "volume_per_species": []
        }])

    stems_counts = stems_df.groupby("species_group_key").size().reset_index(name="stems_count")

    if not logs_df.empty and "stem_key" in logs_df.columns:
        logs_merged = logs_df.merge(stems_df[["stem_key", "species_group_key"]], on="stem_key", how="left")
        logs_merged["volume_sob_m3"] = pd.to_numeric(logs_merged["volume_sob_m3"].replace("", "0"), errors="coerce").fillna(0)
        logs_merged["volume"] = logs_merged["volume_sob_m3"]
        vol_counts = logs_merged.groupby("species_group_key")["volume"].sum().reset_index()
    else:
        vol_counts = pd.DataFrame(columns=["species_group_key", "volume"])

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
        "volume_per_species": stats_df["volume"].astype(float).tolist(),
    }])


def _build_species_table(
    species_groups_df: pd.DataFrame, statistics_df: pd.DataFrame
) -> pd.DataFrame:
    if statistics_df is not None and not statistics_df.empty:
        stats = statistics_df.iloc[0]
        species_names = (
            stats.get("species_names", [])
            if isinstance(stats.get("species_names", []), list)
            else []
        )
        stems_per_species = (
            stats.get("stems_per_species", [])
            if isinstance(stats.get("stems_per_species", []), list)
            else []
        )
        volume_per_species = (
            stats.get("volume_per_species", [])
            if isinstance(stats.get("volume_per_species", []), list)
            else []
        )

        if species_names:
            row_count = len(species_names)
            stems_values = list(stems_per_species[:row_count]) + [0] * max(0, row_count - len(stems_per_species))
            volume_values = list(volume_per_species[:row_count]) + [0.0] * max(0, row_count - len(volume_per_species))
            return pd.DataFrame(
                {
                    "species_name": species_names,
                    "trees": pd.Series(stems_values).fillna(0).astype(int),
                    "volume_m3": pd.to_numeric(pd.Series(volume_values), errors="coerce").fillna(0.0),
                }
            )

    if species_groups_df is not None and not species_groups_df.empty:
        names = species_groups_df.get("species_group_name", pd.Series(dtype=str)).replace("", pd.NA)
        fallback = species_groups_df.get("species_group_key", pd.Series(dtype=str))
        return pd.DataFrame(
            {
                "species_name": names.fillna(fallback).fillna(""),
                "trees": 0,
                "volume_m3": 0.0,
            }
        )

    return empty_standardized_table(STANDARDIZED_SPECIES_TABLE_COLUMNS)


def _build_species_product_volume_from_pri_logs(
    pri_logs: pd.DataFrame, species_groups: pd.DataFrame, products: pd.DataFrame
) -> pd.DataFrame:
    empty = empty_standardized_table(STANDARDIZED_SPECIES_PRODUCT_VOLUME_COLUMNS)
    if pri_logs is None or pri_logs.empty:
        return empty
    if "species_index" not in pri_logs.columns or "assortment_index" not in pri_logs.columns:
        return empty

    logs = pri_logs.copy()
    logs["species_group_key"] = pd.to_numeric(logs["species_index"], errors="coerce").fillna(0).astype(int).astype(str)
    logs["product_key"] = pd.to_numeric(logs["assortment_index"], errors="coerce").fillna(0).astype(int).astype(str)

    if "volume_m3_sob" in logs.columns:
        logs["volume"] = pd.to_numeric(logs["volume_m3_sob"], errors="coerce").fillna(0.0)
    elif "volume_dl_sob" in logs.columns:
        logs["volume"] = pd.to_numeric(logs["volume_dl_sob"], errors="coerce").fillna(0.0) / 10000.0
    elif "volume_m3_custom" in logs.columns:
        logs["volume"] = pd.to_numeric(logs["volume_m3_custom"], errors="coerce").fillna(0.0)
    else:
        logs["volume"] = 0.0

    out = logs[["species_group_key", "product_key", "volume"]].copy()

    if not species_groups.empty and "species_group_key" in species_groups.columns:
        sg = species_groups[["species_group_key", "species_group_name"]].drop_duplicates(
            subset=["species_group_key"], keep="first"
        )
        out = out.merge(sg, on="species_group_key", how="left")
        out["species_name"] = out["species_group_name"].replace("", pd.NA).fillna(out["species_group_key"])
    else:
        out["species_name"] = out["species_group_key"]

    if not products.empty and "product_key" in products.columns:
        pr = products[["product_key", "product_name"]].drop_duplicates(
            subset=["product_key"], keep="first"
        )
        out = out.merge(pr, on="product_key", how="left")
    else:
        out["product_name"] = ""

    out["product_name"] = out["product_name"].replace("", pd.NA).fillna(out["product_key"])
    out.loc[out["product_key"].fillna("").astype(str).str.len() == 0, "product_name"] = "Unknown"

    out = (
        out.groupby(["species_name", "product_name"], sort=False)["volume"]
        .sum()
        .reset_index()
    )
    return _ensure_columns(out, STANDARDIZED_SPECIES_PRODUCT_VOLUME_COLUMNS)


def _standardized_pricing_matrix(
    apt_parse_result: Optional[Union[Dict[str, Any], pd.DataFrame]],
) -> pd.DataFrame:
    if apt_parse_result is None:
        return empty_standardized_table(STANDARDIZED_PRICING_COLUMNS)
    return _ensure_columns(
        price_matrix_from_any_apt_shape(apt_parse_result).copy(),
        STANDARDIZED_PRICING_COLUMNS,
    )


def transform_prd_to_standardized(
    prd_data: Dict[str, pd.DataFrame],
    apt_parse_result: Optional[Union[Dict[str, Any], pd.DataFrame]] = None,
) -> Dict[str, Any]:
    apt_df = _standardized_pricing_matrix(apt_parse_result)
    species_groups = _format_table(prd_data, "species_groups", STANDARDIZED_SPECIES_GROUPS_COLUMNS)
    statistics = _format_table(prd_data, "statistics", STANDARDIZED_STATISTICS_COLUMNS)
    return {
        "header": _format_table(prd_data, "header", STANDARDIZED_HEADER_COLUMNS),
        "machine": _format_table(prd_data, "machine", STANDARDIZED_MACHINE_COLUMNS),
        "objects": _format_table(prd_data, "objects", STANDARDIZED_OBJECTS_COLUMNS),
        "species_groups": species_groups,
        "products": _format_table(prd_data, "products", STANDARDIZED_PRODUCTS_COLUMNS),
        "statistics": statistics,
        "species_table": _ensure_columns(
            _build_species_table(species_groups, statistics),
            STANDARDIZED_SPECIES_TABLE_COLUMNS,
        ),
        "species_product_volume": empty_standardized_table(
            STANDARDIZED_SPECIES_PRODUCT_VOLUME_COLUMNS
        ),
        "stems": empty_standardized_table(STANDARDIZED_STEMS_COLUMNS),
        "logs": pd.DataFrame(),
        "pricing_matrix": apt_df,
        META_SOURCE_TYPE: "classic_prd",
        META_HAS_PRI: False,
    }


def transform_hpr_to_standardized(
    hpr_data: Dict[str, pd.DataFrame],
    apt_parse_result: Optional[Union[Dict[str, Any], pd.DataFrame]] = None,
) -> Dict[str, Any]:
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

    stems = hpr_data.get("stems", pd.DataFrame())
    if not stems.empty:
        stems_out = _ensure_columns(stems.copy(), STANDARDIZED_STEMS_COLUMNS)
        extra = [c for c in stems.columns if c not in STANDARDIZED_STEMS_COLUMNS]
        if extra:
            stems_out = pd.concat([stems_out, stems[extra]], axis=1)
    else:
        stems_out = empty_standardized_table(STANDARDIZED_STEMS_COLUMNS)

    statistics = _compute_hpr_statistics(hpr_data)
    statistics = _ensure_columns(statistics, STANDARDIZED_STATISTICS_COLUMNS)

    apt_df = _standardized_pricing_matrix(apt_parse_result)

    species_groups = _format_table(hpr_data, "species_groups", STANDARDIZED_SPECIES_GROUPS_COLUMNS)
    return {
        "header": _format_table(hpr_data, "header", STANDARDIZED_HEADER_COLUMNS),
        "machine": _format_table(hpr_data, "machine", STANDARDIZED_MACHINE_COLUMNS),
        "objects": objects_out,
        "species_groups": species_groups,
        "products": _format_table(hpr_data, "products", STANDARDIZED_PRODUCTS_COLUMNS),
        "statistics": statistics,
        "species_table": _ensure_columns(
            _build_species_table(species_groups, statistics),
            STANDARDIZED_SPECIES_TABLE_COLUMNS,
        ),
        "species_product_volume": empty_standardized_table(
            STANDARDIZED_SPECIES_PRODUCT_VOLUME_COLUMNS
        ),
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
        "products", "statistics", "species_table", "species_product_volume",
        "stems", "logs", "pricing_matrix"
    ):
        if key in standardized:
            result[key] = standardized[key].copy() if standardized[key] is not None else standardized[key]

    result["header"] = _merge_first_row(result["header"], pri_data.get("header", pd.DataFrame()))
    result["machine"] = _merge_first_row(result["machine"], pri_data.get("machine", pd.DataFrame()))
    result["objects"] = _merge_first_row(result["objects"], pri_data.get("objects", pd.DataFrame()))

    for key in (
        "buyer_vendor", "calibration", "apt_history", "price_matrices",
        "operators", "production_statistics", "log_codes", "tree_codes", "additional_info"
    ):
        if key in pri_data:
            result[key] = pri_data[key]

    if not pri_data.get("logs", pd.DataFrame()).empty:
        pri_logs = pri_data["logs"].copy()
        result["species_product_volume"] = _build_species_product_volume_from_pri_logs(
            pri_logs,
            result.get("species_groups", pd.DataFrame()),
            result.get("products", pd.DataFrame()),
        )
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