from __future__ import annotations

import pandas as pd


def aggregate_stems_by_species(
    stems: pd.DataFrame,
    species_groups: pd.DataFrame,
) -> pd.DataFrame:
    """Count harvested trees (stems) per species.

    Returns a DataFrame with columns ``species_name`` and ``tree_count``.
    """
    empty: pd.DataFrame = pd.DataFrame(columns=["species_name", "tree_count"])
    if stems is None or stems.empty:
        return empty
    if "species_group_key" not in stems.columns:
        return empty

    g = (
        stems.groupby("species_group_key", sort=False)
        .size()
        .reset_index(name="tree_count")
    )

    if (
        species_groups is not None
        and not species_groups.empty
        and "species_group_key" in species_groups.columns
    ):
        sg = species_groups[["species_group_key", "species_group_name"]].drop_duplicates(
            subset=["species_group_key"], keep="first"
        )
        g = g.merge(sg, on="species_group_key", how="left")
        g["species_name"] = g["species_group_name"].replace("", pd.NA).fillna(
            g["species_group_key"]
        )
    else:
        g["species_name"] = g["species_group_key"]

    return g[["species_name", "tree_count"]].copy()


__all__ = ["aggregate_stems_by_species"]
