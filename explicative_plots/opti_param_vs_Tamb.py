"""This code aims to plot several explicative graphs showing the evolution of some optimized parameters,
as a function of ambient temperature. The strategy is to extract all (T_amb, param) pairs from the CSV file 
created by compute_all_settings.py and then plot them. Thus, additionnal computations are not required here."""

import pandas as pd
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cycles import *
from CONSTANTS import *


def get_pairs(param_1, param_2='T_amb', csv_file_path=M1_SETTINGS_FILE_PATH):
    """
    Extract all (param_2, param_1) pairs from the CSV file.
    
    The CSV has a MultiIndex structure with day_types (Low, Medium, High, Worst_day)
    and parameters (T_amb, T_gc_out, P_h_1, COP_CO2_1, ...). Each day_type
    appears at different hours (0-23), resulting in 96 total pairs.
    
    Args:
        param_1 (str): First parameter name to extract (e.g., 'COP_CO2_1', 'P_h_1')
        param_2 (str): Second parameter name to extract (default: 'T_amb')
        csv_file_path (str): Path to the file Mi_optim_settings.csv file
    
    Returns:
        dict: Dictionary with param_2 values as keys and param_1 values as values.
              Multiple entries may share the same param_2 value (from different day_types/hours).
    """
    # Read the CSV with MultiIndex columns (day_type, parameter)
    df = pd.read_csv(csv_file_path, header=[0, 1], index_col=0)
    
    # Dictionary to store param_2 -> param_1 pairs
    pairs_dict = {}
    
    # Extract day_types (first level of column MultiIndex)
    day_types = []
    seen = set()
    for col in df.columns:
        day_type = col[0]
        if day_type not in seen:
            day_types.append(day_type)
            seen.add(day_type)
    
    # Iterate through each day_type and hour to collect (param_2, param_1) pairs
    for day_type in day_types:
        
        # Get param_2 column for this day_type
        if (day_type, param_2) in df.columns:
            param_2_col = df[(day_type, param_2)]
            
            # Get param_1 column for this day_type
            if (day_type, param_1) in df.columns:
                param_1_col = df[(day_type, param_1)]
                
                # Pair them up and store in dictionary
                for hour in param_2_col.index:
                    param_2_val = param_2_col.loc[hour]
                    param_1_val = param_1_col.loc[hour]
                    pairs_dict[param_2_val] = param_1_val
    
    return pairs_dict

############################################# COP_CO2_1 = f(T_amb) #############################################

COP_CO2_1_POLY_DEGREE = 3

def plot_COP_CO2_1_vs_Tamb(pairs_dict, polynomial_regression=False):
    """
    Plot COP_CO2_1 vs T_amb using the provided pairs dictionary.
    
    Args:
        pairs_dict (dict): Dictionary with T_amb (K) as keys and COP_CO2_1 as values.
        polynomial_regression (bool): If True, compute and plot a 3rd degree polynomial regression.
    """
    # Extract T_amb and COP_CO2_1 values
    T_amb_values = np.array(list(pairs_dict.keys()))
    COP_CO2_1_values = np.array(list(pairs_dict.values()))
    
    # Convert to Celsius for plotting
    T_amb_celsius = T_amb_values - 273.15
    
    # Create scatter plot
    plt.figure(figsize=(10, 7))
    plt.scatter(T_amb_celsius, COP_CO2_1_values, color='blue', alpha=0.6, s=50, label='Data points')
    
    # Polynomial regression if requested
    if polynomial_regression:
        # Fit polynomial of specified degree
        coeffs = np.polyfit(T_amb_celsius, COP_CO2_1_values, COP_CO2_1_POLY_DEGREE)
        poly_func = np.poly1d(coeffs)
        
        # Create smooth curve for plotting
        T_amb_smooth = np.linspace(T_amb_celsius.min(), T_amb_celsius.max(), 200)
        COP_fitted = poly_func(T_amb_smooth)
        
        # Plot regression curve
        plt.plot(T_amb_smooth, COP_fitted, 'r-', linewidth=2.5, 
                label=f'Polynomial regression (degree {COP_CO2_1_POLY_DEGREE})')
        
        # Print equation in console
        print(f"Polynomial regression equation (T in °C):")
        equation_console = "COP_CO2_1 = "
        for i, coeff in enumerate(coeffs):
            power = COP_CO2_1_POLY_DEGREE - i
            if power > 0:
                equation_console += f"{coeff:.6e}·T^{power} + "
            else:
                equation_console += f"{coeff:.6e}"
        print(equation_console)
        
        # Display equation on graph - dynamic based on degree
        equation_lines = [f"$COP_{{CO_2}}^{{Std}} = {coeffs[0]:.6f} \\cdot T^{{{COP_CO2_1_POLY_DEGREE}}}$"]
        
        for i in range(1, COP_CO2_1_POLY_DEGREE):
            power = COP_CO2_1_POLY_DEGREE - i
            precision = max(3, 7 - i)  # Adjust precision based on term
            equation_lines.append(f"$\\quad + {coeffs[i]:.{precision}f} \\cdot T^{{{power}}}$")
        
        # Constant term
        equation_lines.append(f"$\\quad + {coeffs[-1]:.3f}$")
        
        equation_text = "\n".join(equation_lines)
        
        plt.text(0.98, 0.35, equation_text, transform=plt.gca().transAxes,
                fontsize=9, verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.85, edgecolor='gray'))
    
    plt.title('COP_CO2_1 vs Ambient air temperature (T_amb)', fontsize=14, pad=15)
    plt.xlabel('Ambient air temperature T_amb (°C)', fontsize=12)
    plt.ylabel('COP_CO2_1', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 40)
    plt.ylim(0, max(COP_CO2_1_values) + 1)
    plt.legend(loc='best', fontsize=11)
    plt.tight_layout()
    plt.show()

    return coeffs if polynomial_regression else None # Return coefficients with a descending order

