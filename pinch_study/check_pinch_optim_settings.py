import os
import sys
import pandas as pd

gdparent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(gdparent_dir)
from cycles import *
from CONSTANTS import *


CASE = 'mono2_45'
CASE_DIRECTORY = os.path.join(CASE_STUDIES_SAVING_DIR, CASE, 'thermo_optim_inputs')
CASE_PLOTS_DIRECTORY = os.path.join(CASE_STUDIES_SAVING_DIR, CASE, 'plots')
OPTI_SETTINGS_FILE_M1 = os.path.join(CASE_DIRECTORY, 'thermo_settings_M1.csv')
OPTI_SETTINGS_FILE_M2 = os.path.join(CASE_DIRECTORY, 'thermo_settings_M2.csv')
T_PROFILE_TES_CO2_DIR = os.path.join(CASE_PLOTS_DIRECTORY, 'check_pinch_TES_CO2_optim_settings')
T_PROFILE_AIR_CO2_M1_DIR = os.path.join(CASE_PLOTS_DIRECTORY, 'check_pinch_air_CO2_M1_optim_settings')
T_PROFILE_AIR_CO2_M2_DIR = os.path.join(CASE_PLOTS_DIRECTORY, 'check_pinch_air_CO2_M2_optim_settings')
T_PROFILE_CO2_IN_DMS_DIR = os.path.join(CASE_PLOTS_DIRECTORY, 'T_profile_CO2_in_DMS')

# T_TES need to be defined in CONSTANTS.py for the CASE under study here 

######################################## CHECK PINCH AIR-CO2 OPTIM SETTINGS ##########################################

def compute_pinch_optim_settings_M1(saving_path=T_PROFILE_AIR_CO2_M1_DIR) -> pd.DataFrame:
    """
    Read optimized parameters (T_amb, P_h, T_gc_out) from M1_optim_settings.csv,
    instantiate a StandardCycle for each (day_type, hour), compute the pinch via
    .get_pinch_air(show=True, saving_path=...), and return a DataFrame of pinches.

    Returns:
        DataFrame indexed by hour, columns = one per day type
        (e.g., ['Low', 'Medium', 'High', 'Worst_day'] depending on the file).
    """
    plt.close('all')
    os.makedirs(saving_path, exist_ok=True)

    # Read multi-index columns (day_type, variable)
    df = pd.read_csv(OPTI_SETTINGS_FILE_M1, index_col=0, header=[0, 1])

    # If the index has a 'hour' label as the first row, remove it
    if len(df.index) > 0 and isinstance(df.index[0], str) and df.index[0].strip().lower() == 'hour':
        df = df.drop(index=df.index[0])

    # Ensure an integer hour index if possible
    try:
        df.index = df.index.astype(int)
    except Exception:
        pass

    # Day types = top-level of the columns
    day_types = list(df.columns.get_level_values(0).unique())

    # Result DataFrame: one column per day_type
    df_pinch = pd.DataFrame(index=df.index, columns=day_types, dtype=float)

    for day in day_types:
        for hour in df.index:
            T_amb = float(df.loc[hour, (day, 'T_amb')])
            P_h = float(df.loc[hour, (day, 'P_h_1')])
            T_gc_out = float(df.loc[hour, (day, 'T_gc_out')])

            cycle = StandardCycle(
                fluid='CarbonDioxide',
                T_ev=T_EV,
                P_h=P_h,
                T_gc_out=T_gc_out,
                T_amb_air=T_amb
            )

            # Save one file per case in the target folder
            save_path = os.path.join(saving_path, f"T_profile_{day}_{int(hour):02d}.png")
            pinch = cycle.get_pinch_air(saving_path=save_path)

            df_pinch.loc[hour, day] = pinch

    return df_pinch

