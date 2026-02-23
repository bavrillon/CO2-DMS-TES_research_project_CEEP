"""
This code is used to compute the optimal high pressure P_h to maximize the COP of CO2 transcritical cycles,
using both a standard cycle and a cycle with DMS. It also includes functions to derive correlations for this pressure, 
and informatively assess the influence of P_h on COP*.
"""
from CONSTANTS import *
from cycles import *
from scipy.optimize import minimize_scalar
from matplotlib.colors import LinearSegmentedColormap
import pandas as pd

# The required pressures P_h_opt_1 for the correlation Ph_opt_1 = f(T_amb) are the same dor all the case studies.
M1_SETTINGS_FOR_CORRELATION_FILE = os.path.join(os.path.dirname(__file__), "case_studies", "mono_45", "thermo_optim_inputs", "thermo_settings_M1.csv")

###################################### STANDARD CYCLE ##############################################

# Optimization of the high pressure to maximize COP for a CO2 transcritical standard cycle (without DMS). 
# If subcritical, P_h is set to P_cond(T_gc_out), so the optimization does not makes sense.

def optimize_Ph_supercritical_std_cycle(T_ev, T_gc_out, sc_ratio=0, P_min=prp.PropsSI('CarbonDioxide', 'Pcrit'), P_max=150e5):
    """
    Optimize high pressure P_h to maximize COP for a single set of parameters.
    Force supercritical cycle.
    """
    def minus_COP_std_cycle(P_h):
        try:
            std_cycle = StandardCycle('CarbonDioxide',
                                  T_ev,
                                  P_h=P_h,
                                  T_gc_out=T_gc_out,
                                  sc_ratio=sc_ratio)
            return -std_cycle.get_COP()
        except ValueError:
            return 2000
    
    # Optimize (with differential evolution)    
    # res = differential_evolution(
    #     lambda x: minus_COP_std_cycle(x[0]),
    #     bounds=[(P_min, P_max)],
    #     polish=True)
    # P_opt = float(res.x[0])
    # COP_max = -res.fun

    # Optimize (with minimize_scalar)
    res = minimize_scalar(
        lambda x: minus_COP_std_cycle(x),
        bounds=(P_min, P_max),
        method='bounded'
    )
    P_opt = res.x
    COP_max = -res.fun

    return P_opt, COP_max

###################################### CYCLE WITH DMS ###############################################

def optimize_Ph_supercritical_cycle_with_DMS(T_ev, T_gc_out, T_amb_air, alpha=0, P_min=prp.PropsSI('CarbonDioxide', 'Pcrit'), P_max=150e5):
    """
    Optimize high pressure P_h to maximize COP for a single set of parameters (including alpha).
    Force supercritical cycle.
    """
    def minus_COP_sbc_cycle(P_h):
        try:
            sbc_cycle = ComplexSystem('CarbonDioxide',
                                    T_ev,
                                    P_h=P_h,
                                    T_gc_out=T_gc_out,
                                    T_amb_air=T_amb_air,
                                    alpha=alpha)
            return -sbc_cycle.get_COP()
        except ValueError:
            return 2000
    
    # # Optimize (with differential evolution)   
    # res = differential_evolution(
    #     lambda x: minus_COP_sbc_cycle(x[0]),
    #     bounds=[(P_min, P_max)],
    #     polish=True)
    # P_opt = float(res.x[0])
    # COP_max = -res.fun

    # Optimize (with minimize_scalar)
    res = minimize_scalar(
        lambda x: minus_COP_sbc_cycle(x),
        bounds=(P_min, P_max),
        method='bounded')
    P_opt = res.x
    COP_max = -res.fun

    return P_opt, COP_max


###################### Ph_opt THROUGH A CORRELATION BASED ON P_h_opt_1 = f(T_amb) #####################

## Correlation only useful for supercritical cycles, since in subcritical cycles P_h = P_sat(T_gc_out).

