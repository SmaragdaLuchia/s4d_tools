import streamlit as st
import pandas as pd
import sys
import os
from typing import Any, List, Optional, Tuple

# Ensure project root is on path when running from streamlit/
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)

from s4d_tools import APTParser, PRDParser, PRIParser, HPRParser, PINParser
from s4d_tools.aggregators.price_matrix import price_matrix_heatmaps_by_assortment
from s4d_tools.transformers import (
    merge_pin_into_standardized,
    merge_pri_into_standardized,
    transform_hpr_to_standardized,
    transform_prd_to_standardized,
)
from s4d_tools.transformers.standradized_schema import META_HAS_PRI, META_SOURCE_TYPE
from s4d_tools.utils.sanitize_s4d2010 import sanitize_s4d2010_xml


def _split_apt_pin_uploads(
    files: Any,
) -> Tuple[Optional[Any], Optional[Any], List[str]]:
    """
    From a single multi-file uploader (``.apt`` / ``.pin``), pick one APT and one PIN if present.
    Returns (apt_file, pin_file, warning_messages).
    """
    if files is None:
        return None, None, []
    fl = files if isinstance(files, list) else [files]
    apt_list = [f for f in fl if f.name.lower().endswith(".apt")]
    pin_list = [f for f in fl if f.name.lower().endswith(".pin")]
    warns: List[str] = []
    if len(apt_list) > 1:
        warns.append(
            f"Multiple APT files uploaded — using **{apt_list[0].name}**; ignoring {len(apt_list) - 1} other(s)."
        )
    if len(pin_list) > 1:
        warns.append(
            f"Multiple PIN files uploaded — using **{pin_list[0].name}**; ignoring {len(pin_list) - 1} other(s)."
        )
    return (
        apt_list[0] if apt_list else None,
        pin_list[0] if pin_list else None,
        warns,
    )


# Page configuration
st.set_page_config(
    page_title="Harvester File Analysis",
    page_icon="🌲",
    layout="wide"
)

# Title and top-level mode (visualize vs redact)
st.title("🌲 Harvester File Analysis")
tab_visualize, tab_redact = st.tabs(["📊 Data visualization", "🔒 Data redaction (GDPR)"])

def _standardized_source_label(source_type: str) -> str:
    """Human-readable label for META_SOURCE_TYPE."""
    if source_type == "stanford_2010_hpr":
        return "Stanford 2010 (HPR)"
    if source_type == "classic_prd":
        return "Classic PRD"
    return source_type or "Unknown"


def _render_pri_style_logs_table(logs_df: pd.DataFrame) -> None:
    """Rich log table view for PRI-shaped production-individual logs."""
    st.write(f"**Total Logs:** {len(logs_df):,}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(
            "Unique Stems",
            logs_df["stem_number"].nunique() if "stem_number" in logs_df.columns else 0,
        )
    with col2:
        st.metric(
            "Unique Species",
            logs_df["species_index"].nunique() if "species_index" in logs_df.columns else 0,
        )
    with col3:
        st.metric(
            "Unique Assortments",
            logs_df["assortment_index"].nunique() if "assortment_index" in logs_df.columns else 0,
        )

    st.subheader("Logs DataFrame")

    if len(logs_df) > 1000:
        st.info(f"Showing first 1,000 of {len(logs_df):,} logs.")
        display_df = logs_df.head(1000)
    else:
        display_df = logs_df

    st.dataframe(display_df, use_container_width=True, height=400)

    if "volume_dl_sob" in logs_df.columns:
        st.subheader("Volume Statistics")
        col1, col2 = st.columns(2)
        with col1:
            total_volume = logs_df["volume_dl_sob"].sum() / 10000
            st.metric("Total Volume (m³ s.o.b.)", f"{total_volume:,.2f}")
        with col2:
            avg_volume = logs_df["volume_dl_sob"].mean() / 10000
            st.metric("Average Log Volume (m³ s.o.b.)", f"{avg_volume:.4f}")

    if "length_actual_cm" in logs_df.columns:
        st.subheader("Length Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Min Length (cm)", f"{logs_df['length_actual_cm'].min():.0f}")
        with col2:
            st.metric("Max Length (cm)", f"{logs_df['length_actual_cm'].max():.0f}")
        with col3:
            st.metric("Avg Length (cm)", f"{logs_df['length_actual_cm'].mean():.1f}")

    if "diameter_top_ob" in logs_df.columns and "diameter_root_ob" in logs_df.columns:
        st.subheader("Diameter Statistics")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Avg Top Diameter (mm)", f"{logs_df['diameter_top_ob'].mean():.0f}")
        with col2:
            st.metric("Avg Root Diameter (mm)", f"{logs_df['diameter_root_ob'].mean():.0f}")
        with col3:
            if "diameter_mid_ob" in logs_df.columns:
                st.metric("Avg Mid Diameter (mm)", f"{logs_df['diameter_mid_ob'].mean():.0f}")


