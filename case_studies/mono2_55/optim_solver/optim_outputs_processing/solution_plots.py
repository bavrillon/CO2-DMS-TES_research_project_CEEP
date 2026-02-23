"""
Extract data from Solution.xml file, build a DataFrame with MultiIndex (day_type, hour) and 
plot the results.
"""
import xml.etree.ElementTree as ET
import pandas as pd
import re
import matplotlib.pyplot as plt
import sys
import os

# Navigate to the root directory (codes_bastien)
root_dir = os.path.dirname(os.path.abspath(__file__))
for _ in range(4):  # 4 levels up
    root_dir = os.path.dirname(root_dir)
sys.path.insert(0, root_dir)

from CONSTANTS import *

parent_dir = os.path.dirname(os.path.abspath(__file__))
grandparent_dir = os.path.dirname(parent_dir)
greatgrandparent_dir = os.path.dirname(grandparent_dir)
SOLUTION_XML_PATH = os.path.join(grandparent_dir, "Solution.xml")
OUTPUT_CSV_PATH = os.path.join(greatgrandparent_dir, "detail_variables_optim.xlsx")
PLOTS_DIR = os.path.join(greatgrandparent_dir, 'plots')
DAT_FILE_PATH = os.path.join(grandparent_dir, 'system_data.dat')

# sys.argv = ['fichier.py', 'arg1', 'arg2']
OPTIM_SETTINGS_FILE_M1 = sys.argv[1]
OPTIM_SETTINGS_FILE_M2 = sys.argv[2]

PRECISION = 5  # Number of decimal places for rounding

####################################################### FUNCTIONS ##############################################################

## Data extraction, calculation and df construction functions

def extract_solution_to_dataframe(xml_file_path=SOLUTION_XML_PATH, precision=PRECISION, save_csv=True):
    """
    Extract data from Solution.xml file and build a DataFrame.
    
    Args:
        xml_file_path (str): Path to Solution.xml file
        precision (int): Number of decimal places to round the data
    Returns:
        pd.DataFrame: DataFrame with MultiIndex (day_type, hour) and columns = parameters
    """

    def parse_variable_name(name):
        """
        Extract parameter name, day_type and hour from a variable name.
        
        Example: 'Q_dot_CO2(Low,0)' -> ('Q_dot_CO2', 'Low', 0)
        
        Args:
            name (str): Variable name in the format 'param_name(day_type,hour)'
        
        Returns:
            tuple: (param_name, day_type, hour) or None if format doesn't match
        """
        # Pattern to extract param_name(day_type,hour)
        pattern = r'([a-zA-Z_][a-zA-Z0-9_]*)\(([A-Za-z_]+),(\d+)\)'
        match = re.match(pattern, name)
        
        if match:
            param_name = match.group(1)
            day_type = match.group(2)
            hour = int(match.group(3))
            return (param_name, day_type, hour)
        
        return None

    # Parse the XML file
    tree = ET.parse(xml_file_path)
    root = tree.getroot()
    
    # List of parameters to extract from XML
    params_to_extract = OUTPUT_VARIABLES
    
    # Define day_types and hours
    day_types = ['Low', 'Medium', 'High', 'Worst_day']
    hours = list(range(24))
    
    # Create a MultiIndex for the DataFrame
    index = pd.MultiIndex.from_product(
        [day_types, hours],
        names=['day_type', 'hour']
    )
    
    # Initialize the DataFrame with NaN
    df = pd.DataFrame(index=index, columns=params_to_extract, dtype=float)
    
    # Iterate through all variables in the XML file
    variables = root.find('variables')
    if variables is not None:
        for variable in variables.findall('variable'):
            name = variable.get('name')

            if 'b_mode' in name:
                value = int(abs(float(variable.get('value'))))  # Binary variable : integer 0 or 1
            else:
                value = float(variable.get('value'))

            # Parse the variable name
            parsed = parse_variable_name(name)
            if parsed is not None:
                param_name, day_type, hour = parsed
                
                # Check if parameter is in the list to extract
                if param_name in params_to_extract:
                    # Check if day_type and hour are valid
                    if day_type in day_types and hour in hours:
                        df.loc[(day_type, hour), param_name] = value
    
    # Calculate alpha = Q_dot_DMS_CO2 / Q_dot_CO2
    df['alpha'] = df['Q_dot_DMS_CO2'] / df['Q_dot_CO2']
    
    # Calculate beta = Q_dot_TES_CO2 / Q_dot_CO2
    df['beta'] = df['Q_dot_TES_CO2'] / df['Q_dot_CO2']

    df = df.round(precision) # Round to 4 decimal places
    
    if save_csv:
        # Save DataFrame to CSV
        df.to_csv(OUTPUT_CSV_PATH)
        print(f"DataFrame saved to '{OUTPUT_CSV_PATH}'")
    
    return df