def compute_pinch_optim_settings_M2(saving_path=T_PROFILE_AIR_CO2_M2_DIR) -> pd.DataFrame:
    """
    Read optimized parameters (T_amb, P_h, T_gc_out, alpha) from M2_optim_settings.csv,
    instantiate a ComplexSystem for each (day_type, hour), compute the pinch via
    .get_pinch_air(saving_path=...), and return a DataFrame of pinches.

    Returns:
        DataFrame indexed by hour, columns = one per day type
        (e.g., ['Low', 'Medium', 'High', 'Worst_day'] depending on the file).
    """
    plt.close('all')
    os.makedirs(saving_path, exist_ok=True)

    # Read multi-index columns (day_type, variable)
    df = pd.read_csv(OPTI_SETTINGS_FILE_M2, index_col=0, header=[0, 1])

    # If the index has a 'hour' label as the first row, remove it
    if len(df.index) > 0 and isinstance(df.index[0], str) and df.index[0].strip().lower() == 'hour':
        df = df.drop(index=df.index[0])

    # Ensure an integer hour index if possible
    try:
        df.index = df.index.astype(int)
    except Exception:
        pass

    # Day types = top-level of the columns
    day_types = list(df.columns.get_level_values(0).unique())

    # Result DataFrame: one column per day_type
    df_pinch = pd.DataFrame(index=df.index, columns=day_types, dtype=float)

    for day in day_types:
        for hour in df.index:
            T_amb = float(df.loc[hour, (day, 'T_amb')])
            P_h = float(df.loc[hour, (day, 'P_h_2')])
            T_gc_out = float(df.loc[hour, (day, 'T_gc_out')])
            alpha = float(df.loc[hour, (day, 'alpha_2')])

            cycle = ComplexSystem(
                fluid='CarbonDioxide',
                T_ev=T_EV,
                P_h=P_h,
                T_gc_out=T_gc_out,
                T_amb_air=T_amb,
                alpha=alpha
            )

            # Save one file per case with a M2-specific prefix
            save_path = os.path.join(saving_path, f"T_profile_M2_{day}_{int(hour):02d}.png")
            pinch = cycle.get_pinch_air(saving_path=save_path)

            df_pinch.loc[hour, day] = pinch

    return df_pinch

######################################## CHECK PINCH TES-CO2 ##########################################

def compute_pinch_TES_CO2_one_cycle(P_h: float, T_gc_out: float, alpha: float, delta_h_CO2: float, T_TES_cold: float, T_TES_hot: float, gas_pinch_TES: float=PINCH_TES, N_nodes: int=25, show=False, saving_path=None) -> float:
    """
    Compute the pinch point (minimum temperature difference) between the TES and CO2 fluid 
    in a single cycle thermodynamic process, and optionally plot the temperature profiles.
    Returns: The pinch temperature difference in K, (float)
    """
    h_DMS_in = get_fluid_property('H', 'T', T_gc_out, 'P', P_h, 'CarbonDioxide')
    h_TES_in = h_DMS_in - delta_h_CO2 * alpha
    T_TES_in = get_fluid_property('T', 'P', P_h, 'H', h_TES_in, 'CarbonDioxide')
    T_TES_out = T_TES_cold + gas_pinch_TES  # Assuming maximum subcooling provided by TES to CO2
    h_TES_out = get_fluid_property('H', 'P', P_h, 'T', T_TES_out, 'CarbonDioxide')
    h_nodes_TES = np.linspace(h_TES_out, h_TES_in, N_nodes)[::-1]
    T_nodes_TES = [T_TES_in]
    for i in range(1, N_nodes):
        T_nodes_TES.append(get_fluid_property('T', 'P', P_h, 'H', h_nodes_TES[i], 'CarbonDioxide'))
    T_nodes_TES = np.array(T_nodes_TES)
        
    T_w = np.linspace(T_TES_cold, T_TES_hot, N_nodes)

    # Find the node where pinch occurs
    pinch_node = np.argmin(T_nodes_TES - T_w[::-1])
    pinch_TES = T_nodes_TES[pinch_node] - T_w[::-1][pinch_node]
    
    if show or (saving_path is not None):
        plt.figure()
        x_normalized = np.linspace(0, 1, N_nodes)
        plt.plot(x_normalized, T_nodes_TES - 273.15, marker='o', color='red', label='Fluid temperature')
        plt.plot(x_normalized, T_w[::-1] - 273.15, marker='s', color='blue', label='Water temperature')
        
        plt.plot(x_normalized[pinch_node], T_nodes_TES[pinch_node] - 273.15, marker='*', markersize=15, color='green', label=f'Pinch point (ΔT = {pinch_TES:.2f} °C)')
        plt.axvline(x=x_normalized[pinch_node], color='green', linestyle='--', alpha=0.5)
        
        plt.xlabel('Condenser/Gas-cooler normalized length (0 = fluid inlet, 1 = fluid outlet)')
        plt.ylabel('Temperature [°C]')
        plt.title('Temperature profiles')
        plt.grid(True)
        plt.legend()
        if saving_path is not None:
            plt.savefig(saving_path, dpi=300)
        if show:
            plt.show()

    return pinch_TES 