def _render_generic_logs_table(logs_df: pd.DataFrame, max_rows: int = 5000) -> None:
    """Simple log table (e.g. HPR machine logs)."""
    st.write(f"**Rows:** {len(logs_df):,}")
    if len(logs_df) > max_rows:
        st.info(f"Showing first {max_rows:,} rows.")
        st.dataframe(logs_df.head(max_rows), use_container_width=True, height=400)
    else:
        st.dataframe(logs_df, use_container_width=True, height=400)


def _looks_like_pri_production_logs(df: pd.DataFrame) -> bool:
    return "stem_number" in df.columns


def _render_price_matrix_tab(data: dict) -> None:
    st.header("Price matrix")
    st.caption(
        "Long-form **diameter × length** cells per species and assortment. "
        "Classic **APT** sources use relative values; Stanford **2010 PIN** (with HPR) maps product matrix prices into the same table."
    )
    pm = data.get("pricing_matrix")
    if pm is None or pm.empty:
        st.info(
            "No price matrix rows in this report. "
            "For **Classic StanForD**, upload a tilde-separated `.apt` that contains group **162/2** "
            "(relative price matrix). If you did upload an APT, try saving it as ISO-8859 / Windows "
            "ANSI from your harvester software, or UTF-8 — the parser tries several encodings."
        )
        return

    st.metric("Matrix rows (cells)", f"{len(pm):,}")
    st.subheader("Long-form table")
    st.dataframe(pm, use_container_width=True, height=360)

    try:
        heatmaps = price_matrix_heatmaps_by_assortment(pm)
    except Exception as e:
        st.warning(f"Could not build per-assortment matrices: {e}")
        return

    if not heatmaps:
        return

    st.subheader("Per-assortment matrix (heatmap table)")
    labels = [
        f"{h['species_name']} — {h['assortment_name']}" for h in heatmaps
    ]
    choice = st.selectbox("Assortment", labels, index=0)
    idx = labels.index(choice)
    h = heatmaps[idx]
    st.dataframe(
        h["relative_value_matrix"],
        use_container_width=True,
        height=min(520, 35 + 35 * len(h["relative_value_matrix"].index)),
    )