def add_input_parameters_to_dataframe(param_names, param_file_path, precision=PRECISION, csv_df_path=OUTPUT_CSV_PATH):
    """
    Add supplementary parameters to the DataFrame stored in CSV. These parameters are not
    calculated by the solver and do not appear in Solution.xml, but rather are model
    input parameters. These optimal parameters are extracted from the solver's input CSV file.
    
    Args:
        param_names (list or str): List of parameter names to add (e.g., ['beta_max', 'COP_CO2_1'])
        precision (int): Number of decimal places to round the data
        param_file_path (str): Path to the input parameters CSV file 
                              (OPTIM_SETTINGS_FILE_M1 or OPTIM_SETTINGS_FILE_M2)
        csv_df_path (str): Path to the solution CSV file to update (default: OUTPUT_CSV_PATH)
    
    Returns:
        pd.DataFrame: Updated DataFrame with the new parameters added
    """
    # Read the input parameters CSV with MultiIndex structure (day_type, parameter)
    param_df = pd.read_csv(param_file_path, header=[0, 1], index_col=0)

    # Read the solution DataFrame
    solution_df = pd.read_csv(csv_df_path)

    # Ensure param_names is a list
    if isinstance(param_names, str):
        param_names = [param_names]

    # Extract day_types from the param_df columns (in order of appearance)
    day_types = []
    seen = set()
    for col in param_df.columns:
        day_type = col[0]
        if day_type not in seen:
            day_types.append(day_type)
            seen.add(day_type)

    # Reshape param_df to match solution_df structure
    param_data_list = []
    for hour in param_df.index:
        for day_type in day_types:
            row_data = {'day_type': day_type, 'hour': hour}
            for param_name in param_names:
                if (day_type, param_name) in param_df.columns:
                    row_data[param_name] = param_df.loc[hour, (day_type, param_name)]
            param_data_list.append(row_data)

    param_data_df = pd.DataFrame(param_data_list)

    # Merge with solution_df on (day_type, hour)
    solution_df = solution_df.merge(param_data_df, on=['day_type', 'hour'], how='left')

    # Ensure newly added columns are float
    for param_name in param_names:
        if param_name in solution_df.columns:
            solution_df[param_name] = pd.to_numeric(solution_df[param_name], errors='coerce').astype(float)

    # Round all float columns to the given precision (exclude 'hour')
    float_cols = solution_df.select_dtypes(include=['float64', 'float32']).columns.tolist()
    float_cols = [c for c in float_cols if c != 'hour']
    solution_df[float_cols] = solution_df[float_cols].round(precision)

    # Save the updated DataFrame
    solution_df.to_csv(csv_df_path, index=False)
    print(f"Parameters {param_names} added to '{csv_df_path}'")

    return solution_df

