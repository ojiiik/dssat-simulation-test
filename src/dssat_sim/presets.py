"""
Configuration file for DSSAT simulations
"""

from datetime import datetime

# Weather Configuration
WEATHER_CONFIG = {
    "data_dir": "./weather_data",
    "station_code": "IDGR",
    "years": [19, 20, 21],  # 2019-2021
    "coordinates": {
        "latitude": -7.2245,
        "longitude": 107.9077,
        "elevation": 0
    },
    "station_params": {
        "tav": 0,
        "amp": 11.8,
        "refht": 2.0,
        "wndht": 2.0
    }
}

# Soil Configuration
SOIL_CONFIG = {
    "soil_id": "IBSG910085",
    "soil_file": "soil_data/SOIL.SOL",
    "download_url": "https://github.com/DSSAT/dssat-csm-data/blob/develop/Soil/SOIL.SOL?raw=true"
}

# Crop Configuration
CROP_CONFIG = {
    "rice": {
        "crop_type": "Rice",
        "cultivar_id": "IB0003",
        "crop_code": "RI"
    },
    "sorghum": {
        "crop_type": "Sorghum", 
        "cultivar_id": "IB0026",
        "crop_code": "SG"
    },
    "maize": {
        "crop_type": "Maize",
        "cultivar_id": "IB0001",
        "crop_code": "MZ"
    }
}

# Field Configuration
FIELD_CONFIG = {
    "field_id": "GARUT001",
    "location_name": "Garut, Indonesia"
}

# Simulation Configuration
SIMULATION_CONFIG = {
    "rice": {
        "initial_conditions": {
            "crop_code": "RI",
            "initial_date": datetime(1980, 7, 3)
        },
        "planting": {
            "planting_date": datetime(2019, 5, 1),
            "population": 25  # plants per m²
        },
        "simulation_controls": {
            "start_date": datetime(1980, 6, 17)
        }
    },
    "sorghum": {
        "initial_conditions": {
            "crop_code": "SG",
            "initial_date": datetime(1980, 7, 3)
        },
        "planting": {
            "planting_date": datetime(2019, 3, 15),
            "population": 15  # plants per m²
        },
        "simulation_controls": {
            "start_date": datetime(1980, 6, 17)
        }
    }
}

# Output Configuration
OUTPUT_CONFIG = {
    "base_dir": "./simulation_results",
    "create_subdirs": True,
    "backup_inputs": True
}

# Default simulation preset
DEFAULT_PRESET = "rice"