def visualize_data(
    data: dict,
    has_pri: Optional[bool] = None,
) -> None:
    """
    Visualize the standardized report shape. Tab layout is identical for
    Classic PRD and Stanford 2010 HPR; optional PRI sections use the same tabs when present.
    """
    if has_pri is None:
        has_pri = bool(data.get(META_HAS_PRI, False))
    else:
        has_pri = bool(has_pri)

    source_type = data.get(META_SOURCE_TYPE, "")
    pm = data.get("pricing_matrix")
    has_price_matrix = pm is not None and not getattr(pm, "empty", True)

    tab_names = [
        "📊 Overview",
        "📋 Basic Info",
        "🌳 Species",
        "📦 Products",
        "📈 Statistics",
    ]
    if has_price_matrix:
        tab_names.append("💰 Price matrix")
    tab_names.extend(
        [
            "🔧 Machine",
            "🌲 Stems",
            "📏 Logs",
        ]
    )
    if has_pri:
        tab_names.append("📋 Additional Info")

    tabs = st.tabs(tab_names)
    it = iter(tabs)
    tab1 = next(it)
    tab2 = next(it)
    tab3 = next(it)
    tab4 = next(it)
    tab5 = next(it)
    tab_price = next(it) if has_price_matrix else None
    tab6 = next(it)
    tab_stems = next(it)
    tab_logs = next(it)
    tab_additional = next(it) if has_pri else None
    
    # TAB 1: Overview
    with tab1:
        st.header("Overview")
        pri_note = " · PRI merged" if has_pri else ""
        price_note = " · Price matrix" if has_price_matrix else ""
        st.caption(
            f"Standardized report · {_standardized_source_label(source_type)}{pri_note}{price_note}"
        )

        col1, col2, col3, col4 = st.columns(4)
        
        # Total stems
        if 'statistics' in data and not data['statistics'].empty:
            total_stems = data['statistics'].iloc[0].get('total_stems', 0)
            col1.metric("Total Trees", f"{total_stems:,}")
        
        # Number of species
        num_species = len(data['species_groups']) if 'species_groups' in data else 0
        col2.metric("Number of Species", num_species)
        
        # Number of products
        num_products = len(data['products']) if 'products' in data else 0
        col3.metric("Number of Products", num_products)
        
        # Site name
        if 'objects' in data and not data['objects'].empty:
            site_name = data['objects'].iloc[0].get('object_name', 'N/A')
            col4.metric("Object Name", site_name)
        
        # Statistics summary
        if 'statistics' in data and not data['statistics'].empty:
            stats = data['statistics'].iloc[0]
            if 'species_names' in stats and 'stems_per_species' in stats:
                species_names = stats['species_names'] if isinstance(stats['species_names'], list) else []
                stems_per_species = stats['stems_per_species'] if isinstance(stats['stems_per_species'], list) else []
                
                # Ensure arrays have the same length
                min_length = min(len(species_names), len(stems_per_species))
                if min_length > 0:
                    st.subheader("Trees by Species")
                    species_df = pd.DataFrame({
                        'Species': species_names[:min_length],
                        'Trees': stems_per_species[:min_length]
                    })
                    st.bar_chart(species_df.set_index('Species'))
    
    # TAB 2: Basic Info (Header, Objects)
    with tab2:
        st.header("Basic Info")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("File Info")
            if 'header' in data and not data['header'].empty:
                header = data['header'].iloc[0]
                st.write(f"**Creation Date:** {header.get('creation_date', 'N/A')}")
                st.write(f"**Modification Date:** {header.get('modification_date', 'N/A')}")
                st.write(f"**Application Version:** {header.get('application_version_created', 'N/A')}")
        
        with col2:
            st.subheader("Object Info")
            if 'objects' in data and not data['objects'].empty:
                obj = data['objects'].iloc[0]
                st.write(f"**Object Name:** {obj.get('object_name', 'N/A')}")
                st.write(f"**Contract Number:** {obj.get('contract_number', 'N/A')}")
        
        # Display DataFrames
        if 'header' in data:
            st.subheader("Header DataFrame")
            st.dataframe(data['header'], use_container_width=True)
        
        if 'objects' in data:
            st.subheader("Objects DataFrame")
            st.dataframe(data['objects'], use_container_width=True)
    
    # TAB 3: Species
    with tab3:
        st.header("Species")
        
        if 'species_groups' in data and not data['species_groups'].empty:
            st.dataframe(data['species_groups'], use_container_width=True)
            
            # Species statistics
            if 'statistics' in data and not data['statistics'].empty:
                stats = data['statistics'].iloc[0]
                if 'species_names' in stats and 'stems_per_species' in stats and 'volume_per_species' in stats:
                    species_names = stats['species_names'] if isinstance(stats['species_names'], list) else []
                    stems_per_species = stats['stems_per_species'] if isinstance(stats['stems_per_species'], list) else []
                    volume_per_species = stats['volume_per_species'] if isinstance(stats['volume_per_species'], list) else []
                    
                    # Ensure all arrays have the same length
                    min_length = min(len(species_names), len(stems_per_species), len(volume_per_species))
                    if min_length > 0:
                        st.subheader("Species Statistics")
                        species_stats_df = pd.DataFrame({
                            'Species': species_names[:min_length],
                            'Trees': stems_per_species[:min_length],
                            'Volume (raw units)': volume_per_species[:min_length]
                        })
                        st.dataframe(species_stats_df, use_container_width=True)
        else:
            st.info("Species data is missing.")
    
    # TAB 4: Products
    with tab4:
        st.header("Products")
        
        if 'products' in data and not data['products'].empty:
            st.dataframe(data['products'], use_container_width=True)
        else:
            st.info("Product data is missing.")
    
    # TAB 5: Statistics
    with tab5:
        st.header("Statistics")
        
        if 'statistics' in data and not data['statistics'].empty:
            stats = data['statistics'].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Total Trees", stats.get('total_stems', 0))
            
            # Stems per species chart
            if 'species_names' in stats and 'stems_per_species' in stats:
                species_names = stats['species_names'] if isinstance(stats['species_names'], list) else []
                stems_per_species = stats['stems_per_species'] if isinstance(stats['stems_per_species'], list) else []
                
                min_length = min(len(species_names), len(stems_per_species))
                if min_length > 0:
                    st.subheader("Trees by Species")
                    species_chart_df = pd.DataFrame({
                        'Species': species_names[:min_length],
                        'Trees': stems_per_species[:min_length]
                    })
                    st.bar_chart(species_chart_df.set_index('Species'))
            
            # Volume per species chart
            if 'species_names' in stats and 'volume_per_species' in stats:
                species_names = stats['species_names'] if isinstance(stats['species_names'], list) else []
                volume_per_species = stats['volume_per_species'] if isinstance(stats['volume_per_species'], list) else []
                
                min_length = min(len(species_names), len(volume_per_species))
                if min_length > 0:
                    st.subheader("Volume by Species (raw units)")
                    volume_chart_df = pd.DataFrame({
                        'Species': species_names[:min_length],
                        'Volume': volume_per_species[:min_length]
                    })
                    st.bar_chart(volume_chart_df.set_index('Species'))
            
            # Statistics DataFrame
            st.subheader("Statistics DataFrame")
            st.dataframe(data['statistics'], use_container_width=True)
        else:
            st.info("Statistics data is missing.")

    if has_price_matrix and tab_price is not None:
        with tab_price:
            _render_price_matrix_tab(data)

    # TAB Machine
    with tab6:
        st.header("Machine Info")
        
        if 'machine' in data and not data['machine'].empty:
            machine = data['machine'].iloc[0]
            st.write(f"**Manufacturer:** {machine.get('machine_base_manufacturer', 'N/A')}")
            st.write(f"**Model:** {machine.get('machine_base_model', 'N/A')}")
            
            st.subheader("Machine DataFrame")
            st.dataframe(data['machine'], use_container_width=True)
        else:
            st.info("Machine data is missing.")

    # TAB 7: Stems (same position for classic and 2010; may be empty for PRD)
    with tab_stems:
        st.header("Stems")
        st.caption(
            "Stem-level rows appear for Stanford 2010 (HPR). "
            "Classic PRD standardized output has no stem table."
        )
        if "stems" in data and not data["stems"].empty:
            st.dataframe(data["stems"], use_container_width=True)
        else:
            st.info("No stem-level rows in this report.")

    # TAB 8: Logs (HPR logs, PRI logs, or both via logs / logs_pri)
    with tab_logs:
        st.header("Logs")
        logs_main = data.get("logs")
        logs_pri_only = data.get("logs_pri")
        if logs_main is None or (hasattr(logs_main, "empty") and logs_main.empty):
            logs_main = pd.DataFrame()
        if logs_pri_only is None or (
            hasattr(logs_pri_only, "empty") and logs_pri_only.empty
        ):
            logs_pri_only = pd.DataFrame()

        if logs_main.empty and logs_pri_only.empty:
            st.info(
                "No log-level rows in this standardized report. "
                "Classic PRD has summary statistics only; use HPR or add PRI for log-level data."
            )
        else:
            if not logs_main.empty:
                st.subheader("Primary log table")
                st.caption(
                    "Report or machine logs (e.g. HPR), or PRI logs when this is the only log source."
                )
                if _looks_like_pri_production_logs(logs_main):
                    _render_pri_style_logs_table(logs_main)
                else:
                    _render_generic_logs_table(logs_main)

            if not logs_pri_only.empty:
                st.subheader("PRI production-individual logs")
                st.caption(
                    "Present when PRI log rows are merged alongside another log table (e.g. HPR + PRI)."
                )
                if _looks_like_pri_production_logs(logs_pri_only):
                    _render_pri_style_logs_table(logs_pri_only)
                else:
                    _render_generic_logs_table(logs_pri_only)

    # PRI: Additional Info only (buyers/vendors, calibration, production stats, operators removed)
    if has_pri:
        if tab_additional is not None and 'additional_info' in data:
            with tab_additional:
                st.header("Additional Info")
                if not data['additional_info'].empty:
                    add_info = data['additional_info'].iloc[0]
                    
                    st.subheader("Coordinates")
                    coord_system_map = {'1': 'WGS84', '': 'N/A'}
                    coord_type_map = {'1': 'Relative coordinates', '2': 'Absolute coordinates', '': 'N/A'}
                    coord_ref_map = {'1': 'Base machine position', '2': 'Crane tip when felling', '3': 'Crane tip when processing', '': 'N/A'}
                    lat_dir_map = {'1': 'North', '2': 'South', '': 'N/A'}
                    lon_dir_map = {'1': 'East', '2': 'West', '': 'N/A'}
                    
                    st.write(f"**Registration Position:** {coord_ref_map.get(str(add_info.get('coord_ref_position', '')), 'N/A')}")
                    st.write(f"**Coordinate Type:** {coord_type_map.get(str(add_info.get('coord_type', '')), 'N/A')}")
                    st.write(f"**Coordinate System:** {coord_system_map.get(str(add_info.get('coord_system', '')), 'N/A')}")
                    
                    coord_lat = add_info.get('coord_start_latitude', '')
                    coord_lat_dir = add_info.get('coord_start_lat_direction', '')
                    coord_lon = add_info.get('coord_start_longitude', '')
                    coord_lon_dir = add_info.get('coord_start_lon_direction', '')
                    coord_alt = add_info.get('coord_start_altitude_m', '')
                    coord_dt = add_info.get('coord_start_datetime', '')
                    
                    if coord_lat:
                        lat_dir_str = lat_dir_map.get(str(coord_lat_dir), '')
                        st.write(f"**Starting Latitude:** {coord_lat} ({lat_dir_str})")
                    if coord_lon:
                        lon_dir_str = lon_dir_map.get(str(coord_lon_dir), '')
                        st.write(f"**Starting Longitude:** {coord_lon} ({lon_dir_str})")
                    if coord_alt:
                        st.write(f"**Altitude above Sea Level:** {coord_alt} m")
                    if coord_dt:
                        st.write(f"**Registration Date/Time:** {coord_dt}")
                    
                    st.subheader("DBH Data")
                    dbh_heights = add_info.get('dbh_height_cm', [])
                    dbh_distances = add_info.get('dbh_derivation_distance_cm', [])
                    if dbh_heights:
                        st.write(f"**DBH Heights (cm):** {dbh_heights}")
                    if dbh_distances:
                        st.write(f"**DBH Derivation Distance (cm):** {dbh_distances}")
                    
                    st.subheader("Stand Age")
                    stand_age_mean = add_info.get('stand_age_mean_years', '')
                    stand_age_std = add_info.get('stand_age_std_dev_years', '')
                    if stand_age_mean:
                        st.write(f"**Mean Age:** {stand_age_mean} years")
                    if stand_age_std:
                        st.write(f"**Standard Deviation:** {stand_age_std} years")
                    
                    st.subheader("Apteri Software")
                    apteri_text = add_info.get('apteri_text', '')
                    apteri_dt = add_info.get('apteri_datetime', '')
                    if apteri_text:
                        st.write(f"**Text:** {apteri_text}")
                    if apteri_dt:
                        st.write(f"**Date/Time:** {apteri_dt}")
                    
                    st.subheader("Optional Text")
                    st.write(f"**To Machine:** {add_info.get('optional_text_to_machine', 'N/A')}")
                    st.write(f"**From Machine:** {add_info.get('optional_text_from_machine', 'N/A')}")
                    
                    # Show other PRI data sections
                    if 'apt_history' in data and not data['apt_history'].empty:
                        st.subheader("APT File History")
                        st.dataframe(data['apt_history'], use_container_width=True)
                    
                    if 'price_matrices' in data and not data['price_matrices'].empty:
                        st.subheader("Price Matrices")
                        st.dataframe(data['price_matrices'], use_container_width=True)
                    
                    if 'log_codes' in data and not data['log_codes'].empty:
                        st.subheader("Log Codes")
                        st.dataframe(data['log_codes'], use_container_width=True)
                    
                    if 'tree_codes' in data and not data['tree_codes'].empty:
                        st.subheader("Tree Codes")
                        st.dataframe(data['tree_codes'], use_container_width=True)
                    
                    st.subheader("Additional Info DataFrame")
                    st.dataframe(data['additional_info'], use_container_width=True)
                else:
                    st.info("Additional info data is missing.")