# data_COP_CO2_1 = get_pairs('COP_CO2_1')
# plot_COP_CO2_1_vs_Tamb(data_COP_CO2_1, polynomial_regression=True)

############################################# P_h_opt_1 = f(T_amb) #############################################

def plot_P_h_opt_1_vs_Tamb(pairs_dict, linear_regression=False):
    """
    Plot P_h_opt_1 vs T_amb using the provided pairs dictionary.
    
    Args:
        pairs_dict (dict): Dictionary with T_amb (K) as keys and P_h_1 as values (in Pa).
        linear_regression (bool): If True, compute and plot piecewise linear regression with breakpoint at T_AMB_MAX_SUBCRITICAL.
    """
    # Extract T_amb and P_h_1 values
    T_amb_values = np.array(list(pairs_dict.keys()))
    P_h_1_values = np.array(list(pairs_dict.values()))
    
    # Convert to Celsius for plotting
    T_amb_celsius = T_amb_values - 273.15
    
    # Convert pressure from Pa to bar
    P_h_1_bar = P_h_1_values / 100000
    
    # Create scatter plot
    plt.figure(figsize=(10, 7))
    plt.scatter(T_amb_celsius, P_h_1_bar, color='green', alpha=0.6, s=50, label='Data points')
    
    # Piecewise linear regression if requested
    if linear_regression:
        # Convert T_AMB_MAX_SUBCRITICAL from K to °C
        T_limit_celsius = T_AMB_MAX_SUBCRITICAL - 273.15
        
        # Split data into two regions
        mask_before = T_amb_celsius <= T_limit_celsius
        mask_after = T_amb_celsius > T_limit_celsius
        
        T_before = T_amb_celsius[mask_before]
        P_before = P_h_1_bar[mask_before]
        
        T_after = T_amb_celsius[mask_after]
        P_after = P_h_1_bar[mask_after]
        
        # Fit linear regression for each region
        equation_lines = []
        colors = ['red', 'orange']
        
        for i, (T_data, P_data, mask, color) in enumerate([(T_before, P_before, mask_before, colors[0]),
                                                              (T_after, P_after, mask_after, colors[1])]):
            if len(T_data) > 1:
                # Fit polynomial of degree 1 (linear)
                coeffs = np.polyfit(T_data, P_data, 1)
                poly_func = np.poly1d(coeffs)
                
                # Create smooth curve for plotting
                T_smooth = np.linspace(T_data.min(), T_data.max(), 100)
                P_fitted = poly_func(T_smooth)
                
                # Plot regression line
                label = f'Subcritical cycle (T ≤ {T_limit_celsius:.1f}°C)' if i == 0 else f'Supercritical cycle (T > {T_limit_celsius:.1f}°C)'
                plt.plot(T_smooth, P_fitted, color=color, linewidth=2.5, label=label)
                
                # Store equation
                cycle_name = 'Subcritical' if i == 0 else 'Supercritical'
                equation_lines.append(f"{cycle_name} cycle: $P_h = {coeffs[0]:.4f} \\cdot T + {coeffs[1]:.2f}$ bar")
        
        # Display equations on graph
        equation_text = "\n".join(equation_lines)
        plt.text(0.98, 0.05, equation_text, transform=plt.gca().transAxes,
                fontsize=9, verticalalignment='bottom', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.85, edgecolor='gray'))
        
        # Add vertical line at T_AMB_MAX_SUBCRITICAL
        plt.axvline(x=T_limit_celsius, color='gray', linestyle='--', linewidth=1.5, alpha=0.7, label=f'T_AMB_MAX_SUBCRITICAL = {T_limit_celsius:.1f}°C')
    
    plt.title('P_h_opt_1 vs Ambient air temperature (T_amb)', fontsize=14, pad=15)
    plt.xlabel('Ambient air temperature T_amb (°C)', fontsize=12)
    plt.ylabel('P_h_opt_1 (bar)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 40)
    plt.ylim(0, max(P_h_1_bar) + 0.5)
    plt.legend(loc='best', fontsize=11)
    plt.tight_layout()
    plt.show()

# data_P_h_opt_1 = get_pairs('P_h_1')
# plot_P_h_opt_1_vs_Tamb(data_P_h_opt_1, linear_regression=True)

############################################# T_gc_out = f(T_amb) #############################################

def plot_T_gc_out_vs_Tamb(pairs_dict, linear_regression=False):
    """
    Plot T_gc_out (which is the same in both MODE 1 and MODE 2) vs T_amb using the provided pairs dictionary.
    
    Args:
        pairs_dict (dict): Dictionary with T_amb (K) as keys and T_gc_out as values.
        linear_regression (bool): If True, compute and plot piecewise linear regression with breakpoint at T_AMB_MAX_SUBCRITICAL.
    """
    # Extract T_amb and T_gc_out values
    T_amb_values = np.array(list(pairs_dict.keys()))
    T_gc_out_values = np.array(list(pairs_dict.values()))
    T_gc_out_values_celsius = T_gc_out_values - 273.15
    
    # Convert to Celsius for plotting
    T_amb_celsius = T_amb_values - 273.15
    
    # Create scatter plot
    plt.figure(figsize=(10, 7))
    plt.scatter(T_amb_celsius, T_gc_out_values_celsius, color='green', alpha=0.6, s=50, label='Data points')
    
    # Piecewise linear regression if requested
    if linear_regression:
        # Convert T_AMB_MAX_SUBCRITICAL from K to °C
        T_limit_celsius = T_AMB_MAX_SUBCRITICAL - 273.15
        
        # Split data into two regions
        mask_before = T_amb_celsius <= T_limit_celsius
        mask_after = T_amb_celsius > T_limit_celsius
        
        T_before = T_amb_celsius[mask_before]
        P_before = T_gc_out_values_celsius[mask_before]
        
        T_after = T_amb_celsius[mask_after]
        P_after = T_gc_out_values_celsius[mask_after]
        
        # Fit linear regression for each region
        equation_lines = []
        colors = ['red', 'orange']
        
        for i, (T_data, P_data, mask, color) in enumerate([(T_before, P_before, mask_before, colors[0]),
                                                              (T_after, P_after, mask_after, colors[1])]):
            if len(T_data) > 1:
                # Fit polynomial of degree 1 (linear)
                coeffs = np.polyfit(T_data, P_data, 1)
                poly_func = np.poly1d(coeffs)
                
                # Create smooth curve for plotting
                T_smooth = np.linspace(T_data.min(), T_data.max(), 100)
                P_fitted = poly_func(T_smooth)
                
                # Plot regression line
                label = f'Subcritical cycle (T ≤ {T_limit_celsius:.1f}°C)' if i == 0 else f'Supercritical cycle (T > {T_limit_celsius:.1f}°C)'
                plt.plot(T_smooth, P_fitted, color=color, linewidth=2.5, label=label)
                
                # Store equation
                cycle_name = 'Subcritical' if i == 0 else 'Supercritical'
                equation_lines.append(f"{cycle_name} cycle: $T_{{gc out}} = {coeffs[0]:.2f} \\cdot T + {coeffs[1]:.0f}$ °C")
        
        # Display equations on graph
        equation_text = "\n".join(equation_lines)
        plt.text(0.98, 0.05, equation_text, transform=plt.gca().transAxes,
                fontsize=9, verticalalignment='bottom', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.85, edgecolor='gray'))
        
        # Add vertical line at T_AMB_MAX_SUBCRITICAL
        plt.axvline(x=T_limit_celsius, color='gray', linestyle='--', linewidth=1.5, alpha=0.7, label=f'T_AMB_MAX_SUBCRITICAL = {T_limit_celsius:.1f}°C')
    
    plt.title('T_gc_out vs Ambient air temperature (T_amb)', fontsize=14, pad=15)
    plt.xlabel('Ambient air temperature T_amb (°C)', fontsize=12)
    plt.ylabel('T_gc_out (°C)', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 40)
    plt.ylim(min(T_gc_out_values_celsius) - 10, max(T_gc_out_values_celsius) + 10)
    plt.legend(loc='best', fontsize=11)
    plt.tight_layout()
    plt.show()

