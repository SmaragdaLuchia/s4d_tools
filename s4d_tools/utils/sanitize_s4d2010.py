"""
Redact GDPR-related and commercially sensitive data in Stanford 2010 (S4D2010) XML.

Targets HPR, PIN, and other messages using ``urn:skogforsk:stanford2010``.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from io import BytesIO
from typing import Union

STANFORD_NS = "urn:skogforsk:stanford2010"

_ALLOWED_ROOT_LOCAL = frozenset({"HarvestedProduction", "ProductInstruction"})


def _local_tag(tag: str) -> str:
    if tag.startswith("{"):
        return tag.split("}", 1)[1]
    return tag


def _stanford_root(elem: ET.Element) -> bool:
    if _local_tag(elem.tag) not in _ALLOWED_ROOT_LOCAL:
        return False
    if elem.tag.startswith("{"):
        return elem.tag.startswith(f"{{{STANFORD_NS}}}")
    return True


def _redact_leaves_under(root: ET.Element, placeholder: str) -> None:
    for node in root.iter():
        if len(node) == 0:
            node.text = placeholder


def _redact_machine_party_blocks(machine: ET.Element, placeholder: str) -> None:
    for ch in machine:
        ln = _local_tag(ch.tag)
        if ln in ("MachineOwner", "LoggingContractor"):
            _redact_leaves_under(ch, placeholder)


def _redact_contact_information_names(root: ET.Element, placeholder: str) -> None:
    for el in root.iter():
        if _local_tag(el.tag) != "ContactInformation":
            continue
        for ch in el:
            if _local_tag(ch.tag) not in ("FirstName", "LastName"):
                continue
            if len(ch) == 0:
                ch.text = placeholder


def _redact_forest_owner_blocks(root: ET.Element, placeholder: str) -> None:
    for el in root.iter():
        if _local_tag(el.tag) != "ForestOwner":
            continue
        for ch in el:
            ln = _local_tag(ch.tag)
            if ln == "Address":
                _redact_leaves_under(ch, placeholder)
            elif ln == "BusinessID" and len(ch) == 0:
                ch.text = placeholder


def _redact_stem_times(root: ET.Element, placeholder: str) -> None:
    for stem in root.iter():
        if _local_tag(stem.tag) != "Stem":
            continue
        for ch in stem:
            ln = _local_tag(ch.tag)
            if ln == "HarvestDate" and len(ch) == 0:
                ch.text = placeholder
            elif ln == "Extension":
                _redact_leaves_under(ch, placeholder)


def sanitize_s4d2010_xml(
    source: Union[bytes, str],
    *,
    placeholder: str = "xxx",
    strip_stem_times: bool = True,
) -> bytes:
    if isinstance(source, str):
        data = source.encode("utf-8")
    else:
        data = source

    try:
        root = ET.fromstring(data)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML: {e}") from e

    if not _stanford_root(root):
        raise ValueError(
            "Expected a Stanford 2010 root element "
            "(HarvestedProduction or ProductInstruction in urn:skogforsk:stanford2010)."
        )

    tree = ET.ElementTree(root)
    ET.register_namespace("", STANFORD_NS)

    for machine in root.iter():
        if _local_tag(machine.tag) == "Machine":
            _redact_machine_party_blocks(machine, placeholder)

    _redact_contact_information_names(root, placeholder)
    _redact_forest_owner_blocks(root, placeholder)

    if strip_stem_times:
        _redact_stem_times(root, placeholder)

    buf = BytesIO()
    tree.write(buf, encoding="utf-8", xml_declaration=True)
    return buf.getvalue()


__all__ = ["STANFORD_NS", "sanitize_s4d2010_xml"]
