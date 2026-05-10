import pandas as pd

from s4d_tools.aggregators import (
    aggregate_volume_by_species_and_product,
    pivot_volume_for_streamlit,
    pivot_volume_to_percent_long,
)


def test_aggregate_volume_by_species_and_product_sums_and_order():
    logs = pd.DataFrame(
        {
            "stem_key": ["s1", "s1", "s2"],
            "product_key": ["p1", "p1", "p1"],
            "volume_sob_m3": ["1.0", "0.5", "2.0"],
        }
    )
    stems = pd.DataFrame(
        {
            "stem_key": ["s1", "s2"],
            "species_group_key": ["spA", "spB"],
        }
    )
    species_groups = pd.DataFrame(
        {
            "species_group_key": ["spA", "spB"],
            "species_group_name": ["Pine", "Birch"],
        }
    )
    products = pd.DataFrame(
        {
            "product_key": ["p1"],
            "product_name": ["Sawlog"],
        }
    )
    out, order = aggregate_volume_by_species_and_product(
        logs, stems, species_groups, products
    )
    assert order == ["Pine", "Birch"]
    assert len(out) == 2
    pine = out[out["species_name"] == "Pine"].iloc[0]
    assert pine["product_name"] == "Sawlog"
    assert pine["volume"] == 1.5
    birch = out[out["species_name"] == "Birch"].iloc[0]
    assert birch["volume"] == 2.0


def test_empty_logs_returns_empty():
    out, order = aggregate_volume_by_species_and_product(
        pd.DataFrame(),
        pd.DataFrame({"stem_key": ["s1"], "species_group_key": ["a"]}),
        pd.DataFrame(),
        pd.DataFrame(),
    )
    assert out.empty
    assert order == []


def test_pivot_volume_for_streamlit_wide():
    long_df = pd.DataFrame(
        {
            "species_name": ["Pine", "Pine", "Birch"],
            "product_name": ["Sawlog", "Pulp", "Sawlog"],
            "volume": [1.0, 0.5, 2.0],
        }
    )
    wide = pivot_volume_for_streamlit(long_df, ["Pine", "Birch"])
    assert "Sawlog" in wide.columns
    assert wide.loc["Pine", "Sawlog"] == 1.0
    assert wide.loc["Pine", "Pulp"] == 0.5
    assert wide.loc["Birch", "Sawlog"] == 2.0


def test_pivot_volume_to_percent_long_rows_sum_to_100():
    pivot = pd.DataFrame(
        [[10.0, 30.0], [40.0, 0.0]],
        index=["A", "B"],
        columns=["P1", "P2"],
    )
    pivot.index.name = "species_name"
    long = pivot_volume_to_percent_long(pivot)
    sums = long.groupby("species_name")["percent"].sum()
    assert abs(sums["A"] - 100.0) < 1e-9
    assert abs(sums["B"] - 100.0) < 1e-9


def test_pivot_skips_when_duplicate_columns_like_bad_merge():
    bad = pd.DataFrame([[1, 2, 3]], columns=["species_name", "species_name", "volume"])
    assert pivot_volume_for_streamlit(bad, []).empty
