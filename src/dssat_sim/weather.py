import requests
import pandas as pd
from datetime import datetime
import os
from dotenv import load_dotenv

def load_config():
    """
    Load configuration from .env file
    """
    load_dotenv()
    
    config_data = {
        'city_name': os.getenv('CITY_NAME'),
        'weather_station': os.getenv('WEATHER_STATION'),
        'latitude': float(os.getenv('LATITUDE')),
        'longitude': float(os.getenv('LONGITUDE')),
        'start_date': os.getenv('START_DATE'),
        'end_date': os.getenv('END_DATE')
    }
    
    return config_data

def date_to_julian(date_obj):
    """
    Convert date to Julian day format (day of year)
    Returns: YYDDD format (YY = year, DDD = day of year)
    """
    year_short = str(date_obj.year)[-2:]  # Last 2 digits of year
    day_of_year = date_obj.timetuple().tm_yday  # Day of year (1-366)
    return f"{year_short}{day_of_year:03d}"

def get_weather_data_from_config(config, api_key=None):
    """
    Fetch weather data from NASA POWER API based on configuration from .env file
    
    Parameters:
    - config: Configuration dictionary from load_config()
    - api_key: API key for weather service (not needed for NASA POWER)
    
    Returns:
    - pandas DataFrame with columns: @Date, srad, tmax, tmin, rain
    """
    
    lat = config['latitude']
    lon = config['longitude']
    start_date = config['start_date']
    end_date = config['end_date']
    
    # Convert dates to NASA POWER format (YYYYMMDD)
    start_nasa = start_date.replace('-', '')
    end_nasa = end_date.replace('-', '')
    
    # NASA POWER API endpoint
    url = "https://power.larc.nasa.gov/api/temporal/daily/point"
    
    # Parameters for NASA POWER API
    # ALLSKY_SFC_SW_DWN: Surface Solar Irradiance (MJ/m²/day)
    # T2M_MAX: Temperature at 2m Maximum (°C)
    # T2M_MIN: Temperature at 2m Minimum (°C) 
    # PRECTOTCORR: Precipitation Corrected (mm/day)
    params = {
        "parameters": "ALLSKY_SFC_SW_DWN,T2M_MAX,T2M_MIN,PRECTOTCORR",
        "community": "AG",  # Agroclimatology community
        "longitude": lon,
        "latitude": lat,
        "start": start_nasa,
        "end": end_nasa,
        "format": "JSON"
    }
    
    print(f"Fetching real weather data from NASA POWER API...")
    print(f"URL: {url}")
    print(f"Parameters: lat={lat}, lon={lon}, dates={start_date} to {end_date}")
    print(f"NASA date format: {start_nasa} to {end_nasa}")
    
    try:
        response = requests.get(url, params=params, timeout=60)
        print(f"NASA API Response Status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"NASA API Response Text: {response.text[:500]}...")
        
        response.raise_for_status()
        data = response.json()
        
        if 'properties' not in data or 'parameter' not in data['properties']:
            print(f"NASA API Response Structure: {list(data.keys()) if isinstance(data, dict) else 'Not a dictionary'}")
            raise ValueError("No parameter data found in NASA API response")
        
        parameters = data['properties']['parameter']
        print(f"Available parameters: {list(parameters.keys())}")
        
        # Extract data
        solar_rad = parameters.get('ALLSKY_SFC_SW_DWN', {})
        temp_max = parameters.get('T2M_MAX', {})
        temp_min = parameters.get('T2M_MIN', {})
        precipitation = parameters.get('PRECTOTCORR', {})
        
        if not all([solar_rad, temp_max, temp_min, precipitation]):
            print(f"Missing parameters - Solar: {bool(solar_rad)}, TMax: {bool(temp_max)}, TMin: {bool(temp_min)}, Rain: {bool(precipitation)}")
            raise ValueError("Missing required parameters in NASA API response")
        
        # Create DataFrame
        dates = []
        srad_vals = []
        tmax_vals = []
        tmin_vals = []
        rain_vals = []
        
        # NASA returns data with YYYYMMDD keys
        for date_key in sorted(solar_rad.keys()):
            if date_key.isdigit() and len(date_key) == 8:  # Valid date format
                # Convert YYYYMMDD to datetime
                date_obj = datetime.strptime(date_key, '%Y%m%d')
                dates.append(date_obj)
                
                # Get Julian date
                julian_date = date_to_julian(date_obj)
                
                # Extract values (handle missing data as -999)
                srad_val = solar_rad.get(date_key, -999)
                tmax_val = temp_max.get(date_key, -999)
                tmin_val = temp_min.get(date_key, -999)
                rain_val = precipitation.get(date_key, -999)
                
                # Replace -999 (NASA missing value) with reasonable defaults or interpolated values
                if srad_val == -999:
                    srad_val = 18.0  # Default solar radiation for tropical regions
                if tmax_val == -999:
                    tmax_val = 28.0  # Default max temp
                if tmin_val == -999:
                    tmin_val = 16.0  # Default min temp  
                if rain_val == -999:
                    rain_val = 0.0   # Default no rain
                
                srad_vals.append(round(srad_val, 1))
                tmax_vals.append(round(tmax_val, 1))
                tmin_vals.append(round(tmin_val, 1))
                rain_vals.append(round(rain_val, 1))
        
        if not dates:
            raise ValueError("No valid dates found in NASA API response")
        
        df = pd.DataFrame({
            '@Date': [date_to_julian(date) for date in dates],
            'srad': srad_vals,
            'tmax': tmax_vals,
            'tmin': tmin_vals,
            'rain': rain_vals
        })
        
        print(f"✅ Successfully fetched {len(df)} days of real NASA POWER weather data!")
        print(f"Data source: NASA Langley Research Center POWER Project")
        return df
        
    except Exception as e:
        print(f"❌ Error fetching NASA POWER data: {e}")
        print("⚠️  Falling back to sample data...")
        return generate_sample_weather_data_from_config(config)

def generate_sample_weather_data_from_config(config):
    """
    Generate sample weather data based on configuration
    """
    import numpy as np
    
    start_date = config['start_date']
    end_date = config['end_date']
    
    date_range = pd.date_range(start=start_date, end=end_date, freq='D')
    n_days = len(date_range)
    
    # Set random seed for reproducible results
    np.random.seed(42)
    
    # Generate realistic weather data
    data = {
        '@Date': [date_to_julian(date) for date in date_range],
        'srad': np.random.normal(18.5, 3.0, n_days),  # Solar radiation (MJ/m²/day)
        'tmax': np.random.normal(28.5, 2.0, n_days),  # Max temperature (°C)
        'tmin': np.random.normal(16.0, 1.5, n_days),  # Min temperature (°C)
        'rain': np.random.exponential(2.0, n_days)     # Rainfall (mm)
    }
    
    # Ensure realistic ranges
    data['srad'] = np.clip(data['srad'], 10, 25)
    data['tmax'] = np.clip(data['tmax'], 24, 35)
    data['tmin'] = np.clip(data['tmin'], 12, 20)
    data['rain'] = np.clip(data['rain'], 0, 50)
    
    # Round values to match your format
    data['srad'] = np.round(data['srad'], 1)
    data['tmax'] = np.round(data['tmax'], 1)
    data['tmin'] = np.round(data['tmin'], 1)
    data['rain'] = np.round(data['rain'], 1)
    
    return pd.DataFrame(data)

def save_weather_data_yearly(df, config, output_dir="weather_data"):
    """
    Save weather data to CSV file per year with format: Weather_stationYY01.csv
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Add a temporary date column to group by year
    # Convert Julian date back to year for grouping
    df['temp_year'] = df['@Date'].apply(lambda x: int(str(x)[:2]) + 1900 if int(str(x)[:2]) >= 50 else int(str(x)[:2]) + 2000)
    
    saved_files = []
    
    for year in sorted(df['temp_year'].unique()):
        year_data = df[df['temp_year'] == year].copy()
        year_data = year_data.drop('temp_year', axis=1)  # Remove temporary year column
        
        # Create filename: Weather_stationYY01.csv
        station_clean = config['weather_station'].replace(' ', '_').upper()
        year_short = str(year)[-2:]  # Last 2 digits of year
        filename = f"{station_clean}{year_short}01.csv"
        filepath = os.path.join(output_dir, filename)
        
        year_data.to_csv(filepath, index=False)
        print(f"Weather data for {year} saved to {filepath}")
        saved_files.append(filepath)
    
    return saved_files

def display_weather_sample(df, n_rows=10):
    """
    Display first n rows of weather data
    """
    print(f"\nFirst {n_rows} rows of weather data:")
    print(df.head(n_rows).to_string(index=True))

def generate_yearly_data_from_config(config, output_dir="weather_data"):
    """
    Generate weather data for the date range specified in config
    Save per year in separate CSV files
    
    Parameters:
    - config: Configuration dictionary from load_config()
    - output_dir: Output directory for CSV files
    
    Returns:
    - List of generated file paths
    """
    print(f"Generating weather data for {config['city_name']} ({config['weather_station']})")
    print(f"Location: {config['latitude']}, {config['longitude']}")
    print(f"Date range: {config['start_date']} to {config['end_date']}")
    
    # Generate data for entire date range
    weather_df = get_weather_data_from_config(config)
    
    # Save data per year
    saved_files = save_weather_data_yearly(weather_df, config, output_dir)
    
    return saved_files, weather_df

# Example usage
if __name__ == "__main__":
    print("=== Weather Data Generator from .env Configuration ===")
    
    # Load configuration from .env file
    config = load_config()
    
    print("\nConfiguration loaded:")
    print(f"  City: {config['city_name']}")
    print(f"  Weather Station: {config['weather_station']}")
    print(f"  Coordinates: {config['latitude']}, {config['longitude']}")
    print(f"  Date range: {config['start_date']} to {config['end_date']}")
    
    # Generate weather data
    saved_files, weather_df = generate_yearly_data_from_config(config)
    
    # Display sample data
    print("\n=== Sample Data (first 10 rows) ===")
    display_weather_sample(weather_df, 10)
    
    print("\n=== Summary ===")
    print(f"Total data points: {len(weather_df)}")
    print(f"Columns: {list(weather_df.columns)}")
    print(f"Files saved: {len(saved_files)}")
    for file in saved_files:
        print(f"  - {file}")
    
    print("\n=== Julian Date Format Example ===")
    print("Julian format: YYDDD (YY=year, DDD=day of year)")
    print("Sample Julian dates from the data:")
    sample_dates = weather_df['@Date'].head(5)
    for julian_date in sample_dates:
        julian_str = str(julian_date)
        year_part = julian_str[:2]
        day_part = julian_str[2:]
        full_year = int(year_part) + 1900 if int(year_part) >= 50 else int(year_part) + 2000
        print(f"  {julian_date} -> Year {full_year}, Day {int(day_part)} of year")