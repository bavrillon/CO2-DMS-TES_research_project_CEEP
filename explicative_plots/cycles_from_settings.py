import pandas as pd
import sys
import os

gdparent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(gdparent_dir)
from cycles import *
from CONSTANTS import *


CASE = 'mono2_45'
CASE_DIRECTORY = os.path.join(CASE_STUDIES_SAVING_DIR, CASE, 'thermo_optim_inputs')
CASE_PLOTS_DIRECTORY = os.path.join(CASE_STUDIES_SAVING_DIR, CASE, 'plots')
OPTI_SETTINGS_FILE_M1 = os.path.join(CASE_DIRECTORY, 'thermo_settings_M1.csv')
OPTI_SETTINGS_FILE_M2 = os.path.join(CASE_DIRECTORY, 'thermo_settings_M2.csv')
M1_CYCLES_DIR = os.path.join(CASE_PLOTS_DIRECTORY, 'cycles', 'M1_cycles')
M1_PINCHES_DIR = os.path.join(CASE_PLOTS_DIRECTORY, 'pinch', 'M1_pinches')
M2_CYCLES_DIR = os.path.join(CASE_PLOTS_DIRECTORY, 'cycles', 'M2_cycles')
M2_PINCHES_DIR = os.path.join(CASE_PLOTS_DIRECTORY, 'pinch', 'M2_pinches')

def _normalize_to_list(value, valid_values, label):
    """Normalize a str or iterable into a list while validating allowed values."""
    if isinstance(value, str):
        values = [value]
    else:
        try:
            values = list(value)
        except TypeError:
            raise ValueError(f"{label} must be a string or an iterable of strings")
    normalized = []
    for v in values:
        v_lower = v.lower()
        if v_lower not in valid_values:
            raise ValueError(f"Invalid {label}: {v}. Allowed: {valid_values}")
        normalized.append(v_lower)
    return normalized

def plot_M1_cycle(day_type, hour, cycle_to_plot='main', diagram=('Ph', 'Ts'), pinch_air=False, show=False, save=False):
    """
    Compute and plot the standard refrigeration cycle from optimization settings.

    diagram: 'Ph', 'Ts' or an iterable of both.
    pinch_air: if True, plots temperature profiles in the air heat exchanger.
    """
    
    cycle_choice = _normalize_to_list(cycle_to_plot, {'main'}, 'cycle_to_plot')
    if 'dms' in cycle_choice:
        print("Warning: Standard cycles do not have a DMS subcycle. Plotting main cycle instead.")
    diag_choice = _normalize_to_list(diagram, {'ph', 'ts'}, 'diagram')
    
    # Load the CSV file
    csv_path = OPTI_SETTINGS_FILE_M1
    df = pd.read_csv(csv_path, header=[0, 1], index_col=0)
    
    # Select the appropriate column based on day_type
    if day_type not in ['Low', 'Medium', 'High', 'Worst_day']:
        raise ValueError(f"day_type must be one of: 'Low', 'Medium', 'High', 'Worst_day'. Got: {day_type}")
    
    if hour < 0 or hour > 23:
        raise ValueError(f"hour must be between 0 and 23. Got: {hour}")
    
    # Extract parameters for the specified hour and day_type
    try:
        T_amb = df.loc[hour, (day_type, 'T_amb')]
        P_h_1 = df.loc[hour, (day_type, 'P_h_1')]
        T_gc_out = df.loc[hour, (day_type, 'T_gc_out')]
    except KeyError as e:
        print(f"Error accessing data for day_type='{day_type}', hour={hour}")
        print(f"Available day_types: {df.columns.get_level_values(0).unique().tolist()}")
        raise e
    
    # Create and compute the cycle
    cycle = StandardCycle(
        fluid='CarbonDioxide',
        T_ev=T_EV,
        P_h=P_h_1,
        T_gc_out=T_gc_out,
        T_amb_air=T_amb,
    )
    
    cycle.compute_cycle()
    COP = cycle.get_COP()
    
    print(f"\n{'='*60}")
    print(f"Standard Cycle - {day_type} day, Hour {hour}")
    print(f"{'='*60}")
    print(f"T_amb = {T_amb - 273.15:.2f} °C")
    print(f"P_h = {P_h_1/1e5:.2f} bar")
    print(f"T_gc_out = {T_gc_out - 273.15:.2f} °C")
    print(f"COP = {COP:.3f}")
    print(f"Cycle type: {'Transcritical' if cycle.transcritical_cycle else 'Subcritical'}")
    print(f"{'='*60}\n")
    
    # Create plots
    if show or save:
        save_dir = M1_CYCLES_DIR
        if save and not os.path.exists(save_dir):
            os.makedirs(save_dir)
        
        if 'ts' in diag_choice:
            cycle.plot_TS(show=show)
            if save:
                save_path_TS = os.path.join(save_dir, f'TS_M1_{day_type}_h{hour}.png')
                plt.savefig(save_path_TS, dpi=300, bbox_inches='tight')
                print(f"Saved T-S diagram to: {save_path_TS}")
        
        if 'ph' in diag_choice:
            cycle.plot_HP(show=show)
            if save:
                save_path_HP = os.path.join(save_dir, f'HP_M1_{day_type}_h{hour}.png')
                plt.savefig(save_path_HP, dpi=300, bbox_inches='tight')
                print(f"Saved H-P diagram to: {save_path_HP}")
    
    # Pinch analysis plot for air heat exchanger
    if pinch_air:
        save_dir_2 = M1_PINCHES_DIR
        if save and not os.path.exists(save_dir_2):
            os.makedirs(save_dir_2)
        save_path_pinch = os.path.join(save_dir_2, f'Air_CO2_{day_type}_h{hour}.png') if save else None
        cycle.get_pinch_air(show=show, saving_path=save_path_pinch)
        print("Generated pinch analysis plot for air heat exchanger.")
    
    return cycle

