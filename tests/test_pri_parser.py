import pytest
import pandas as pd
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from stanford_parser.stanford_classic.pri_parser import PRIParser


class TestPRIParser:
    @pytest.fixture
    def sample_pri_file(self):
        fixtures_dir = Path(__file__).parent / "fixtures"
        pri_file = fixtures_dir / "toy_test.pri"
        if not pri_file.exists():
            pytest.skip(f"Test file {pri_file} not found. Add a toy_test.pri file to tests/fixtures/")
        return str(pri_file)
    
    def test_parse_all(self, sample_pri_file):
        parser = PRIParser(sample_pri_file)
        data = parser.parse()
        
        assert isinstance(data, dict)
        expected_keys = [
            'header', 'machine', 'objects', 'buyer_vendor', 'calibration',
            'apt_history', 'species_groups', 'products', 'price_matrices',
            'operators', 'production_statistics', 'log_codes', 'tree_codes',
            'additional_info', 'logs'
        ]
        for key in expected_keys:
            assert key in data
            assert isinstance(data[key], pd.DataFrame)
    
    def test_parse_header(self, sample_pri_file):
        parser = PRIParser(sample_pri_file)
        header_df = parser._parse_header()
        
        assert isinstance(header_df, pd.DataFrame)
        assert not header_df.empty
        assert len(header_df) == 1
        
        expected_columns = [
            'creation_date', 'modification_date', 'valid_from_date',
            'start_date', 'application_version'
        ]
        for col in expected_columns:
            assert col in header_df.columns
        
        row = header_df.iloc[0]
        assert row['creation_date'] == '20240601080000'
        assert row['modification_date'] == ''
        assert row['valid_from_date'] == ''
        assert row['start_date'] == ''
        assert row['application_version'] == ''
    
    def test_parse_machine(self, sample_pri_file):
        parser = PRIParser(sample_pri_file)
        machine_df = parser._parse_machine()
        
        assert isinstance(machine_df, pd.DataFrame)
        assert not machine_df.empty
        assert len(machine_df) == 1
        
        expected_columns = [
            'machine_id', 'machine_base_manufacturer', 'machine_base_model',
            'machine_serial', 'head_model'
        ]
        for col in expected_columns:
            assert col in machine_df.columns
        
        row = machine_df.iloc[0]
        assert row['machine_id'] == 'TOY_MACHINE_01'
        assert row['machine_base_manufacturer'] == ''
        assert row['machine_base_model'] == ''
        assert row['machine_serial'] == ''
        assert row['head_model'] == ''
    
    def test_parse_objects(self, sample_pri_file):
        parser = PRIParser(sample_pri_file)
        objects_df = parser._parse_objects()
        
        assert isinstance(objects_df, pd.DataFrame)
        assert not objects_df.empty
        assert len(objects_df) == 1
        
        expected_columns = [
            'contract_number', 'contract_number_swedish', 'operator_id',
            'object_name', 'object_status'
        ]
        for col in expected_columns:
            assert col in objects_df.columns
        
        row = objects_df.iloc[0]
        assert row['contract_number'] == ''
        assert row['contract_number_swedish'] == ''
        assert row['operator_id'] == ''
        assert row['object_name'] == 'ToySite 1'
        assert row['object_status'] == ''
    
    def test_parse_species_groups(self, sample_pri_file):
        parser = PRIParser(sample_pri_file)
        species_df = parser._parse_species_groups()
        
        assert isinstance(species_df, pd.DataFrame)
        assert species_df.empty
    
    def test_parse_products(self, sample_pri_file):
        parser = PRIParser(sample_pri_file)
        products_df = parser._parse_products()
        
        assert isinstance(products_df, pd.DataFrame)
        assert products_df.empty
    
    def test_parser_initialization(self, sample_pri_file):
        parser = PRIParser(sample_pri_file)
        
        assert parser.file_path == sample_pri_file
        assert parser._raw_data is None
    
    def test_load_raw_data(self, sample_pri_file):
        parser = PRIParser(sample_pri_file)
        raw_data = parser._load_raw_data()
        
        assert raw_data is not None
        assert isinstance(raw_data, dict)
        
        assert (1, 2) in raw_data
        assert raw_data[(1, 2)] == 'PRI'
        assert (1, 3) in raw_data
        assert raw_data[(1, 3)] == 'iso-8859-15'
        assert (3, 1) in raw_data
        assert raw_data[(3, 1)] == 'TOY_MACHINE_01'
        assert (11, 4) in raw_data
        assert raw_data[(11, 4)] == '20240601080000'
        assert (21, 3) in raw_data
        assert raw_data[(21, 3)] == 'ToySite 1'
        assert (256, 1) in raw_data
        assert raw_data[(256, 1)] == '121 141 250'
        assert (257, 1) in raw_data
        assert raw_data[(257, 1)] == '1 1 150 2 1 45 1 2 200'
        assert (500, 1) in raw_data
        assert raw_data[(500, 1)] == '130'
    
    def test_get_value_helper(self, sample_pri_file):
        parser = PRIParser(sample_pri_file)
        
        assert parser._get_value(1, 2) == 'PRI'
        assert parser._get_value(1, 3) == 'iso-8859-15'
        assert parser._get_value(3, 1) == 'TOY_MACHINE_01'
        assert parser._get_value(11, 4) == '20240601080000'
        assert parser._get_value(21, 3) == 'ToySite 1'
        assert parser._get_value(256, 1) == '121 141 250'
        assert parser._get_value(257, 1) == '1 1 150 2 1 45 1 2 200'
        assert parser._get_value(500, 1) == '130'
        assert parser._get_value(999, 999, 'default') == 'default'
        assert parser._get_value(999, 999) is None
    
    def test_parse_list(self, sample_pri_file):
        parser = PRIParser(sample_pri_file)
        
        assert parser._parse_list('1 2 3') == [1, 2, 3]
        assert parser._parse_list('10 20 30', int) == [10, 20, 30]
        assert parser._parse_list('1.5 2.5 3.5', float) == [1.5, 2.5, 3.5]
        assert parser._parse_list('') == []
        assert parser._parse_list(None) == []
    
    def test_parse_multiline_list(self, sample_pri_file):
        parser = PRIParser(sample_pri_file)
        
        assert parser._parse_multiline_list('line1\nline2\nline3') == ['line1', 'line2', 'line3']
        assert parser._parse_multiline_list('single') == ['single']
        assert parser._parse_multiline_list('') == []
        assert parser._parse_multiline_list(None) == []
    
    def test_invalid_file_path(self):
        parser = PRIParser("non_existent_file.pri")
        with pytest.raises(FileNotFoundError):
            parser._load_raw_data()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
