import pytest
import pandas as pd
import xml.etree.ElementTree as ET
import sys
import os
from pathlib import Path

# Add project root to Python path 
project_root = Path(__file__).parent.parent  
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from stanford_parser.stanford_2010.hpr_parser import HPRParser


class TestHPRParser:
    @pytest.fixture
    def sample_hpr_file(self):
        fixtures_dir = Path(__file__).parent / "fixtures"
        hpr_file = fixtures_dir / "toy_test.hpr"
        if not hpr_file.exists():
            pytest.skip(f"Test file {hpr_file} not found. Add a toy_test.hpr file to tests/fixtures/")
        return str(hpr_file)
    
    
    def test_parse_all(self, sample_hpr_file):
        parser = HPRParser(sample_hpr_file)
        data = parser.parse_all()
        
        # Check that parse_all returns a dictionary with expected keys
        assert isinstance(data, dict)
        expected_keys = ['header', 'machine', 'species_groups', 'products', 'objects', 'stems', 'logs']
        for key in expected_keys:
            assert key in data
            assert isinstance(data[key], pd.DataFrame)
    
    def test_parse_header(self, sample_hpr_file):
        parser = HPRParser(sample_hpr_file)
        header_df = parser._parse_header()
        
        assert isinstance(header_df, pd.DataFrame)
        assert not header_df.empty
        assert len(header_df) == 1
        
        # Check expected header columns
        expected_columns = [
            'creation_date', 'modification_date', 'application_version_created',
            'application_version_modified', 'country_code'
        ]
        for col in expected_columns:
            assert col in header_df.columns
        
        # Check ALL header data from toy file
        row = header_df.iloc[0]
        # Dates are formatted from ISO to DD-MM-YYYY HH:MM
        assert row['creation_date'] == '01-06-2024 08:00'
        assert row['modification_date'] == '01-06-2024 16:00'
        assert row['application_version_created'] == 'ToyMaker 1.0'
        assert row['application_version_modified'] == 'ToyMaker 1.0'
        assert row['country_code'] == '233'
    
    def test_parse_machine(self, sample_hpr_file):
        parser = HPRParser(sample_hpr_file)
        machine_df = parser._parse_machine()
        
        assert isinstance(machine_df, pd.DataFrame)
        assert not machine_df.empty
        assert len(machine_df) == 1
        
        # Check expected machine columns
        expected_columns = [
            'machine_category', 'machine_key', 'machine_user_id',
            'machine_head_manufacturer', 'machine_head_model',
            'operator_key', 'operator_first_name', 'operator_last_name'
        ]
        for col in expected_columns:
            assert col in machine_df.columns
        
        # Check ALL machine data from toy file
        row = machine_df.iloc[0]
        assert row['machine_category'] == 'Harvester'
        assert row['machine_key'] == '1234567890'
        assert row['machine_user_id'] == 'TOY_MACHINE_01'
        assert row['machine_head_manufacturer'] == 'ToyHead'
        assert row['machine_head_model'] == 'TH-500'
        assert row['operator_key'] == '999'
        assert row['operator_first_name'] == 'Test'
        assert row['operator_last_name'] == 'Driver'
    
    def test_parse_objects(self, sample_hpr_file):
        parser = HPRParser(sample_hpr_file)
        objects_df = parser._parse_objects()
        
        assert isinstance(objects_df, pd.DataFrame)
        assert not objects_df.empty
        assert len(objects_df) == 1
        
        # Check expected object columns
        expected_columns = [
            'object_key', 'object_name', 'sub_object_key'
        ]
        for col in expected_columns:
            assert col in objects_df.columns
        
        # Check ALL object data from toy file
        row = objects_df.iloc[0]
        assert row['object_key'] == 'TOY_SITE_01'
        assert row['object_name'] == 'Toy Forest Stand'
        assert row['sub_object_key'] == 'Sub_01'
    
    def test_parse_stems(self, sample_hpr_file):
        parser = HPRParser(sample_hpr_file)
        stems_df = parser._parse_stems()
        
        assert isinstance(stems_df, pd.DataFrame)
        assert not stems_df.empty
        assert len(stems_df) == 1
        
        # Check expected stem columns
        expected_columns = [
            'stem_key', 'object_key', 'sub_object_key', 'species_group_key',
            'stem_number', 'dbh'
        ]
        for col in expected_columns:
            assert col in stems_df.columns
        
        # Check ALL stem data from toy file
        row = stems_df.iloc[0]
        assert row['stem_key'] == 'STEM_001'
        assert row['object_key'] == 'TOY_SITE_01'
        assert row['sub_object_key'] == 'Sub_01'
        assert row['species_group_key'] == '1'
        assert row['stem_number'] == '1'
        assert row['dbh'] == '250'
    
    def test_parse_logs(self, sample_hpr_file):
        parser = HPRParser(sample_hpr_file)
        logs_df = parser._parse_logs()
        
        assert isinstance(logs_df, pd.DataFrame)
        assert not logs_df.empty
        assert len(logs_df) == 1
        
        # Check expected log columns
        expected_columns = [
            'stem_key', 'log_key', 'product_key', 'volume_price_m3',
            'volume_sob_m3', 'volume_sub_m3', 'cutting_reason', 'start_pos',
            'log_length', 'diameter_butt_ob', 'diameter_butt_ub',
            'diameter_mid_ob', 'diameter_mid_ub', 'diameter_top_ob', 'diameter_top_ub'
        ]
        for col in expected_columns:
            assert col in logs_df.columns
        
        # Check ALL log data from toy file
        row = logs_df.iloc[0]
        assert row['stem_key'] == 'STEM_001'
        assert row['log_key'] == '1'
        assert row['product_key'] == '1'
        assert row['volume_sub_m3'] == '0.150'
        assert row['log_length'] == '450'
        assert row['diameter_top_ub'] == '200'
    
    def test_parse_species_groups(self, sample_hpr_file):
        parser = HPRParser(sample_hpr_file)
        species_df = parser._parse_species_groups()
        
        assert isinstance(species_df, pd.DataFrame)
        # Species groups are empty in toy file (not defined)
        assert species_df.empty
    
    def test_parse_products(self, sample_hpr_file):
        parser = HPRParser(sample_hpr_file)
        products_df = parser._parse_products()
        
        assert isinstance(products_df, pd.DataFrame)
        # Products are empty in toy file (not defined)
        assert products_df.empty
    
    def test_get_text_helper(self, sample_hpr_file):
        parser = HPRParser(sample_hpr_file)
        header_node = parser.root.find('s:HarvestedProductionHeader', parser.ns)
        
        # Test that _get_text extracts text correctly
        creation_date = parser._get_text(header_node, 's:CreationDate')
        assert creation_date is not None
        assert isinstance(creation_date, str)
        
        # Test that _get_text returns empty string for non-existent tags
        non_existent = parser._get_text(header_node, 's:NonExistentTag')
        assert non_existent == ''
    
    def test_units_extraction(self, sample_hpr_file):
        parser = HPRParser(sample_hpr_file)
        
        # Check that units are set
        assert parser.units['length'] == 'cm'
        assert parser.units['diameter'] == 'mm'
        assert parser.units['volume'] == 'm3'
    
    def test_invalid_file_path(self):
        with pytest.raises(FileNotFoundError):
            HPRParser("non_existent_file.hpr")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
