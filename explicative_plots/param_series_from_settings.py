"""
This module contains functions to plot the evolution of the pre-calculated 
optimal parameters over hours for each day type, for both M1 and M2 cycles. 
It reads the optimization settings from CSV files, extracts the relevant 
parameters, and creates line plots to visualize how these parameters change.
The parameters that are plotted 
"""
import os
import sys
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cycles import *
from CONSTANTS import *


CASE = 'mono2_45'
CASE_DIRECTORY = os.path.join(CASE_STUDIES_SAVING_DIR, CASE, 'thermo_optim_inputs')
CASE_PLOTS_DIRECTORY = os.path.join(CASE_STUDIES_SAVING_DIR, CASE, 'plots', 'pre-calculated_parameters_series')
OPTI_SETTINGS_FILE_M1 = os.path.join(CASE_DIRECTORY, 'thermo_settings_M1.csv')
OPTI_SETTINGS_FILE_M2 = os.path.join(CASE_DIRECTORY, 'thermo_settings_M2.csv')

def plot_param_M1_series_by_daytype(parameter_name, csv_path=OPTI_SETTINGS_FILE_M1, saving=False, one_graph=False):
    """
    Plot the evolution of a parameter over hours for each day type, for standard cycle.
    parameter_name : str
        One of 'T_amb', 'T_gc_out', 'P_h_1', 'COP_CO2_1', 'delta_h_CO2_1', 'beta_1_max', 'COP_DMS_TES'
    one_graph : bool, default False
        If True, plot all day types on a single graph with different colors.
        If False, create subplots with one subplot per day type.
    """
    # Read CSV with MultiIndex structure
    df = pd.read_csv(csv_path, header=[0, 1], index_col=0)
    df.index.name = 'hour'
    
    # Get unique day types (first level of MultiIndex) in order of appearance
    seen = set()
    day_types = []
    for col in df.columns:
        day_type = col[0]
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
    
    # Unit mapping for parameters
    unit_map = {
        'T_amb': '°C',
        'P_h_1': 'bar',
        'T_gc_out': '°C',
        'delta_h_CO2_1': 'kJ/kg',
        'beta_1_max': '–',
        'COP_CO2_1': '–',
        'COP_DMS_TES': '–',
    }
    
    unit = unit_map.get(parameter_name, '')
    ylabel = f'{parameter_name} ({unit})' if unit else parameter_name
    
    if one_graph:
        # Single graph with all day types
        fig, ax = plt.subplots(figsize=(12, 7))
        
        hours = df.index.tolist()
        
        for day_type in day_types:
            values = df[(day_type, parameter_name)].tolist()
            
            # Convert P_h_opt from Pa to bar
            if parameter_name == 'P_h_1':
                values = [v / 1e5 for v in values]

            # Convert temperatures from K to °C
            if parameter_name in ['T_amb', 'T_gc_out']:
                values = [v - 273.15 for v in values]
            
            color = color_map.get(day_type, 'blue')
            ax.plot(hours, values, marker='o', linewidth=2.5, markersize=6, 
                   color=color, label=day_type)
        
        ax.set_xlabel('Hour')
        ax.set_ylabel(ylabel)
        ax.set_title(f'{parameter_name} - All day types', pad=15)
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
                hours = df.index.tolist()
                values = df[(day_type, parameter_name)].tolist()
                
                # Convert P_h_opt from Pa to bar
                if parameter_name == 'P_h_1':
                    values = [v / 1e5 for v in values]

                # Convert temperatures from K to °C
                if parameter_name in ['T_amb', 'T_gc_out']:
                    values = [v - 273.15 for v in values]
                
                color = color_map.get(day_type, 'blue')
                axes[idx].plot(hours, values, marker='o', linewidth=2.5, markersize=6, color=color)
                axes[idx].set_xlabel('Hour')
                axes[idx].set_ylabel(ylabel)
                axes[idx].set_title(f'{parameter_name} - {day_type}', pad=15)
                axes[idx].grid(True, alpha=0.3)
                axes[idx].set_xticks(range(0, 24, 2))
        
        plt.tight_layout(pad=3.0)
    
    if saving:
        os.makedirs(CASE_PLOTS_DIRECTORY, exist_ok=True)
        graph_type = 'one' if one_graph else 'subplots'
        filename = f'parameter_series_M1_{parameter_name}_{graph_type}.png'
        filepath = os.path.join(CASE_PLOTS_DIRECTORY, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {filepath}")
    
    plt.show()

def plot_param_M2_series_by_daytype(parameter_name, csv_path=OPTI_SETTINGS_FILE_M2, saving=False, one_graph=False):
    """
    Plot the evolution of a parameter over hours for each day type, for M2 cycle.
    parameter_name : str
        One of 'T_amb', 'T_gc_out', 'P_h_2', 'alpha', 'delta_h_CO2_2', 'beta_2_max', 
                'COP_star_2', 'COP_CO2_2', 'COP_DMS_CO2'
        Or additionnal useful parameters : 'COP_CO2_2/COP_DMS_CO2'
    one_graph : bool, default False
        If True, plot all day types on a single graph with different colors.
        If False, create subplots with one subplot per day type.
    """
    # Read CSV with MultiIndex structure
    df = pd.read_csv(csv_path, header=[0, 1], index_col=0)
    df.index.name = 'hour'
    
    # Get unique day types (first level of MultiIndex) in order of appearance
    seen = set()
    day_types = []
    for col in df.columns:
        day_type = col[0]
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
    
    # Unit mapping for parameters
    unit_map = {
        'T_amb': '°C',
        'P_h_2': 'bar',
        'T_gc_out': '°C',
        'alpha': '–',
        'COP_star_2': '–',
        'COP_CO2_2': '–',
        'COP_DMS_CO2': '–',
        'delta_h_CO2_2': 'kJ/kg',
        'beta_2_max': '–',
        'COP_CO2_2/COP_DMS_CO2': '–',
    }
    
    unit = unit_map.get(parameter_name, '')
    ylabel = f'{parameter_name} ({unit})' if unit else parameter_name
    
    if one_graph:
        # Single graph with all day types
        fig, ax = plt.subplots(figsize=(12, 7))
        
        hours = df.index.tolist()
        
        for day_type in day_types:
            if parameter_name == 'COP_CO2_2/COP_DMS_CO2':
                values = (df[(day_type, 'COP_CO2_2')] / df[(day_type, 'COP_DMS_CO2')]).tolist()
            else:
                values = df[(day_type, parameter_name)].tolist()
            
            # Convert P_h_opt from Pa to bar
            if parameter_name == 'P_h_2':
                values = [v / 1e5 for v in values]

            # Convert temperatures from K to °C
            if parameter_name in ['T_amb', 'T_gc_out']:
                values = [v - 273.15 for v in values]

            color = color_map.get(day_type, 'blue')
            ax.plot(hours, values, linewidth=2.5,  
                   color=color, label=day_type)
        
        ax.set_xlabel('Hour')
        ax.set_ylabel(ylabel)
        ax.set_title(f'{parameter_name} - All day types', pad=15)
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
                hours = df.index.tolist()
                values = df[(day_type, parameter_name)].tolist()
                
                # Convert P_h_opt from Pa to bar
                if parameter_name == 'P_h_2':
                    values = [v / 1e5 for v in values]

                # Convert temperatures from K to °C
                if parameter_name in ['T_amb', 'T_gc_out']:
                    values = [v - 273.15 for v in values]
                
                unit = unit_map.get(parameter_name, '')
                ylabel = f'{parameter_name} ({unit})' if unit else parameter_name
                
                color = color_map.get(day_type, 'blue')
                axes[idx].plot(hours, values, linewidth=2.5, color=color)
                axes[idx].set_xlabel('Hour')
                axes[idx].set_ylabel(ylabel)
                axes[idx].set_title(f'{parameter_name} - {day_type}', pad=15)
                axes[idx].grid(True, alpha=0.3)
                axes[idx].set_xticks(range(0, 24, 2))
        
        plt.tight_layout(pad=3.0)
    
    if saving:
        os.makedirs('plots', exist_ok=True)
        graph_type = 'one' if one_graph else 'subplots'
        filename = f'parameter_series_M2_{parameter_name}_{graph_type}.png'
        filepath = os.path.join(CASE_PLOTS_DIRECTORY, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {filepath}")
    
    plt.show()

def plot_load_distribution_cycle(mode='both', csv_input_path_M1=OPTI_SETTINGS_FILE_M1, csv_input_path_M2=OPTI_SETTINGS_FILE_M2, saving=False):
    """
    Plot the load distribution between CO2 cycle, DMS (M2), and TES (M1 and M2) for each day type.
    
    Mode M1 (Standard cycle with TES only):
    - CO2 cycle share: 1/(1+beta_1)
    - TES share: beta_1/(1+beta_1)
    
    Mode M2 (ComplexSystem with DMS and TES):
    - CO2 cycle share: 1/(1+alpha+beta_2)
    - DMS share: alpha/(1+alpha+beta_2)
    - TES share: beta_2/(1+alpha+beta_2)
    
    Parameters:
    -----------
    mode : str, default 'both'
        'M1' to plot M1 only, 'M2' to plot M2 only, 'both' to plot M1 then M2
    csv_input_path_M1 : str
        Path to M1 optimization settings CSV
    csv_input_path_M2 : str
        Path to M2 optimization settings CSV
    saving : bool, default False
        If True, save the plot to disk
    """
    
    if mode == 'both':
        # Call M1 and M2 separately
        plot_load_distribution_cycle(mode='M1', csv_input_path_M1=csv_input_path_M1, 
                                    csv_input_path_M2=csv_input_path_M2, saving=saving)
        plot_load_distribution_cycle(mode='M2', csv_input_path_M1=csv_input_path_M1, 
                                    csv_input_path_M2=csv_input_path_M2, saving=saving)
        return
    
    # Color mapping for the components
    component_colors = {
        'CO2 cycle': '#1f77b4',    # Blue
        'DMS': '#ff7f0e',          # Orange
        'TES': '#2ca02c'           # Green
    }
    
    if mode == 'M1':
        # ===== MODE M1 ======
        df_M1 = pd.read_csv(csv_input_path_M1, header=[0, 1], index_col=0)
        df_M1.index.name = 'hour'
        
        seen = set()
        day_types = []
        for col in df_M1.columns:
            day_type = col[0]
            if day_type not in seen:
                day_types.append(day_type)
                seen.add(day_type)
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 11))
        axes = axes.flatten()
        
        for idx, day_type in enumerate(day_types):
            if idx < 4:
                hours = df_M1.index.tolist()
                beta_1 = df_M1[(day_type, 'beta_1_max')].values
                
                denominator = 1 + beta_1
                co2_share = 1 / denominator
                tes_share = beta_1 / denominator
                
                axes[idx].plot(hours, co2_share, marker='o', linewidth=2.5, markersize=6,
                              color=component_colors['CO2 cycle'], label='CO2 cycle')
                axes[idx].plot(hours, tes_share, marker='^', linewidth=2.5, markersize=6,
                              color=component_colors['TES'], label='TES max')
                
                axes[idx].set_xlabel('Hour', fontsize=11)
                axes[idx].set_ylabel('Load share (–)', fontsize=11)
                axes[idx].set_title(f'M1: Load distribution - {day_type}', fontsize=12, pad=15)
                axes[idx].grid(True, alpha=0.3)
                axes[idx].set_xticks(range(0, 24, 2))
                axes[idx].legend(loc='upper right', framealpha=0.9, fontsize=10)
                axes[idx].set_ylim(0, 1.05)
        
        plt.suptitle('Mode M1', fontsize=14, y=1.00)
        plt.tight_layout()
        
        if saving:
            os.makedirs(CASE_PLOTS_DIRECTORY, exist_ok=True)
            filepath = os.path.join(CASE_PLOTS_DIRECTORY, 'load_distribution_M1.png')
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"Figure saved: {filepath}")
        
        plt.show()
    
    elif mode == 'M2':
        # ===== MODE M2 =====
        df_M2 = pd.read_csv(csv_input_path_M2, header=[0, 1], index_col=0)
        df_M2.index.name = 'hour'
        
        seen = set()
        day_types = []
        for col in df_M2.columns:
            day_type = col[0]
            if day_type not in seen:
                day_types.append(day_type)
                seen.add(day_type)
        
        fig, axes = plt.subplots(2, 2, figsize=(14, 11))
        axes = axes.flatten()
        
        for idx, day_type in enumerate(day_types):
            if idx < 4:
                hours = df_M2.index.tolist()
                alpha = df_M2[(day_type, 'alpha_2')].values
                beta_2 = df_M2[(day_type, 'beta_2_max')].values
                
                denominator = 1 + alpha + beta_2
                co2_share = 1 / denominator
                dms_share = alpha / denominator
                tes_share = beta_2 / denominator
                
                axes[idx].plot(hours, co2_share, marker='o', linewidth=2.5, markersize=6,
                              color=component_colors['CO2 cycle'], label='CO2 cycle')
                axes[idx].plot(hours, dms_share, marker='s', linewidth=2.5, markersize=6,
                              color=component_colors['DMS'], label='DMS')
                axes[idx].plot(hours, tes_share, marker='^', linewidth=2.5, markersize=6,
                              color=component_colors['TES'], label='TES max')
                
                axes[idx].set_xlabel('Hour', fontsize=11)
                axes[idx].set_ylabel('Load share (–)', fontsize=11)
                axes[idx].set_title(f'M2: Load distribution - {day_type}', fontsize=12, pad=15)
                axes[idx].grid(True, alpha=0.3)
                axes[idx].set_xticks(range(0, 24, 2))
                axes[idx].legend(loc='upper right', framealpha=0.9, fontsize=10)
                axes[idx].set_ylim(0, 1.05)
        
        plt.suptitle('Mode M2', fontsize=14, y=1.00)
        plt.tight_layout()
        
        if saving:
            os.makedirs(CASE_PLOTS_DIRECTORY, exist_ok=True)
            filepath = os.path.join(CASE_PLOTS_DIRECTORY, 'load_distribution_M2.png')
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"Figure saved: {filepath}")
        
        plt.show()
    
    else:
        raise ValueError("mode must be 'M1', 'M2', or 'both'")

