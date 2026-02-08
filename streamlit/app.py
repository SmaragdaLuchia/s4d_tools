import streamlit as st
import pandas as pd
import sys
import os

# Ensure project root is on path when running from streamlit/
_here = os.path.dirname(os.path.abspath(__file__))
_root = os.path.dirname(_here)
if _root not in sys.path:
    sys.path.insert(0, _root)

from s4d_tools import PRDParser, PRIParser, HPRParser

# Page configuration
st.set_page_config(
    page_title="Harvester File Analysis",
    page_icon="🌲",
    layout="wide"
)

# Title and description
st.title("🌲 Harvester File Analysis")
st.write("Upload your .prd or .hpr files to view statistics and analysis.")
st.write("**Note:** PRI (Production-individual) file can be uploaded together with PRD file to get additional production information.")

# File upload
uploaded_file = st.file_uploader("Drag PRD or HPR file here", type=['prd', 'hpr'])
uploaded_pri_file = st.file_uploader("Drag PRI file here (optional, must come with PRD file)", type=['pri'])

def calculate_hpr_statistics(hpr_data):
    """
    Calculate statistics from HPR data to match PRD statistics structure.
    Returns a statistics DataFrame with the same structure as PRD.
    """
    statistics_data = {}
    
    # Total stems
    total_stems = len(hpr_data['stems']) if not hpr_data['stems'].empty else 0
    statistics_data['total_stems'] = total_stems
    
    # Calculate stems per species
    if not hpr_data['stems'].empty:
        # Count stems per species
        stems_per_species_counts = hpr_data['stems'].groupby('species_group_key').size()
        
        # Get species names in order from species_groups
        species_names = []
        stems_counts = []
        volume_per_species = []
        
        if not hpr_data['species_groups'].empty:
            species_groups = hpr_data['species_groups']
            
            # Join logs with stems to get species_group_key for volume calculation
            logs_with_stems = None
            if not hpr_data['logs'].empty:
                logs_with_stems = hpr_data['logs'].merge(
                    hpr_data['stems'][['stem_key', 'species_group_key']],
                    on='stem_key',
                    how='left'
                )
            
            for _, species in species_groups.iterrows():
                species_key = species.get('species_group_key', '')
                if species_key:
                    species_name = species.get('species_group_name', '')
                    count = int(stems_per_species_counts.get(species_key, 0))
                    
                    species_names.append(species_name if species_name else species_key)
                    stems_counts.append(count)
                    
                    # Calculate volume for this species
                    if logs_with_stems is not None and not logs_with_stems.empty:
                        species_logs = logs_with_stems[logs_with_stems['species_group_key'] == species_key]
                        if not species_logs.empty:
                            # Convert volume to numeric (m³), then to raw units (multiply by 100)
                            volumes = pd.to_numeric(species_logs['volume_sob_m3'].replace('', '0'), errors='coerce').fillna(0)
                            total_volume_m3 = volumes.sum()
                            total_volume_raw = int(total_volume_m3 * 100)  # Convert m³ to raw units (like PRD)
                            volume_per_species.append(total_volume_raw)
                        else:
                            volume_per_species.append(0)
                    else:
                        volume_per_species.append(0)
        else:
            # If no species_groups, use unique species_group_keys from stems
            unique_species_keys = hpr_data['stems']['species_group_key'].unique()
            for species_key in unique_species_keys:
                if species_key:
                    species_names.append(species_key)
                    stems_counts.append(int(stems_per_species_counts.get(species_key, 0)))
                    volume_per_species.append(0)  # Can't calculate volume without species_groups
        
        # Ensure all lists have the same length
        if species_names:
            reference_length = len(species_names)
            stems_counts = (stems_counts + [0] * (reference_length - len(stems_counts)))[:reference_length]
            volume_per_species = (volume_per_species + [0] * (reference_length - len(volume_per_species)))[:reference_length]
        
        statistics_data['species_names'] = species_names
        statistics_data['stems_per_species'] = stems_counts
        statistics_data['volume_per_species'] = volume_per_species
    else:
        statistics_data['species_names'] = []
        statistics_data['stems_per_species'] = []
        statistics_data['volume_per_species'] = []
    
    return pd.DataFrame([statistics_data])

