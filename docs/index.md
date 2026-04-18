# s4d_tools

s4d_tools is a Python package for working with **StanForD** (Standard for Forest Data) harvester and production files. It reads machine-specific binary and XML-style exports and turns them into structured **pandas** tables.

The **s4d_tools** parsers cover both standards in use today:

- **SFD Classic**, including production (`.prd`), production-individual (`.pri`), and product instructions (`.apt`).
- **SFD 2010**, including harvester production (`.hpr`) and product instructions (`.pin`).
