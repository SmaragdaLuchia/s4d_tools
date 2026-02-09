# StanForD Parser

A web-based visualization tool for analyzing StanForD (Standard for Forest Data) harvester files. This application parses and visualizes data from production (.prd), production-individual (.pri), and harvester production (.hpr) files, providing comprehensive statistics and insights about forest harvesting operations.

## Features

- **File Parsing**: Supports multiple StanForD file formats:
  - `.prd` - Production files
  - `.pri` - Production-individual files (can be combined with PRD)
  - `.hpr` - Harvester production files (2010 format)
- **Interactive Visualization**: Web-based interface built with Streamlit
- **Comprehensive Analysis**: View statistics, species distribution, product information, machine data, and more
- **Data Export**: Explore parsed data through interactive tables and charts

## Setup Instructions

### Prerequisites

- Python 3.11 or higher
- pip (Python package installer)

### Step 1: Clone the Repository

```bash
git clone <repository-url>
cd s4d_tools
```

### Step 2: Create a Virtual Environment

It's recommended to use a virtual environment to isolate project dependencies:

```bash
# Create virtual environment
python3 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate

# On Windows:
# venv\Scripts\activate
```

### Step 3: Install Dependencies

```bash
# Make sure virtual environment is activated
pip install --upgrade pip
pip install -r requirements.txt
```

### Step 4: Run the Streamlit Application

```bash
# Run the main application
streamlit run streamlit/app.py

# Or run the alternative application
streamlit run streamlit/app_et.py
```

The application will start and automatically open in your default web browser at `http://localhost:8501`.

### Step 5: Using the Application

1. Upload a `.prd` or `.hpr` file using the file uploader
2. Optionally upload a `.pri` file if you have a corresponding PRD file
3. Explore the parsed data through the interactive tabs:
   - **Overview**: Summary statistics and key metrics
   - **Basic Info**: File header and object information
   - **Species**: Species groups and distribution
   - **Products**: Product information
   - **Statistics**: Detailed production statistics
   - **Machine**: Machine information and specifications