def merge_prd_pri_data(prd_data, pri_data):
    """
    Merge PRD and PRI data. PRI data (production-individual) complements PRD data.
    Returns merged data dictionary.
    """
    merged_data = prd_data.copy()
    
    # Merge header - PRI may have additional fields
    if 'header' in pri_data and not pri_data['header'].empty:
        pri_header = pri_data['header'].iloc[0]
        if 'header' in merged_data and not merged_data['header'].empty:
            # Update with PRI header info if PRD header is missing some fields
            prd_header = merged_data['header'].iloc[0]
            for key, value in pri_header.items():
                if key not in prd_header or (prd_header[key] == '' and value != ''):
                    merged_data['header'].iloc[0][key] = value
    
    # Merge machine - PRI may have additional fields
    if 'machine' in pri_data and not pri_data['machine'].empty:
        pri_machine = pri_data['machine'].iloc[0]
        if 'machine' in merged_data and not merged_data['machine'].empty:
            prd_machine = merged_data['machine'].iloc[0]
            for key, value in pri_machine.items():
                if key not in prd_machine or (prd_machine[key] == '' and value != ''):
                    merged_data['machine'].iloc[0][key] = value
    
    # Merge objects - PRI may have additional fields like operator_id
    if 'objects' in pri_data and not pri_data['objects'].empty:
        pri_objects = pri_data['objects'].iloc[0]
        if 'objects' in merged_data and not merged_data['objects'].empty:
            prd_objects = merged_data['objects'].iloc[0]
            for key, value in pri_objects.items():
                if key not in prd_objects or (prd_objects[key] == '' and value != ''):
                    merged_data['objects'].iloc[0][key] = value
    
    # Species groups and products should be the same, but PRI may have additional info
    # We'll keep PRD's version as it has production statistics
    
    # Add all PRI-specific production-individual data
    for key in ['buyer_vendor', 'calibration', 'apt_history', 'price_matrices', 
                'operators', 'production_statistics', 'log_codes', 'tree_codes', 
                'additional_info', 'logs']:
        if key in pri_data:
            merged_data[key] = pri_data[key]
    
    return merged_data