def get_ordered_pairs(M1_csv_file_path, param_1='P_h_1', param_2='T_amb'):
    """
    Extract all (param_2, param_1) pairs from the CSV file.
    
    The CSV has a MultiIndex structure with day_types (Low, Medium, High, Worst_day)
    and parameters (T_amb, T_gc_out, P_h_1, COP_CO2_1, ...). Each day_type
    appears at different hours (0-23), resulting in 96 total pairs.
    
    Args:
        param_1 (str): First parameter name to extract (here 'P_h_1')
        param_2 (str): Second parameter name to extract (here 'T_amb')
        csv_file_path (str): Path to the file Mi_optim_settings.csv file
    
    Returns:
       2-dimensional numpy array: First row = param_2 values (in ascending order) ; Second row = param_1 values
    """
    # Read the CSV with MultiIndex columns (day_type, parameter)
    df = pd.read_csv(M1_csv_file_path, header=[0, 1], index_col=0)
    
    # Lists to store param_2 and param_1 values
    param_2_values = []
    param_1_values = []
    
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
                
                # Pair them up and append to lists
                for hour in param_2_col.index:
                    param_2_val = param_2_col.loc[hour]
                    param_1_val = param_1_col.loc[hour]
                    if float(param_2_val) >= T_AMB_MAX_SUBCRITICAL:  # Only supercritical cycles
                        param_2_values.append(param_2_val)
                        param_1_values.append(param_1_val)
    
    # Convert to numpy arrays
    param_2_array = np.array(param_2_values)
    param_1_array = np.array(param_1_values)
    
    # Sort by param_2 values in ascending order
    sort_indices = np.argsort(param_2_array)
    param_2_sorted = param_2_array[sort_indices]
    param_1_sorted = param_1_array[sort_indices]
    
    # Return as 2D numpy array: first row = param_2 values, second row = param_1 values
    return np.array([param_2_sorted, param_1_sorted])

def get_interpolation_P_h_opt_1_vs_Tamb(M1_csv_file_path):
    """Get interpolation function for P_h_opt_1 vs T_amb based on linear regression."""
    ordered_pairs = get_ordered_pairs(param_1='P_h_1', param_2='T_amb', M1_csv_file_path=M1_csv_file_path)
    x_data_points, y_data_points = ordered_pairs[0], ordered_pairs[1]
    
    def interpolation(x):
        x = np.asarray(x)
        return np.interp(x, x_data_points, y_data_points)
    
    return interpolation

def plot_interpolation_P_h_opt_1_vs_Tamb(M1_csv_file_path):
    """Plot the interpolation function for P_h_opt_1 vs T_amb and display the correlation equation."""
    ordered_pairs = get_ordered_pairs(param_1='P_h_1', param_2='T_amb', M1_csv_file_path=M1_csv_file_path)
    x_data_points, y_data_points = ordered_pairs[0], ordered_pairs[1]
    
    # Convert to °C and bar for correlation
    x_data_celsius = x_data_points - 273.15
    y_data_bar = y_data_points / 1e5
    
    # Compute linear regression: P_h (bar) = a * T_amb (°C) + b
    coefficients = np.polyfit(x_data_celsius, y_data_bar, 1)
    a, b = coefficients[0], coefficients[1]
    
    # Compute R² coefficient
    y_fit = a * x_data_celsius + b
    ss_res = np.sum((y_data_bar - y_fit) ** 2)
    ss_tot = np.sum((y_data_bar - np.mean(y_data_bar)) ** 2)
    r_squared = 1 - (ss_res / ss_tot)
    
    # Create equation string
    equation = f"P_h_opt_1 (bar) = {a:.4f} * T_amb (°C) + {b:.4f}"
    equation_with_r2 = f"{equation}  (R² = {r_squared:.6f})"
    
    # Print equation to terminal
    print("\n" + "="*70)
    print("CORRELATION EQUATION FOR P_h_opt_1 vs T_amb (supercritical cycles)")
    print("="*70)
    print(f"\n{equation_with_r2}\n")
    print("="*70 + "\n")
    
    interpolation = get_interpolation_P_h_opt_1_vs_Tamb(M1_csv_file_path)
    
    x_smooth = np.linspace(min(x_data_points), max(x_data_points), 200)
    y_smooth = interpolation(x_smooth)
    
    plt.figure(figsize=(10, 6))
    plt.scatter(x_data_celsius, y_data_bar, color='blue', label='Data Points', alpha=0.6)
    plt.plot(x_smooth - 273.15, y_smooth/1e5, color='red', label='Interpolation', linewidth=2)
    
    # Add equation to plot
    plt.text(0.05, 0.95, equation_with_r2, transform=plt.gca().transAxes, 
             fontsize=10, verticalalignment='top', bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))
    
    plt.title('Interpolation of P_h_opt_1 vs T_amb (supercritical cycles)')
    plt.xlabel('T_amb (°C)')
    plt.ylabel('P_h_opt_1 (bar)')
    plt.legend()
    plt.grid(True)
    plt.show()
    
    return equation_with_r2