def add_parameters_from_dat_to_dataframe(param_names=DAT_PARAMETERS, dat_file_path=DAT_FILE_PATH, precision=PRECISION, csv_df_path=OUTPUT_CSV_PATH):
    """
    Read external time-series parameters directly from the AMPL .dat file and append them
    to the solution CSV. Expected parameters follow the pattern:

        param <name> :=
        [ 'Low', 0] <value>
        ...
        [ 'Worst_day', 23] <value>;

    Args:
        param_names (list | str): Parameter names to extract from the .dat file.
        dat_file_path (str): Path to the AMPL .dat file (default: DAT_FILE_PATH).
        precision (int): Number of decimal places to round the data.
        csv_df_path (str): Path to the solution CSV file to update.

    Returns:
        pd.DataFrame: Updated DataFrame with the external parameters added.
    """

    # Ensure param_names is a list
    if isinstance(param_names, str):
        param_names = [param_names]

    # Load current solution DataFrame
    solution_df = pd.read_csv(csv_df_path)

    # Load .dat content once
    with open(dat_file_path, "r", encoding="utf-8") as f:
        dat_content = f.read()

    def parse_param_block(param_name, content):
        """Extract (day_type, hour, value) tuples for a given param from the .dat text."""
        # Capture the block between "param <name> :=" and the terminating semicolon
        block_pattern = rf"param\s+{re.escape(param_name)}\s*:=\s*(.*?)\s*;"
        block_match = re.search(block_pattern, content, re.DOTALL)
        if not block_match:
            raise ValueError(f"Parameter '{param_name}' not found in {dat_file_path}")

        block = block_match.group(1)
        entry_pattern = r"\[\s*'?([^',]+)'?\s*,\s*(\d+)\s*\]\s*([-+]?\d*\.\d+(?:[eE][-+]?\d+)?|[-+]?\d+\.?(?:[eE][-+]?\d+)?)"
        entries = re.findall(entry_pattern, block)

        parsed = []
        for day_type, hour, value in entries:
            parsed.append((day_type.strip(), int(hour), float(value)))
        return parsed

    # Build mapping for each requested parameter
    for param in param_names:
        parsed_entries = parse_param_block(param, dat_content)
        value_map = {(day_type, hour): val for day_type, hour, val in parsed_entries}

        # Align values to existing day_type/hour rows; fallback to NaN when missing
        solution_df[param] = [
            value_map.get((day_type, hour), pd.NA)
            for day_type, hour in zip(solution_df['day_type'], solution_df['hour'])
        ]
    
    # Ensure newly added columns are float
    for param_name in param_names:
        if param_name in solution_df.columns:
            solution_df[param_name] = pd.to_numeric(solution_df[param_name], errors='coerce').astype(float)
    
    # Round all float columns to the given precision (exclude 'hour')
    float_cols = solution_df.select_dtypes(include=['float64', 'float32']).columns.tolist()
    float_cols = [c for c in float_cols if c != 'hour']
    solution_df[float_cols] = solution_df[float_cols].round(precision)

    # Persist updates
    solution_df.to_csv(csv_df_path, index=False)
    print(f"Parameters {param_names} added to '{csv_df_path}' from '{dat_file_path}'")

    return solution_df

def compute_parameters_in_dataframe(computed_param_names=COMPUTED_PARAMETERS, precision=PRECISION, csv_df_path=OUTPUT_CSV_PATH):
    """
    Compute real parameters from strategy-dependent inputs and append them to the CSV:
    - P_h = b_mode * P_h_2 + (1 - b_mode) * P_h_1
    - COP_DMS = b_mode * COP_DMS_CO2 + COP_DMS_TES[Q_dot_DMS_TES > 0.001]
    - COP_CO2 = b_mode * COP_CO2_2 + (1 - b_mode) * COP_CO2_1
    - COP_star = b_mode * COP_star_2 + (1 - b_mode) * COP_CO2_1
    - beta_max = b_mode * beta_2_max + (1 - b_mode) * beta_1_max
    
    Args:
        computed_param_names (list | str): Parameter names to compute.
        precision (int): Number of decimal places to round the data.
        csv_df_path (str): Path to the solution CSV file to update.
    
    Returns:
        pd.DataFrame: Updated DataFrame with computed parameters added.
    """

    if isinstance(computed_param_names, str):
        computed_param_names = [computed_param_names]

    df = pd.read_csv(csv_df_path)

    # Convenience views
    b_mode = df.get('b_mode')
    q_dms_tes = df.get('Q_dot_DMS_TES')

    if 'P_h' in computed_param_names:
        df['P_h'] = b_mode * df['P_h_2'] + (1 - b_mode) * df['P_h_1']

    if 'COP_DMS' in computed_param_names:
        df['COP_DMS'] = b_mode * df['COP_DMS_CO2'] + (q_dms_tes > 0.001).astype(float) * df['COP_DMS_TES']

    if 'COP_CO2' in computed_param_names:
        df['COP_CO2'] = b_mode * df['COP_CO2_2'] + (1 - b_mode) * df['COP_CO2_1']

    if 'COP_star' in computed_param_names:
        df['COP_star'] = b_mode * df['COP_star_2'] + (1 - b_mode) * df['COP_CO2_1']

    if 'beta_max' in computed_param_names:
        df['beta_max'] = b_mode * df['beta_2_max'] + (1 - b_mode) * df['beta_1_max']

    # Round all float columns to the given precision (exclude 'hour')
    float_cols = df.select_dtypes(include=['float64', 'float32']).columns.tolist()
    float_cols = [c for c in float_cols if c != 'hour']
    df[float_cols] = df[float_cols].round(precision)

    df.to_csv(csv_df_path, index=False)
    print(f"Computed parameters {computed_param_names} added to '{csv_df_path}'")
    return df

