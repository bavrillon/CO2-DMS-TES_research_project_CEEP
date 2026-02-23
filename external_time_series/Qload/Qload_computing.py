"""
Compute hourly refrigeration load by day type based on temperature clustering, 
using the methodology from "Data-driven modeling of the refrigeration load in supermarkets" 
by A. Schulte and al. (2024).
"""
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import os

os.chdir(os.path.dirname(__file__))
parent_dir = os.path.dirname(os.path.dirname(__file__))
grandparent_dir = os.path.dirname(parent_dir)

# Fourier coefficients for hourly load profile (k_time)
D_COEFS_HOURS = {}

def load_fourier_coefficients_from_file(filepath="coef_hours.txt"):
    """
    Load Fourier series coefficients from file.
    
    Args:
        filepath (str): Path to coefficients file
    
    Returns:
        dict: Dictionary with location/temperature combinations as keys
    """
    D = {
        "MTmadrid": {}, "MTotterup": {}, "MTtrondheim": {},
        "LTmadrid": {}, "LTotterup": {}, "LTtrondheim": {}
    }
    
    with open(filepath, "r", encoding="utf8") as file:
        for line in file.readlines():
            parts = line.split()
            coef_name = parts[0]
            D["MTmadrid"][coef_name] = float(parts[1])
            D["LTmadrid"][coef_name] = float(parts[2])
            D["MTotterup"][coef_name] = float(parts[3])
            D["LTotterup"][coef_name] = float(parts[4])
            D["MTtrondheim"][coef_name] = float(parts[5])
            D["LTtrondheim"][coef_name] = float(parts[6])
    
    return D