with tab_visualize:
    st.write("Upload your .prd or .hpr files to view statistics and analysis.")
    st.write(
        "**Note:** PRI (Production-individual) can be added with PRD for more production detail. "
        "Optional **APT** (classic bucking instructions) adds relative price matrices for PRD. "
        "For **Stanford 2010 HPR**, optional **PIN** (Product Instruction XML) supplies the product price matrix. "
        "You can upload **APT and/or PIN** in the same optional uploader below."
    )

    # File upload
    uploaded_file = st.file_uploader("Drag PRD or HPR file here", type=['prd', 'hpr'])
    uploaded_pri_file = st.file_uploader("Drag PRI file here (optional, must come with PRD file)", type=['pri'])
    uploaded_apt_pin = st.file_uploader(
        "Drag APT and/or PIN here (optional — classic PRD bucking / HPR product price matrix)",
        type=["apt", "pin"],
        accept_multiple_files=True,
    )
    uploaded_apt_file, uploaded_pin_file, _apt_pin_upload_warnings = _split_apt_pin_uploads(
        uploaded_apt_pin
    )

    # Validate PRI file upload (cannot be provided alone)
    if uploaded_pri_file is not None and uploaded_file is None:
        st.error("❌ PRI file cannot be uploaded without a PRD file. Please upload a PRD file first.")
        st.stop()

    if uploaded_file is None and uploaded_apt_pin is not None:
        _n = len(uploaded_apt_pin) if isinstance(uploaded_apt_pin, list) else 1
        if _n > 0:
            st.error(
                "❌ APT/PIN cannot be uploaded without a PRD or HPR file. "
                "Please upload a main report file first."
            )
            st.stop()

    if uploaded_file is not None:
        st.success("File successfully uploaded!")
        st.write(f"**File Name:** {uploaded_file.name}")

        if uploaded_pri_file is not None:
            st.success("PRI file successfully uploaded!")
            st.write(f"**PRI File Name:** {uploaded_pri_file.name}")

        for w in _apt_pin_upload_warnings:
            st.warning(w)

        if uploaded_apt_file is not None:
            st.success("APT file successfully uploaded!")
            st.write(f"**APT File Name:** {uploaded_apt_file.name}")

        if uploaded_pin_file is not None:
            st.success("PIN file successfully uploaded!")
            st.write(f"**PIN File Name:** {uploaded_pin_file.name}")

        # Determine file type
        file_extension = uploaded_file.name.split('.')[-1].lower()
        file_type = 'hpr' if file_extension == 'hpr' else 'prd'
        temp_file = f"temp_{file_type}_file.{file_extension}"

        # Save uploaded file temporarily
        with open(temp_file, "wb") as f:
            f.write(uploaded_file.getbuffer())

        temp_pri_file = None
        if uploaded_pri_file is not None:
            temp_pri_file = f"temp_pri_file.pri"
            with open(temp_pri_file, "wb") as f:
                f.write(uploaded_pri_file.getbuffer())

        temp_apt_file = None
        if uploaded_apt_file is not None:
            temp_apt_file = "temp_apt_file.apt"
            with open(temp_apt_file, "wb") as f:
                f.write(uploaded_apt_file.getbuffer())

        temp_pin_file = None
        if uploaded_pin_file is not None:
            temp_pin_file = "temp_pin_file.pin"
            with open(temp_pin_file, "wb") as f:
                f.write(uploaded_pin_file.getbuffer())

        try:
            has_apt = temp_apt_file is not None and os.path.exists(temp_apt_file)
            apt_parse_result = None

            with st.spinner(f"Parsing {file_extension.upper()} file..."):
                if file_type == 'hpr':
                    parser = HPRParser(temp_file)
                    parsed_data = parser.parse_all()
                else:
                    parser = PRDParser(temp_file)
                    parsed_data = parser.parse()

            if has_apt:
                with st.spinner("Parsing APT file (price matrix)..."):
                    apt_parse_result = APTParser(temp_apt_file).parse()

            if file_type == 'hpr':
                data = transform_hpr_to_standardized(
                    parsed_data,
                    apt_parse_result=apt_parse_result,
                )
            else:
                data = transform_prd_to_standardized(
                    parsed_data,
                    apt_parse_result=apt_parse_result,
                )

            if temp_pin_file is not None and os.path.exists(temp_pin_file):
                if file_type != 'hpr':
                    st.warning(
                        "PIN (Product Instruction) applies to Stanford 2010 HPR only; "
                        "ignoring the PIN file for this PRD report."
                    )
                else:
                    with st.spinner("Parsing PIN file (product / price matrix)..."):
                        pin_data = PINParser(temp_pin_file).parse_all()
                        data = merge_pin_into_standardized(data, pin_data)

            # Parse PRI file if provided
            pri_data = None
            has_pri = False
            if temp_pri_file is not None and os.path.exists(temp_pri_file):
                with st.spinner("Parsing PRI file..."):
                    pri_parser = PRIParser(temp_pri_file)
                    pri_data = pri_parser.parse()
                    has_pri = True

                    data = merge_pri_into_standardized(data, pri_data)

            st.success("File successfully parsed!")

            # Visualize only the standardized transformation output
            visualize_data(data, has_pri=has_pri)

            # Clean up temporary files
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if temp_pri_file and os.path.exists(temp_pri_file):
                os.remove(temp_pri_file)
            if temp_apt_file and os.path.exists(temp_apt_file):
                os.remove(temp_apt_file)
            if temp_pin_file and os.path.exists(temp_pin_file):
                os.remove(temp_pin_file)

        except Exception as e:
            st.error(f"Error parsing file: {str(e)}")
            st.exception(e)
            # Clean up temporary files on error
            if os.path.exists(temp_file):
                os.remove(temp_file)
            if temp_pri_file and os.path.exists(temp_pri_file):
                os.remove(temp_pri_file)
            if temp_apt_file and os.path.exists(temp_apt_file):
                os.remove(temp_apt_file)
            if temp_pin_file and os.path.exists(temp_pin_file):
                os.remove(temp_pin_file)

    else:
        st.info("👆 Please upload a PRD or HPR file to start the analysis.")