def visualize_data(data, file_type, has_pri=False):
    """
    Unified visualization function for PRD, HPR, and PRD+PRI data.
    """
    # For HPR, calculate statistics to match PRD structure
    if file_type == 'hpr':
        data['statistics'] = calculate_hpr_statistics(data)
    
    # Create tabs for different sections
    tab_names = [
        "📊 Overview", 
        "📋 Basic Info", 
        "🌳 Species", 
        "📦 Products", 
        "📈 Statistics",
        "🔧 Machine"
    ]
    
    # Add PRI tabs if PRI data is available
    if has_pri:
        tab_names.extend([
            "👥 Buyers/Vendors",
            "🔧 Calibration",
            "📊 Production Statistics",
            "👤 Operators",
            "📋 Additional Info",
            "📏 Logs"
        ])
    
    tabs = st.tabs(tab_names)
    tab1, tab2, tab3, tab4, tab5, tab6 = tabs[0], tabs[1], tabs[2], tabs[3], tabs[4], tabs[5]
    # PRI tabs
    tab_buyer_vendor = tabs[6] if len(tabs) > 6 else None
    tab_calibration = tabs[7] if len(tabs) > 7 else None
    tab_prod_stats = tabs[8] if len(tabs) > 8 else None
    tab_operators = tabs[9] if len(tabs) > 9 else None
    tab_additional = tabs[10] if len(tabs) > 10 else None
    tab_pri_logs = tabs[11] if len(tabs) > 11 else None
    
    # TAB 1: Overview
    with tab1:
        st.header("Overview")
        
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
    
    # TAB 6: Machine
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
    
    # Additional tabs for HPR-specific data
    if file_type == 'hpr':
        tab7, tab8 = st.tabs(["🌲 Stems", "📏 Logs"])
        
        with tab7:
            st.header("Stems")
            if 'stems' in data and not data['stems'].empty:
                st.dataframe(data['stems'], use_container_width=True)
            else:
                st.info("Stems data is missing.")
        
        with tab8:
            st.header("Logs")
            if 'logs' in data and not data['logs'].empty:
                st.dataframe(data['logs'], use_container_width=True)
            else:
                st.info("Logs data is missing.")
    
    # PRI-specific tabs for production-individual data
    if has_pri:
        # Buyer/Vendor tab
        if tab_buyer_vendor is not None and 'buyer_vendor' in data:
            with tab_buyer_vendor:
                st.header("Buyers and Vendors")
                if not data['buyer_vendor'].empty:
                    bv = data['buyer_vendor'].iloc[0]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Buyer")
                        st.write(f"**Text:** {bv.get('buyer_text', 'N/A')}")
                        st.write(f"**Matrix Text:** {bv.get('buyer_matrix_text', 'N/A')}")
                        
                        st.subheader("Vendor")
                        st.write(f"**Code:** {bv.get('vendor_code', 'N/A')}")
                        st.write(f"**Name:** {bv.get('vendor_name', 'N/A')}")
                        st.write(f"**Address:** {bv.get('vendor_address', 'N/A')}")
                        st.write(f"**Email:** {bv.get('vendor_email', 'N/A')}")
                        st.write(f"**Phone:** {bv.get('vendor_phone', 'N/A')}")
                    
                    with col2:
                        st.subheader("Subcontractor")
                        st.write(f"**Code:** {bv.get('subcontractor_code', 'N/A')}")
                        st.write(f"**Name:** {bv.get('subcontractor_name', 'N/A')}")
                        st.write(f"**Address:** {bv.get('subcontractor_address', 'N/A')}")
                        st.write(f"**Email:** {bv.get('subcontractor_email', 'N/A')}")
                        st.write(f"**Phone:** {bv.get('subcontractor_phone', 'N/A')}")
                    
                    st.subheader("Buyer/Vendor DataFrame")
                    st.dataframe(data['buyer_vendor'], use_container_width=True)
                else:
                    st.info("Buyer/vendor data is missing.")
        
        # Calibration tab
        if tab_calibration is not None and 'calibration' in data:
            with tab_calibration:
                st.header("Calibration Data")
                if not data['calibration'].empty:
                    cal = data['calibration'].iloc[0]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Length Calibration")
                        st.write(f"**Number of Calibrations:** {cal.get('num_length_calibrations', 0)}")
                        st.write(f"**Length Positions (cm):** {cal.get('length_positions_cm', [])[:10]}...")
                        st.write(f"**Length Corrections (mm):** {cal.get('length_corrections_mm', [])[:10]}...")
                    
                    with col2:
                        st.subheader("Diameter Calibration")
                        st.write(f"**Number of Calibrations:** {cal.get('num_diameter_calibrations', 0)}")
                        st.write(f"**Diameter Positions (mm):** {cal.get('diameter_positions_mm', [])[:10]}...")
                        st.write(f"**Diameter Corrections (mm):** {cal.get('diameter_corrections_mm', [])[:10]}...")
                    
                    st.subheader("Calibration DataFrame")
                    st.dataframe(data['calibration'], use_container_width=True)
                else:
                    st.info("Calibration data is missing.")
        
        # Production statistics tab
        if tab_prod_stats is not None and 'production_statistics' in data:
            with tab_prod_stats:
                st.header("Production Statistics")
                if not data['production_statistics'].empty:
                    stats = data['production_statistics'].iloc[0]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    col1.metric("Stems", stats.get('num_stems', 0))
                    col2.metric("Logs", stats.get('num_logs', 0))
                    col3.metric("Distance Covered (km)", f"{stats.get('distance_covered_km', 0):.2f}")
                    col4.metric("Multi-tree Operations", stats.get('num_multi_tree_occasions', 0))
                    
                    st.subheader("Detailed Statistics")
                    st.write(f"**Total Stems (on site):** {stats.get('total_stems_site', 0)}")
                    st.write(f"**Total Logs (on site):** {stats.get('total_logs_site', 0)}")
                    st.write(f"**Multi-tree Processed Stems:** {stats.get('num_multi_tree_stems', 0)}")
                    st.write(f"**Estimated Bunched Logs:** {stats.get('estimated_logs_bunched', 0)}")
                    
                    # Volume per species
                    volumes = stats.get('total_merchantable_volume_m3_ub', [])
                    if volumes and isinstance(volumes, list) and len(volumes) > 0:
                        st.subheader("Merchantable Volume by Species (m³ u.b.)")
                        if 'species_groups' in data and not data['species_groups'].empty:
                            species_names = data['species_groups']['species_group_name'].tolist()
                            min_len = min(len(species_names), len(volumes))
                            if min_len > 0:
                                volume_df = pd.DataFrame({
                                    'Species': species_names[:min_len],
                                    'Volume (m³ u.b.)': volumes[:min_len]
                                })
                                st.dataframe(volume_df, use_container_width=True)
                                st.bar_chart(volume_df.set_index('Species'))
                    
                    st.subheader("Production Statistics DataFrame")
                    st.dataframe(data['production_statistics'], use_container_width=True)
                else:
                    st.info("Production statistics data is missing.")
        
        # Operators tab
        if tab_operators is not None and 'operators' in data:
            with tab_operators:
                st.header("Operators")
                if not data['operators'].empty:
                    st.dataframe(data['operators'], use_container_width=True)
                else:
                    st.info("Operators data is missing.")
        
        # Additional info tab
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
        
        # Logs tab
        if tab_pri_logs is not None and 'logs' in data:
            with tab_pri_logs:
                st.header("Individual Logs")
                if not data['logs'].empty:
                    logs_df = data['logs']
                    
                    st.write(f"**Total Logs:** {len(logs_df):,}")
                    
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("Unique Stems", logs_df['stem_number'].nunique() if 'stem_number' in logs_df.columns else 0)
                    with col2:
                        st.metric("Unique Species", logs_df['species_index'].nunique() if 'species_index' in logs_df.columns else 0)
                    with col3:
                        st.metric("Unique Assortments", logs_df['assortment_index'].nunique() if 'assortment_index' in logs_df.columns else 0)
                    
                    st.subheader("Logs DataFrame")
                    
                    if len(logs_df) > 1000:
                        st.info(f"Showing first 1,000 of {len(logs_df):,} logs. Use filters to narrow down results.")
                        display_df = logs_df.head(1000)
                    else:
                        display_df = logs_df
                    
                    st.dataframe(display_df, use_container_width=True, height=400)
                    
                    if 'volume_dl_sob' in logs_df.columns:
                        st.subheader("Volume Statistics")
                        col1, col2 = st.columns(2)
                        with col1:
                            total_volume = logs_df['volume_dl_sob'].sum() / 10000
                            st.metric("Total Volume (m³ s.o.b.)", f"{total_volume:,.2f}")
                        with col2:
                            avg_volume = logs_df['volume_dl_sob'].mean() / 10000
                            st.metric("Average Log Volume (m³ s.o.b.)", f"{avg_volume:.4f}")
                    
                    if 'length_actual_cm' in logs_df.columns:
                        st.subheader("Length Statistics")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Min Length (cm)", f"{logs_df['length_actual_cm'].min():.0f}")
                        with col2:
                            st.metric("Max Length (cm)", f"{logs_df['length_actual_cm'].max():.0f}")
                        with col3:
                            st.metric("Avg Length (cm)", f"{logs_df['length_actual_cm'].mean():.1f}")
                    
                    if 'diameter_top_ob' in logs_df.columns and 'diameter_root_ob' in logs_df.columns:
                        st.subheader("Diameter Statistics")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("Avg Top Diameter (mm)", f"{logs_df['diameter_top_ob'].mean():.0f}")
                        with col2:
                            st.metric("Avg Root Diameter (mm)", f"{logs_df['diameter_root_ob'].mean():.0f}")
                        with col3:
                            if 'diameter_mid_ob' in logs_df.columns:
                                st.metric("Avg Mid Diameter (mm)", f"{logs_df['diameter_mid_ob'].mean():.0f}")
                else:
                    st.info("Logs data is missing.")