def plot_TES_max_degree_by_daytype(mode='both', csv_input_path_M1=OPTI_SETTINGS_FILE_M1, csv_input_path_M2=OPTI_SETTINGS_FILE_M2, saving=False, one_graph=False):
    """
    Plot beta_max and delta_T_sc_TES over hours for each day type.
    
    Mode M1: shows beta_1_max and corresponding delta_T_sc_TES (computed from StandardCycle)
    Mode M2: shows beta_2_max and corresponding delta_T_sc_TES_max (computed from ComplexSystem)
    Mode 'both': plots M1 then M2 as two separate figures
    
    For each hour and day type:
    - Instantiates the appropriate Cycle with the optimized parameters
    - Computes the cycle
    - Extracts delta_T_sc_TES using get_delta_T_sc_TES()
    - Plots both beta_max (solid line) and delta_T_sc_TES (dashed line) with dual y-axes
    
    Parameters:
    -----------
    mode : str, default 'both'
        'M1' for Standard cycle only, 'M2' for ComplexSystem only, 'both' for M1 then M2
    csv_input_path_M1 : str
        Path to the M1 optimization settings CSV file
    csv_input_path_M2 : str
        Path to the M2 optimization settings CSV file
    saving : bool, default False
        If True, save the plot to disk
    one_graph : bool, default False
        If True, plot all day types on a single graph with different colors.
        If False, create subplots with one subplot per day type.
    """
    
    if mode == 'both':
        # Call M1 and M2 separately
        plot_TES_max_degree_by_daytype(mode='M1', csv_input_path_M1=csv_input_path_M1, 
                                       csv_input_path_M2=csv_input_path_M2, 
                                       saving=saving, one_graph=one_graph)
        plot_TES_max_degree_by_daytype(mode='M2', csv_input_path_M1=csv_input_path_M1, 
                                       csv_input_path_M2=csv_input_path_M2, 
                                       saving=saving, one_graph=one_graph)
        return
    
    # Color mapping for day types
    color_map = {
        'Low': '#87CEEB',           # Light blue
        'Medium': '#DAA520',         # Dark yellow (goldenrod)
        'High': '#FF7F50',           # Coral orange
        'Worst_day': '#DC143C'       # Crimson red
    }
    
    if mode == 'M1':
        # ===== MODE M1 =====
        df_M1 = pd.read_csv(csv_input_path_M1, header=[0, 1], index_col=0)
        df_M1.index.name = 'hour'
        
        seen = set()
        day_types = []
        for col in df_M1.columns:
            day_type = col[0]
            if day_type not in seen:
                day_types.append(day_type)
                seen.add(day_type)
        
        # Compute delta_T_sc_TES for each hour and day type (M1)
        delta_T_sc_TES_M1_data = {}
        beta_1_max_data = {}
        
        for day_type in day_types:
            delta_T_sc_TES_list = []
            beta_1_max_list = []
            
            for hour in df_M1.index:
                # Get cycle parameters for this hour and day type
                T_amb = df_M1.loc[hour, (day_type, 'T_amb')]
                T_gc_out = df_M1.loc[hour, (day_type, 'T_gc_out')]
                P_h = df_M1.loc[hour, (day_type, 'P_h_1')]
                beta_1_max = df_M1.loc[hour, (day_type, 'beta_1_max')]
                T_ev = 273.15 - 10

                 # Instantiate and compute the ComplexSystem
                cycle = ComplexSystem(
                    fluid='CarbonDioxide',
                    T_ev=T_ev,
                    P_h=P_h,
                    T_gc_out=T_gc_out,
                    T_amb_air=T_amb,
                    beta=beta_1_max)
                cycle.compute_cycle()
                
                # Get the DMS subcooling degree
                delta_T_sc_TES = cycle.get_delta_T_sc_TES()
                
                beta_1_max_list.append(beta_1_max)
                delta_T_sc_TES_list.append(delta_T_sc_TES)
            
            delta_T_sc_TES_M1_data[day_type] = delta_T_sc_TES_list
            beta_1_max_data[day_type] = beta_1_max_list
        
        hours = df_M1.index.tolist()
        
        if one_graph:
            fig, ax1 = plt.subplots(figsize=(12, 7))
            ax2 = ax1.twinx()
            
            for day_type in day_types:
                color = color_map.get(day_type, 'blue')
                ax1.plot(hours, beta_1_max_data[day_type], marker='o', linewidth=2.5, markersize=6,
                        color=color, label=f'{day_type} (beta_1_max)', linestyle='-')
            
            ax1.set_xlabel('Hour')
            ax1.set_ylabel('beta_1_max (–)', color='black')
            ax1.tick_params(axis='y', labelcolor='black')
            ax1.grid(True, alpha=0.3)
            ax1.set_xticks(range(0, 24, 2))
            
            for day_type in day_types:
                color = color_map.get(day_type, 'blue')
                ax2.plot(hours, delta_T_sc_TES_M1_data[day_type], marker='s', linewidth=2.5, markersize=6,
                        color=color, label=f'{day_type} (ΔT_sc_TES)', linestyle='--')
            
            ax2.set_ylabel('ΔT_sc_TES (K)', color='black')
            ax2.tick_params(axis='y', labelcolor='black')
            
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', framealpha=0.9, fontsize=10)
            
            ax1.set_title('M1: TES max degree - All day types', pad=15)
            plt.tight_layout()
        
        else:
            fig, axes = plt.subplots(2, 2, figsize=(14, 11))
            axes = axes.flatten()
            
            for idx, day_type in enumerate(day_types):
                if idx < 4:
                    ax1 = axes[idx]
                    ax2 = ax1.twinx()
                    
                    color = color_map.get(day_type, 'blue')
                    
                    ax1.plot(hours, beta_1_max_data[day_type], marker='o', linewidth=2.5, markersize=6,
                            color=color, label='beta_1_max', linestyle='-')
                    ax1.set_xlabel('Hour')
                    ax1.set_ylabel('beta_1_max (–)', color=color)
                    ax1.tick_params(axis='y', labelcolor=color)
                    ax1.grid(True, alpha=0.3)
                    ax1.set_xticks(range(0, 24, 2))
                    
                    ax2.plot(hours, delta_T_sc_TES_M1_data[day_type], marker='s', linewidth=2.5, markersize=6,
                            color=color, label='ΔT_sc_TES', linestyle='--')
                    ax2.set_ylabel('ΔT_sc_TES (K)', color=color)
                    ax2.tick_params(axis='y', labelcolor=color)
                    
                    ax1.set_title(f'M1: TES max degree - {day_type}', pad=15)
                    
                    lines1, labels1 = ax1.get_legend_handles_labels()
                    lines2, labels2 = ax2.get_legend_handles_labels()
                    ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', framealpha=0.9, fontsize=10)
            
            plt.tight_layout(pad=3.0)
        
        if saving:
            os.makedirs(CASE_PLOTS_DIRECTORY, exist_ok=True)
            graph_type = 'one' if one_graph else 'subplots'
            filename = f'TES_max_degree_M1_{graph_type}.png'
            filepath = os.path.join(CASE_PLOTS_DIRECTORY, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"Figure saved: {filepath}")
        
        plt.show()
    
    elif mode == 'M2':
        # ===== MODE M2 =====
        df_M2 = pd.read_csv(csv_input_path_M2, header=[0, 1], index_col=0)
        df_M2.index.name = 'hour'
        
        seen = set()
        day_types = []
        for col in df_M2.columns:
            day_type = col[0]
            if day_type not in seen:
                day_types.append(day_type)
                seen.add(day_type)
        
        # Compute delta_T_sc_TES_max for each hour and day type (M2)
        delta_T_sc_TES_M2_data = {}
        beta_2_max_data = {}
        
        for day_type in day_types:
            delta_T_sc_TES_max_list = []
            beta_2_max_list = []
            
            for hour in df_M2.index:
                T_amb = df_M2.loc[hour, (day_type, 'T_amb')]
                T_gc_out = df_M2.loc[hour, (day_type, 'T_gc_out')]
                P_h = df_M2.loc[hour, (day_type, 'P_h_2')]
                alpha = df_M2.loc[hour, (day_type, 'alpha_2')]
                beta_2_max = df_M2.loc[hour, (day_type, 'beta_2_max')]
                T_ev = 273.15 - 10
                
                cycle = ComplexSystem(
                    fluid='CarbonDioxide',
                    T_ev=T_ev,
                    P_h=P_h,
                    T_gc_out=T_gc_out,
                    T_amb_air=T_amb,
                    alpha=alpha,
                    beta=beta_2_max
                )
                cycle.compute_cycle()
                
                delta_T_sc_TES_max = cycle.get_delta_T_sc_TES()
                
                delta_T_sc_TES_max_list.append(delta_T_sc_TES_max)
                beta_2_max_list.append(beta_2_max)
            
            delta_T_sc_TES_M2_data[day_type] = delta_T_sc_TES_max_list
            beta_2_max_data[day_type] = beta_2_max_list
        
        hours = df_M2.index.tolist()
        
        if one_graph:
            fig, ax1 = plt.subplots(figsize=(12, 7))
            ax2 = ax1.twinx()
            
            for day_type in day_types:
                color = color_map.get(day_type, 'blue')
                ax1.plot(hours, beta_2_max_data[day_type], marker='o', linewidth=2.5, markersize=6,
                        color=color, label=f'{day_type} (beta_2_max)', linestyle='-')
            
            ax1.set_xlabel('Hour')
            ax1.set_ylabel('beta_2_max (–)', color='black')
            ax1.tick_params(axis='y', labelcolor='black')
            ax1.grid(True, alpha=0.3)
            ax1.set_xticks(range(0, 24, 2))
            
            for day_type in day_types:
                color = color_map.get(day_type, 'blue')
                ax2.plot(hours, delta_T_sc_TES_M2_data[day_type], marker='s', linewidth=2.5, markersize=6,
                        color=color, label=f'{day_type} (ΔT_sc_TES_max)', linestyle='--')
            
            ax2.set_ylabel('ΔT_sc_TES_max (K)', color='black')
            ax2.tick_params(axis='y', labelcolor='black')
            
            lines1, labels1 = ax1.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', framealpha=0.9, fontsize=10)
            
            ax1.set_title('M2: TES max degree - All day types', pad=15)
            plt.tight_layout()
        
        else:
            fig, axes = plt.subplots(2, 2, figsize=(14, 11))
            axes = axes.flatten()
            
            for idx, day_type in enumerate(day_types):
                if idx < 4:
                    ax1 = axes[idx]
                    ax2 = ax1.twinx()
                    
                    color = color_map.get(day_type, 'blue')
                    
                    ax1.plot(hours, beta_2_max_data[day_type], marker='o', linewidth=2.5, markersize=6,
                            color=color, label='beta_2_max', linestyle='-')
                    ax1.set_xlabel('Hour')
                    ax1.set_ylabel('beta_2_max (–)', color=color)
                    ax1.tick_params(axis='y', labelcolor=color)
                    ax1.grid(True, alpha=0.3)
                    ax1.set_xticks(range(0, 24, 2))
                    
                    ax2.plot(hours, delta_T_sc_TES_M2_data[day_type], marker='s', linewidth=2.5, markersize=6,
                            color=color, label='ΔT_sc_TES_max', linestyle='--')
                    ax2.set_ylabel('ΔT_sc_TES_max (K)', color=color)
                    ax2.tick_params(axis='y', labelcolor=color)
                    
                    ax1.set_title(f'M2: TES max degree - {day_type}', pad=15)
                    
                    lines1, labels1 = ax1.get_legend_handles_labels()
                    lines2, labels2 = ax2.get_legend_handles_labels()
                    ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', framealpha=0.9, fontsize=10)
            
            plt.tight_layout(pad=3.0)
        
        if saving:
            os.makedirs(CASE_PLOTS_DIRECTORY, exist_ok=True)
            graph_type = 'one' if one_graph else 'subplots'
            filename = f'TES_max_degree_M2_{graph_type}.png'
            filepath = os.path.join(CASE_PLOTS_DIRECTORY, filename)
            plt.savefig(filepath, dpi=300, bbox_inches='tight')
            print(f"Figure saved: {filepath}")
        
        plt.show()
    
    else:
        raise ValueError("mode must be 'M1', 'M2', or 'both'")