with tab_redact:
    st.write(
        "Upload **Stanford 2010 XML** (e.g. `.hpr`, `.pin`) to produce a copy with sensitive fields "
        "replaced by a placeholder, with optional redaction of stem harvest dates and extension timestamps."
    )
    st.caption(
        "Classic `.prd` / `.pri` reports are not XML; use an HPR or PIN export in the Stanford 2010 schema."
    )
    redact_upload = st.file_uploader(
        "Stanford 2010 XML (HPR, PIN, …)",
        type=["hpr", "pin", "xml", "mom", "hqc", "thp"],
        key="redact_xml_upload",
    )
    redact_placeholder = st.text_input("Placeholder text", value="xxx", key="redact_placeholder")
    redact_strip_times = st.checkbox(
        "Redact stem HarvestDate and all timings under Stem/Extension",
        value=True,
        key="redact_strip_times",
    )
    if redact_upload is not None:
        raw_xml = redact_upload.getvalue()
        try:
            sanitized = sanitize_s4d2010_xml(
                raw_xml,
                placeholder=(redact_placeholder.strip() or "xxx"),
                strip_stem_times=redact_strip_times,
            )
            base_name = redact_upload.name.rsplit(".", 1)
            dl_name = (
                f"redacted_{base_name[0]}.{base_name[1]}"
                if len(base_name) == 2
                else f"redacted_{redact_upload.name}"
            )
            st.download_button(
                label="Download redacted XML",
                data=sanitized,
                file_name=dl_name,
                mime="application/xml",
                key="redact_download",
            )
        except ValueError as err:
            st.error(str(err))
