import pandas as pd
from s4d_tools.utils.date_utils import format_date

from .utils.helpers import (
    get_value,
    load_raw_data,
    normalize_value,
    parse_list,
    parse_multiline_list,
)


class PRDParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self._raw_data = None

    def _load_raw_data(self):
        if self._raw_data is None:
            self._raw_data = load_raw_data(self.file_path, merge_duplicate_keys=True)
        return self._raw_data

    def _get_value(self, group_id, variable_id, default=None):
        if self._raw_data is None:
            self._load_raw_data()
        return get_value(self._raw_data, group_id, variable_id, default)

    def _parse_header(self):
        header_data = []

        creation_date_raw = normalize_value(self._get_value(11, 4, ''), list_join="\n")
        modification_date_raw = normalize_value(self._get_value(12, 4, ''), list_join="\n")
        application_version_created = normalize_value(self._get_value(2, 2, ''), list_join="\n")
        application_version_modified = normalize_value(self._get_value(2, 2, ''), list_join="\n")

        creation_date = format_date(creation_date_raw) if creation_date_raw else ''
        modification_date = format_date(modification_date_raw) if modification_date_raw else ''

        header_data.append({
            'creation_date': creation_date,
            'modification_date': modification_date,
            'application_version_created': application_version_created,
            'application_version_modified': application_version_modified
        })

        return pd.DataFrame(header_data)

    def _parse_machine(self):
        machine_data = []

        machine_base_manufacturer = normalize_value(self._get_value(3, 5, ''), list_join="\n")
        machine_base_model = normalize_value(self._get_value(3, 6, ''), list_join="\n")

        machine_data.append({
            'machine_base_manufacturer': machine_base_manufacturer,
            'machine_base_model': machine_base_model
        })

        return pd.DataFrame(machine_data)

    def _parse_objects(self):
        objects_data = []

        contract_id = normalize_value(self._get_value(21, 1, ''), list_join="\n")
        sub_object_name = normalize_value(self._get_value(21, 3, ''), list_join="\n")
        site_name = sub_object_name.split(' ')[0]

        objects_data.append({
            'contract_number': contract_id,
            'object_name': site_name
        })

        return pd.DataFrame(objects_data)

    def _parse_species_groups(self):
        species_groups_data = []

        species_names = parse_multiline_list(self._get_value(120, 1, ''))
        species_ids = parse_list(self._get_value(120, 3, ''), int)

        for name, species_id in zip(species_names, species_ids):
            species_groups_data.append({
                'species_group_key': str(species_id),
                'species_group_name': name
            })

        return pd.DataFrame(species_groups_data)

    def _parse_products(self):
        products_data = []

        product_names = parse_multiline_list(self._get_value(121, 1, ''))

        for idx, product_name in enumerate(product_names, start=1):
            products_data.append({
                'product_key': str(idx),
                'product_name': product_name
            })

        return pd.DataFrame(products_data)

    def _parse_statistics(self):
        statistics_data = []

        total_stems = normalize_value(self._get_value(221, 1, ''), list_join="\n")
        stems_per_species = parse_list(self._get_value(222, 1, ''), int)

        species_names = parse_multiline_list(self._get_value(120, 1, ''))

        if species_names or stems_per_species:
            reference_length = max(
                len(species_names) if species_names else 0,
                len(stems_per_species) if stems_per_species else 0
            )
            if species_names:
                species_names = (species_names + [''] * (reference_length - len(species_names)))[:reference_length]
            else:
                species_names = [''] * reference_length

            if stems_per_species:
                stems_per_species = (stems_per_species + [0] * (reference_length - len(stems_per_species)))[:reference_length]
            else:
                stems_per_species = [0] * reference_length

        total_stems_int = int(total_stems) if total_stems and total_stems.isdigit() else 0
        statistics_data.append({
            'total_stems': total_stems_int,
            'stems_per_species': stems_per_species,
            'species_names': species_names
        })

        return pd.DataFrame(statistics_data)

    def parse(self):
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