## Visualize the correlation:
# plot_interpolation_P_h_opt_1_vs_Tamb(M1_SETTINGS_FOR_CORRELATION_FILE)

## Literature comparison
## with "A correlation of optimal heat rejection pressures in transcritical carbon 
## dioxide cycles", S.M. Liaoa , T.S. Zhaoa, A. Jakobsen (2000)
# C = 1.003
# K = 0.121
# µ = K/C
# t_ev = -10
# coefs_lit_1 = (2.7572+0.1304*t_ev-3.072*µ) / (1+0.0538*t_ev+0.1606*µ)
# coefs_lit_0 = - (8.7946+0.02605*t_ev-105.48*µ) /(1+0.05163*t_ev+0.2212*µ)
# coefs_literature = [coefs_lit_0, coefs_lit_1]
# coefs_experiment = [19.9625-5*2.1821,2.1821]
# T_gc_out_array = np.linspace(30,45,75)

def plot_linear_comparison(T_array, coefs_literature, coefs_experiment, T_ref=38):
    """
    Plot literature vs experiment linear fits on the same chart.

    Parameters:
    -----------
    T_array : array
        Temperature range (x-axis)
    coefs_literature : list
        Coefficients [intercept, slope] for literature
    coefs_experiment : list
        Coefficients [intercept, slope] for experiment
    T_ref : float
        Reference temperature for the relative error (°C)
    """
    # Compute linear functions
    y_literature = coefs_literature[0] + coefs_literature[1] * T_array
    y_experiment = coefs_experiment[0] + coefs_experiment[1] * T_array

    # Relative error at T_ref
    y_lit_ref = coefs_literature[0] + coefs_literature[1] * T_ref
    y_exp_ref = coefs_experiment[0] + coefs_experiment[1] * T_ref
    relative_error = abs(y_exp_ref - y_lit_ref) / abs(y_lit_ref)

    # Plot
    plt.figure(figsize=(10, 6))
    plt.plot(T_array, y_literature, 'b-', label='Literature', linewidth=2)
    plt.plot(T_array, y_experiment, 'r-', label='Experiment', linewidth=2)
    
    plt.xlabel('Gas-cooler outlet temperature T_gc_out (°C)', fontsize=12)
    plt.ylabel('Optimal heat rejection pressure P_opt (bar)', fontsize=12)
    plt.title('Literature vs Experiment', fontsize=14)
    plt.legend(fontsize=11)
    plt.grid(True, alpha=0.3)
    plt.text(
        0.02,
        0.98,
        f"Relative change at {T_ref}°C: {relative_error * 100:.2f}%",
        transform=plt.gca().transAxes,
        va='top',
        fontsize=10,
        bbox=dict(boxstyle='round', facecolor='white', alpha=0.8)
    )
    plt.tight_layout()
    plt.show()

    print(
        f"Relative change at {T_ref}°C: {relative_error * 100:.2f}% "
        f"(Literature={y_lit_ref:.3f} bar, Experiment={y_exp_ref:.3f} bar)"
    )

# plot_linear_comparison(T_gc_out_array, coefs_literature, coefs_experiment)


############################### INFLUENCE OF P_h ON COP* ############################################
# Assessment of the influence of the high pressure on the COP* of the overall system,
# for a T_amb, T_gc_out and given, the goal being to plot the results

