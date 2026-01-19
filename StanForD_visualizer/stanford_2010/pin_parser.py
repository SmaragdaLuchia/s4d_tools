import xml.etree.ElementTree as ET
import pandas as pd

class PINParser:
    """Parses Product Instructions"""
    def __init__(self, file_path):
        self.file_path = file_path
        self.tree = ET.parse(file_path)
        self.root = self.tree.getroot()
        self.ns = {'s': 'urn:skogforsk:stanford2010'}


            
            