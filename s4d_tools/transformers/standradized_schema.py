"""
Standardized schema for StanForD report data.

The transformation layer converts parser output (classic PRD/PRI or Stanford 2010 HPR)
into this single shape so that visualization and downstream code do not depend on
the source format.
"""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

STANDARDIZED_HEADER_COLUMNS = [
    "creation_date",
    "modification_date",
    "application_version_created",
    "application_version_modified",
    "country_code",
]

STANDARDIZED_MACHINE_COLUMNS = [
    "machine_base_manufacturer",
    "machine_base_model",
]

STANDARDIZED_OBJECTS_COLUMNS = [
    "object_name",
    "contract_number",
]

STANDARDIZED_SPECIES_GROUPS_COLUMNS = [
    "species_group_key",
    "species_group_name",
]

STANDARDIZED_PRODUCTS_COLUMNS = [
    "product_key",
    "product_name",
]

STANDARDIZED_STATISTICS_COLUMNS = [
    "total_stems",
    "species_names",
    "stems_per_species",
    "volume_per_species",
]

STANDARDIZED_STEMS_COLUMNS = [
    "stem_key",
    "object_key",
    "sub_object_key",
    "species_group_key",
    "harvest_date",
    "stem_number",
]

STANDARDIZED_LOGS_COLUMNS = [
    "stem_key",
    "log_key",
    "product_key",
    "volume_sob_m3",
    "volume_sub_m3",
    "length_cm",
    "diameter_top_ob",
    "diameter_mid_ob",
    "diameter_root_ob",
]

StandardizedReport = Dict[str, pd.DataFrame]

META_SOURCE_TYPE = "source_type" #"classic_prd" | "stanford_2010_hpr"
META_HAS_PRI = "has_pri"  # bool

SOURCE_TYPES = ("classic_prd", "stanford_2010_hpr")


def empty_standardized_table(columns: List[str]) -> pd.DataFrame:
    return pd.DataFrame(columns=columns)


def empty_standardized_report(source_type: str, has_pri: bool = False) -> Dict[str, Any]:
   return {
        "header": empty_standardized_table(STANDARDIZED_HEADER_COLUMNS),
        "machine": empty_standardized_table(STANDARDIZED_MACHINE_COLUMNS),
        "objects": empty_standardized_table(STANDARDIZED_OBJECTS_COLUMNS),
        "species_groups": empty_standardized_table(STANDARDIZED_SPECIES_GROUPS_COLUMNS),
        "products": empty_standardized_table(STANDARDIZED_PRODUCTS_COLUMNS),
        "statistics": empty_standardized_table(STANDARDIZED_STATISTICS_COLUMNS),
        "stems": empty_standardized_table(STANDARDIZED_STEMS_COLUMNS),
        "logs": empty_standardized_table(STANDARDIZED_LOGS_COLUMNS),
        META_SOURCE_TYPE: source_type,
        META_HAS_PRI: has_pri,
    }
