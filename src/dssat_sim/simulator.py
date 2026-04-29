"""
DSSAT Crop Simulation Module
============================

A modular Python script for running DSSAT crop simulations with weather data,
soil profiles, and various crop cultivars.

Author: Generated from Jupyter Notebook
Date: September 2025
"""

import pandas as pd
import os
import tempfile
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from DSSATTools import (
    crop,
    WeatherStation,
    SoilProfile,
    SoilLayer,
    filex,
    DSSAT
)


class DSSATSimulator:
    """Main class for DSSAT crop simulation management."""
    
    def __init__(self, project_name: str = "dssat_simulation"):
        """
        Initialize DSSAT Simulator.
        
        Args:
            project_name: Name of the simulation project
        """
        self.project_name = project_name
        self.weather_station = None
        self.soil_profile = None
        self.cultivar = None
        self.field = None
        self.simulation_dir = None
        
    def load_weather_data(self, weather_data_dir: str = "data/weather",
                         station_code: str = "IDGR", 
                         years: Optional[List[int]] = None) -> WeatherStation:
        """
        Load weather data from CSV files and create weather station.
        
        Args:
            weather_data_dir: Directory containing weather CSV files
            station_code: Weather station code
            years: List of years to load (default: [19, 20, 21] for 2019-2021)
            
        Returns:
            WeatherStation object
        """
        if years is None:
            years = [19, 20, 21]  # 2019-2021
            
        print(f"Loading weather data for years: {[2000 + y for y in years]}")
        
        df_list = []
        for year in years:
            file_path = os.path.join(weather_data_dir, f"{station_code}{year:02d}01.csv")
            if os.path.exists(file_path):
                df_list.append(pd.read_csv(file_path))
                print(f"  ✓ Loaded {file_path}")
            else:
                print(f"  ✗ Warning: {file_path} not found")
        
        if not df_list:
            raise FileNotFoundError(f"No weather data files found in {weather_data_dir}")
        
        # Combine all years
        df = pd.concat(df_list, ignore_index=True)
        df.columns = ['date', 'srad', 'tmax', 'tmin', 'rain']
        df["date"] = pd.to_datetime(df["date"], format='%y%j')
        
        print(f"Combined weather data: {len(df)} records")
        print(f"Date range: {df['date'].min()} to {df['date'].max()}")
        
        # Create weather station (Garut, Indonesia coordinates)
        self.weather_station = WeatherStation(
            insi=station_code, 
            lat=-7.2245, 
            long=107.9077, 
            elev=0, 
            tav=0, 
            amp=11.8, 
            refht=2.0, 
            wndht=2.0, 
            table=df
        )
        
        print(f"✓ Weather station '{station_code}' created successfully")
        return self.weather_station
    
    def load_soil_profile(self, soil_id: str = "IBSG910085", 
                         soil_file_path: str = "data/soil/SOIL.SOL",
                         download_if_missing: bool = True) -> SoilProfile:
        """
        Load soil profile from DSSAT soil file.
        
        Args:
            soil_id: Soil profile ID to load
            soil_file_path: Path to soil file
            download_if_missing: Download soil file if not found
            
        Returns:
            SoilProfile object
        """
        # Create soil_data directory if it doesn't exist
        soil_dir = os.path.dirname(soil_file_path)
        if soil_dir:
            os.makedirs(soil_dir, exist_ok=True)
        
        # Download soil file if missing
        if not os.path.exists(soil_file_path) and download_if_missing:
            print(f"Downloading DSSAT soil file to {soil_file_path}")
            try:
                response = urllib.request.urlopen(
                    'https://github.com/DSSAT/dssat-csm-data/blob/develop/Soil/SOIL.SOL?raw=true'
                )
                soil_file_str = ''.join([l.decode('utf-8') for l in response])
                with open(soil_file_path, 'w') as f:
                    f.write(soil_file_str)
                print(f"✓ Soil file downloaded successfully")
            except Exception as e:
                raise Exception(f"Failed to download soil file: {e}")
        
        # Load soil profile
        if not os.path.exists(soil_file_path):
            raise FileNotFoundError(f"Soil file not found: {soil_file_path}")
        
        self.soil_profile = SoilProfile.from_file(soil_id, soil_file_path)
        print(f"✓ Soil profile '{soil_id}' loaded successfully")
        return self.soil_profile
    
    def set_cultivar(self, crop_type: str = "Rice", cultivar_id: str = "IB0003"):
        """
        Set crop cultivar for simulation.
        
        Args:
            crop_type: Type of crop (Rice, Sorghum, Maize, etc.)
            cultivar_id: Cultivar ID code
        """
        crop_classes = {
            "Rice": crop.Rice,
            "Sorghum": crop.Sorghum,
            "Maize": crop.Maize,
            "Wheat": crop.Wheat,
            "Soybean": crop.Soybean,
        }
        
        if crop_type not in crop_classes:
            raise ValueError(f"Unsupported crop type: {crop_type}. Available: {list(crop_classes.keys())}")
        
        self.cultivar = crop_classes[crop_type](cultivar_id)
        print(f"✓ {crop_type} cultivar '{cultivar_id}' set successfully")
        return self.cultivar
    
    def create_field(self, field_id: str = "DTR00001") -> filex.Field:
        """
        Create field definition with weather station and soil profile.
        
        Args:
            field_id: Field identifier
            
        Returns:
            Field object
        """
        if self.weather_station is None:
            raise ValueError("Weather station not loaded. Call load_weather_data() first.")
        if self.soil_profile is None:
            raise ValueError("Soil profile not loaded. Call load_soil_profile() first.")
        
        self.field = filex.Field(
            id_field=field_id, 
            wsta=self.weather_station, 
            flob=0, 
            fldt='DR000', 
            fldd=0, 
            flds=0, 
            id_soil=self.soil_profile
        )
        
        print(f"✓ Field '{field_id}' created successfully")
        return self.field
    
    def create_initial_conditions(self, crop_code: str = "SG", 
                                initial_date: Optional[datetime] = None) -> filex.InitialConditions:
        """
        Create initial conditions for simulation.
        
        Args:
            crop_code: Crop code (SG for Sorghum, RI for Rice, etc.)
            initial_date: Initial conditions date
            
        Returns:
            InitialConditions object
        """
        if initial_date is None:
            initial_date = datetime(1980, 7, 3)
        
        initial_conditions = filex.InitialConditions(
            pcr=crop_code, 
            icdat=initial_date, 
            icrt=500, 
            icnd=0,
            icrn=1, 
            icre=1, 
            icres=1300, 
            icren=.5, 
            icrep=0, 
            icrip=100, 
            icrid=10,
            table=pd.DataFrame([
                (10, .06, 2.5, 1.8),
                (22, .06, 2.5, 1.8),
                (52, .195, 3., 4.5),
                (82, .21, 3.5, 5.0),
                (112, 0.2, 2., 2.0),
                (142, 0.2, 1., 0.7),
                (172, 0.2, 1., 0.6),
            ], columns=['icbl', 'sh2o', 'snh4', 'sno3'])
        )
        
        print(f"✓ Initial conditions created for {crop_code} crop")
        return initial_conditions
    
    def create_planting(self, planting_date: Optional[datetime] = None, 
                       population: int = 18) -> filex.Planting:
        """
        Create planting configuration.
        
        Args:
            planting_date: Date of planting
            population: Plant population
            
        Returns:
            Planting object
        """
        if planting_date is None:
            planting_date = datetime(2025, 5, 1)
        
        planting = filex.Planting(
            pdate=planting_date, 
            ppop=population, 
            ppoe=population, 
            plme='S',
            plds='R', 
            plrs=45, 
            plrd=0, 
            pldp=5
        )
        
        print(f"✓ Planting configured for {planting_date.strftime('%Y-%m-%d')}")
        return planting
    
    def create_simulation_controls(self, start_date: Optional[datetime] = None) -> filex.SimulationControls:
        """
        Create simulation control parameters.
        
        Args:
            start_date: Simulation start date
            
        Returns:
            SimulationControls object
        """
        if start_date is None:
            start_date = datetime(1980, 6, 17)
        
        simulation_controls = filex.SimulationControls(
            general=filex.SCGeneral(sdate=start_date),
            options=filex.SCOptions(water='Y', nitro='Y', symbi='N'),
            methods=filex.SCMethods(infil='S'),
            management=filex.SCManagement(irrig='N', ferti='R', resid='N', harvs='M')
        )
        
        print(f"✓ Simulation controls configured")
        return simulation_controls
    
    def run_simulation(self, output_dir: Optional[str] = None, **kwargs) -> Any:
        """
        Run the complete DSSAT simulation.
        
        Args:
            output_dir: Directory for simulation output
            **kwargs: Additional parameters for simulation components
            
        Returns:
            Simulation results
        """
        print("=" * 60)
        print(f"DSSAT Simulation: {self.project_name}")
        print("=" * 60)
        
        # Set up output directory
        if output_dir is None:
            output_dir = os.path.join(tempfile.gettempdir(), f"{self.project_name}_output")
        
        os.makedirs(output_dir, exist_ok=True)
        self.simulation_dir = output_dir
        
        # Validate prerequisites
        if self.weather_station is None:
            raise ValueError("Weather station not loaded. Call load_weather_data() first.")
        if self.soil_profile is None:
            raise ValueError("Soil profile not loaded. Call load_soil_profile() first.")
        if self.cultivar is None:
            raise ValueError("Cultivar not set. Call set_cultivar() first.")
        if self.field is None:
            self.create_field()
        
        # Create simulation components
        initial_conditions = self.create_initial_conditions(**kwargs.get('initial_conditions', {}))
        planting = self.create_planting(**kwargs.get('planting', {}))
        simulation_controls = self.create_simulation_controls(**kwargs.get('simulation_controls', {}))
        
        # Create DSSAT simulation environment
        print(f"Creating DSSAT simulation in: {output_dir}")
        dssat = DSSAT(output_dir)
        
        # Run simulation
        print("Running DSSAT simulation...")
        try:
            results = dssat.run_treatment(
                field=self.field,
                cultivar=self.cultivar,
                planting=planting,
                initial_conditions=initial_conditions,
                simulation_controls=simulation_controls
            )
            
            print("✓ Simulation completed successfully!")
            print(f"Results saved to: {output_dir}")
            return results
            
        except Exception as e:
            print(f"✗ Simulation failed: {e}")
            raise