## Plotting functions

def plot_solution(x_names, csv_path=OUTPUT_CSV_PATH, saving_path=None, show=False, one_graph=False):
    """
    Plot parameters from the solution CSV file by day type and hour.
    
    Args:
        x_names (str or list): Column name(s) to plot from the CSV file
        csv_path (str): Path to the solution CSV file (default: OUTPUT_CSV_PATH)
        saving_path (str): Path to save the figure to disk (default: None)
        one_graph (bool): If True, plot all day types on a single graph with different colors.
                         If False, create subplots with one subplot per day type (default: False)
    """
    # Read CSV
    df = pd.read_csv(csv_path)
    
    # Ensure x_names is a list
    if isinstance(x_names, str):
        x_names = [x_names]
    
    # Get unique day types in order of appearance
    seen = set()
    day_types = []
    for day_type in df['day_type']:
        if day_type not in seen:
            day_types.append(day_type)
            seen.add(day_type)
    
    # Color mapping for day types
    color_map = {
        'Low': '#87CEEB',           # Light blue
        'Medium': '#DAA520',         # Dark yellow (goldenrod)
        'High': '#FF7F50',           # Coral orange
        'Worst_day': '#DC143C'       # Crimson red
    }
    
    # Unit mapping for common parameters
    unit_map = {
        'T_amb': '°C',
        'P_h': 'bar',
        'T_gc_out': '°C',
        'Q_dot_CO2': 'kW',
        'Q_dot_DMS_CO2': 'kW',
        'Q_dot_TES_CO2': 'kW',
        'Q_dot_DMS_TES': 'kW',
        'M_dot_CO2': 'kg/s',
        'M_dot_TES_charge': 'kg/s',
        'M_dot_TES_discharge': 'kg/s',
        'V_TES_hot': 'm³',
        'V_TES_cold': 'm³',
        'W_dot_comp_DMS': 'kW',
        'alpha': '–',
        'beta': '–',
        'COP_CO2_2': '–',
        'COP_CO2_1': '–',
        'COP_DMS_CO2': '–',
        'COP_DMS_TES': '–',
        'COP_star': '–',
        'beta_max': '–',
        'C_elec': '€/kWh',
        'b_mode': '–',
    }
    
    # For each parameter to plot
    for param_name in x_names:
        if param_name not in df.columns:
            print(f"Warning: '{param_name}' not found in CSV columns. Skipping.")
            continue
        
        unit = unit_map.get(param_name, '')
        ylabel = f'{param_name} ({unit})' if unit else param_name
        
        if one_graph:
            # Single graph with all day types
            fig, ax = plt.subplots(figsize=(12, 7))
            
            for day_type in day_types:
                day_type_data = df[df['day_type'] == day_type]
                hours = day_type_data['hour'].tolist()
                values_series = day_type_data[param_name].astype(float).copy()
                # For COP_DMS, skip plotting points where COP_DMS == 0 (DMS off)
                if param_name == 'COP_DMS':
                    values_series[values_series == 0] = float('nan')
                values = values_series.tolist()

                color = color_map.get(day_type, 'blue')
                ax.plot(hours, values, linewidth=2.5, 
                       color=color, label=day_type)
            
            ax.set_xlabel('Hour')
            ax.set_ylabel(ylabel)
            ax.set_title(f'{param_name} - All day types', pad=15)
            ax.grid(True, alpha=0.3)
            ax.set_xticks(range(0, 24, 2))
            ax.legend(loc='best', framealpha=0.9)
            
            plt.tight_layout()
            
        else:
            # Multiple subplots, one per day type
            fig, axes = plt.subplots(2, 2, figsize=(14, 11))
            axes = axes.flatten()
            
            # Plot for each day type
            for idx, day_type in enumerate(day_types):
                if idx < 4:  # Only plot if there are subplots available
                    day_type_data = df[df['day_type'] == day_type]
                    hours = day_type_data['hour'].tolist()
                    values_series = day_type_data[param_name].astype(float).copy()
                    # For COP_DMS, skip plotting points where COP_DMS == 0 (DMS off)
                    if param_name == 'COP_DMS':
                        values_series[values_series == 0] = float('nan')
                    values = values_series.tolist()

                    color = color_map.get(day_type, 'blue')
                    axes[idx].plot(hours, values, linewidth=2.5, color=color)
                    axes[idx].set_xlabel('Hour')
                    axes[idx].set_ylabel(ylabel)
                    axes[idx].set_title(f'{param_name} - {day_type}', pad=15)
                    axes[idx].grid(True, alpha=0.3)
                    axes[idx].set_xticks(range(0, 24, 2))
            
            plt.tight_layout(pad=3.0)
        
        if saving_path is not None:
            graph_type = 'one' if one_graph else 'subplots'
            filename = f'solution_{param_name}_{graph_type}.png'
            filepath = os.path.join(saving_path, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"Figure saved: {filepath}")
        
        if show:
            plt.show()
        else:
            plt.close('all')

