from __future__ import annotations

from typing import Optional

import altair as alt
import pandas as pd

from s4d_tools.aggregators.species_product import pivot_volume_to_percent_long


def assortment_breakdown_percent_chart(
    pivot: pd.DataFrame,
    *,
    title: str,
    x_title: str = "Share of volume (%)",
    y_title: str = "Species",
    color_title: str = "Product",
) -> alt.Chart:
    percent_long = pivot_volume_to_percent_long(pivot)
    if percent_long.empty:
        return alt.Chart(pd.DataFrame()).mark_point()

    volume_long = (
        pivot.reset_index()
        .melt(
            id_vars=[pivot.index.name or "species_name"],
            var_name="product_name",
            value_name="volume_m3",
        )
        .rename(columns={pivot.index.name or "species_name": "species_name"})
    )
    volume_long["volume_m3"] = pd.to_numeric(volume_long["volume_m3"], errors="coerce").fillna(0.0)
    long = percent_long.merge(
        volume_long,
        on=["species_name", "product_name"],
        how="left",
    )

    species_order: Optional[list] = pivot.index.tolist() if len(pivot.index) else None
    n = len(species_order) if species_order else 1
    row_px = 52
    height = max(280, row_px * n)

    base = (
        alt.Chart(long)
        .mark_bar()
        .encode(
            x=alt.X(
                "percent:Q",
                stack="zero",
                scale=alt.Scale(domain=[0, 100]),
                title=x_title,
            ),
            y=alt.Y(
                "species_name:N",
                sort=species_order,
                title=y_title,
                scale=alt.Scale(paddingInner=0.06, paddingOuter=0.06),
            ),
            color=alt.Color("product_name:N", title=color_title),
            tooltip=[
                alt.Tooltip("species_name:N", title=y_title),
                alt.Tooltip("product_name:N", title=color_title),
                alt.Tooltip("percent:Q", title="%", format=".1f"),
                alt.Tooltip("volume_m3:Q", title="Volume (m³)", format=".2f"),
            ],
        )
    )
    return (
        base.properties(title=title, height=height)
        .configure_axis(labelLimit=200)
        .configure_legend(orient="bottom", columns=4, labelLimit=260)
        .interactive()
    )