def compute_pinch_TES_CO2_optim_settings_M2(saving_path=T_PROFILE_TES_CO2_DIR) -> pd.DataFrame:
    """
    Read optimized parameters (P_h, T_gc_out, delta_h_CO2) from M2_optim_settings.csv,
    and compute the pinch between TES and CO2 for each (day_type, hour) using
    compute_pinch_TES_CO2_one_cycle().
    Returns:
        DataFrame indexed by hour, columns = one per day type
        (e.g., ['Low', 'Medium', 'High', 'Worst_day'] depending on the file).
    """
    plt.close('all')
    os.makedirs(saving_path, exist_ok=True)

    # TES strategy for this CASE
    if CASE.startswith('mono'):
        TES_mono = True
    else:        
        TES_mono = False

    # Read multi-index columns (day_type, variable)
    df = pd.read_csv(OPTI_SETTINGS_FILE_M2, index_col=0, header=[0, 1])

    # If the index has a 'hour' label as the first row, remove it
    if len(df.index) > 0 and isinstance(df.index[0], str) and df.index[0].strip().lower() == 'hour':
        df = df.drop(index=df.index[0])

    # Ensure an integer hour index if possible
    try:
        df.index = df.index.astype(int)
    except Exception:
        pass

    # Day types = top-level of the columns
    day_types = list(df.columns.get_level_values(0).unique())

    # Result DataFrame: one column per day_type
    df_pinch = pd.DataFrame(index=df.index, columns=day_types, dtype=float)

    for day in day_types:
        for hour in df.index:
            P_h = float(df.loc[hour, (day, 'P_h_2')])
            T_gc_out = float(df.loc[hour, (day, 'T_gc_out')])
            alpha = float(df.loc[hour, (day, 'alpha_2')])
            delta_h_CO2 = float(df.loc[hour, (day, 'delta_h_CO2_2')])
            beta_max = float(df.loc[hour, (day, 'beta_2_max')])

            if TES_mono:
                T_TES_C = T_TES['Mono']['cold'] +273.15
                T_TES_H = T_TES['Mono']['hot'] +273.15
            else:
                T_TES_C = T_TES[day]['cold'] +273.15
                T_TES_H = T_TES[day]['hot'] +273.15

            if beta_max > 0:
                # Save one file per case with a TES-specific prefix
                if saving_path is not None:
                    file = os.path.join(saving_path, f"T_profile_TES_M2_{day}_{int(hour):02d}.png")
                else:
                    file = None
                pinch = compute_pinch_TES_CO2_one_cycle(
                    P_h=P_h,
                    T_gc_out=T_gc_out,
                    alpha=alpha,
                    delta_h_CO2=delta_h_CO2,
                    T_TES_cold=T_TES_C,
                    T_TES_hot=T_TES_H,
                    saving_path=file)
                df_pinch.loc[hour, day] = pinch
            else:
                df_pinch.loc[hour, day] = None  # No TES subcooling present

    return df_pinch

###################################### CHECK T PROFILE CO2 IN DMS ########################################