def assess_Ph_influence_sbc_cycle(T_gc_out, T_amb_air, alpha=0, plot=True, T_ev=T_EV, P_min=prp.PropsSI('CarbonDioxide', 'Pcrit'), P_max=150e5, n_points=50):
    """
    Assess the influence of the high pressure P_h on COP for a single set of parameters (including alpha).
    Force supercritical cycle (in case of a subcritical cyle, P is set to P_cond(T_gc_out)).
    """
    P_h_values = np.linspace(P_min, P_max, n_points)
    COP_values = []

    for P_h in P_h_values:
        try:
            sbc_cycle = ComplexSystem('CarbonDioxide',
                                    T_ev,
                                    P_h=P_h,
                                    T_gc_out=T_gc_out,
                                    T_amb_air=T_amb_air,
                                    alpha=alpha)
            COP = sbc_cycle.get_COP()
        except ValueError:
            COP = np.nan  # Assign NaN for invalid solutions
        COP_values.append(COP)

    if plot:
        plt.figure(figsize=(10, 6))
        plt.plot(P_h_values / 1e5, COP_values, marker='o', linestyle='--', color='green')
        plt.title(f"Influence of heat rejection pressure P_h on COP* (T_amb={T_amb_air-273.15:.1f}°C ; alpha={alpha})")
        plt.xlabel('P_h (bar)')
        plt.ylabel('COP*')
        plt.grid(True)
        plt.xlim(P_min / 1e5, P_max / 1e5)
        plt.ylim(0, max(filter(lambda x: x is not np.nan, COP_values)) * 1.1)
        plt.show()

    return P_h_values, COP_values

# # Day type 'High' at 15h
# T_amb_0 = 304.2659
# P_h_0 = 8816920.2
# T_gc_out_0 = 309.2659
# alpha_0 = 0
# assess_Ph_influence_sbc_cycle(T_gc_out_0, T_amb_0, alpha=alpha_0)


def plot_COP_vs_Ph_for_different_Tgcout(T_gc_out_range, plot=True, T_ev=T_EV, P_min=prp.PropsSI('CarbonDioxide', 'Pcrit'), P_max=125e5, n_points=30):
    """
    Plot COP* vs P_h for different T_gc_out and with alpha = 0, on the same chart.
    """
    T_gc_out_range = np.asarray(T_gc_out_range)
    T_amb_air_range = T_gc_out_range - PINCH_AIR
    # P_h_values = np.linspace(P_min, P_max, n_points)
    
    # Scale fitting the needs
    t = np.linspace(0, 10, n_points)
    expo = 6/7
    expt = np.power(expo,t)
    expt_norm = (expt - np.power(expo,t[-1]))/(1- np.power(expo,t[-1]))
    P_h_values = P_min + (P_max - P_min) * expt_norm

    COP_values_by_Tgcout = []
    for T_gc_out, T_amb_air in zip(T_gc_out_range, T_amb_air_range):
        COP_values = []
        for P_h in P_h_values:
            try:
                sbc_cycle = ComplexSystem(
                    'CarbonDioxide',
                    T_ev,
                    P_h=P_h,
                    T_gc_out=T_gc_out,
                    T_amb_air=T_amb_air,
                    alpha=0
                )
                COP = sbc_cycle.get_COP()
            except ValueError:
                COP = np.nan
                print(f"Invalid solution for P_h={P_h:.2e} Pa")
            COP_values.append(COP)
        COP_values_by_Tgcout.append(np.array(COP_values))

    if plot:
        plt.figure(figsize=(5.2, 8))
        cmap = LinearSegmentedColormap.from_list('brown_orange', ['#6f4e37', '#ff8c00'])
        colors = cmap(np.linspace(0, 1, len(T_gc_out_range)))
        for idx, (T_gc_out, COP_values) in enumerate(zip(T_gc_out_range, COP_values_by_Tgcout)):
            plt.plot(
                P_h_values / 1e5,
                COP_values,
                marker='o',
                linestyle='--',
                color=colors[idx],
                label=f"$T_{{gc \ out}}={T_gc_out - 273.15:.1f}°C$",
                markersize=3
            )
        plt.title('COP* vs $P_h$ for different $T_{gc\,out}$')
        plt.xlabel('$P_h$ (bar)')
        plt.ylabel('COP* (-)')
        plt.grid(True)
        plt.xlim(P_min / 1e5, P_max / 1e5)
        if COP_values_by_Tgcout:
            all_cops = np.concatenate(COP_values_by_Tgcout)
            if np.any(~np.isnan(all_cops)):
                plt.ylim(0, np.nanmax(all_cops) * 1.1)
        plt.legend(fontsize=8)
        plt.show()

    return P_h_values, COP_values_by_Tgcout, T_amb_air_range

T_gc_out_range_0 = np.arange(33, 47.1, 2) + 273.15
# plot_COP_vs_Ph_for_different_Tgcout(T_gc_out_range_0, n_points=25)