# Validate PRI file upload (cannot be provided alone)
if uploaded_pri_file is not None and uploaded_file is None:
    st.error("❌ PRI file cannot be uploaded without a PRD file. Please upload a PRD file first.")
    st.stop()

if uploaded_file is not None:
    st.success("File successfully uploaded!")
    st.write(f"**File Name:** {uploaded_file.name}")
    
    if uploaded_pri_file is not None:
        st.success("PRI file successfully uploaded!")
        st.write(f"**PRI File Name:** {uploaded_pri_file.name}")
    
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
    
    try:
        # Parse main file based on type
        with st.spinner(f"Parsing {file_extension.upper()} file..."):
            if file_type == 'hpr':
                parser = HPRParser(temp_file)
                data = parser.parse_all()
            else:
                parser = PRDParser(temp_file)
                data = parser.parse()
        
        # Parse PRI file if provided
        pri_data = None
        has_pri = False
        if temp_pri_file is not None and os.path.exists(temp_pri_file):
            with st.spinner("Parsing PRI file..."):
                pri_parser = PRIParser(temp_pri_file)
                pri_data = pri_parser.parse()
                has_pri = True
                
                # Merge PRD and PRI data (including logs)
                if file_type == 'prd':
                    data = merge_prd_pri_data(data, pri_data)
                else:
                    data.update(pri_data)
        
        st.success("File successfully parsed!")
        
        # Visualize data
        visualize_data(data, file_type, has_pri=has_pri)
        
        # Clean up temporary files
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if temp_pri_file and os.path.exists(temp_pri_file):
            os.remove(temp_pri_file)
    
    except Exception as e:
        st.error(f"Error parsing file: {str(e)}")
        st.exception(e)
        # Clean up temporary files on error
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if temp_pri_file and os.path.exists(temp_pri_file):
            os.remove(temp_pri_file)

else:
    st.info("👆 Please upload a PRD or HPR file to start the analysis.")
