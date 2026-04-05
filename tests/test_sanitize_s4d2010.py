import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

_project_root = Path(__file__).resolve().parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from s4d_tools.utils.sanitize_s4d2010 import sanitize_s4d2010_xml

NS = "urn:skogforsk:stanford2010"


def _q(name: str) -> str:
    return f"{{{NS}}}{name}"


def test_redacts_machine_owner_logging_contractor_contact_forest_owner():
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<HarvestedProduction xmlns="{NS}">
  <Machine machineCategory="Harvester">
    <MachineOwner>
      <FirstName>Secret</FirstName>
      <Address><Street>A</Street><City>B</City></Address>
    </MachineOwner>
    <LoggingContractor>
      <BusinessName>ACME</BusinessName>
    </LoggingContractor>
    <OperatorDefinition>
      <ContactInformation>
        <FirstName>Op</FirstName>
        <LastName>Er</LastName>
      </ContactInformation>
    </OperatorDefinition>
  </Machine>
  <ObjectDefinition>
    <ForestOwner>
      <Address><Street>X</Street></Address>
      <BusinessID>123</BusinessID>
    </ForestOwner>
  </ObjectDefinition>
</HarvestedProduction>
"""
    out = sanitize_s4d2010_xml(xml.encode(), strip_stem_times=False)
    root = ET.fromstring(out)
    mo = root.find(f".//{{{NS}}}MachineOwner")
    assert mo.find(_q("FirstName")).text == "xxx"
    assert mo.find(f".//{{{NS}}}Street").text == "xxx"
    lc = root.find(f".//{{{NS}}}LoggingContractor")
    assert lc.find(_q("BusinessName")).text == "xxx"
    ci = root.find(f".//{{{NS}}}ContactInformation")
    assert ci.find(_q("FirstName")).text == "xxx"
    assert ci.find(_q("LastName")).text == "xxx"
    fo = root.find(f".//{{{NS}}}ForestOwner")
    assert fo.find(f".//{{{NS}}}Street").text == "xxx"
    assert fo.find(_q("BusinessID")).text == "xxx"


def test_redacts_stem_harvest_and_extension():
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<HarvestedProduction xmlns="{NS}">
  <Machine machineCategory="Harvester"><MachineOwner/><LoggingContractor/></Machine>
  <Stem>
    <HarvestDate>2024-09-23T14:54:27.58+02:00</HarvestDate>
    <Extension>
      <FellCutStartTime>t1</FellCutStartTime>
      <FellCutEndTime>t2</FellCutEndTime>
    </Extension>
  </Stem>
</HarvestedProduction>
"""
    out = sanitize_s4d2010_xml(xml.encode(), strip_stem_times=True)
    root = ET.fromstring(out)
    stem = root.find(f".//{{{NS}}}Stem")
    assert stem.find(_q("HarvestDate")).text == "xxx"
    ext = stem.find(_q("Extension"))
    assert ext.find(_q("FellCutStartTime")).text == "xxx"
    assert ext.find(_q("FellCutEndTime")).text == "xxx"


def test_pin_root_accepted():
    xml = f"""<?xml version="1.0" encoding="utf-8"?>
<ProductInstruction xmlns="{NS}">
  <ProductDefinition>
    <ClassifiedProductDefinition>
      <ProductPresentationOrder>1</ProductPresentationOrder>
      <DiameterDefinition><Z>z</Z></DiameterDefinition>
    </ClassifiedProductDefinition>
  </ProductDefinition>
</ProductInstruction>
"""
    out = sanitize_s4d2010_xml(xml.encode(), strip_stem_times=False)
    root = ET.fromstring(out)
    assert root.tag == _q("ProductInstruction")
    cpd = root.find(f".//{{{NS}}}ClassifiedProductDefinition")
    assert list(cpd)[0].tag == _q("ProductPresentationOrder")
    assert cpd.find(f".//{{{NS}}}DiameterDefinition") is not None


def test_rejects_non_stanford_xml():
    bad = b"<root><a/></root>"
    with pytest.raises(ValueError, match="Stanford 2010"):
        sanitize_s4d2010_xml(bad)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