def fourier_series(coefs_dict, coef_names, period, x, location_code):
    """
    Compute Fourier series approximation.
    
    Args:
        coefs_dict (dict): Dictionary containing Fourier coefficients
        coef_names (list): List of coefficient names ['a1', 'b1', 'a2', 'b2', ..., 'c']
        period (float): Period of the function (24 for hours)
        x (float): Time value
        location_code (str): Code like 'MTmadrid', 'LTmadrid', etc.
    
    Returns:
        float: Fourier series value at x
    """
    y = 0
    for i in range(len(coef_names) // 2):
        a = coefs_dict[location_code][coef_names[2 * i]]
        b = coefs_dict[location_code][coef_names[2 * i + 1]]
        y += a * np.sin(2 * np.pi * (i + 1) * x / period) + \
             b * np.cos(2 * np.pi * (i + 1) * x / period)
    
    # Add constant term
    y += coefs_dict[location_code][coef_names[-1]]
    return y

def k_ambient_temperature(location_code, temp, a_t_dict, Q_nom_dict):
    """
    Compute temperature-dependent load factor.
    
    Args:
        location_code (str): Location code ('MTmadrid', etc.)
        temp (float or np.array): Ambient temperature(s)
        a_t_dict (dict): Temperature coefficients by location
        Q_nom_dict (dict): Nominal loads by location
    
    Returns:
        float or np.array: Load factor(s)
    """
    return np.where(temp > 0, a_t_dict[location_code] * temp + 1.0, 1.0)

def compute_refrigeration_load(temp, hour, location_code, 
                               coefs_dict, coef_names,
                               a_t_dict, Q_nom_dict):
    """
    Compute refrigeration load at given temperature and hour.
    
    Args:
        temp (float): Ambient temperature (°C)
        hour (float): Hour of day (0-23)
        location_code (str): Location/temperature code ('MTmadrid', 'LTmadrid', etc.)
        coefs_dict (dict): Fourier coefficients dictionary
        coef_names (list): Coefficient names
        a_t_dict (dict): Temperature factor coefficients
        Q_nom_dict (dict): Nominal loads
    
    Returns:
        float: Refrigeration load (kW)
    """
    k_hour = fourier_series(coefs_dict, coef_names, 24, float(hour), location_code)
    k_temp = k_ambient_temperature(location_code, temp, a_t_dict, Q_nom_dict)
    
    return Q_nom_dict[location_code] * k_temp * k_hour

def compute_hourly_load_by_day_type(hourly_T_df, classification_df, 
                                    location_code='MTmadrid',
                                    coef_hours_file='coef_hours.txt',
                                    output_csv=None):
    """
    Compute hourly refrigeration load for each day type based on temperature clustering.
    
    This function:
    1. Loads Fourier coefficients for load profile calculation
    2. For each day type (Low, Medium, High, Worst_day):
       - Extracts hourly temperatures
       - Computes refrigeration loads using Fourier series + temperature factors
       - Calculates mean hourly load profile
    3. Exports results to CSV if requested
    
    Args:
        hourly_T_df (pd.DataFrame): Hourly temperatures with date index and H00-H23 columns
        classification_df (pd.DataFrame): Day type classification with date index
        location_code (str): Location code ('MTmadrid', 'LTmadrid', 'MTotterup', etc.)
        coef_hours_file (str): Path to Fourier coefficients file
        output_csv (str or None): Path to save CSV output
    
    Returns:
        pd.DataFrame: Hourly load by day type (rows=hours 0-23, cols=Low/Medium/High/Worst_day)
    """
    
    # Load Fourier coefficients
    coefs_dict = load_fourier_coefficients_from_file(coef_hours_file)
    coef_names = ['a1', 'b1', 'a2', 'b2', 'a3', 'b3', 'a4', 'b4',
                  'a5', 'b5', 'a6', 'b6', 'a7', 'b7', 'a8', 'b8', 'c']
    
    # Environmental factors (temperature coefficients and nominal loads)
    a_t_dict = {
        'MTmadrid': 0.0698, 'LTmadrid': 0.0066,
        'MTotterup': 0.0370, 'LTotterup': 0.0107,
        'MTtrondheim': 0.0277, 'LTtrondheim': 0.0044
    }
    
    Q_nom_dict = {
        'MTmadrid': 35.59, 'LTmadrid': 35.92,
        'MTotterup': 8.94, 'LTotterup': 3.69,
        'MTtrondheim': 19.73, 'LTtrondheim': 4.00
    }
    
    # Align indices between temperature and classification dataframes
    common_dates = hourly_T_df.index.intersection(classification_df.index)
    hourly_T_df = hourly_T_df.loc[common_dates]
    classification_df = classification_df.loc[common_dates]
    
    # Compute loads for each day type
    hourly_load_by_type = {}
    
    for day_type in ['Low', 'Medium', 'High']:
        mask = (classification_df['day_type'] == day_type)
        type_temps = hourly_T_df[mask]
        
        if len(type_temps) > 0:
            # Compute loads for all hours and all days in this type
            loads_list = []
            for date_idx in type_temps.index:
                daily_loads = []
                for hour in range(24):
                    temp = type_temps.loc[date_idx, f'H{str(hour).zfill(2)}']
                    load = compute_refrigeration_load(
                        temp, hour, location_code,
                        coefs_dict, coef_names, a_t_dict, Q_nom_dict
                    )
                    daily_loads.append(load)
                loads_list.append(daily_loads)
            
            # Calculate mean hourly load for this day type
            loads_array = np.array(loads_list)
            hourly_load_by_type[day_type] = loads_array.mean(axis=0)
        else:
            hourly_load_by_type[day_type] = np.zeros(24)
    
    # Handle worst day separately
    worst_day_mask = (classification_df['day_type'] == 'Worst_day')
    if worst_day_mask.any():
        worst_day_idx = classification_df[worst_day_mask].index[0]
        worst_day_temps = hourly_T_df.loc[worst_day_idx]
        
        worst_day_loads = []
        for hour in range(24):
            temp = worst_day_temps[f'H{str(hour).zfill(2)}']
            load = compute_refrigeration_load(
                temp, hour, location_code,
                coefs_dict, coef_names, a_t_dict, Q_nom_dict
            )
            worst_day_loads.append(load)
        
        hourly_load_by_type['Worst_day'] = np.array(worst_day_loads)
    else:
        hourly_load_by_type['Worst_day'] = np.zeros(24)
    
    # Create output DataFrame
    output_df = pd.DataFrame({
        'hour': range(24),
        'Low': hourly_load_by_type['Low'],
        'Medium': hourly_load_by_type['Medium'],
        'High': hourly_load_by_type['High'],
        'Worst_day': hourly_load_by_type['Worst_day']
    })
    
    # Export to CSV if requested
    if output_csv is not None:
        output_df.to_csv(output_csv, index=False, encoding='utf-8', float_format='%.6f')
        print(f"Hourly refrigeration load by day type exported to {output_csv}")
    
    return output_df

def plot_hourly_load_by_day_type(load_df, save_path=None, show=True):
    """
    Plot hourly refrigeration load for each day type.
    
    Inspired by the plotting methodology from clustering_&_saving.py.
    Creates a line plot with 4 curves (Low, Medium, High, Worst_day),
    each with distinct colors.
    
    Args:
        load_df (pd.DataFrame): DataFrame with columns 'hour', 'Low', 'Medium', 'High', 'Worst_day'
        save_path (str or None): Path to save the figure; if None, does not save
        show (bool): Whether to display the figure
    """
    
    # Define colors for each day type
    color_map = {
        'Low': 'darkturquoise',
        'Medium': 'gold',
        'High': 'coral',
        'Worst_day': 'red'
    }
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    
    # Plot each day type
    for day_type in ['Low', 'Medium', 'High', 'Worst_day']:
        if day_type in load_df.columns:
            ax.plot(
                load_df['hour'],
                load_df[day_type],
                linewidth=2.5,
                label=day_type,
                color=color_map[day_type]
            )
    
    # Formatting
    ax.set_xlabel('Hour of the day', fontweight='bold', fontsize=12)
    ax.set_ylabel('Refrigeration Load (kW)', fontweight='bold', fontsize=12)
    ax.set_title('Hourly Refrigeration Load by Day Type', fontweight='bold', fontsize=14)
    
    # Grid and tick settings
    ax.grid(True, linestyle='--', alpha=0.7)
    ax.set_xticks(range(0, 24, 2))
    ax.tick_params(axis='y', direction='in')
    ax.tick_params(axis='x', direction='in')
    
    # Legend
    ax.legend(fontsize=11, loc='best', framealpha=0.9)
    
    plt.tight_layout()
    
    # Save if requested
    if save_path is not None:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {save_path}")
    
    # Show or close
    if show:
        plt.show()
    else:
        plt.close('all')


########################################### EXECUTION ZONE ##########################################

HOURLY_T_PATH = os.path.join(parent_dir, "clustering_and_T", "hourly_T_2024_Madrid.csv")
CLUSTERING_PATH = os.path.join(parent_dir, "outputs_external_time_series", "day_type_clustering.csv")
OUTPUT_LOAD_PATH = os.path.join(parent_dir, "outputs_external_time_series", "hourly_avg_Qload_clustered.csv")
PLOT_PATH = os.path.join(grandparent_dir, "explicative_plots", "clustered_external_time_series", "avg_hourly_load_clustered.png")

hourly_T_df = pd.read_csv(HOURLY_T_PATH, parse_dates=["Date"], index_col="Date")
classification_df = pd.read_csv(CLUSTERING_PATH, parse_dates=["Date"], index_col="Date")

# load_df = compute_hourly_load_by_day_type(
#     hourly_T_df, 
#     classification_df,
#     location_code='MTmadrid',
#     coef_hours_file='coef_hours.txt',
#     output_csv=OUTPUT_LOAD_PATH
# )

# plot_hourly_load_by_day_type(load_df, save_path=PLOT_PATH, show=True)