# data_T_gc_out = get_pairs('T_gc_out')
# plot_T_gc_out_vs_Tamb(data_T_gc_out, linear_regression=True)

############################################# COP_DMS_TES = f(T_amb) #############################################

COP_DMS_TES_POLY_DEGREE = 3

def plot_COP_DMS_TES_vs_Tamb(pairs_dict, polynomial_regression=False):
    """
    Plot COP_DMS_TES vs T_amb using the provided pairs dictionary.
    
    Args:
        pairs_dict (dict): Dictionary with T_amb (K) as keys and COP_DMS_TES as values.
        polynomial_regression (bool): If True, compute and plot a 3rd degree polynomial regression.
    """
    # Extract T_amb and COP_DMS_TES values
    T_amb_values = np.array(list(pairs_dict.keys()))
    COP_DMS_TES_values = np.array(list(pairs_dict.values()))
    
    # Convert to Celsius for plotting
    T_amb_celsius = T_amb_values - 273.15
    
    # Create scatter plot
    plt.figure(figsize=(10, 7))
    plt.scatter(T_amb_celsius, COP_DMS_TES_values, color='purple', alpha=0.6, s=50, label='Data points')
    
    # Polynomial regression if requested
    if polynomial_regression:
        # Fit polynomial of specified degree
        coeffs = np.polyfit(T_amb_celsius, COP_DMS_TES_values, COP_DMS_TES_POLY_DEGREE)
        poly_func = np.poly1d(coeffs)
        
        # Create smooth curve for plotting
        T_amb_smooth = np.linspace(T_amb_celsius.min(), T_amb_celsius.max(), 200)
        COP_fitted = poly_func(T_amb_smooth)
        
        # Plot regression curve
        plt.plot(T_amb_smooth, COP_fitted, 'r-', linewidth=2.5, 
                label=f'Polynomial regression (degree {COP_DMS_TES_POLY_DEGREE})')
        
        # Print equation in console
        print(f"Polynomial regression equation (T in °C):")
        equation_console = "COP_DMS_TES = "
        for i, coeff in enumerate(coeffs):
            power = COP_DMS_TES_POLY_DEGREE - i
            if power > 0:
                equation_console += f"{coeff:.6e}·T^{power} + "
            else:
                equation_console += f"{coeff:.6e}"
        print(equation_console)
        
        # Display equation on graph - dynamic based on degree
        equation_lines = [f"$COP_{{DMS\\_TES}} = {coeffs[0]:.6f} \\cdot T^{{{COP_DMS_TES_POLY_DEGREE}}}$"]
        
        for i in range(1, COP_DMS_TES_POLY_DEGREE):
            power = COP_DMS_TES_POLY_DEGREE - i
            precision = max(3, 7 - i)  # Adjust precision based on term
            equation_lines.append(f"$\\quad + {coeffs[i]:.{precision}f} \\cdot T^{{{power}}}$")
        
        # Constant term
        equation_lines.append(f"$\\quad + {coeffs[-1]:.3f}$")
        
        equation_text = "\n".join(equation_lines)
        
        plt.text(0.98, 0.35, equation_text, transform=plt.gca().transAxes,
                fontsize=9, verticalalignment='top', horizontalalignment='right',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.85, edgecolor='gray'))
    
    plt.title('COP_DMS_TES vs Ambient air temperature (T_amb)', fontsize=14, pad=15)
    plt.xlabel('Ambient air temperature T_amb (°C)', fontsize=12)
    plt.ylabel('COP_DMS_TES', fontsize=12)
    plt.grid(True, alpha=0.3)
    plt.xlim(0, 40)
    plt.ylim(0, max(COP_DMS_TES_values) + 1)
    plt.legend(loc='best', fontsize=11)
    plt.tight_layout()
    plt.show()

    return coeffs if polynomial_regression else None # Return coefficients with a descending order

# data_COP_DMS_TES = get_pairs('COP_DMS_TES')
# plot_COP_DMS_TES_vs_Tamb(data_COP_DMS_TES, polynomial_regression=True)

