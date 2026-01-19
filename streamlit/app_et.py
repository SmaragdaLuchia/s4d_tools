import streamlit as st
import pandas as pd
import sys
import os

# Add parent directory to path to import parsers
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from StanForD_visualizer.stanford_classic.prd_parser import PRDParser
from StanForD_visualizer.stanford_classic.pri_parser import PRIParser
from StanForD_visualizer.stanford_2010.hpr_parser import HPRParser

# Page configuration
st.set_page_config(
    page_title="Harvesteri Failide Analüüs",
    page_icon="🌲",
    layout="wide"
)

# Title and description
st.title("🌲 Harvesteri Failide Analüüs")
st.write("Lae üles oma .prd või .hpr failid, et näha statistikat ja analüüsi.")
st.write("**Märkus:** PRI (Production-individual) faili saab laadida koos PRD failiga täiendava tootmise info saamiseks.")

# File upload
uploaded_file = st.file_uploader("Lohista PRD või HPR fail siia", type=['prd', 'hpr'])
uploaded_pri_file = st.file_uploader("Lohista PRI fail siia (valikuline, peab tulema koos PRD failiga)", type=['pri'])

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
                'additional_info']:
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
        "📊 Ülevaade", 
        "📋 Põhiinfo", 
        "🌳 Liigid", 
        "📦 Tooted", 
        "📈 Statistika",
        "🔧 Masin"
    ]
    
    # Add PRI tabs if PRI data is available
    if has_pri:
        tab_names.extend([
            "👥 Ostud/Müüjad",
            "🔧 Kalibreerimine",
            "📊 Tootmise statistika",
            "👤 Operaatorid",
            "📋 Lisainfo"
        ])
    
    tabs = st.tabs(tab_names)
    tab1, tab2, tab3, tab4, tab5, tab6 = tabs[0], tabs[1], tabs[2], tabs[3], tabs[4], tabs[5]
    # PRI tabs
    tab_buyer_vendor = tabs[6] if len(tabs) > 6 else None
    tab_calibration = tabs[7] if len(tabs) > 7 else None
    tab_prod_stats = tabs[8] if len(tabs) > 8 else None
    tab_operators = tabs[9] if len(tabs) > 9 else None
    tab_additional = tabs[10] if len(tabs) > 10 else None
    
    # TAB 1: Overview
    with tab1:
        st.header("Ülevaade")
        
        col1, col2, col3, col4 = st.columns(4)
        
        # Total stems
        if 'statistics' in data and not data['statistics'].empty:
            total_stems = data['statistics'].iloc[0].get('total_stems', 0)
            col1.metric("Kokku puid", f"{total_stems:,}")
        
        # Number of species
        num_species = len(data['species_groups']) if 'species_groups' in data else 0
        col2.metric("Liikide arv", num_species)
        
        # Number of products
        num_products = len(data['products']) if 'products' in data else 0
        col3.metric("Toodete arv", num_products)
        
        # Site name
        if 'objects' in data and not data['objects'].empty:
            site_name = data['objects'].iloc[0].get('object_name', 'N/A')
            col4.metric("Objekti nimi", site_name)
        
        # Statistics summary
        if 'statistics' in data and not data['statistics'].empty:
            stats = data['statistics'].iloc[0]
            if 'species_names' in stats and 'stems_per_species' in stats:
                species_names = stats['species_names'] if isinstance(stats['species_names'], list) else []
                stems_per_species = stats['stems_per_species'] if isinstance(stats['stems_per_species'], list) else []
                
                # Ensure arrays have the same length
                min_length = min(len(species_names), len(stems_per_species))
                if min_length > 0:
                    st.subheader("Puid liigiti")
                    species_df = pd.DataFrame({
                        'Liik': species_names[:min_length],
                        'Puid': stems_per_species[:min_length]
                    })
                    st.bar_chart(species_df.set_index('Liik'))
    
    # TAB 2: Basic Info (Header, Objects)
    with tab2:
        st.header("Põhiinfo")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Faili info")
            if 'header' in data and not data['header'].empty:
                header = data['header'].iloc[0]
                st.write(f"**Loomise kuupäev:** {header.get('creation_date', 'N/A')}")
                st.write(f"**Muutmise kuupäev:** {header.get('modification_date', 'N/A')}")
                st.write(f"**Rakenduse versioon:** {header.get('application_version_created', 'N/A')}")
        
        with col2:
            st.subheader("Objekti info")
            if 'objects' in data and not data['objects'].empty:
                obj = data['objects'].iloc[0]
                st.write(f"**Objekti nimi:** {obj.get('object_name', 'N/A')}")
                st.write(f"**Lepingu number:** {obj.get('contract_number', 'N/A')}")
        
        # Display DataFrames
        if 'header' in data:
            st.subheader("Header DataFrame")
            st.dataframe(data['header'], use_container_width=True)
        
        if 'objects' in data:
            st.subheader("Objects DataFrame")
            st.dataframe(data['objects'], use_container_width=True)
    
    # TAB 3: Species
    with tab3:
        st.header("Liigid")
        
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
                        st.subheader("Liikide statistika")
                        species_stats_df = pd.DataFrame({
                            'Liik': species_names[:min_length],
                            'Puid': stems_per_species[:min_length],
                            'Maht (toorühikud)': volume_per_species[:min_length]
                        })
                        st.dataframe(species_stats_df, use_container_width=True)
        else:
            st.info("Liikide andmed puuduvad.")
    
    # TAB 4: Products
    with tab4:
        st.header("Tooted")
        
        if 'products' in data and not data['products'].empty:
            st.dataframe(data['products'], use_container_width=True)
        else:
            st.info("Toodete andmed puuduvad.")
    
    # TAB 5: Statistics
    with tab5:
        st.header("Statistika")
        
        if 'statistics' in data and not data['statistics'].empty:
            stats = data['statistics'].iloc[0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.metric("Kokku puid", stats.get('total_stems', 0))
            
            # Stems per species chart
            if 'species_names' in stats and 'stems_per_species' in stats:
                species_names = stats['species_names'] if isinstance(stats['species_names'], list) else []
                stems_per_species = stats['stems_per_species'] if isinstance(stats['stems_per_species'], list) else []
                
                min_length = min(len(species_names), len(stems_per_species))
                if min_length > 0:
                    st.subheader("Puid liigiti")
                    species_chart_df = pd.DataFrame({
                        'Liik': species_names[:min_length],
                        'Puid': stems_per_species[:min_length]
                    })
                    st.bar_chart(species_chart_df.set_index('Liik'))
            
            # Volume per species chart
            if 'species_names' in stats and 'volume_per_species' in stats:
                species_names = stats['species_names'] if isinstance(stats['species_names'], list) else []
                volume_per_species = stats['volume_per_species'] if isinstance(stats['volume_per_species'], list) else []
                
                min_length = min(len(species_names), len(volume_per_species))
                if min_length > 0:
                    st.subheader("Maht liigiti (toorühikud)")
                    volume_chart_df = pd.DataFrame({
                        'Liik': species_names[:min_length],
                        'Maht': volume_per_species[:min_length]
                    })
                    st.bar_chart(volume_chart_df.set_index('Liik'))
            
            # Statistics DataFrame
            st.subheader("Statistika DataFrame")
            st.dataframe(data['statistics'], use_container_width=True)
        else:
            st.info("Statistika andmed puuduvad.")
    
    # TAB 6: Machine
    with tab6:
        st.header("Masina info")
        
        if 'machine' in data and not data['machine'].empty:
            machine = data['machine'].iloc[0]
            st.write(f"**Tootja:** {machine.get('machine_base_manufacturer', 'N/A')}")
            st.write(f"**Mudel:** {machine.get('machine_base_model', 'N/A')}")
            
            st.subheader("Machine DataFrame")
            st.dataframe(data['machine'], use_container_width=True)
        else:
            st.info("Masina andmed puuduvad.")
    
    # Additional tabs for HPR-specific data
    if file_type == 'hpr':
        tab7, tab8 = st.tabs(["🌲 Puid", "📏 Palgid"])
        
        with tab7:
            st.header("Puid (Stems)")
            if 'stems' in data and not data['stems'].empty:
                st.dataframe(data['stems'], use_container_width=True)
            else:
                st.info("Puid andmed puuduvad.")
        
        with tab8:
            st.header("Palgid (Logs)")
            if 'logs' in data and not data['logs'].empty:
                st.dataframe(data['logs'], use_container_width=True)
            else:
                st.info("Palgid andmed puuduvad.")
    
    # PRI-specific tabs for production-individual data
    if has_pri:
        # Buyer/Vendor tab
        if tab_buyer_vendor is not None and 'buyer_vendor' in data:
            with tab_buyer_vendor:
                st.header("Ostjad ja müüjad")
                if not data['buyer_vendor'].empty:
                    bv = data['buyer_vendor'].iloc[0]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Ostja")
                        st.write(f"**Tekst:** {bv.get('buyer_text', 'N/A')}")
                        st.write(f"**Maatriks tekst:** {bv.get('buyer_matrix_text', 'N/A')}")
                        
                        st.subheader("Tarnija")
                        st.write(f"**Kood:** {bv.get('vendor_code', 'N/A')}")
                        st.write(f"**Nimi:** {bv.get('vendor_name', 'N/A')}")
                        st.write(f"**Aadress:** {bv.get('vendor_address', 'N/A')}")
                        st.write(f"**E-post:** {bv.get('vendor_email', 'N/A')}")
                        st.write(f"**Telefon:** {bv.get('vendor_phone', 'N/A')}")
                    
                    with col2:
                        st.subheader("Alamleping")
                        st.write(f"**Kood:** {bv.get('subcontractor_code', 'N/A')}")
                        st.write(f"**Nimi:** {bv.get('subcontractor_name', 'N/A')}")
                        st.write(f"**Aadress:** {bv.get('subcontractor_address', 'N/A')}")
                        st.write(f"**E-post:** {bv.get('subcontractor_email', 'N/A')}")
                        st.write(f"**Telefon:** {bv.get('subcontractor_phone', 'N/A')}")
                    
                    st.subheader("Buyer/Vendor DataFrame")
                    st.dataframe(data['buyer_vendor'], use_container_width=True)
                else:
                    st.info("Ostjate/müüjate andmed puuduvad.")
        
        # Calibration tab
        if tab_calibration is not None and 'calibration' in data:
            with tab_calibration:
                st.header("Kalibreerimise andmed")
                if not data['calibration'].empty:
                    cal = data['calibration'].iloc[0]
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.subheader("Pikkuse kalibreerimine")
                        st.write(f"**Kalibreerimiste arv:** {cal.get('num_length_calibrations', 0)}")
                        st.write(f"**Pikkuse positsioonid (cm):** {cal.get('length_positions_cm', [])[:10]}...")
                        st.write(f"**Pikkuse korrektsioonid (mm):** {cal.get('length_corrections_mm', [])[:10]}...")
                    
                    with col2:
                        st.subheader("Läbimõõdu kalibreerimine")
                        st.write(f"**Kalibreerimiste arv:** {cal.get('num_diameter_calibrations', 0)}")
                        st.write(f"**Läbimõõdu positsioonid (mm):** {cal.get('diameter_positions_mm', [])[:10]}...")
                        st.write(f"**Läbimõõdu korrektsioonid (mm):** {cal.get('diameter_corrections_mm', [])[:10]}...")
                    
                    st.subheader("Calibration DataFrame")
                    st.dataframe(data['calibration'], use_container_width=True)
                else:
                    st.info("Kalibreerimise andmed puuduvad.")
        
        # Production statistics tab
        if tab_prod_stats is not None and 'production_statistics' in data:
            with tab_prod_stats:
                st.header("Tootmise statistika")
                if not data['production_statistics'].empty:
                    stats = data['production_statistics'].iloc[0]
                    
                    col1, col2, col3, col4 = st.columns(4)
                    
                    col1.metric("Puid", stats.get('num_stems', 0))
                    col2.metric("Palgid", stats.get('num_logs', 0))
                    col3.metric("Kaetud vahemaa (km)", f"{stats.get('distance_covered_km', 0):.2f}")
                    col4.metric("Mitme puu töötlemisi", stats.get('num_multi_tree_occasions', 0))
                    
                    st.subheader("Täpsem statistika")
                    st.write(f"**Kokku puid (objektil):** {stats.get('total_stems_site', 0)}")
                    st.write(f"**Kokku palgid (objektil):** {stats.get('total_logs_site', 0)}")
                    st.write(f"**Mitme puu töödeldud puid:** {stats.get('num_multi_tree_stems', 0)}")
                    st.write(f"**Kokkukogutud palgid:** {stats.get('estimated_logs_bunched', 0)}")
                    
                    # Volume per species
                    volumes = stats.get('total_merchantable_volume_m3_ub', [])
                    if volumes and isinstance(volumes, list) and len(volumes) > 0:
                        st.subheader("Kaubalik maht liigiti (m³ u.b.)")
                        if 'species_groups' in data and not data['species_groups'].empty:
                            species_names = data['species_groups']['species_group_name'].tolist()
                            min_len = min(len(species_names), len(volumes))
                            if min_len > 0:
                                volume_df = pd.DataFrame({
                                    'Liik': species_names[:min_len],
                                    'Maht (m³ u.b.)': volumes[:min_len]
                                })
                                st.dataframe(volume_df, use_container_width=True)
                                st.bar_chart(volume_df.set_index('Liik'))
                    
                    st.subheader("Production Statistics DataFrame")
                    st.dataframe(data['production_statistics'], use_container_width=True)
                else:
                    st.info("Tootmise statistika andmed puuduvad.")
        
        # Operators tab
        if tab_operators is not None and 'operators' in data:
            with tab_operators:
                st.header("Operaatorid")
                if not data['operators'].empty:
                    st.dataframe(data['operators'], use_container_width=True)
                else:
                    st.info("Operaatorite andmed puuduvad.")
        
        # Additional info tab
        if tab_additional is not None and 'additional_info' in data:
            with tab_additional:
                st.header("Lisainfo")
                if not data['additional_info'].empty:
                    add_info = data['additional_info'].iloc[0]
                    
                    st.subheader("Koordinaadid")
                    coord_system_map = {'1': 'WGS84', '': 'N/A'}
                    coord_type_map = {'1': 'Suhtelised koordinaadid', '2': 'Absoluutsed koordinaadid', '': 'N/A'}
                    coord_ref_map = {'1': 'Masina baaspositsioon', '2': 'Kraana ots fellingu ajal', '3': 'Kraana ots töötlemise ajal', '': 'N/A'}
                    lat_dir_map = {'1': 'Põhi', '2': 'Lõuna', '': 'N/A'}
                    lon_dir_map = {'1': 'Ida', '2': 'Lääs', '': 'N/A'}
                    
                    st.write(f"**Registreerimise positsioon:** {coord_ref_map.get(str(add_info.get('coord_ref_position', '')), 'N/A')}")
                    st.write(f"**Koordinaatide tüüp:** {coord_type_map.get(str(add_info.get('coord_type', '')), 'N/A')}")
                    st.write(f"**Koordinaatide süsteem:** {coord_system_map.get(str(add_info.get('coord_system', '')), 'N/A')}")
                    
                    coord_lat = add_info.get('coord_start_latitude', '')
                    coord_lat_dir = add_info.get('coord_start_lat_direction', '')
                    coord_lon = add_info.get('coord_start_longitude', '')
                    coord_lon_dir = add_info.get('coord_start_lon_direction', '')
                    coord_alt = add_info.get('coord_start_altitude_m', '')
                    coord_dt = add_info.get('coord_start_datetime', '')
                    
                    if coord_lat:
                        lat_dir_str = lat_dir_map.get(str(coord_lat_dir), '')
                        st.write(f"**Algne laiuskraad:** {coord_lat} ({lat_dir_str})")
                    if coord_lon:
                        lon_dir_str = lon_dir_map.get(str(coord_lon_dir), '')
                        st.write(f"**Algne pikkuskraad:** {coord_lon} ({lon_dir_str})")
                    if coord_alt:
                        st.write(f"**Kõrgus merepinnast:** {coord_alt} m")
                    if coord_dt:
                        st.write(f"**Registreerimise kuupäev/aeg:** {coord_dt}")
                    
                    st.subheader("DBH andmed")
                    dbh_heights = add_info.get('dbh_height_cm', [])
                    dbh_distances = add_info.get('dbh_derivation_distance_cm', [])
                    if dbh_heights:
                        st.write(f"**DBH kõrgused (cm):** {dbh_heights}")
                    if dbh_distances:
                        st.write(f"**DBH tuletamise kaugus (cm):** {dbh_distances}")
                    
                    st.subheader("Metsa vanus")
                    stand_age_mean = add_info.get('stand_age_mean_years', '')
                    stand_age_std = add_info.get('stand_age_std_dev_years', '')
                    if stand_age_mean:
                        st.write(f"**Keskmine vanus:** {stand_age_mean} aastat")
                    if stand_age_std:
                        st.write(f"**Standardhälve:** {stand_age_std} aastat")
                    
                    st.subheader("Apteri tarkvara")
                    apteri_text = add_info.get('apteri_text', '')
                    apteri_dt = add_info.get('apteri_datetime', '')
                    if apteri_text:
                        st.write(f"**Tekst:** {apteri_text}")
                    if apteri_dt:
                        st.write(f"**Kuupäev/aeg:** {apteri_dt}")
                    
                    st.subheader("Valikuline tekst")
                    st.write(f"**Masinale:** {add_info.get('optional_text_to_machine', 'N/A')}")
                    st.write(f"**Masinast:** {add_info.get('optional_text_from_machine', 'N/A')}")
                    
                    # Show other PRI data sections
                    if 'apt_history' in data and not data['apt_history'].empty:
                        st.subheader("APT faili ajalugu")
                        st.dataframe(data['apt_history'], use_container_width=True)
                    
                    if 'price_matrices' in data and not data['price_matrices'].empty:
                        st.subheader("Hindamismaatriksid")
                        st.dataframe(data['price_matrices'], use_container_width=True)
                    
                    if 'log_codes' in data and not data['log_codes'].empty:
                        st.subheader("Palgi koodid")
                        st.dataframe(data['log_codes'], use_container_width=True)
                    
                    if 'tree_codes' in data and not data['tree_codes'].empty:
                        st.subheader("Puu koodid")
                        st.dataframe(data['tree_codes'], use_container_width=True)
                    
                    st.subheader("Additional Info DataFrame")
                    st.dataframe(data['additional_info'], use_container_width=True)
                else:
                    st.info("Lisainfo andmed puuduvad.")

# Validate PRI file upload (cannot be provided alone)
if uploaded_pri_file is not None and uploaded_file is None:
    st.error("❌ PRI faili ei saa laadida ilma PRD failita. Palun lae esmalt PRD fail.")
    st.stop()

if uploaded_file is not None:
    st.success("Fail edukalt laetud!")
    st.write(f"**Faili nimi:** {uploaded_file.name}")
    
    if uploaded_pri_file is not None:
        st.success("PRI fail edukalt laetud!")
        st.write(f"**PRI faili nimi:** {uploaded_pri_file.name}")
    
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
        with st.spinner(f"Parsin {file_extension.upper()} faili..."):
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
            with st.spinner("Parsin PRI faili..."):
                pri_parser = PRIParser(temp_pri_file)
                pri_data = pri_parser.parse()
                has_pri = True
                
                # Merge PRD and PRI data
                if file_type == 'prd':
                    data = merge_prd_pri_data(data, pri_data)
        
        st.success("Fail edukalt parsimist!")
        
        # Visualize data
        visualize_data(data, file_type, has_pri=has_pri)
        
        # Clean up temporary files
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if temp_pri_file and os.path.exists(temp_pri_file):
            os.remove(temp_pri_file)
    
    except Exception as e:
        st.error(f"Viga faili parsimisel: {str(e)}")
        st.exception(e)
        # Clean up temporary files on error
        if os.path.exists(temp_file):
            os.remove(temp_file)
        if temp_pri_file and os.path.exists(temp_pri_file):
            os.remove(temp_pri_file)

else:
    st.info("👆 Palun lae üles PRD või HPR fail, et alustada analüüsi.")
