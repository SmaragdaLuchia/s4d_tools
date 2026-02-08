import xml.etree.ElementTree as ET
import pandas as pd
from .._utils import format_date


class HPRParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.tree = ET.parse(file_path)
        self.root = self.tree.getroot()
        self.ns = {'s': 'urn:skogforsk:stanford2010'}
        self.units = {
            'length': self.root.attrib.get('lengthUnit', 'cm'), 
            'diameter': self.root.attrib.get('diameterUnit', 'mm'),
            'volume': self.root.attrib.get('volumeUnit', 'm3')
        }

    def _get_text(self, node, tag):
        """
        Helper method to safely extract text from an XML node.
        Returns empty string if node is None or tag is not found.
        """
        if node is None:
            return ''
        found = node.find(tag, self.ns)
        return found.text if found is not None else ''

    def _parse_header(self):
        """
        Private method to parse header information from HPR file.
        Returns a DataFrame with header metadata.
        """
        header_data = []
        header_node = self.root.find('s:HarvestedProductionHeader', self.ns)
        
        creation_date_raw = self._get_text(header_node, 's:CreationDate')
        modification_date_raw = self._get_text(header_node, 's:ModificationDate')
        application_version_created = self._get_text(header_node, 's:ApplicationVersionCreated')
        application_version_modified = self._get_text(header_node, 's:ApplicationVersionModified')
        country_code = self._get_text(header_node, 's:CountryCode')

        # Format dates from ISO to DD-MM-YYYY HH:MM
        creation_date = format_date(creation_date_raw)
        modification_date = format_date(modification_date_raw)

        header_data.append({
            'creation_date': creation_date,
            'modification_date': modification_date,
            'application_version_created': application_version_created,
            'application_version_modified': application_version_modified,
            'country_code': country_code
        })
        
        return pd.DataFrame(header_data)

    def _parse_machine(self):
        """
        Private method to parse machine and operator information from HPR file.
        Returns a DataFrame with machine and operator details.
        """
        machine_data = []
        machine_node = self.root.find('s:Machine', self.ns)
        
        machine_category = machine_node.attrib.get('machineCategory', '') if machine_node is not None else ''
        machine_key = self._get_text(machine_node, 's:MachineKey')
        machine_user_id = self._get_text(machine_node, 's:MachineUserID')
        machine_owner_id = self._get_text(machine_node, 's:MachineOwnerID')
        machine_application_version = self._get_text(machine_node, 's:MachineApplicationVersion')
        machine_base_manufacturer = self._get_text(machine_node, 's:MachineBaseManufacturer')
        machine_base_model = self._get_text(machine_node, 's:MachineBaseModel')
        base_machine_manufacturer_id = self._get_text(machine_node, 's:BaseMachineManufacturerID')
        machine_head_manufacturer = self._get_text(machine_node, 's:MachineHeadManufacturer')
        machine_head_model = self._get_text(machine_node, 's:MachineHeadModel')
        
        # Operator information
        operator_def = machine_node.find('s:OperatorDefinition', self.ns) if machine_node is not None else None
        operator_key = self._get_text(operator_def, 's:OperatorKey')
        operator_user_id = self._get_text(operator_def, 's:OperatorUserID')
        contact_info = operator_def.find('s:ContactInformation', self.ns) if operator_def is not None else None
        operator_first_name = self._get_text(contact_info, 's:FirstName')
        operator_last_name = self._get_text(contact_info, 's:LastName')

        machine_data.append({
            'machine_category': machine_category,
            'machine_key': machine_key,
            'machine_user_id': machine_user_id,
            'machine_owner_id': machine_owner_id,
            'machine_application_version': machine_application_version,
            'machine_base_manufacturer': machine_base_manufacturer,
            'machine_base_model': machine_base_model,
            'base_machine_manufacturer_id': base_machine_manufacturer_id,
            'machine_head_manufacturer': machine_head_manufacturer,
            'machine_head_model': machine_head_model,
            'operator_key': operator_key,
            'operator_user_id': operator_user_id,
            'operator_first_name': operator_first_name,
            'operator_last_name': operator_last_name
        })
        
        return pd.DataFrame(machine_data)

    def _parse_species_groups(self):
        """
        Private method to parse species group definitions from HPR file.
        Returns a DataFrame with species group information including grading rules and bark function parameters.
        """
        species_groups_data = []
        species_groups = self.root.findall('.//s:SpeciesGroupDefinition', self.ns)
        
        for species_group in species_groups:
            species_group_key = self._get_text(species_group, 's:SpeciesGroupKey')
            modification_date_raw = self._get_text(species_group, 's:SpeciesGroupModificationDate')
            modification_date = format_date(modification_date_raw)
            species_group_user_id = species_group.find('s:SpeciesGroupUserID', self.ns)
            species_group_user_id_value = species_group_user_id.text if species_group_user_id is not None else ''
            species_group_user_id_agency = species_group_user_id.attrib.get('agency', '') if species_group_user_id is not None else ''
            species_group_name = self._get_text(species_group, 's:SpeciesGroupName')
            species_group_info = species_group.find('s:SpeciesGroupInfo', self.ns)
            species_group_info_value = species_group_info.text if species_group_info is not None and species_group_info.text else ''
            species_group_version = species_group.find('s:SpeciesGroupVersion', self.ns)
            species_group_version_value = species_group_version.text if species_group_version is not None else ''
            species_group_presentation_order = self._get_text(species_group, 's:SpeciesGroupPresentationOrder')
            dbh_height = self._get_text(species_group, 's:DBHHeight')
            
            # Parse Grades
            grades = species_group.find('s:Grades', self.ns)
            start_grade = self._get_text(grades, 's:StartGrade')
            mth_start_grade = self._get_text(grades, 's:MTHStartGrade')
            
            # Parse BarkFunction
            bark_function = species_group.find('s:BarkFunction', self.ns)
            bark_function_category = bark_function.attrib.get('barkFunctionCategory', '') if bark_function is not None else ''
            swedish_zacco = bark_function.find('s:SwedishZacco', self.ns) if bark_function is not None else None
            constant_a = self._get_text(swedish_zacco, 's:ConstantA')
            factor_b = self._get_text(swedish_zacco, 's:FactorB')
            
            species_groups_data.append({
                'species_group_key': species_group_key,
                'modification_date': modification_date,
                'species_group_user_id': species_group_user_id_value,
                'species_group_user_id_agency': species_group_user_id_agency,
                'species_group_name': species_group_name,
                'species_group_info': species_group_info_value,
                'species_group_version': species_group_version_value,
                'species_group_presentation_order': species_group_presentation_order,
                'dbh_height': dbh_height,
                'start_grade': start_grade,
                'mth_start_grade': mth_start_grade,
                'bark_function_category': bark_function_category,
                'bark_constant_a': constant_a,
                'bark_factor_b': factor_b
            })
        
        return pd.DataFrame(species_groups_data)

    def _parse_products(self):
        """
        Private method to parse product definitions from HPR file.
        Returns a DataFrame with product information.
        """
        products_data = []
        products = self.root.findall('.//s:ProductDefinition', self.ns)
        
        for product in products:
            product_key = self._get_text(product, 's:ProductKey')
            classified_product = product.find('s:ClassifiedProductDefinition', self.ns)
            product_name = self._get_text(classified_product, 's:ProductName')
            product_modification_date_raw = self._get_text(classified_product, 's:ModificationDate')
            product_modification_date = format_date(product_modification_date_raw)
            product_user_id = classified_product.find('s:ProductUserID', self.ns) if classified_product is not None else None
            product_user_id_value = product_user_id.text if product_user_id is not None else ''
            product_user_id_agency = product_user_id.attrib.get('agency', '') if product_user_id is not None else ''
            product_species_group_key = self._get_text(classified_product, 's:SpeciesGroupKey')
            
            products_data.append({
                'product_key': product_key,
                'product_name': product_name,
                'product_modification_date': product_modification_date,
                'product_user_id': product_user_id_value,
                'product_user_id_agency': product_user_id_agency,
                'species_group_key': product_species_group_key
            })
        
        return pd.DataFrame(products_data)

    def _parse_objects(self):
        """
        Private method to parse object and sub-object definitions from HPR file.
        Returns a DataFrame with object and sub-object information.
        """
        objects_data = []
        objects = self.root.findall('.//s:ObjectDefinition', self.ns)
        
        for obj in objects:
            object_key = self._get_text(obj, 's:ObjectKey')
            object_user_id = obj.find('s:ObjectUserID', self.ns)
            object_user_id_value = object_user_id.text if object_user_id is not None else ''
            object_user_id_agency = object_user_id.attrib.get('agency', '') if object_user_id is not None else ''
            object_name = self._get_text(obj, 's:ObjectName')
            object_modification_date_raw = self._get_text(obj, 's:ObjectModificationDate')
            object_modification_date = format_date(object_modification_date_raw)
            forest_certification = self._get_text(obj, 's:ForestCertification')
            contract_number = obj.find('s:ContractNumber', self.ns)
            contract_number_value = contract_number.text if contract_number is not None else ''
            contract_number_category = contract_number.attrib.get('ContractCategory', '') if contract_number is not None else ''
            real_estate_id_object = self._get_text(obj, 's:RealEstateIDObject')
            start_date_raw = self._get_text(obj, 's:StartDate')
            start_date = format_date(start_date_raw)
            
            # Parse SubObject
            sub_object = obj.find('s:SubObject', self.ns)
            sub_object_key = self._get_text(sub_object, 's:SubObjectKey')
            sub_object_user_id = sub_object.find('s:SubObjectUserID', self.ns) if sub_object is not None else None
            sub_object_user_id_value = sub_object_user_id.text if sub_object_user_id is not None else ''
            sub_object_user_id_agency = sub_object_user_id.attrib.get('agency', '') if sub_object_user_id is not None else ''
            sub_object_name = self._get_text(sub_object, 's:SubObjectName')
            real_estate_id_sub_object = self._get_text(sub_object, 's:RealEstateIDSubObject')
            
            objects_data.append({
                'object_key': object_key,
                'object_user_id': object_user_id_value,
                'object_user_id_agency': object_user_id_agency,
                'object_name': object_name,
                'object_modification_date': object_modification_date,
                'forest_certification': forest_certification,
                'contract_number': contract_number_value,
                'contract_number_category': contract_number_category,
                'real_estate_id_object': real_estate_id_object,
                'start_date': start_date,
                'sub_object_key': sub_object_key,
                'sub_object_user_id': sub_object_user_id_value,
                'sub_object_user_id_agency': sub_object_user_id_agency,
                'sub_object_name': sub_object_name,
                'real_estate_id_sub_object': real_estate_id_sub_object
            })
        
        return pd.DataFrame(objects_data)

    def _parse_stems(self):
        """
        Private method to parse stem information from HPR file.
        Returns a DataFrame with stem measurements and metadata.
        """
        stems_data = []
        stems = self.root.findall('.//s:Stem', self.ns)
        
        for stem in stems:
            # Parse basic stem information
            stem_key = self._get_text(stem, 's:StemKey')
            object_key = self._get_text(stem, 's:ObjectKey')
            sub_object_key = self._get_text(stem, 's:SubObjectKey')
            species_group_key = self._get_text(stem, 's:SpeciesGroupKey')
            operator_key_stem = self._get_text(stem, 's:OperatorKey')
            harvest_date_raw = self._get_text(stem, 's:HarvestDate')
            harvest_date = format_date(harvest_date_raw)
            stem_number = self._get_text(stem, 's:StemNumber')
            processing_category = self._get_text(stem, 's:ProcessingCategory')
            stump_treatment = self._get_text(stem, 's:StumpTreatment')
            
            # Parse coordinates (base machine position)
            all_coords = stem.findall('s:StemCoordinates', self.ns)
            base_coords = None
            for coord in all_coords:
                if coord.attrib.get('receiverPosition') == 'Base machine position':
                    base_coords = coord
                    break
            base_lat = self._get_text(base_coords, 's:Latitude')
            base_lon = self._get_text(base_coords, 's:Longitude')
            base_alt = self._get_text(base_coords, 's:Altitude')
            
            # Parse extension information
            extension = stem.find('s:Extension', self.ns)
            session_id = self._get_text(extension, 's:SessionId')
            analyzed_length = self._get_text(extension, 's:AnalyzedLength')
            
            # Parse SingleTreeProcessedStem data
            single_tree = stem.find('s:SingleTreeProcessedStem', self.ns)
            dbh = self._get_text(single_tree, 's:DBH')
            ref_diameter = single_tree.find('s:ReferenceDiameter', self.ns) if single_tree is not None else None
            ref_diameter_value = ref_diameter.text if ref_diameter is not None else ''
            ref_diameter_height = ref_diameter.attrib.get('referenceDiameterHeight', '') if ref_diameter is not None else ''
            
            # Parse stem grade
            stem_grade = single_tree.find('s:StemGrade', self.ns) if single_tree is not None else None
            grade_value = self._get_text(stem_grade, 's:GradeValue')
            
            # Append stem data
            stems_data.append({
                'stem_key': stem_key,
                'object_key': object_key,
                'sub_object_key': sub_object_key,
                'species_group_key': species_group_key,
                'operator_key': operator_key_stem,
                'harvest_date': harvest_date,
                'stem_number': stem_number,
                'processing_category': processing_category,
                'stump_treatment': stump_treatment,
                'base_latitude': base_lat,
                'base_longitude': base_lon,
                'base_altitude': base_alt,
                'session_id': session_id,
                'analyzed_length': analyzed_length,
                'dbh': dbh,
                'reference_diameter': ref_diameter_value,
                'reference_diameter_height': ref_diameter_height,
                'grade_value': grade_value
            })
        
        return pd.DataFrame(stems_data)

    def _parse_logs(self):
        """
        Private method to parse log information from HPR file.
        Returns a DataFrame with log measurements.
        """
        logs_data = []
        stems = self.root.findall('.//s:Stem', self.ns)
        
        for stem in stems:
            stem_key = self._get_text(stem, 's:StemKey')
            single_tree = stem.find('s:SingleTreeProcessedStem', self.ns)
            
            # Parse logs within this stem
            if single_tree is not None:
                logs = single_tree.findall('s:Log', self.ns)
                for log in logs:
                    log_key = self._get_text(log, 's:LogKey')
                    product_key = self._get_text(log, 's:ProductKey')
                    
                    # Parse log volumes (multiple categories)
                    log_volumes = log.findall('s:LogVolume', self.ns)
                    volume_price = ''
                    volume_sob = ''
                    volume_sub = ''
                    for vol in log_volumes:
                        category = vol.attrib.get('logVolumeCategory', '')
                        value = vol.text if vol.text is not None else ''
                        if category == 'm3 (price)':
                            volume_price = value
                        elif category == 'm3sob':
                            volume_sob = value
                        elif category == 'm3sub':
                            volume_sub = value
                    
                    # Parse cutting category
                    cutting_cat = log.find('s:CuttingCategory', self.ns)
                    cutting_reason = self._get_text(cutting_cat, 's:CuttingReason')
                    
                    # Parse extension (start position)
                    log_extension = log.find('s:Extension', self.ns)
                    start_pos = self._get_text(log_extension, 's:StartPos')
                    
                    # Parse log measurements
                    log_measurement = log.find('s:LogMeasurement', self.ns)
                    log_length = self._get_text(log_measurement, 's:LogLength')
                    
                    # Parse log diameters (multiple categories)
                    log_diameters = log_measurement.findall('s:LogDiameter', self.ns) if log_measurement is not None else []
                    diameter_butt_ob = ''
                    diameter_butt_ub = ''
                    diameter_mid_ob = ''
                    diameter_mid_ub = ''
                    diameter_top_ob = ''
                    diameter_top_ub = ''
                    for dia in log_diameters:
                        category = dia.attrib.get('logDiameterCategory', '')
                        value = dia.text if dia.text is not None else ''
                        if category == 'Butt ob':
                            diameter_butt_ob = value
                        elif category == 'Butt ub':
                            diameter_butt_ub = value
                        elif category == 'Mid ob':
                            diameter_mid_ob = value
                        elif category == 'Mid ub':
                            diameter_mid_ub = value
                        elif category == 'Top ob':
                            diameter_top_ob = value
                        elif category == 'Top ub':
                            diameter_top_ub = value
                    
                    # Append log data (with stem_key for linking)
                    logs_data.append({
                        'stem_key': stem_key,  # Link log to stem
                        'log_key': log_key,
                        'product_key': product_key,
                        'volume_price_m3': volume_price,
                        'volume_sob_m3': volume_sob,
                        'volume_sub_m3': volume_sub,
                        'cutting_reason': cutting_reason,
                        'start_pos': start_pos,
                        'log_length': log_length,
                        'diameter_butt_ob': diameter_butt_ob,
                        'diameter_butt_ub': diameter_butt_ub,
                        'diameter_mid_ob': diameter_mid_ob,
                        'diameter_mid_ub': diameter_mid_ub,
                        'diameter_top_ob': diameter_top_ob,
                        'diameter_top_ub': diameter_top_ub
                    })
        
        return pd.DataFrame(logs_data)

    def parse_all(self):
        """
        Parses the file and returns a dictionary containing DataFrames:
        'header', 'machine', 'species_groups', 'products', 'objects', 'stems', 'logs'.
        """
        return {   
            'header': self._parse_header(),
            'machine': self._parse_machine(),
            'species_groups': self._parse_species_groups(),
            'products': self._parse_products(),
            'objects': self._parse_objects(),
            'stems': self._parse_stems(),
            'logs': self._parse_logs()
        }

    def visualize(self, data=None):
        """
        Simple visualization: prints out the parsed data.
        If data is None, calls parse_all() first.
        """
        if data is None:
            data = self.parse_all()
        
        print("=" * 80)
        print("PARSED DATA VISUALIZATION")
        print("=" * 80)
        
        for key, df in data.items():
            print(f"\n--- {key.upper()} ---")
            if df.empty:
                print(f"  (No {key} data)")
            else:
                print(df.to_string())
                print(f"\n  Shape: {df.shape[0]} rows × {df.shape[1]} columns")


        print("\n" + "=" * 80)

class PINParser:
    """Parses Product Instructions (XML)"""
    def parse(self, file):
        # Logic to read <ProductDefinition>, <Species>, etc.
        pass