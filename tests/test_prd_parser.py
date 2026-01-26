import pytest
import pandas as pd
import sys
from pathlib import Path

# Add project root to Python path 
project_root = Path(__file__).parent.parent  
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from stanford_parser.stanford_classic.prd_parser import PRDParser


class TestPRDParser:
    @pytest.fixture
    def sample_prd_file(self):
        fixtures_dir = Path(__file__).parent / "fixtures"
        prd_file = fixtures_dir / "toy_test.prd"
        if not prd_file.exists():
            pytest.skip(f"Test file {prd_file} not found. Add a toy_test.prd file to tests/fixtures/")
        return str(prd_file)
    
    def test_parse_all(self, sample_prd_file):
        parser = PRDParser(sample_prd_file)
        data = parser.parse()
        
        assert isinstance(data, dict)
        expected_keys = ['header', 'machine', 'objects', 'species_groups', 'products', 'statistics']
        for key in expected_keys:
            assert key in data
            assert isinstance(data[key], pd.DataFrame)
    
    def test_parse_header(self, sample_prd_file):
        parser = PRDParser(sample_prd_file)
        header_df = parser._parse_header()
        
        assert isinstance(header_df, pd.DataFrame)
        assert not header_df.empty
        assert len(header_df) == 1
        
        expected_columns = [
            'creation_date', 'modification_date', 'application_version_created',
            'application_version_modified'
        ]
        for col in expected_columns:
            assert col in header_df.columns
        
        row = header_df.iloc[0]
        assert row['creation_date'] == '01-06-2024 08:00'
        assert row['modification_date'] == '01-06-2024 16:00'
        assert row['application_version_created'] == ''
        assert row['application_version_modified'] == ''
    
    def test_parse_machine(self, sample_prd_file):
        parser = PRDParser(sample_prd_file)
        machine_df = parser._parse_machine()
        
        assert isinstance(machine_df, pd.DataFrame)
        assert not machine_df.empty
        assert len(machine_df) == 1
        
        expected_columns = [
            'machine_base_manufacturer', 'machine_base_model'
        ]
        for col in expected_columns:
            assert col in machine_df.columns
        
        row = machine_df.iloc[0]
        assert row['machine_base_manufacturer'] == 'ToyFactory'
        assert row['machine_base_model'] == '' 
    
    def test_parse_objects(self, sample_prd_file):
        parser = PRDParser(sample_prd_file)
        objects_df = parser._parse_objects()
        
        assert isinstance(objects_df, pd.DataFrame)
        assert not objects_df.empty
        assert len(objects_df) == 1
        
        expected_columns = [
            'contract_number', 'object_name'
        ]
        for col in expected_columns:
            assert col in objects_df.columns
        
        row = objects_df.iloc[0]
        assert row['contract_number'] == '9999'
        assert row['object_name'] == 'ToySite'
    
    def test_parse_species_groups(self, sample_prd_file):
        parser = PRDParser(sample_prd_file)
        species_df = parser._parse_species_groups()
        
        assert isinstance(species_df, pd.DataFrame)
        assert not species_df.empty
        assert len(species_df) == 2
        
        expected_columns = [
            'species_group_key', 'species_group_name'
        ]
        for col in expected_columns:
            assert col in species_df.columns
        
        assert species_df.iloc[0]['species_group_key'] == '1'
        assert species_df.iloc[0]['species_group_name'] == 'Pine'
        assert species_df.iloc[1]['species_group_key'] == '2'
        assert species_df.iloc[1]['species_group_name'] == 'Spruce'
    
    def test_parse_products(self, sample_prd_file):
        parser = PRDParser(sample_prd_file)
        products_df = parser._parse_products()
        
        assert isinstance(products_df, pd.DataFrame)
        assert not products_df.empty
        assert len(products_df) == 2
        
        expected_columns = [
            'product_key', 'product_name'
        ]
        for col in expected_columns:
            assert col in products_df.columns
        
        assert products_df.iloc[0]['product_key'] == '1'
        assert products_df.iloc[0]['product_name'] == 'Sawlog'
        assert products_df.iloc[1]['product_key'] == '2'
        assert products_df.iloc[1]['product_name'] == 'Pulp'
    
    def test_parse_statistics(self, sample_prd_file):
        parser = PRDParser(sample_prd_file)
        statistics_df = parser._parse_statistics()
        
        assert isinstance(statistics_df, pd.DataFrame)
        assert not statistics_df.empty
        assert len(statistics_df) == 1
        
        expected_columns = [
            'total_stems', 'stems_per_species', 'species_names'
        ]
        for col in expected_columns:
            assert col in statistics_df.columns
        
        row = statistics_df.iloc[0]
        assert row['total_stems'] == 50
        assert row['stems_per_species'] == [30, 20]
        assert row['species_names'] == ['Pine', 'Spruce']
    
    def test_parser_initialization(self, sample_prd_file):
        parser = PRDParser(sample_prd_file)
        
        assert parser.file_path == sample_prd_file
        assert parser._raw_data is None
    
    def test_load_raw_data(self, sample_prd_file):
        parser = PRDParser(sample_prd_file)
        raw_data = parser._load_raw_data()
        
        assert raw_data is not None
        assert isinstance(raw_data, dict)
        
        assert (1, 2) in raw_data
        assert raw_data[(1, 2)] == 'PRD'
        assert (1, 3) in raw_data
        assert raw_data[(1, 3)] == 'iso-8859-15'
        assert (3, 1) in raw_data
        assert raw_data[(3, 1)] == 'TOY_MACHINE_01'
        assert (3, 5) in raw_data
        assert raw_data[(3, 5)] == 'ToyFactory'
        assert (11, 4) in raw_data
        assert raw_data[(11, 4)] == '20240601080000'
        assert (12, 4) in raw_data
        assert raw_data[(12, 4)] == '20240601160000'
        assert (21, 1) in raw_data
        assert raw_data[(21, 1)] == '9999'
        assert (21, 3) in raw_data
        assert raw_data[(21, 3)] == 'ToySite 1'
        assert (120, 1) in raw_data
        assert raw_data[(120, 1)] == 'Pine\nSpruce'
        assert (120, 3) in raw_data
        assert raw_data[(120, 3)] == '1 2'
        assert (121, 1) in raw_data
        assert raw_data[(121, 1)] == 'Sawlog\nPulp'
        assert (221, 1) in raw_data
        assert raw_data[(221, 1)] == '50'
        assert (222, 1) in raw_data
        assert raw_data[(222, 1)] == '30 20'
        assert (249, 1) in raw_data
        assert raw_data[(249, 1)] == '500 200'
        assert (249, 5) in raw_data
        assert raw_data[(249, 5)] == '100 50'
    
    def test_get_value_helper(self, sample_prd_file):
        parser = PRDParser(sample_prd_file)
        
        assert parser._get_value(1, 2) == 'PRD'
        assert parser._get_value(1, 3) == 'iso-8859-15'
        assert parser._get_value(3, 1) == 'TOY_MACHINE_01'
        assert parser._get_value(3, 5) == 'ToyFactory'
        assert parser._get_value(11, 4) == '20240601080000'
        assert parser._get_value(12, 4) == '20240601160000'
        assert parser._get_value(21, 1) == '9999'
        assert parser._get_value(21, 3) == 'ToySite 1'
        assert parser._get_value(120, 1) == 'Pine\nSpruce'
        assert parser._get_value(120, 3) == '1 2'
        assert parser._get_value(121, 1) == 'Sawlog\nPulp'
        assert parser._get_value(221, 1) == '50'
        assert parser._get_value(222, 1) == '30 20'
        assert parser._get_value(249, 1) == '500 200'
        assert parser._get_value(249, 5) == '100 50'
        assert parser._get_value(999, 999, 'default') == 'default'
        assert parser._get_value(999, 999) is None
    
    def test_invalid_file_path(self):
        parser = PRDParser("non_existent_file.prd")
        with pytest.raises(FileNotFoundError):
            parser._load_raw_data()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
