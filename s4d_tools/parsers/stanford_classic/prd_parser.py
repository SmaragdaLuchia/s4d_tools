import pandas as pd
from s4d_tools.utils.date_utils import format_date
from .constants import DEFAULT_ENCODING, BLOCK_SEPARATOR

class PRDParser:
    """Parses Production reports (Summaries)"""
    def __init__(self, file_path):
        self.file_path = file_path
        self._raw_data = None

    def _load_raw_data(self):
        """Load and parse raw PRD file data into dictionary."""
        if self._raw_data is None:
            with open(self.file_path, 'r', encoding=DEFAULT_ENCODING) as file:
                content = file.read()
                data = content.split(BLOCK_SEPARATOR)

                data_dict = {}

                for data_item in data:
                    parts = data_item.strip().split(maxsplit=2)

                    if len(parts) >= 2:
                        group_id = int(parts[0])
                        variable_id = int(parts[1])
                        value = parts[2] if len(parts) > 2 else None

                        data_dict[(group_id, variable_id)] = value

                self._raw_data = data_dict
        return self._raw_data

    def _get_value(self, group_id, variable_id, default=None):
        """Helper method to get value from raw data by group and variable ID."""
        if self._raw_data is None:
            self._load_raw_data()
        return self._raw_data.get((group_id, variable_id), default)

    def _parse_header(self):
        """
        Private method to parse header information from PRD file.
        Returns a DataFrame with header metadata.
        """
        header_data = []
        
        creation_date_raw = self._get_value(11, 4, '')  # start_date
        modification_date_raw = self._get_value(12, 4, '')  # end_date
        application_version_created = self._get_value(2, 2, '')  # software_version
        application_version_modified = self._get_value(2, 2, '')  # software_version
        
        # Format dates from YYYYMMDDHHMMSS to DD-MM-YYYY HH:MM
        creation_date = format_date(creation_date_raw) if creation_date_raw else ''
        modification_date = format_date(modification_date_raw) if modification_date_raw else ''
        
        # Include all fields that CAN be filled from PRD (even if empty)
        # Removed: country_code (never in PRD)
        header_data.append({
            'creation_date': creation_date,
            'modification_date': modification_date,
            'application_version_created': application_version_created,
            'application_version_modified': application_version_modified
        })
        
        return pd.DataFrame(header_data)

    def _parse_machine(self):
        """
        Private method to parse machine information from PRD file.
        Returns a DataFrame with machine details.
        """
        machine_data = []
        
        machine_base_manufacturer = self._get_value(3, 5, '')
        machine_base_model = self._get_value(3, 6, '')

        machine_data.append({
            'machine_base_manufacturer': machine_base_manufacturer,
            'machine_base_model': machine_base_model
        })
        
        return pd.DataFrame(machine_data)

    def _parse_objects(self):
        """
        Private method to parse object/location information from PRD file.
        Returns a DataFrame with object and sub-object information.
        """
        objects_data = []
        
        contract_id = self._get_value(21, 1, '')
        sub_object_name = self._get_value(21, 3, '')
        site_name = sub_object_name.split(' ')[0]
        
        

        objects_data.append({
            'contract_number': contract_id,
            'object_name': site_name
        })
        
        return pd.DataFrame(objects_data)

    def _parse_species_groups(self):
        """
        Private method to parse species group definitions from PRD file.
        Returns a DataFrame with species group information.
        """
        species_groups_data = []
        
        species_names_str = self._get_value(120, 1, '')
        species_ids_str = self._get_value(120, 3, '')
        
        # Parse species names and IDs
        if species_names_str:
            species_names = [name.strip() for name in species_names_str.split('\n') if name.strip()]
        else:
            species_names = []
            
        if species_ids_str:
            try:
                species_ids = [int(x.strip()) for x in species_ids_str.split() if x.strip()]
            except:
                species_ids = []
        else:
            species_ids = []
        
        for name, species_id in zip(species_names, species_ids):
            species_groups_data.append({
                'species_group_key': str(species_id),
                'species_group_name': name
            })
        
        return pd.DataFrame(species_groups_data)

    def _parse_products(self):
        """
        Private method to parse product definitions from PRD file.
        Returns a DataFrame with product information.
        """
        products_data = []
        
        product_names_str = self._get_value(121, 1, '')
        
        if product_names_str:
            product_names = [name.strip() for name in product_names_str.split('\n') if name.strip()]
        else:
            product_names = []
        
        for idx, product_name in enumerate(product_names, start=1):
            products_data.append({
                'product_key': str(idx),
                'product_name': product_name
            })
        
        return pd.DataFrame(products_data)

    def _parse_statistics(self):
        """
        Private method to parse production statistics from PRD file.
        Returns a DataFrame with production statistics.
        """
        statistics_data = []
        
        total_stems = self._get_value(221, 1, '')
        stems_per_species_str = self._get_value(222, 1, '')
        
        # Parse stems per species
        stems_per_species = []
        if stems_per_species_str:
            try:
                stems_per_species = [int(x.strip()) for x in stems_per_species_str.split() if x.strip()]
            except:
                pass
        
        # Get species names for matching
        species_names_str = self._get_value(120, 1, '')
        species_names = []
        if species_names_str:
            species_names = [name.strip() for name in species_names_str.split('\n') if name.strip()]
        
        # Ensure all lists have the same length to prevent DataFrame creation errors
        # Use the maximum length of both lists as reference to prevent data loss
        # Pad shorter lists with default values 
        if species_names or stems_per_species:
            reference_length = max(
                len(species_names) if species_names else 0,
                len(stems_per_species) if stems_per_species else 0
            )
            # Pad shorter lists, never truncate longer ones (preserves all data)
            if species_names:
                species_names = (species_names + [''] * (reference_length - len(species_names)))[:reference_length]
            else:
                species_names = [''] * reference_length
            
            if stems_per_species:
                stems_per_species = (stems_per_species + [0] * (reference_length - len(stems_per_species)))[:reference_length]
            else:
                stems_per_species = [0] * reference_length
        
        # Include all fields that CAN be filled from PRD (even if empty)
        total_stems_int = int(total_stems) if total_stems and total_stems.isdigit() else 0
        statistics_data.append({
            'total_stems': total_stems_int,
            'stems_per_species': stems_per_species,
            'species_names': species_names
        })

        return pd.DataFrame(statistics_data)

    def parse(self):
        """
        Parses the file and returns a dictionary containing DataFrames:
        'header', 'machine', 'objects', 'species_groups', 'products', 'statistics'.
        """
        self._load_raw_data()
        
        return {
            'header': self._parse_header(),
            'machine': self._parse_machine(),
            'objects': self._parse_objects(),
            'species_groups': self._parse_species_groups(),
            'products': self._parse_products(),
            'statistics': self._parse_statistics()
        }

    def visualize(self, data=None):
        """
        Visualizes the parsed PRD data in a readable format.
        If data is None, calls parse() first.
        """
        if data is None:
            data = self.parse()
        
        print("=" * 80)
        print("PRD FILE VISUALIZATION")
        print("=" * 80)
        
        for key, df in data.items():
            print(f"\n--- {key.upper()} ---")
            if df.empty:
                print(f"  (No {key} data)")
            else:
                print(df.to_string())
                print(f"\n  Shape: {df.shape[0]} rows × {df.shape[1]} columns")
                
                # Special formatting for statistics
                if key == 'statistics' and not df.empty:
                    stats_row = df.iloc[0]
                    if 'stems_per_species' in stats_row and 'species_names' in stats_row:
                        species_names = stats_row['species_names']
                        stems_per_species = stats_row['stems_per_species']
                        
                        if species_names and stems_per_species:
                            print("\n  Stems per Species:")
                            for name, count in zip(species_names, stems_per_species):
                                print(f"    {name}: {count}")

        print("\n" + "=" * 80)