def plot_DMS_degree_M2_by_daytype(csv_path=OPTI_SETTINGS_FILE_M2, saving=False, one_graph=False):
    """
    Fore mode M2, plot alpha and delta_T_sc_DMS over hours for each day type on the same graph.
    
    For each hour and day type:
    - Instantiates a ComplexSystem with the optimized parameters
    - Computes the cycle
    - Extracts delta_T_sc_DMS using get_delta_T_sc_DMS()
    - Plots both alpha (solid line) and delta_T_sc_DMS (dashed line) with dual y-axes
    
    Parameters:
    -----------
    csv_path : str
        Path to the M2 optimization settings CSV file
    saving : bool, default False
        If True, save the plot to disk
    one_graph : bool, default False
        If True, plot all day types on a single graph with different colors.
        If False, create subplots with one subplot per day type.
    """
    # Read CSV with MultiIndex structure
    df = pd.read_csv(csv_path, header=[0, 1], index_col=0)
    df.index.name = 'hour'
    
    # Get unique day types (first level of MultiIndex) in order of appearance
    seen = set()
    day_types = []
    for col in df.columns:
        day_type = col[0]
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
    
    # Compute delta_T_sc_DMS for each hour and day type
    delta_T_sc_DMS_data = {}
    alpha_data = {}
    
    for day_type in day_types:
        delta_T_sc_DMS_list = []
        alpha_list = []
        
        for hour in df.index:
            # Get cycle parameters for this hour and day type
            T_amb = df.loc[hour, (day_type, 'T_amb')]
            T_gc_out = df.loc[hour, (day_type, 'T_gc_out')]
            P_h = df.loc[hour, (day_type, 'P_h_2')]
            alpha = df.loc[hour, (day_type, 'alpha_2')]
            T_ev = 273.15 - 10 
            
            # Instantiate and compute the ComplexSystem
            cycle = ComplexSystem(
                fluid='CarbonDioxide',
                T_ev=T_ev,
                P_h=P_h,
                T_gc_out=T_gc_out,
                T_amb_air=T_amb,
                alpha=alpha
            )
            cycle.compute_cycle()
            
            # Get the DMS subcooling degree
            delta_T_sc_DMS = cycle.get_delta_T_sc_DMS()
            
            delta_T_sc_DMS_list.append(delta_T_sc_DMS)
            alpha_list.append(alpha)
        
        delta_T_sc_DMS_data[day_type] = delta_T_sc_DMS_list
        alpha_data[day_type] = alpha_list
    
    hours = df.index.tolist()
    
    if one_graph:
        # Single graph with all day types, dual y-axes
        fig, ax1 = plt.subplots(figsize=(12, 7))
        ax2 = ax1.twinx()
        
        # Plot alpha on left y-axis (solid lines)
        for day_type in day_types:
            color = color_map.get(day_type, 'blue')
            ax1.plot(hours, alpha_data[day_type], marker='o', linewidth=2.5, markersize=6, 
                    color=color, label=f'{day_type} (alpha)', linestyle='-')
        
        ax1.set_xlabel('Hour')
        ax1.set_ylabel('alpha (–)', color='black')
        ax1.tick_params(axis='y', labelcolor='black')
        ax1.grid(True, alpha=0.3)
        ax1.set_xticks(range(0, 24, 2))
        
        # Plot delta_T_sc_DMS on right y-axis (dashed lines)
        for day_type in day_types:
            color = color_map.get(day_type, 'blue')
            ax2.plot(hours, delta_T_sc_DMS_data[day_type], marker='s', linewidth=2.5, markersize=6, 
                    color=color, label=f'{day_type} (ΔT_sc)', linestyle='--')
        
        ax2.set_ylabel('ΔT_sc_DMS (K)', color='black')
        ax2.tick_params(axis='y', labelcolor='black')
        
        # Combine legends from both axes
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', framealpha=0.9, fontsize=10)
        
        ax1.set_title('DMS degree parameters - All day types', pad=15)
        plt.tight_layout()
        
    else:
        # Multiple subplots, one per day type with dual y-axes
        fig, axes = plt.subplots(2, 2, figsize=(14, 11))
        axes = axes.flatten()
        
        # Plot for each day type
        for idx, day_type in enumerate(day_types):
            if idx < 4:  # Only plot if there are subplots available
                ax1 = axes[idx]
                ax2 = ax1.twinx()
                
                color = color_map.get(day_type, 'blue')
                
                # Plot alpha on left y-axis (solid line)
                ax1.plot(hours, alpha_data[day_type], marker='o', linewidth=2.5, markersize=6, 
                        color=color, label='alpha', linestyle='-')
                ax1.set_xlabel('Hour')
                ax1.set_ylabel('alpha (–)', color=color)
                ax1.tick_params(axis='y', labelcolor=color)
                ax1.grid(True, alpha=0.3)
                ax1.set_xticks(range(0, 24, 2))
                
                # Plot delta_T_sc_DMS on right y-axis (dashed line)
                ax2.plot(hours, delta_T_sc_DMS_data[day_type], marker='s', linewidth=2.5, markersize=6, 
                        color=color, label='ΔT_sc_DMS', linestyle='--')
                ax2.set_ylabel('ΔT_sc_DMS (K)', color=color)
                ax2.tick_params(axis='y', labelcolor=color)
                
                ax1.set_title(f'DMS degree - {day_type}', pad=15)
                
                # Combined legend
                lines1, labels1 = ax1.get_legend_handles_labels()
                lines2, labels2 = ax2.get_legend_handles_labels()
                ax1.legend(lines1 + lines2, labels1 + labels2, loc='best', framealpha=0.9, fontsize=10)
        
        plt.tight_layout(pad=3.0)
    
    if saving:
        os.makedirs(CASE_PLOTS_DIRECTORY, exist_ok=True)
        graph_type = 'one' if one_graph else 'subplots'
        filename = f'DMS_degree_{graph_type}.png'
        filepath = os.path.join(CASE_PLOTS_DIRECTORY, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {filepath}")
    
    plt.show()

########################### EXECUTION ZONE ###########################

# for param in ['T_amb', 'T_gc_out', 'P_h_1', 'COP_CO2_1', 'beta_1_max', 'COP_DMS_TES']:
#     plot_param_M1_series_by_daytype(param, saving=True, one_graph=True)

# for param in ['P_h_2', 'alpha_2', 'beta_2_max', 'COP_star_2', 'COP_CO2_2', 'COP_DMS_CO2']:
#     plot_param_M2_series_by_daytype(param, saving=True, one_graph=True)

# plot_param_M2_series_by_daytype('alpha_2', saving=True, one_graph=True)

# plot_load_distribution_cycle(mode='both', saving=True)

# plot_DMS_degree_M2_by_daytype(saving=True)

# plot_TES_max_degree_by_daytype(mode='both', saving=True)