def plot_beta_and_beta_max(day_type=['Low', 'Medium', 'High', 'Worst_day'], csv_path=OUTPUT_CSV_PATH, saving_path=None, show=False):
    """
    Plot `beta` and `beta_max` for each requested day type on separate subplots.

    Args:
        day_type (list): Day types to include (default: all four)
        csv_path (str): Path to the solution CSV file
        saving_path (str | None): Directory to save the figure; if None, does not save
        show (bool): Whether to display the figure interactively
    """
    # Read CSV
    df = pd.read_csv(csv_path)

    # Basic validations
    if 'beta' not in df.columns:
        print("Warning: 'beta' not found in CSV. Run extract_solution_to_dataframe() first.")
        return
    if 'beta_max' not in df.columns:
        print("Warning: 'beta_max' not found in CSV. Run compute_parameters_in_dataframe('beta_max') after adding 'beta_1_max'/'beta_2_max'.")
        # Proceed anyway with only beta

    # Preserve day type order as found in CSV, filter to requested ones
    seen = set()
    csv_order = []
    for dt in df['day_type']:
        if dt not in seen:
            seen.add(dt)
            csv_order.append(dt)
    selected_day_types = [dt for dt in csv_order if dt in day_type]
    if not selected_day_types:
        print("Warning: No matching day types found in CSV for the requested list.")
        return

    # Create subplots: up to 4 (2x2)
    n = len(selected_day_types)
    rows = 2
    cols = 2
    fig, axes = plt.subplots(rows, cols, figsize=(14, 11))
    axes = axes.flatten()

    # Color mapping for day types
    color_map = {
        'Low': '#87CEEB',           # Light blue
        'Medium': '#DAA520',         # Dark yellow (goldenrod)
        'High': '#FF7F50',           # Coral orange
        'Worst_day': '#DC143C'       # Crimson red
    }
    beta_max_color = '#000000'  # black

    # Plot per day type
    for idx, dt in enumerate(selected_day_types):
        ax = axes[idx]
        subset = df[df['day_type'] == dt].sort_values('hour')
        hours = subset['hour']
        beta_vals = subset['beta']
        beta_color = color_map.get(dt, '#1f77b4')  # fallback to blue if day_type unknown
        ax.plot(hours, beta_vals, linewidth=2.5, 
                color=beta_color, label='beta')

        if 'beta_max' in subset.columns:
            beta_max_vals = subset['beta_max']
            ax.plot(hours, beta_max_vals, linestyle='--', linewidth=2.2,
                    color=beta_max_color, label='beta_max')

            # Highlight exceedances (beta > beta_max)
            exceed_mask = (beta_vals > beta_max_vals)
            if exceed_mask.any():
                ax.scatter(hours[exceed_mask], beta_vals[exceed_mask], color='#DC143C',
                           s=40, zorder=3, label='exceedance')

        ax.set_xlabel('Hour')
        ax.set_ylabel('beta (–)')
        ax.set_title(f'beta vs beta_max - {dt}', pad=15)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(range(0, 24, 2))
        ax.legend(loc='best', framealpha=0.9)

    # Hide unused axes if fewer than 4 day types
    for j in range(len(selected_day_types), rows * cols):
        axes[j].set_visible(False)

    plt.tight_layout(pad=3.0)

    # Save if requested
    if saving_path is not None:
        filename = 'solution_beta_vs_beta_max.png'
        filepath = os.path.join(saving_path, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {filepath}")

    # Show or close
    if show:
        plt.show()
    else:
        plt.close('all')

def plot_load_real_distribution(day_type=['Low', 'Medium', 'High', 'Worst_day'], csv_path=OUTPUT_CSV_PATH, saving_path=None, show=False):
    """
    Plot load distribution among CO2, DMS_CO2, and TES_CO2 for each requested day type.
    One subplot per day type."""
    df = pd.read_csv(csv_path)

    required_cols = ['day_type', 'hour', 'Q_dot_CO2', 'Q_dot_DMS_CO2', 'Q_dot_TES_CO2']
    for col in required_cols:
        if col not in df.columns:
            print(f"Warning: '{col}' not found in CSV. Run extract_solution_to_dataframe() first.")
            return

    # Preserve CSV day type order and filter to requested ones
    seen = set()
    csv_order = []
    for dt in df['day_type']:
        if dt not in seen:
            seen.add(dt)
            csv_order.append(dt)
    if isinstance(day_type, str):
        day_type = [day_type]
    selected_day_types = [dt for dt in csv_order if dt in day_type]
    if not selected_day_types:
        print("Warning: No matching day types found in CSV for the requested list.")
        return

    fig, axes = plt.subplots(2, 2, figsize=(14, 11))
    axes = axes.flatten()

    color_map = {
        'Q_dot_CO2': "#5daee9",      # base
        'Q_dot_DMS_CO2': "#f0a564",  # middle
        'Q_dot_TES_CO2': "#66C566",  # top
    }

    for idx, dt in enumerate(selected_day_types):
        if idx >= len(axes):
            break
        ax = axes[idx]
        subset = df[df['day_type'] == dt].sort_values('hour')
        hours = subset['hour']

        co2 = subset['Q_dot_CO2']
        dms = subset['Q_dot_DMS_CO2']
        tes = subset['Q_dot_TES_CO2']

        co2_label = 'CO2 unsubcooled'
        dms_label = 'DMS'
        tes_label = 'TES subcooling'
        load_label = 'Total load'

        ax.bar(hours, co2, color=color_map['Q_dot_CO2'], label=co2_label)
        ax.bar(hours, dms, bottom=co2, color=color_map['Q_dot_DMS_CO2'], label=dms_label)
        ax.bar(hours, tes, bottom=co2 + dms, color=color_map['Q_dot_TES_CO2'], label=tes_label)

        ax.plot(hours, subset['Q_dot_load'], color='black', linewidth=1.8, linestyle='--', label=load_label)

        ax.set_xlabel('Hour')
        ax.set_ylabel('Q_dot (kW)')
        ax.set_title(f'Load distribution - {dt}', pad=15)
        ax.grid(True, alpha=0.3)
        ax.set_xticks(range(0, 24, 2))
        handles, labels = ax.get_legend_handles_labels()
        order = [load_label, co2_label, dms_label, tes_label]
        ordered_handles = [h for l, h in zip(labels, handles) if l in order]
        label_map = dict(zip(labels, handles))
        ordered_handles = [label_map[l] for l in order if l in label_map]
        ordered_labels = [l for l in order if l in label_map]
        ax.legend(ordered_handles, ordered_labels, loc='best', framealpha=0.9)

    # Hide unused axes
    for j in range(len(selected_day_types), len(axes)):
        axes[j].set_visible(False)

    plt.tight_layout(pad=3.0)

    if saving_path is not None:
        filename = 'solution_load_distribution.png'
        filepath = os.path.join(saving_path, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {filepath}")

    if show:
        plt.show()
    else:
        plt.close('all')


########################### EXECUTION ZONE - Order of execution matters ############################

## Creation of a CSV file with all VARIABLES
extract_solution_to_dataframe()

## Addition of input parameters of the optimization) to the CSV file
add_input_parameters_to_dataframe(['T_amb', 'T_gc_out', 'P_h_1'], OPTIM_SETTINGS_FILE_M1)
add_input_parameters_to_dataframe(['P_h_2', 'COP_star_2'], OPTIM_SETTINGS_FILE_M2)
add_parameters_from_dat_to_dataframe()

## Compute the real parameters given the strategy adopted by the optimization at each time step
## (ex: COP_CO2 = b_mode * COP_CO2_2 + (1 - b_mode) * COP_CO2_1 )
compute_parameters_in_dataframe()

## Plotting of parameters (ALL_PARAMETERS) from the CSV file (one plot with all day types per parameter)
plot_solution(ALL_PARAMETERS, saving_path=PLOTS_DIR, show=False, one_graph=True)

plot_beta_and_beta_max(saving_path=PLOTS_DIR, show=False)

plot_load_real_distribution(show=False, saving_path=PLOTS_DIR)