def run_preset(crop_type: str):
    """Run a complete DSSAT simulation using a named preset from `dssat_sim.presets`.

    Args:
        crop_type: One of the keys in CROP_CONFIG (e.g., "rice", "sorghum", "maize").

    Returns:
        Whatever `DSSATSimulator.run_simulation()` returns.

    Raises:
        ValueError: If crop_type is not in CROP_CONFIG.
    """
    from dssat_sim.presets import (
        CROP_CONFIG,
        FIELD_CONFIG,
        OUTPUT_CONFIG,
        SIMULATION_CONFIG,
        SOIL_CONFIG,
        WEATHER_CONFIG,
    )

    if crop_type not in CROP_CONFIG:
        raise ValueError(
            f"Unknown crop preset: {crop_type!r}. Available: {list(CROP_CONFIG)}"
        )

    crop_cfg = CROP_CONFIG[crop_type]
    sim_cfg = SIMULATION_CONFIG.get(crop_type, SIMULATION_CONFIG["rice"])

    project_name = (
        f"{crop_type}_simulation_"
        f"{FIELD_CONFIG['location_name'].lower().replace(' ', '_').replace(',', '')}"
    )
    simulator = DSSATSimulator(project_name)

    print(f"Starting {crop_cfg['crop_type']} simulation for {FIELD_CONFIG['location_name']}")
    print("=" * 60)

    simulator.load_weather_data(
        weather_data_dir=WEATHER_CONFIG["data_dir"],
        station_code=WEATHER_CONFIG["station_code"],
        years=WEATHER_CONFIG["years"],
    )
    simulator.load_soil_profile(
        soil_id=SOIL_CONFIG["soil_id"],
        soil_file_path=SOIL_CONFIG["soil_file"],
        download_if_missing=True,
    )
    simulator.set_cultivar(
        crop_type=crop_cfg["crop_type"],
        cultivar_id=crop_cfg["cultivar_id"],
    )
    simulator.create_field(FIELD_CONFIG["field_id"])

    output_dir = os.path.join(OUTPUT_CONFIG["base_dir"], crop_type)
    if OUTPUT_CONFIG["create_subdirs"]:
        os.makedirs(output_dir, exist_ok=True)

    return simulator.run_simulation(
        output_dir=output_dir,
        initial_conditions=sim_cfg["initial_conditions"],
        planting=sim_cfg["planting"],
        simulation_controls=sim_cfg["simulation_controls"],
    )