def plot_T_CO2_in_DMS(day_type, hour, N_nodes=20, saving_path=T_PROFILE_CO2_IN_DMS_DIR, show=True):
    """
    Plot the evolution of CO2 fluid temperature in the DMS heat exchanger.
    day_type : str ('Low', 'Medium', 'High', 'Worst_day')
    hour : int (0-23)
    saving_path : str, optional (if None, does not save)
    show : bool
    """
    # Load optimized parameters
    df_settings = pd.read_csv(OPTI_SETTINGS_FILE_M2, header=[0, 1], index_col=0)
    
    # Extract parameters for the specified day and hour
    T_amb = df_settings.loc[hour, (day_type, 'T_amb')]
    P_h_opt = df_settings.loc[hour, (day_type, 'P_h_2')]
    alpha = df_settings.loc[hour, (day_type, 'alpha_2')]
    T_gc_out = df_settings.loc[hour, (day_type, 'T_gc_out')]
    
    cycle = ComplexSystem(
        fluid='CarbonDioxide',
        T_ev=T_EV, 
        P_h=P_h_opt,
        T_gc_out=T_gc_out,
        T_amb_air=T_amb,
        alpha=alpha)
    
    # Calculate the cycle to obtain temperatures in the DMS
    cycle.compute_cycle()
    h_nodes_DMS = np.linspace(cycle.h_sc_DMS_out, cycle.h_sc_in, N_nodes)[::-1]
    T_nodes_DMS = []
    for h in h_nodes_DMS:
        T_nodes_DMS.append(get_fluid_property('T', 'P', P_h_opt, 'H', h, 'CarbonDioxide'))
    T_nodes_DMS = np.array(T_nodes_DMS)
    x_normalized = np.linspace(0, 1, N_nodes)
    
    # Plot temperature profile
    plt.figure(figsize=(10, 6))
    plt.plot(x_normalized, T_nodes_DMS - 273.15, 
             marker='o', linewidth=2.5, markersize=7, color='#1f77b4', 
             label='CO₂ temperature profile')
    
    plt.xlabel('Normalized position in DMS heat exchanger', 
               fontsize=12, fontweight='bold')
    plt.ylabel('CO₂ Temperature [°C]', fontsize=12, fontweight='bold')
    plt.title(f'CO₂ Temperature Evolution in DMS Heat Exchanger\n'
              f'{day_type} - {hour}h00 | T_amb = {T_amb:.1f}°C | α = {alpha:.3f}',
              fontsize=13, fontweight='bold')
    plt.grid(True, alpha=0.3, linestyle='--')
    plt.legend(loc='best', fontsize=10)
    plt.tight_layout()
    
    if saving_path is not None:
        os.makedirs(saving_path, exist_ok=True)
        filename = f"T_CO2_in_DMS_{day_type}_h{hour:02d}-Tamb{T_amb:.1f}C_alpha{alpha:.3f}.png"
        filepath = os.path.join(saving_path, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"Graph saved: {filepath}")
    
    if show:
        plt.show()
    else:
        plt.close()

def plot_T_CO2_in_DMS_optim_settings_M2(saving_path=T_PROFILE_CO2_IN_DMS_DIR):
    """Plot T profile in DMS for all optimized settings from M2_optim_settings.csv."""
    plt.close('all')

    # Read multi-index columns (day_type, variable)
    df = pd.read_csv(OPTI_SETTINGS_FILE_M2, index_col=0, header=[0, 1])

    # If the index has a 'hour' label as the first row, remove it
    if len(df.index) > 0 and isinstance(df.index[0], str) and df.index[0].strip().lower() == 'hour':
        df = df.drop(index=df.index[0])

    # Ensure an integer hour index if possible
    try:
        df.index = df.index.astype(int)
    except Exception:
        pass

    # Day types = top-level of the columns
    day_types = list(df.columns.get_level_values(0).unique())

    for day in day_types:
        for hour in df.index:
            plot_T_CO2_in_DMS(
                day_type=day,
                hour=hour,
                saving_path=saving_path,
                show=False)
            print(f"Plotted and saved T profile in DMS for {day} at hour {hour}.")

######################################## EXECUTION ZONE ##########################################
plt.close('all')

# df_pinch_M1_results = compute_pinch_optim_settings_M1()
# print("Computed pinches for M1 cycle optimization settings:")
# print(df_pinch_M1_results)

# df_pinch_M2_results = compute_pinch_optim_settings_M2()
# print("Computed pinches for M2 cycle optimization settings:")
# print(df_pinch_M2_results)

# df_pinch_TES_results = compute_pinch_TES_CO2_optim_settings_M2()
# print("Computed pinches for TES cycle optimization settings:")
# print(df_pinch_TES_results)

# plot_T_CO2_in_DMS('Medium', 15, show=True)
# plot_T_CO2_in_DMS_optim_settings_M2()
# print("Plotted and saved all T profiles in DMS for M2 cycle optimization settings.")