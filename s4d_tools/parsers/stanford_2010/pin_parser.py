import xml.etree.ElementTree as ET
from typing import Dict, Optional, Tuple

import pandas as pd

from s4d_tools.parsers.stanford_2010.constants import STANFORD_2010_NS
from s4d_tools.parsers.stanford_2010.utils import get_text


def _safe_int(value: Optional[str]) -> Optional[int]:
    if value is None or str(value).strip() == "":
        return None
    try:
        return int(float(str(value).strip()))
    except ValueError:
        return None


def _product_class_upper_maps(
    classified_product: Optional[ET.Element],
    ns: Dict[str, str],
) -> Tuple[Dict[int, int], Dict[int, int]]:
    """
    From DiameterDefinition / LengthDefinition, map each class lower limit to the upper
    bound (next class lower, or *ClassMAX for the last class).
    """
    d_map: Dict[int, int] = {}
    l_map: Dict[int, int] = {}
    if classified_product is None:
        return d_map, l_map

    ddef = classified_product.find("s:DiameterDefinition", ns)
    if ddef is not None:
        dclasses = ddef.find("s:DiameterClasses", ns)
        if dclasses is not None:
            lows = [
                v
                for dc in dclasses.findall("s:DiameterClass", ns)
                if (v := _safe_int(get_text(dc, "s:DiameterClassLowerLimit"))) is not None
            ]
            dmax_el = dclasses.find("s:DiameterClassMAX", ns)
            dmax = _safe_int(dmax_el.text) if dmax_el is not None else None
            lows = sorted(set(lows))
            for i, lo in enumerate(lows):
                d_map[lo] = lows[i + 1] if i + 1 < len(lows) else (dmax if dmax is not None else lo)

    ldef = classified_product.find("s:LengthDefinition", ns)
    if ldef is not None:
        lows = [
            v
            for lc in ldef.findall("s:LengthClass", ns)
            if (v := _safe_int(get_text(lc, "s:LengthClassLowerLimit"))) is not None
        ]
        lmax_el = ldef.find("s:LengthClassMAX", ns)
        lmax = _safe_int(lmax_el.text) if lmax_el is not None else None
        lows = sorted(set(lows))
        for i, lo in enumerate(lows):
            l_map[lo] = lows[i + 1] if i + 1 < len(lows) else (lmax if lmax is not None else lo)

    return d_map, l_map


class PINParser:
    def __init__(self, file_path):
        self.file_path = file_path
        self.tree = ET.parse(file_path)
        self.root = self.tree.getroot()
        self.ns = STANFORD_2010_NS

    def _parse_products(self):
        products_data = []
        products = self.root.findall('.//s:ProductDefinition', self.ns)

        for product in products:
            product_user_id = product.find('s:ProductUserID', self.ns)
            product_user_id_value = product_user_id.text if product_user_id is not None and product_user_id.text is not None else ''
            product_user_id_agency = product_user_id.attrib.get('agency', '') if product_user_id is not None else ''

            classified_product = product.find('s:ClassifiedProductDefinition', self.ns)
            product_name = get_text(classified_product, 's:ProductName')
            product_info = get_text(classified_product, 's:ProductInfo')
            stem_type_code = get_text(classified_product, 's:StemTypeCode')

            species_group_user_id = classified_product.find('s:SpeciesGroupUserID', self.ns) if classified_product is not None else None
            species_group_user_id_value = (
                species_group_user_id.text if species_group_user_id is not None and species_group_user_id.text is not None else ''
            )
            species_group_user_id_agency = species_group_user_id.attrib.get('agency', '') if species_group_user_id is not None else ''

            products_data.append({
                'product_user_id': product_user_id_value,
                'product_user_id_agency': product_user_id_agency,
                'product_name': product_name,
                'product_info': product_info,
                'stem_type_code': stem_type_code,
                'species_group_user_id': species_group_user_id_value,
                'species_group_user_id_agency': species_group_user_id_agency
            })

        return pd.DataFrame(products_data)

    def _parse_price_matrices(self):
        price_matrix_data = []
        products = self.root.findall('.//s:ProductDefinition', self.ns)

        for product in products:
            product_user_id = product.find('s:ProductUserID', self.ns)
            product_user_id_value = product_user_id.text if product_user_id is not None and product_user_id.text is not None else ''
            product_user_id_agency = product_user_id.attrib.get('agency', '') if product_user_id is not None else ''

            classified_product = product.find('s:ClassifiedProductDefinition', self.ns)
            product_name = get_text(classified_product, 's:ProductName')

            d_lim_by_lower, l_lim_by_lower = _product_class_upper_maps(classified_product, self.ns)

            product_matrixes = classified_product.find('s:ProductMatrixes', self.ns) if classified_product is not None else None
            product_matrix_items = product_matrixes.findall('s:ProductMatrixItem', self.ns) if product_matrixes is not None else []

            for matrix_item in product_matrix_items:
                diameter_class_lower_limit = matrix_item.attrib.get('diameterClassLowerLimit')
                length_class_lower_limit = matrix_item.attrib.get('lengthClassLowerLimit')
                d_lo = _safe_int(diameter_class_lower_limit)
                l_lo = _safe_int(length_class_lower_limit)
                d_upper = d_lim_by_lower.get(d_lo, d_lo) if d_lo is not None else None
                l_upper = l_lim_by_lower.get(l_lo, l_lo) if l_lo is not None else None

                price = get_text(matrix_item, 's:Price')
                distribution = get_text(matrix_item, 's:Distribution')
                limitation = get_text(matrix_item, 's:Limitation')
                bucking_criteria = get_text(matrix_item, 's:BuckingCriteria')


                price_matrix_data.append({
                    'product_user_id': product_user_id_value,
                    'product_user_id_agency': product_user_id_agency,
                    'product_name': product_name,
                    'diameter_class_lower_limit': diameter_class_lower_limit,
                    'diameter_class_limit': str(d_upper) if d_upper is not None else '',
                    'length_class_lower_limit': length_class_lower_limit,
                    'length_class_limit': str(l_upper) if l_upper is not None else '',
                    'price': price,
                    'distribution': distribution,
                    'limitation': limitation,
                    'bucking_criteria': bucking_criteria,
                })

        return pd.DataFrame(price_matrix_data)

    def parse_all(self):
        """
        Parses the file and returns a dictionary containing DataFrames:
        'products' and 'price_matrices'.
        """
        return {
            'products': self._parse_products(),
            'price_matrices': self._parse_price_matrices()
        }