def main():
    """Example usage of the DSSAT Simulator."""
    
    # Create simulator instance
    simulator = DSSATSimulator("rice_simulation_garut")
    
    try:
        # Load weather data
        weather_station = simulator.load_weather_data(
            weather_data_dir="data/weather",
            station_code="IDGR",
            years=[19, 20, 21]  # 2019-2021
        )
        
        # Load soil profile
        soil_profile = simulator.load_soil_profile(
            soil_id="IBSG910085",
            soil_file_path="data/soil/SOIL.SOL"
        )
        
        # Set rice cultivar
        cultivar = simulator.set_cultivar(
            crop_type="Rice",
            cultivar_id="IB0003"
        )
        
        # Create field
        field = simulator.create_field("DTR00001")
        
        # Run simulation
        results = simulator.run_simulation(
            output_dir="results/simulation_output",
            initial_conditions={
                'crop_code': 'RI',  # Rice code
                'initial_date': datetime(1980, 7, 3)
            },
            planting={
                'planting_date': datetime(2025, 5, 1),
                'population': 18
            },
            simulation_controls={
                'start_date': datetime(1980, 6, 17)
            }
        )
        
        print("\n" + "=" * 60)
        print("SIMULATION SUMMARY")
        print("=" * 60)
        print(f"Project: {simulator.project_name}")
        print(f"Weather Station: {weather_station.insi}")
        print(f"Soil Profile: {soil_profile}")
        print(f"Cultivar: {cultivar}")
        print(f"Output Directory: {simulator.simulation_dir}")
        print("=" * 60)
        
        return results
        
    except Exception as e:
        print(f"\n✗ Error in simulation: {e}")
        raise


if __name__ == "__main__":
    # Run the simulation
    results = main()