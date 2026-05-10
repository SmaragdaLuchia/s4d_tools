from __future__ import annotations

from typing import Iterable, List, Tuple

import pandas as pd


def aggregate_volume_by_species_and_product(
    logs: pd.DataFrame,
    stems: pd.DataFrame,
    species_groups: pd.DataFrame,
    products: pd.DataFrame,
) -> Tuple[pd.DataFrame, List[str]]:
    empty = pd.DataFrame(columns=["species_name", "product_name", "volume"])
    if logs is None or logs.empty or stems is None or stems.empty:
        return empty, []
    if "stem_key" not in logs.columns or "stem_key" not in stems.columns:
        return empty, []
    if "species_group_key" not in stems.columns:
        return empty, []

    stems_small = stems[["stem_key", "species_group_key"]].drop_duplicates(
        subset=["stem_key"], keep="first"
    )
    merged = logs.merge(stems_small, on="stem_key", how="inner")
    if merged.empty:
        return empty, []

    if "product_key" not in merged.columns:
        merged["product_key"] = ""

    merged = merged.loc[:, ~merged.columns.duplicated()].copy()
    if "volume_sob_m3" not in merged.columns:
        merged["volume"] = 0.0
    else:
        merged["volume_sob_m3"] = pd.to_numeric(
            merged["volume_sob_m3"].replace("", "0"), errors="coerce"
        ).fillna(0)
        merged["volume"] = merged["volume_sob_m3"]

    g = (
        merged.groupby(["species_group_key", "product_key"], sort=False)["volume"]
        .sum()
        .reset_index()
    )

    if not species_groups.empty and "species_group_key" in species_groups.columns:
        sg = species_groups[["species_group_key", "species_group_name"]].drop_duplicates(
            subset=["species_group_key"], keep="first"
        )
        g = g.merge(sg, on="species_group_key", how="left")
        g["species_name"] = g["species_group_name"].replace("", pd.NA).fillna(
            g["species_group_key"]
        )
    else:
        g["species_name"] = g["species_group_key"]

    if not products.empty and "product_key" in products.columns:
        pn = "product_name" if "product_name" in products.columns else None
        if pn:
            pr = products[["product_key", pn]].drop_duplicates(
                subset=["product_key"], keep="first"
            )
            g = g.merge(pr, on="product_key", how="left")
            g["product_name"] = g[pn].replace("", pd.NA)
        else:
            g["product_name"] = pd.NA
    else:
        g["product_name"] = pd.NA

    pk = g["product_key"].fillna("").astype(str)
    g["product_name"] = g["product_name"].fillna(pk)
    g.loc[pk.str.len() == 0, "product_name"] = "Unknown"
    g["product_name"] = g["product_name"].fillna("Unknown")

    out = (
        g.groupby(["species_name", "product_name"], sort=False)["volume"]
        .sum()
        .reset_index()
    )

    species_order = _species_name_order(species_groups, out["species_name"].unique())
    out = out.loc[:, ~out.columns.duplicated()].copy()
    return out, species_order


def pivot_volume_for_streamlit(
    sp_long: pd.DataFrame, species_order: List[str]
) -> pd.DataFrame:
    if sp_long is None or sp_long.empty:
        return pd.DataFrame()
    df = sp_long.loc[:, ~sp_long.columns.duplicated()].copy()
    required = ("species_name", "product_name", "volume")
    if any(c not in df.columns for c in required):
        return pd.DataFrame()
    df["species_name"] = df["species_name"].astype(str)
    df["product_name"] = df["product_name"].astype(str)
    df["volume"] = pd.to_numeric(df["volume"], errors="coerce").fillna(0)
    pivot = df.pivot_table(
        index="species_name",
        columns="product_name",
        values="volume",
        aggfunc="sum",
        fill_value=0.0,
    )
    if species_order:
        ordered = [s for s in species_order if s in pivot.index]
        rest = [s for s in pivot.index.tolist() if s not in ordered]
        pivot = pivot.reindex(ordered + rest)
    return pivot


def pivot_volume_to_percent_long(pivot: pd.DataFrame) -> pd.DataFrame:
    if pivot is None or pivot.empty:
        return pd.DataFrame(columns=["species_name", "product_name", "percent"])
    p = pivot.apply(pd.to_numeric, errors="coerce").fillna(0.0)
    idx_name = p.index.name or "species_name"
    p.index.name = idx_name
    row_sums = p.sum(axis=1)
    pct = p.div(row_sums.replace(0, float("nan")), axis=0).fillna(0.0) * 100.0
    long = pct.reset_index().melt(
        id_vars=[idx_name],
        var_name="product_name",
        value_name="percent",
    )
    return long.rename(columns={idx_name: "species_name"})


def _species_name_order(
    species_groups: pd.DataFrame, present_species_names: Iterable[str]
) -> List[str]:
    present = list(present_species_names)
    if not present:
        return []
    seen: set[str] = set()
    ordered: List[str] = []

    if (
        species_groups is not None
        and not species_groups.empty
        and "species_group_key" in species_groups.columns
    ):
        name_col = (
            "species_group_name"
            if "species_group_name" in species_groups.columns
            else "species_group_key"
        )
        for _, row in species_groups.iterrows():
            raw = row.get(name_col, row.get("species_group_key", ""))
            name = (
                str(raw).strip()
                if pd.notna(raw) and str(raw).strip() != ""
                else str(row.get("species_group_key", ""))
            )
            if name in present and name not in seen:
                seen.add(name)
                ordered.append(name)

    for n in sorted(set(present) - seen):
        ordered.append(n)
    return ordered


__all__ = [
    "aggregate_volume_by_species_and_product",
    "pivot_volume_for_streamlit",
    "pivot_volume_to_percent_long",
]
