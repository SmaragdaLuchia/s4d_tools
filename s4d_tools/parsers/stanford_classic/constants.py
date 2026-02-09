
DEFAULT_ENCODING = 'iso-8859-15'  
BLOCK_SEPARATOR = '~'           

PRD_VARIABLE_MAP = {
# --- 1. Header & Machine Info ---
    (1, 4): "file_version",          # e.g., 0
    (2, 2): "software_version",      # e.g., LUUA.hrv.env
    (3, 5): "machine_manufacturer",  # e.g., Komatsu Forest
    (3, 6): "machine_model",         # e.g., 931-3
    
    # --- 2. Dates (Timestamps) ---
    # StanForD files often have multiple dates. 
    # Usually: 11=Start, 12=End/Current, 16=Print date
    (11, 4): "start_date",           # YYYYMMDDHHMMSS
    (12, 4): "end_date",             # This is usually the main "report date"
    (13, 4): "print_date",

    # --- 3. Location / Site ---
    (21, 1): "contract_id",          # e.g., 1122
    (21, 3): "site_name",            # e.g., L75 e 9 LR

    # --- 4. Species Definitions ---
    # Group 120 defines the species.
    (120, 1): "species_names",       # List: MÄND, KUUSK, KASK...
    (120, 3): "species_ids",         # List: 1, 2, 3...

    # --- 5. Product Definitions ---
    # Group 121 defines the products (logs).
    (121, 1): "product_names",       # List: MA palk, MA paber...
    
    # --- 6. Dimensions (for Matrices) ---
    (131, 1): "diameter_classes",    # The columns for the matrix
    (132, 1): "length_classes",      # The rows for the matrix

    # --- 7. Production Statistics (The most important part!) ---
    # Group 221 = Total Stems
    (221, 1): "total_stems",         # Value: 3287

    # Group 222 = Stems per Species
    # Note in your file: "2308 771 144 64 0" -> Matches the 5 species in Grp 120
    (222, 1): "stems_per_species",   

    # Group 234 = Volume per Species (Raw units)
    # Note: You usually need to divide this by 100 or 1000 to get m3.
    # Check the documentation or compare with PDF report.
    (234, 1): "volume_per_species",  

    # --- 8. Matrices (Raw Data) ---
    (201, 1): "matrix_log_count",    # The massive list of counts
    (202, 1): "matrix_volume",       # The massive list of volumes
}

# --- Andmetüübid (Data Types) ---
# See aitab parseril otsustada, kas jätta väärtus stringiks 
# või teha numbriks.
# 'int': Täisarv
# 'float': Ujukomaarv
# 'list_str': Nimekiri stringidest (eraldatud reavahetusega)
# 'list_int': Nimekiri numbritest (eraldatud tühikuga)

PRI_VARIABLE_MAP = {
    # --- 1. Header & System Info ---
    (1, 2): "file_type",             # e.g., PRI
    (1, 3): "character_set",         # e.g., iso-8859-15
    (1, 4): "file_version",
    (2, 2): "system_identity",       # e.g., LUUA.hrv.env
    (2, 5): "setup_file",            # e.g., FIMMMASETUS1506.SPP
    (2, 6): "country_version",       # e.g., FI_versio...
    (3, 1): "machine_id",            # e.g., 0000000001
    (3, 5): "machine_manufacturer",  # e.g., Komatsu Forest
    (3, 6): "machine_model",         # e.g., 931-3
    (3, 8): "head_model",            # e.g., C93
    (5, 1): "software_version_1",    # e.g., MaxiXT 1.8.X...
    (5, 2): "software_version_2",

    # --- 2. Dates (Instruction Validity) ---
    (11, 4): "creation_date",        # YYYYMMDDHHMMSS
    (12, 4): "modification_date",    # e.g., 20240507...
    (13, 4): "valid_from_date",      

    # --- 3. Location / Object ---
    (21, 1): "contract_number",      # e.g., 1122
    (21, 2): "operator_id",          # e.g., 12345
    (21, 3): "site_name",            # e.g., L75 e 9 LR
    (21, 5): "object_status",        # 0 = Not started/Active

    # --- 4. Species Definitions (Standard) ---
    (120, 1): "species_names",       # List: MÄND, KUUSK...
    (120, 3): "species_ids",         # List: 1, 2, 3...

    # --- 5. Product Definitions (Standard) ---
    (121, 1): "product_names",       # List: MA palk, MA paber...
    (121, 2): "product_species_map", # Maps products to species IDs
    (121, 4): "product_modify_date", 
    (121, 6): "product_group_ids",

    # --- 6. Bucking Instructions (The "Rules") ---
    # Group 131 is the core Price Matrix (Value per diameter/length)
    (131, 1): "price_matrix_values", 
    
    # Group 132 defines the length classes (columns of the matrix)
    (132, 1): "length_classes",      # e.g., 300, 330, 360... (cm)
    
    # Group 134 defines limitation matrices (forced cuts)
    (134, 1): "limit_matrix_min",    
    (134, 2): "limit_matrix_max",

    # Group 141-143: Distribution and Quality
    (141, 1): "distribution_matrix", # Target distribution percentages
    (142, 1): "permitted_matrix",    # Allowed diameter/length combos
    (143, 1): "quality_labels",      # e.g., A, B, C or 1, 2, 3

    # --- 7. Production Totals (Present in this PRI) ---
    # PRI files sometimes track current production status
    (221, 1): "current_total_stems", # Value: 3287
    (290, 1): "running_volume_cnt",  # Accumulating volume/counter

    # --- 8. Manufacturer Specific (Komatsu/MaxiXT) ---
    # These groups (1-300, 300-600) contain the detailed
    # fine-tuning parameters for the bucking computer.
    (112, 1): "color_marking_1",
    (113, 1): "color_marking_2",
    
    # Common Komatsu Matrix Extensions (observed in file)
    # These usually correspond to specific bucking parameters per species
    (301, 40): "matrix_ext_301",
    (302, 40): "matrix_ext_302",
    (303, 40): "matrix_ext_303",
    (341, 1): "bucking_param_set_1",
    (342, 1): "bucking_param_set_2",
    (343, 1): "bucking_param_set_3",
    (371, 1): "bucking_param_set_4",
    (372, 1): "bucking_param_set_5",
    (402, 1): "bucking_param_set_6",
    (432, 1): "bucking_param_set_7",
    (492, 1): "bucking_param_set_8",
}

PRD_DATA_TYPES = {
    "start_date": "str",
    "end_date": "str",
    "total_stems": "int",
    "species_names": "list_str",
    "species_ids": "list_int",
    "product_names": "list_str",
    "diameter_classes": "list_int",
    "length_classes": "list_int",
    "stems_per_species": "list_int",
    "volume_per_species": "list_int", # Keep as int for now, format in frontend
    "matrix_log_count": "list_int",
}