def plot_M2_cycle(day_type, hour, cycle_to_plot='main', diagram=('Ph', 'Ts'), pinch_air=False, show=False, save=False):
    """
    Compute and plot the complex cycle with subcooling (M2) from optimization settings.

    cycle_to_plot: 'main', 'DMS' or an iterable of both.
    diagram: 'Ph', 'Ts' or an iterable of both.
    pinch_air: None, 'main', 'DMS' or an iterable of both.
        If None, no pinch analysis plots are generated.
        If 'main', plots temperature profiles in the main cycle air heat exchanger.
        If 'DMS', plots temperature profiles in the DMS air heat exchanger (if alpha > 0).
        If an iterable of both, plots both.
    """
    
    # Load the CSV file
    csv_path = OPTI_SETTINGS_FILE_M2
    df = pd.read_csv(csv_path, header=[0, 1], index_col=0)
    
    # Select the appropriate column based on day_type
    if day_type not in ['Low', 'Medium', 'High', 'Worst_day']:
        raise ValueError(f"day_type must be one of: 'Low', 'Medium', 'High', 'Worst_day'. Got: {day_type}")
    
    if hour < 0 or hour > 23:
        raise ValueError(f"hour must be between 0 and 23. Got: {hour}")
    
    # Extract parameters for the specified hour and day_type
    try:
        T_amb = df.loc[hour, (day_type, 'T_amb')]
        P_h_2 = df.loc[hour, (day_type, 'P_h_2')]
        T_gc_out = df.loc[hour, (day_type, 'T_gc_out')]
        alpha = df.loc[hour, (day_type, 'alpha_2')]
        beta_max = df.loc[hour, (day_type, 'beta_2_max')]
    except KeyError as e:
        print(f"Error accessing data for day_type='{day_type}', hour={hour}")
        print(f"Available day_types: {df.columns.get_level_values(0).unique().tolist()}")
        raise e
    
    cycle_choice = _normalize_to_list(cycle_to_plot, {'main', 'dms'}, 'cycle_to_plot')
    diag_choice = _normalize_to_list(diagram, {'ph', 'ts'}, 'diagram')

    # Create and compute the cycle
    cycle = ComplexSystem(
        fluid='CarbonDioxide',
        T_ev=T_EV,
        P_h=P_h_2,
        T_gc_out=T_gc_out,
        T_amb_air=T_amb,
        alpha=alpha,
        beta=beta_max
    )
    
    cycle.compute_cycle()
    COP_CO2 = cycle.get_CO2_COP()
    COP_star = cycle.get_COP()
    
    if alpha > 0:
        COP_DMS = cycle.get_DMS_COP()
    else:
        COP_DMS = None
    
    print(f"\n{'='*60}")
    print(f"Complex Cycle (M2) - {day_type} day, Hour {hour}")
    print(f"{'='*60}")
    print(f"T_amb = {T_amb - 273.15:.2f} °C")
    print(f"P_h = {P_h_2/1e5:.2f} bar")
    print(f"T_gc_out = {T_gc_out - 273.15:.2f} °C")
    print(f"alpha = {alpha:.4f}")
    print(f"beta_max = {beta_max:.4f}")
    print(f"COP_CO2 (main cycle) = {COP_CO2:.3f}")
    if COP_DMS is not None:
        print(f"COP_DMS = {COP_DMS:.3f}")
    print(f"COP_star (system) = {COP_star:.3f}")
    print(f"{'='*60}\n")
    
    # Create plots based on cycle_to_plot parameter
    if show or save:
        save_dir = M2_CYCLES_DIR
        if save and not os.path.exists(save_dir):
            os.makedirs(save_dir)

        # Main cycle plots
        if 'main' in cycle_choice:
            if 'ts' in diag_choice:
                cycle.plot_TS(show=show, save=False)
                if save:
                    save_path_TS = os.path.join(save_dir, f'TS_M2_main_{day_type}_h{hour}.png')
                    plt.savefig(save_path_TS, dpi=300, bbox_inches='tight')
                    print(f"Saved T-S diagram (main cycle) to: {save_path_TS}")
            if 'ph' in diag_choice:
                cycle.plot_HP(show=show, save=False)
                if save:
                    save_path_HP = os.path.join(save_dir, f'HP_M2_main_{day_type}_h{hour}.png')
                    plt.savefig(save_path_HP, dpi=300, bbox_inches='tight')
                    print(f"Saved H-P diagram (main cycle) to: {save_path_HP}")

        # DMS cycle plots
        if 'dms' in cycle_choice:
            if alpha == 0:
                print("Warning: alpha = 0, no DMS subcycle exists. Skipping DMS plots.")
            else:
                if 'ts' in diag_choice:
                    cycle.plot_TS_DMS(show=show, save=False)
                    if save:
                        save_path_TS = os.path.join(save_dir, f'TS_M2_DMS_{day_type}_h{hour}.png')
                        plt.savefig(save_path_TS, dpi=300, bbox_inches='tight')
                        print(f"Saved T-S diagram (DMS cycle) to: {save_path_TS}")
                if 'ph' in diag_choice:
                    cycle.plot_HP_DMS(show=show, save=False)
                    if save:
                        save_path_HP = os.path.join(save_dir, f'HP_M2_DMS_{day_type}_h{hour}.png')
                        plt.savefig(save_path_HP, dpi=300, bbox_inches='tight')
                        print(f"Saved H-P diagram (DMS cycle) to: {save_path_HP}")
    
    # Pinch analysis plots for air heat exchangers
    if pinch_air:
        save_dir_2 = M2_PINCHES_DIR
        if save and not os.path.exists(save_dir_2):
            os.makedirs(save_dir_2)
        save_path_pinch = os.path.join(save_dir_2, f'Air_CO2_{day_type}_h{hour}.png') if save else None
        pinch_choice = _normalize_to_list(pinch_air, {'main', 'dms'}, 'pinch_air')
        save_path_pinch_main = os.path.join(save_dir_2, f'Air_CO2_{day_type}_h{hour}.png') if save else None
        save_path_pinch_dms = os.path.join(save_dir_2, f'Air_DMS_{day_type}_h{hour}.png') if save else None
        
        if 'main' in pinch_choice:
            cycle.get_pinch_air(show=show, saving_path=save_path_pinch_main)
        
        if 'dms' in pinch_choice:
            if alpha == 0:
                print("Warning: alpha = 0, no DMS subcycle exists. Skipping DMS pinch plot.")
            else:
                cycle.get_pinch_air_DMS(show=show, saving_path=save_path_pinch_dms)
    
    return cycle


############### EXECUTION ZONE ###############

for day in DAY_TYPES:
    for hr in range(0, 24):
        plot_M1_cycle(day_type=day, hour=hr, diagram=['Ph','Ts'], pinch_air=True, show=False, save=True)
        plot_M2_cycle(day_type=day, hour=hr, cycle_to_plot=['main', 'DMS'], diagram=['Ph','Ts'], pinch_air=['main','dms'], show=False, save=True)
        

# plot_M2_cycle(
#     day_type='High',
#     hour=15,
#     cycle_to_plot=['main', 'DMS'],
#     diagram=['Ph', 'Ts'],          
#     show=False,            
#     save=True             
# )

# plot_M1_cycle(day_type='Medium', hour=12, diagram=['Ph', 'Ts'], pinch_air=True, show=False, save=True)
# plot_M2_cycle(day_type='Medium', hour=12, cycle_to_plot=['main', 'DMS'], diagram='Ph', pinch_air=['main','dms'], show=False, save=True)