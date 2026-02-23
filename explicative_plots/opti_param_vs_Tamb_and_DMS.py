"""Build a parameter database structured with one CSV file per ambient air temperature (T_amb).
Each CSV file contains rows across all `alpha` values and includes the columns:
'T_amb';'alpha';'P_h_Sbc';'delta_T_sc_DMS';'COP_CO2_Sbc';'COP_DMS_CO2';'COP_star_Sbc'.
Also used to plot parameter surfaces in the (T_amb, alpha) plane.
"""
import pandas as pd
import re
import os
import sys
from mpl_toolkits.mplot3d import Axes3D
from scipy.interpolate import griddata

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cycles import *
from CONSTANTS import *
from pinch_study.compute_pinch_air import get_T_gc_out_min_subcritical
from opti_Ph import get_interpolation_P_h_opt_1_vs_Tamb

DATA_3D_DB_PATH = os.path.join(DATA_3D_SAVING_DIR, 'COP_star_vs_alpha_and_Tamb')
DB_PARAMS = ['P_h_Sbc', 'delta_T_sc_DMS', 'COP_CO2_Sbc', 'COP_DMS_CO2', 'COP_star_Sbc']

# Alpha interpolation (manually extracted from previous computations)
Tamb_data_points = np.array([5] + [4*k for k in range(2, 11)]) + 273.15
alpha_data_points = np.array([0.6, 0.62, 0.68, 0.8, 0.9, 1.2, 1.25, 1.3, 1.3, 1.16])  # max alpha at each T_amb data points

def complete_db(T_start, T_stop, T_step, db_path=DATA_3D_DB_PATH):
    """Creates one CSV per `T_amb` value. After finishing each `T_amb`, writes its CSV.
    CSV columns: 'T_amb';'alpha';'P_h_Sbc';'delta_T_sc_DMS';'COP_CO2_Sbc';'COP_DMS_CO2';'COP_star_Sbc'."""

    interpolation_Ph_opt_1_vs_Tamb = get_interpolation_P_h_opt_1_vs_Tamb(M1_csv_file_path=M1_SETTINGS_FILE_PATH)
    print("[P_h_opt_1 = f(T_amb) correlation sucessfully obtained from M1 settings]")

    T_amb_range = np.arange(T_start, T_stop, T_step)

    for T_amb in T_amb_range:
        rows = []
        alpha_max_at_Tamb = np.interp(T_amb, Tamb_data_points, alpha_data_points)
        alpha_range_at_Tamb = np.arange(0, alpha_max_at_Tamb + 0.02, 0.02)
        enough_alpha_for_Tamb = False
        for alpha in alpha_range_at_Tamb:
            if enough_alpha_for_Tamb:
                break
            try:
                if T_amb <= T_AMB_MAX_SUBCRITICAL:
                    T_gc_out = get_T_gc_out_min_subcritical(T_amb, max_iter=50, required_pinch=PINCH_AIR)[0]
                    P_h = prp.PropsSI('P', 'T', T_gc_out, 'Q', 0.5, "CarbonDioxide")
                else:
                    T_gc_out = T_amb + PINCH_AIR
                    P_h = interpolation_Ph_opt_1_vs_Tamb(T_amb)

                sbc_cycle = ComplexSystem(
                    fluid="CarbonDioxide",
                    T_ev=T_EV,
                    P_h=P_h,
                    T_gc_out=T_gc_out,
                    T_amb_air=T_amb,
                    alpha=alpha
                )
                sbc_cycle.compute_cycle()

                COP_star_Sbc = sbc_cycle.get_COP()
                COP_DMS_CO2 = sbc_cycle.get_DMS_COP()
                COP_CO2_Sbc = sbc_cycle.get_CO2_COP()
                delta_T_sc_DMS = sbc_cycle.get_delta_T_sc_DMS()

                rows.append({
                    'T_amb': T_amb,
                    'alpha': float(alpha),
                    'P_h_Sbc': float(P_h),
                    'delta_T_sc_DMS': float(delta_T_sc_DMS),
                    'COP_CO2_Sbc': float(COP_CO2_Sbc),
                    'COP_DMS_CO2': float(COP_DMS_CO2),
                    'COP_star_Sbc': float(COP_star_Sbc),
                })
            except Exception as e:
                print(f"Error at T_amb={T_amb - 273.15:.2f}°C, alpha={alpha:.4f}: {str(e)}")
                rows.append({
                    'T_amb': T_amb,
                    'alpha': float(alpha),
                    'P_h_Sbc': np.nan,
                    'delta_T_sc_DMS': np.nan,
                    'COP_CO2_Sbc': np.nan,
                    'COP_DMS_CO2': np.nan,
                    'COP_star_Sbc': np.nan,
                })
                enough_alpha_for_Tamb = True

        # Write CSV for this T_amb (semicolon-delimited)
        df_out = pd.DataFrame(rows, columns=[
            'T_amb','alpha','P_h_Sbc','delta_T_sc_DMS','COP_CO2_Sbc','COP_DMS_CO2','COP_star_Sbc'
        ])
        T_amb_C = T_amb - 273.15  # filename in °C for readability
        fname = f"T_amb_{T_amb_C:.2f}C.csv".replace(' ', '')
        fpath = os.path.join(db_path, fname)
        df_out.to_csv(fpath, sep=';', index=False)
        print(f"==========> Computation done: {T_amb_C:.2f} °C")

def plot_param_vs_Tamb_and_DMS_3D(param, db_path=DATA_3D_DB_PATH, style='scatter_plot', variable='alpha', save_fig=False):
    """Plot a 3D representation of a parameter across (T_amb, variable) plane.
    param : str
        Parameter to plot: 'P_h_Sbc', 'COP_CO2_Sbc', 'COP_DMS_CO2', or 'COP_star_Sbc'
    db_path : str, optional
        Path to the database folder containing CSV files (default: DATA_3D_DB_PATH).
    style : str, optional
        Plot style: 'scatter_plot' (default) for scatter points or 'surface' for interpolated surface.
    variable : str, optional
        Variable to plot against T_amb: 'alpha' (default) or 'delta_T_sc_DMS'.
    save_fig : bool, optional
        If True, save the figure to disk (default: False).
    """
    # Validate parameter
    if param not in DB_PARAMS:
        raise ValueError(f"Parameter must be one of {DB_PARAMS}, got '{param}'")
    
    if style not in ['scatter_plot', 'surface']:
        raise ValueError(f"style must be 'scatter_plot' or 'surface', got '{style}'")
    
    if variable not in ['alpha', 'delta_T_sc_DMS']:
        raise ValueError(f"variable must be 'alpha' or 'delta_T_sc_DMS', got '{variable}'")

    # Load all CSV files from the database folder
    csv_files = sorted([f for f in os.listdir(db_path) if f.endswith('.csv')])
    
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {db_path}")

    # Combine all data
    data_list = []
    for csv_file in csv_files:
        fpath = os.path.join(db_path, csv_file)
        df = pd.read_csv(fpath, sep=';')
        data_list.append(df)
    
    df_combined = pd.concat(data_list, ignore_index=True)

    # Filter out rows with NaN values in the parameter of interest
    initial_rows = len(df_combined)
    df_combined = df_combined.dropna(subset=[param, variable, 'T_amb'])
    filtered_rows = len(df_combined)
    
    if initial_rows > filtered_rows:
        print(f"Filtered out {initial_rows - filtered_rows} rows with NaN values ({filtered_rows} rows remaining)")

    # Extract data and convert T_amb to Celsius for plotting
    T_amb_K = df_combined['T_amb'].values
    T_amb_C = T_amb_K - 273.15
    var_values = df_combined[variable].values
    param_values = df_combined[param].values
    
    print(f"Data range: T_amb=[{T_amb_C.min():.1f}, {T_amb_C.max():.1f}]°C, {variable}=[{var_values.min():.3f}, {var_values.max():.3f}]")

    # Unit map for labeling
    unit_map = {
        'P_h_Sbc': 'Pa',
        'delta_T_sc_DMS': '°C',
        'COP_CO2_Sbc': '–',
        'COP_DMS_CO2': '–',
        'COP_star_Sbc': '–'
    }
    param_unit = unit_map.get(param, '–')
    var_unit = unit_map.get(variable, '–')
    
    # Label map for LaTeX display
    label_map = {
        'alpha': r'$\alpha$',
        'delta_T_sc_DMS': r'$\Delta T_{\mathrm{sc \ DMS}}$ (°C)'
    }
    var_label = label_map.get(variable, variable)

    # Create 3D plot
    fig = plt.figure(figsize=(14, 9))
    ax = fig.add_subplot(111, projection='3d')

    if style == 'scatter_plot':
        # Scatter plot for the data points
        scatter = ax.scatter(T_amb_C, var_values, param_values, c=param_values, cmap='viridis', s=20, alpha=0.6)
        cbar = plt.colorbar(scatter, ax=ax, shrink=0.5, aspect=5)
        cbar.set_label(f'{param} ({param_unit})', fontsize=10)
    
    elif style == 'surface':
        # Create a regular grid for interpolation
        T_amb_C_grid = np.linspace(T_amb_C.min(), T_amb_C.max(), 50)
        var_grid = np.linspace(var_values.min(), var_values.max(), 50)
        T_amb_C_mesh, var_mesh = np.meshgrid(T_amb_C_grid, var_grid)
        
        # Interpolate parameter values on the grid
        points = np.column_stack([T_amb_C, var_values])
        param_mesh = griddata(points, param_values, (T_amb_C_mesh, var_mesh), method='cubic')
        
        # Plot surface
        surf = ax.plot_surface(T_amb_C_mesh, var_mesh, param_mesh, cmap='viridis', alpha=0.8)
        cbar = plt.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
        cbar.set_label(f'{param} ({param_unit})', fontsize=10)

    # Add labels and title
    ax.set_xlabel(r'$T_{\mathrm{amb}}$ (°C)', fontsize=11)
    ax.set_ylabel(var_label, fontsize=11)
    ax.set_zlabel(f'{param} ({param_unit})', fontsize=11)
    ax.set_title(f'{param} vs ($T_{{\\mathrm{{amb}}}}$, {label_map[variable]}) - {style}', fontsize=14, pad=20)

    plt.tight_layout()

    if save_fig:
        os.makedirs(EXPLICATIVE_PLOTS_SAVING_DIR, exist_ok=True)
        ax.view_init(elev=30, azim=30, roll=0)
        fname = f'surface_3D_{param}_{variable}_{style}.png'
        fpath = os.path.join(EXPLICATIVE_PLOTS_SAVING_DIR, fname)
        bbox_inches='tight'
        plt.savefig(fpath, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {fpath}")

    plt.show()

def plot_param_vs_alpha(param, T_amb_C, db_path=DATA_3D_DB_PATH, save_fig=False):
    """Plot parameter vs alpha for one or multiple temperatures.
    param : str
        Parameter to plot: 'P_h_Sbc', 'COP_CO2_Sbc', 'COP_DMS_CO2', or 'COP_star_Sbc'
    T_amb_C : float or list of float
        Ambient temperature(s) in Celsius. Can be a single value or a list of values.
    db_path : str, optional
        Path to the database folder containing CSV files (default: DATA_3D_DB_PATH).
    save_fig : bool, optional
        If True, save the figure to disk (default: False).
    """
    if param not in DB_PARAMS:
        raise ValueError(f"Parameter must be one of {DB_PARAMS}, got '{param}'")

    # Convert single temperature to list for uniform handling
    if isinstance(T_amb_C, (int, float)):
        T_amb_C_list = [T_amb_C]
    else:
        T_amb_C_list = list(T_amb_C)
    
    csv_files = sorted([f for f in os.listdir(db_path) if f.endswith('.csv')])
    if not csv_files:
        raise FileNotFoundError(f"No CSV files found in {db_path}")

    data = [pd.read_csv(os.path.join(db_path, f), sep=';') for f in csv_files]
    df = pd.concat(data, ignore_index=True)
    
    unique_T = np.unique(df['T_amb'].values)
    unit_map = {'P_h_Sbc': 'Pa', 'delta_T_sc_DMS': 'K', 'COP_CO2_Sbc': '–', 'COP_DMS_CO2': '–', 'COP_star_Sbc': '–'}
    unit = unit_map.get(param, '–')
    
    # Create color map (blue to green gradient)
    cmap = plt.cm.viridis if len(T_amb_C_list) > 1 else plt.cm.Blues
    colors = cmap(np.linspace(0.3, 0.9, len(T_amb_C_list)))
    
    plt.figure(figsize=(10, 6))
    
    T_used_list = []
    for idx, T_target_C in enumerate(T_amb_C_list):
        target_K = T_target_C + 273.15
        T_match = unique_T[np.abs(unique_T - target_K).argmin()]
        df_sel = df[np.isclose(df['T_amb'], T_match)].sort_values('alpha')
        
        if df_sel.empty:
            print(f"Warning: No rows found for T_amb close to {T_target_C:.2f} °C, skipping")
            continue
        
        alpha = df_sel['alpha'].values
        y = df_sel[param].values
        T_used_C = T_match - 273.15
        T_used_list.append(T_used_C)
        
        label = f'T_amb = {T_used_C:.2f} °C'
        plt.plot(alpha, y, marker='o', label=label, color=colors[idx], linewidth=2, markersize=6)
        
        if abs(T_match - target_K) > 0.05:
            print(f"Warning: used T_amb {T_used_C:.2f} °C (closest in DB) instead of requested {T_target_C:.2f} °C")
    
    plt.xlabel('DMS parameter α (–)', fontsize=11)
    plt.ylabel(f'{param} ({unit})', fontsize=11)
    
    if len(T_amb_C_list) == 1:
        plt.title(f'{param} vs α (T_amb = {T_used_list[0]:.2f} °C)', fontsize=12)
    else:
        plt.title(f'{param} vs α (multiple temperatures)', fontsize=12)
    
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.tight_layout()

    if save_fig:
        os.makedirs(EXPLICATIVE_PLOTS_SAVING_DIR, exist_ok=True)
        if len(T_amb_C_list) == 1:
            fname = f'alpha_curve_{param}_T{T_used_list[0]:.2f}C.png'.replace(' ', '')
        else:
            fname = f'alpha_curve_{param}_multi_T.png'
        fpath = os.path.join(EXPLICATIVE_PLOTS_SAVING_DIR, fname)
        plt.savefig(fpath, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {fpath}")

    plt.show()

## Modeling and organizing database data ##

def aggregate_and_organise_db_data(param, db_path=DATA_3D_DB_PATH, final_saving_path=None):
    """Aggregate all CSV files in db_path into a single DataFrame,
    whose rows correspond to different ambient temperatures and
    whose columns correspond to different alpha values.
    param : str
        Parameter to extract and organize: 'P_h_Sbc', 'delta_T_sc_DMS', 
        'COP_CO2_Sbc', 'COP_DMS_CO2', or 'COP_star_Sbc'
    """
    # Validate parameter
    if param not in DB_PARAMS:
        raise ValueError(f"Parameter must be one of {DB_PARAMS}, got '{param}'")
    
    # Get all CSV files matching the pattern T_amb_*.csv
    csv_files = sorted([f for f in os.listdir(db_path) if f.endswith('.csv')])
    
    # Filter only files matching the pattern T_amb_<number>C.csv
    pattern = re.compile(r'^T_amb_[\d.]+C\.csv$')
    valid_files = [f for f in csv_files if pattern.match(f)]
    
    if not valid_files:
        raise FileNotFoundError(f"No valid CSV files found in {db_path} matching pattern 'T_amb_<temperature>C.csv'")
    
    print(f"Found {len(valid_files)} CSV files to aggregate for parameter '{param}'")
    
    # Load all CSV files
    data_list = []
    for csv_file in valid_files:
        fpath = os.path.join(db_path, csv_file)
        df = pd.read_csv(fpath, sep=';')
        data_list.append(df)
    
    # Combine all DataFrames
    df_combined = pd.concat(data_list, ignore_index=True)
    
    # Sort by T_amb and alpha
    df_combined = df_combined.sort_values(['T_amb', 'alpha']).reset_index(drop=True)
    
    # Pivot: rows = T_amb, columns = alpha, values = param
    df_pivoted = df_combined.pivot(index='T_amb', columns='alpha', values=param)
    
    # Sort index and columns
    df_pivoted = df_pivoted.sort_index()
    df_pivoted = df_pivoted[sorted(df_pivoted.columns)]
    
    # Save organized data
    if final_saving_path is None:
        file_path = output_file = os.path.join(db_path, f'organized_{param}.csv')
    else:
        output_file = final_saving_path
    df_pivoted.to_csv(output_file, sep=';')
    
    print(f"\nOrganization complete for '{param}':")
    print(f"  Rows (T_amb): {len(df_pivoted)} temperatures")
    print(f"  Columns (alpha): {len(df_pivoted.columns)} alpha values")
    print(f"  Temperature range: {df_pivoted.index.min():.2f} - {df_pivoted.index.max():.2f} K")
    print(f"  Alpha range: {df_pivoted.columns.min():.4f} - {df_pivoted.columns.max():.4f}")
    print(f"  Saved to: {output_file}")
    
    return df_pivoted

def cut_rows_out_from_csv(csv_file):
    """Remove columns from a CSV file based on alpha_max interpolation (see at the top of the file).
    For each row (T_amb) in the CSV file, calculates alpha_max_at_Tamb using
    interpolation, then removes all columns where alpha > alpha_max_at_Tamb.
    Modifies the CSV file in-place."""

    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"File not found: {csv_file}")
    
    # Load the CSV file
    df = pd.read_csv(csv_file, sep=';', index_col=0)
    
    # Convert column headers (alpha values) to float
    alpha_columns = df.columns.astype(float).values
    
    # Process each row
    rows_modified = 0
    for idx in df.index:
        T_amb = idx  # T_amb value from the index
        
        # Calculate alpha_max for this T_amb
        alpha_max_at_Tamb = np.interp(T_amb, Tamb_data_points, alpha_data_points)
        
        # Find columns to keep (alpha <= alpha_max_at_Tamb)
        columns_to_keep = alpha_columns[alpha_columns <= alpha_max_at_Tamb]
        columns_to_remove = alpha_columns[alpha_columns > alpha_max_at_Tamb]
        
        if len(columns_to_remove) > 0:
            # Remove columns with alpha > alpha_max
            df.loc[idx, [str(c) for c in columns_to_remove]] = np.nan
            rows_modified += 1
    
    # Remove columns that are entirely NaN
    df = df.dropna(axis=1, how='all')
    
    # Save the modified CSV
    df.to_csv(csv_file, sep=';')
    
    print(f"CSV file modified and saved: {csv_file}")
    print(f"  Rows processed: {rows_modified}")
    print(f"  Remaining columns: {len(df.columns)}")
    print(f"  Remaining rows: {len(df)}")

def plot_param_vs_Tamb_and_alpha_3D(param, db_file_path, style='scatter_plot', save_fig=False):
    """Plot 3D representation of parameter in (T_amb, alpha) plane using an aggregated database file.   
    param : str
        Parameter to plot: 'P_h_Sbc', 'COP_CO2_Sbc', 'COP_DMS_CO2', or 'COP_star_Sbc'
    db_file_path : str
        Path to the aggregated database file (CSV) generated by aggregate_and_organise_db_data().
        The file should have T_amb values as rows (index) and alpha values as columns.
    style : str, optional
        Plot style: 'scatter_plot' (default) for scatter points or 'surface' for interpolated surface.
    save_fig : bool, optional
        If True, save the figure to EXPLICATIVE_PLOTS_SAVING_DIR (default: False).
    """
    # Validate parameter
    if param not in DB_PARAMS:
        raise ValueError(f"Parameter must be one of {DB_PARAMS}, got '{param}'")
    
    if style not in ['scatter_plot', 'surface']:
        raise ValueError(f"style must be 'scatter_plot' or 'surface', got '{style}'")
    
    if not os.path.exists(db_file_path):
        raise FileNotFoundError(f"File not found: {db_file_path}")
    
    # Load the aggregated database file
    # This file should have T_amb (K) as index and alpha values as columns
    df = pd.read_csv(db_file_path, sep=';', index_col=0)
    
    # Get T_amb values (index in K) and alpha values (columns)
    T_amb_K = df.index.values
    T_amb_C = T_amb_K - 273.15  # Convert to Celsius for plotting
    alpha_columns = df.columns.values  # Keep as strings initially
    alpha_values = df.columns.astype(float).values
    
    # Prepare data for plotting (remove NaN values)
    T_amb_list = []
    alpha_list = []
    param_list = []
    
    for i, t_amb_k in enumerate(T_amb_K):
        for j, alpha_col in enumerate(alpha_columns):
            val = df.iloc[i, j]  # Use iloc for positional indexing
            if not np.isnan(val):
                T_amb_list.append(t_amb_k - 273.15)  # Convert to Celsius
                alpha_list.append(alpha_values[j])
                param_list.append(val)
    
    T_amb_array = np.array(T_amb_list)
    alpha_array = np.array(alpha_list)
    param_array = np.array(param_list)
    
    if len(param_array) == 0:
        raise ValueError(f"No valid data found in database file for parameter '{param}'")
    
    print(f"Data range: T_amb=[{T_amb_array.min():.1f}, {T_amb_array.max():.1f}]°C, alpha=[{alpha_array.min():.3f}, {alpha_array.max():.3f}]")
    
    # Unit map for labeling
    unit_map = {
        'P_h_Sbc': 'Pa',
        'delta_T_sc_DMS': '°C',
        'COP_CO2_Sbc': '–',
        'COP_DMS_CO2': '–',
        'COP_star_Sbc': '–'
    }
    param_unit = unit_map.get(param, '–')
    
    # Create 3D plot
    fig = plt.figure(figsize=(14, 9))
    ax = fig.add_subplot(111, projection='3d')
    
    if style == 'scatter_plot':
        # Scatter plot for the data points
        scatter = ax.scatter(T_amb_array, alpha_array, param_array, 
                           c=param_array, cmap='viridis', s=20, alpha=0.6)
        cbar = plt.colorbar(scatter, ax=ax, shrink=0.5, aspect=5)
        cbar.set_label(f'{param} ({param_unit})', fontsize=10)
    
    elif style == 'surface':
        # Create a regular grid for interpolation
        T_amb_grid = np.linspace(T_amb_array.min(), T_amb_array.max(), 50)
        alpha_grid = np.linspace(alpha_array.min(), alpha_array.max(), 50)
        T_amb_mesh, alpha_mesh = np.meshgrid(T_amb_grid, alpha_grid)
        
        # Interpolate parameter values on the grid
        points = np.column_stack([T_amb_array, alpha_array])
        param_mesh = griddata(points, param_array, (T_amb_mesh, alpha_mesh), method='cubic')
        
        # Plot surface
        surf = ax.plot_surface(T_amb_mesh, alpha_mesh, param_mesh, cmap='viridis', alpha=0.8)
        cbar = plt.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
        cbar.set_label(f'{param} ({param_unit})', fontsize=10)
    
    # Add labels and title
    ax.set_xlabel(r'$T_{\mathrm{amb}}$ (°C)', fontsize=11)
    ax.set_ylabel(r'$\alpha (-)$', fontsize=11)
    ax.set_zlabel(f'{param} ({param_unit})', fontsize=11)
    ax.set_title(f'{param} vs ($T_{{\\mathrm{{amb}}}}$, α) - {style}', fontsize=14, pad=20)
    
    plt.tight_layout()
    
    if save_fig:
        os.makedirs(EXPLICATIVE_PLOTS_SAVING_DIR, exist_ok=True)
        ax.view_init(elev=30, azim=30, roll=0)
        fname = f'surface_3D_{param}_alpha_{style}.png'
        fpath = os.path.join(EXPLICATIVE_PLOTS_SAVING_DIR, fname)
        plt.savefig(fpath, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {fpath}")
    
    plt.show()

def plot_param_modeled_vs_alpha(param, T_amb_C, db_file_path, alpha_upper_bounds=None, point_stride=1, save_fig=False):
    """Plot modeled parameter vs alpha for one or multiple temperatures.
    param : str
        Parameter to plot: 'P_h_Sbc', 'COP_CO2_Sbc', 'COP_DMS_CO2', or 'COP_star_Sbc'
    T_amb_C : float or list of float
        Ambient temperature(s) in Celsius. Can be a single value or a list of values.
    alpha_upper_bounds : float or list of float or None
        Maximum alpha to plot for each temperature. Must be same length as T_amb_C
        when T_amb_C is a list; if T_amb_C is a single value, a single float is allowed.
        If None, plots up to the maximum available alpha for each temperature.
    point_stride : int, optional
        Plot every Nth point after sorting by alpha. Use 1 for all points, 2 for 1/2,
        3 for 1/3, or 4 for 1/4 (default: 1).
    db_file_path : str, optional
        Path to the aggregated database CSV (generated by aggregate_and_organise_db_data).
        File must have T_amb (K) as index and alpha values as columns.
    save_fig : bool, optional
        If True, save the figure to disk (default: False).
    """
    if param not in DB_PARAMS:
        raise ValueError(f"Parameter must be one of {DB_PARAMS}, got '{param}'")
    
    if not os.path.exists(db_file_path):
        raise FileNotFoundError(f"File not found: {db_file_path}")
    
    # Load the aggregated database file (T_amb as index, alpha values as columns)
    df = pd.read_csv(db_file_path, sep=';', index_col=0)
    
    # Convert single temperature to list for uniform handling
    if isinstance(T_amb_C, (int, float)):
        T_amb_C_list = [T_amb_C]
    else:
        T_amb_C_list = list(T_amb_C)

    if alpha_upper_bounds is None:
        alpha_upper_bounds_list = None
    elif isinstance(alpha_upper_bounds, (int, float)):
        alpha_upper_bounds_list = [alpha_upper_bounds]
    else:
        alpha_upper_bounds_list = list(alpha_upper_bounds)

    if alpha_upper_bounds_list is not None and len(alpha_upper_bounds_list) != len(T_amb_C_list):
        raise ValueError(
            f"alpha_upper_bounds must have same length as T_amb_C "
            f"({len(alpha_upper_bounds_list)} vs {len(T_amb_C_list)})"
        )

    if point_stride not in (1, 2, 3, 4):
        raise ValueError("point_stride must be 1, 2, 3, or 4")
    
    # Get unique T_amb values from the file (index is in K)
    unique_T_K = df.index.values
    
    unit_map = {'P_h_Sbc': 'Pa', 'delta_T_sc_DMS': 'K', 'COP_CO2_Sbc': '–', 'COP_DMS_CO2': '–', 'COP_star_Sbc': '–'}
    unit = unit_map.get(param, '–')
    
    # Create color map (blue to green gradient)
    cmap = plt.cm.viridis if len(T_amb_C_list) > 1 else plt.cm.Blues
    colors = cmap(np.linspace(0.3, 0.9, len(T_amb_C_list)))
    
    plt.figure(figsize=(5, 6))
    
    T_used_list = []
    for idx, T_target_C in enumerate(T_amb_C_list):
        target_K = T_target_C + 273.15
        # Find the closest T_amb in the database
        T_match_K = unique_T_K[np.abs(unique_T_K - target_K).argmin()]
        
        # Extract the row for this T_amb
        row_data = df.loc[T_match_K]
        
        # Remove NaN values and sort by alpha
        alpha_values = df.columns.astype(float).values
        valid_mask = ~row_data.isna().values
        alpha_valid = alpha_values[valid_mask]
        param_valid = row_data[valid_mask].values
        
        # Apply per-temperature alpha upper bound when provided
        if alpha_upper_bounds_list is None:
            alpha_upper = None
        else:
            alpha_upper = alpha_upper_bounds_list[idx]

        if alpha_upper is not None:
            bound_mask = alpha_valid <= alpha_upper
            alpha_valid = alpha_valid[bound_mask]
            param_valid = param_valid[bound_mask]

        # Sort by alpha
        sort_idx = np.argsort(alpha_valid)
        alpha_sorted = alpha_valid[sort_idx]
        param_sorted = param_valid[sort_idx]

        if point_stride > 1:
            alpha_sorted = alpha_sorted[::point_stride]
            param_sorted = param_sorted[::point_stride]
        
        if len(alpha_sorted) == 0:
            if alpha_upper is None:
                print(f"Warning: No valid data found for T_amb close to {T_target_C:.2f} °C, skipping")
            else:
                print(
                    f"Warning: No valid data found for T_amb close to {T_target_C:.2f} °C "
                    f"with alpha <= {alpha_upper:.3f}, skipping"
                )
            continue
        
        T_used_C = T_match_K - 273.15
        T_used_list.append(T_used_C)
        
        label = f'T_amb = {T_used_C:.2f} °C'
        plt.plot(alpha_sorted, param_sorted, marker='v', label=label, 
                 color=colors[idx], linewidth=2, markersize=6, linestyle='--')
        
        if abs(T_match_K - target_K) > 0.05:
            print(f"Warning: used T_amb {T_used_C:.2f} °C (closest in DB) instead of requested {T_target_C:.2f} °C")
    
    if param == 'COP_star_Sbc':
        param_name = 'COP*'
    else:
        param_name = param

    plt.xlabel(r'$\alpha$ (–)', fontsize=11)
    plt.ylabel(f'{param_name} ({unit})', fontsize=11)
    
    if len(T_amb_C_list) == 1:
        plt.title(f'{param_name} vs $\\alpha$ (T_amb = {T_used_list[0]:.2f} °C)', fontsize=12)
    else:
        plt.title(f'{param_name} vs $\\alpha$', fontsize=12)
    
    plt.grid(True, alpha=0.3)
    plt.legend(fontsize=10)
    plt.tight_layout()

    if save_fig:
        os.makedirs(EXPLICATIVE_PLOTS_SAVING_DIR, exist_ok=True)
        if len(T_amb_C_list) == 1:
            fname = f'alpha_curve_{param}_T{T_used_list[0]:.2f}C_modeled.png'.replace(' ', '')
        else:
            fname = f'alpha_curve_{param}_multi_T_modeled.png'
        fpath = os.path.join(EXPLICATIVE_PLOTS_SAVING_DIR, fname)
        plt.savefig(fpath, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {fpath}")

    plt.show()

def model_and_sample_db(param, db_file_path, poly_reg_degree=3, plot_reg=False, save_data=False):
    """Model (with polynomial regression) and sample an aggregated database file.
    
    For each alpha value (column) in the aggregated database, performs polynomial
    regression of degree poly_reg_degree on param = f(T_amb), optionally plots the
    results, samples the function with 0.5°C step, and returns a DataFrame with
    temperatures as rows and alpha values as columns.
    param : str
        Parameter to model: 'P_h_Sbc', 'COP_CO2_Sbc', 'COP_DMS_CO2', or 'COP_star_Sbc'
    db_file_path : str
        Path to the aggregated database CSV (generated by aggregate_and_organise_db_data).
        File must have T_amb (K) as index and alpha values as columns.
    poly_reg_degree : int, optional
        Degree of polynomial regression (default: 3)
    plot_reg : bool, optional
        If True, save regression plots in 'reg_plots' folder (default: False)
    save_data : bool, optional
        If True, save the resulting DataFrame to CSV (default: False)
    
    Returns
    -------
    pd.DataFrame
        DataFrame with temperatures (°C) as rows and alpha values as columns
    """
    if param not in DB_PARAMS:
        raise ValueError(f"Parameter must be one of {DB_PARAMS}, got '{param}'")
    
    if not os.path.exists(db_file_path):
        raise FileNotFoundError(f"File not found: {db_file_path}")

    # Load aggregated CSV (T_amb as index, alpha values as columns)
    df = pd.read_csv(db_file_path, sep=';', index_col=0)

    # Extract alpha values from columns
    alpha_values = sorted(df.columns.astype(float).values)

    # Get T_amb range (index is in K)
    T_amb_min_K = df.index.min()
    T_amb_max_K = df.index.max()
    T_amb_min_C = T_amb_min_K - 273.15
    T_amb_max_C = T_amb_max_K - 273.15
    
    # Create sampling grid (0.5°C step) - use linspace to ensure exact number of points
    n_points = int(np.round((T_amb_max_C - T_amb_min_C) / 0.5)) + 1
    T_amb_sample_global_C = np.linspace(T_amb_min_C, T_amb_max_C, n_points)
    
    # Create output DataFrame
    result_df = pd.DataFrame(index=T_amb_sample_global_C, columns=alpha_values)
    result_df.index.name = 'T_amb_C'
    
    # Create plot directory if needed
    if plot_reg:
        db_dirname = os.path.dirname(db_file_path)
        reg_plots_path = os.path.join(db_dirname, 'reg_plots')
        os.makedirs(reg_plots_path, exist_ok=True)
    
    unit_map = {'P_h_Sbc': 'Pa', 'delta_T_sc_DMS': 'K', 'COP_CO2_Sbc': '–', 'COP_DMS_CO2': '–', 'COP_star_Sbc': '–'}
    unit = unit_map.get(param, '–')
    
    # Process each alpha value
    for alpha in alpha_values:
        alpha_col = str(alpha)
        if alpha_col not in df.columns:
            print(f"Warning: alpha column {alpha_col} not found, skipping")
            continue

        # Extract data for regression
        T_amb_data_K = df.index.values
        T_amb_data_C = T_amb_data_K - 273.15
        param_data = df[alpha_col].values
        
        # Remove NaN values
        valid_mask = ~np.isnan(param_data)
        T_amb_data_C = T_amb_data_C[valid_mask]
        param_data = param_data[valid_mask]
        
        if len(T_amb_data_C) < poly_reg_degree + 1:
            print(f"Warning: Not enough data for alpha = {alpha:.2f}, skipping")
            continue
        
        # Filter out data points between 21°C and 25.1°C for regression
        mask = (T_amb_data_C < 21.0) | (T_amb_data_C > 25.1)
        T_amb_filtered_C = T_amb_data_C[mask]
        param_filtered = param_data[mask]
        
        # Check if we still have enough points after filtering
        if len(T_amb_filtered_C) < poly_reg_degree + 1:
            print(f"Warning: Not enough data after filtering for alpha = {alpha:.2f}, skipping")
            continue
        
        # Get the temperature range for this alpha
        T_amb_alpha_min_C = T_amb_data_C.min()
        T_amb_alpha_max_C = T_amb_data_C.max()
        
        # Perform polynomial regression on filtered data
        coeffs = np.polyfit(T_amb_filtered_C, param_filtered, poly_reg_degree)
        poly_model = np.poly1d(coeffs)
        
        # Sample the model only within the valid temperature range for this alpha
        # Initialize with NaN for all temperatures
        param_sampled_full = np.full(len(T_amb_sample_global_C), np.nan)
        
        # Find indices where we should sample (within data range for this alpha)
        valid_indices = (T_amb_sample_global_C >= T_amb_alpha_min_C) & (T_amb_sample_global_C <= T_amb_alpha_max_C)
        param_sampled_full[valid_indices] = poly_model(T_amb_sample_global_C[valid_indices])
        
        # Store in result DataFrame
        result_df[alpha] = param_sampled_full
        
        # Plot if requested
        if plot_reg:
            # For plotting, use only the valid range
            T_amb_plot_C = T_amb_sample_global_C[valid_indices]
            param_plot = param_sampled_full[valid_indices]
            
            plt.figure(figsize=(10, 6))
            # Plot all database points (including filtered ones) in different colors
            plt.scatter(T_amb_filtered_C, param_filtered, color='blue', s=50, alpha=0.6, label='Used for regression')
            if len(T_amb_data_C) > len(T_amb_filtered_C):
                excluded_mask = ~mask
                plt.scatter(T_amb_data_C[excluded_mask], param_data[excluded_mask], 
                           color='gray', s=50, alpha=0.4, marker='x', label='Excluded (21-25.1°C)')
            plt.plot(T_amb_plot_C, param_plot, color='red', linewidth=2, label=f'Polynomial fit (degree {poly_reg_degree})')
            plt.xlabel(r'$T_{\mathrm{amb}}$ (°C)', fontsize=11)
            plt.ylabel(f'{param} ({unit})', fontsize=11)
            plt.title(f'{param} vs $T_{{\\mathrm{{amb}}}}$ (α = {alpha:.2f})', fontsize=12)
            plt.legend(fontsize=10)
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            fname = f'reg_{param}_alpha{alpha:.2f}.png'.replace(' ', '').replace('.', '_')
            fpath = os.path.join(reg_plots_path, fname)
            plt.savefig(fpath, dpi=300, bbox_inches='tight')
            plt.close()
            print(f"Regression plot saved: {fname}")
    
    # Save data if requested
    if save_data:
        output_dir = os.path.dirname(db_file_path)
        fname = f'sampled_{param}_poly{poly_reg_degree}.csv'
        fpath = os.path.join(output_dir, fname)
        result_df.to_csv(fpath, sep=';')
        print(f"Sampled data saved: {fpath}")
    
    print(f"Modeling complete: {len(alpha_values)} alpha values processed")
    return result_df

def plot_modeled_param_vs_Tamb_and_DMS_3D(file_path, style='surface', save_fig=False):
    """Plot 3D representation of modeled parameter data from CSV created by model_and_sample_db_for_article().
    file_path : str
        Path to the CSV file containing modeled data (output from model_and_sample_db_for_article)
    style : str, optional
        Plot style: 'scatter_plot' for scatter points or 'surface' (default) for interpolated surface
    save_fig : bool, optional
        If True, save the figure to EXPLICATIVE_PLOTS_SAVING_DIR (default: False)
    """
    if style not in ['scatter_plot', 'surface']:
        raise ValueError(f"style must be 'scatter_plot' or 'surface', got '{style}'")
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Load the modeled data
    df = pd.read_csv(file_path, sep=';', index_col=0)
    
    # Extract parameter name from filename (e.g., 'sampled_COP_star_Sbc_poly3.csv' -> 'COP_star_Sbc')
    filename = os.path.basename(file_path)
    param = filename.replace('sampled_', '').split('_poly')[0]
    
    # Get T_amb values (index) and alpha values (columns)
    T_amb_C = df.index.values
    alpha_columns = df.columns.values  # Keep as strings initially
    alpha_values = df.columns.astype(float).values
    
    # Prepare data for plotting (remove NaN values for scatter plot)
    T_amb_list = []
    alpha_list = []
    param_list = []
    
    for i, t_amb in enumerate(T_amb_C):
        for j, alpha_col in enumerate(alpha_columns):
            val = df.iloc[i, j]  # Use iloc for positional indexing
            if not np.isnan(val):
                T_amb_list.append(t_amb)
                alpha_list.append(alpha_values[j])
                param_list.append(val)
    
    T_amb_array = np.array(T_amb_list)
    alpha_array = np.array(alpha_list)
    param_array = np.array(param_list)
    
    # Unit map for labeling
    unit_map = {
        'P_h_Sbc': 'Pa',
        'delta_T_sc_DMS': 'K',
        'COP_CO2_Sbc': '–',
        'COP_DMS_CO2': '–',
        'COP_star_Sbc': '–'
    }
    param_unit = unit_map.get(param, '–')
    
    # Create 3D plot
    fig = plt.figure(figsize=(6,5))
    ax = fig.add_subplot(111, projection='3d')
    
    if style == 'scatter_plot':
        # Scatter plot for the data points
        scatter = ax.scatter(T_amb_array, alpha_array, param_array, 
                           c=param_array, cmap='viridis', s=20, alpha=0.6)
        cbar = plt.colorbar(scatter, ax=ax, shrink=0.5, aspect=5)
        cbar.set_label(f'{param} ({param_unit})', fontsize=10)
    
    elif style == 'surface':
        # Create a regular grid for interpolation
        T_amb_grid = np.linspace(T_amb_array.min(), T_amb_array.max(), 50)
        alpha_grid = np.linspace(alpha_array.min(), alpha_array.max(), 50)
        T_amb_mesh, alpha_mesh = np.meshgrid(T_amb_grid, alpha_grid)
        
        # Interpolate parameter values on the grid
        points = np.column_stack([T_amb_array, alpha_array])
        param_mesh = griddata(points, param_array, (T_amb_mesh, alpha_mesh), method='cubic')
        
        # Plot surface
        surf = ax.plot_surface(T_amb_mesh, alpha_mesh, param_mesh, cmap='viridis', alpha=0.8)
        # cbar = plt.colorbar(surf, ax=ax, shrink=0.5, aspect=5)
        # cbar.set_label(f'{param} ({param_unit})', fontsize=10)
    
    # Add labels and title
    if param == 'COP_star_Sbc':
        param_name = 'COP*'
    else:
        param_name = param
    ax.set_xlabel(r'$T_{\mathrm{amb}}$ (°C)', fontsize=11)
    ax.set_ylabel(r'$\alpha (-)$', fontsize=11)
    ax.set_zlabel(f'{param_name} ({param_unit})', fontsize=11)
    ax.set_title(f'{param_name} vs ($T_{{\\mathrm{{amb}}}}$, α)', fontsize=14, pad=20)
    
    plt.tight_layout()
    
    if save_fig:
        os.makedirs(EXPLICATIVE_PLOTS_SAVING_DIR, exist_ok=True)
        ax.view_init(elev=30, azim=50, roll=0)
        fname = f'surface_3D_{param}_alpha_{style}_modeled.png'
        fpath = os.path.join(EXPLICATIVE_PLOTS_SAVING_DIR, fname)
        plt.savefig(fpath, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {fpath}")
    
    plt.show()

################################# EXECUTION ZONE #################################

#### DB CONSTRUCTION ####
# """Select the right SAVING_PATH_DATA at the top of the file before running this part !"""
# T_START_Celcius = 5
# T_STOP_Celcius = 41.1
# complete_db(T_START_Celcius + 273.15, T_STOP_Celcius + 273.15, 0.5)


#### RAW PLOTS ####
# plot_param_vs_Tamb_and_DMS_3D(param='COP_star_Sbc', db_path=DATA_3D_DB_PATH, style='surface', variable='alpha', save_fig=False)
# plot_param_vs_alpha('COP_star_Sbc', [4*k for k in range(1,11)], db_path=DATA_3D_DB_PATH)


#### DB MODELING AND MODELS PLOTS ####
RAW_DATA = os.path.join(DATA_3D_SAVING_DIR, 'model_COP_star_vs_Tamb_and_alpha.csv')
MODELED_DATA = os.path.join(DATA_3D_SAVING_DIR, 'sampled_COP_star_Sbc_poly3.csv')

# aggregate_and_organise_db_data('COP_star_Sbc', db_path=DATA_3D_DB_PATH, final_saving_path=RAW_DATA)
# cut_rows_out_from_csv(RAW_DATA)
# plot_param_vs_Tamb_and_alpha_3D('COP_star_Sbc', db_file_path=RAW_DATA, style='surface', save_fig=False)
T_amb_C_0 = [5,10,15] + [4*k for k in range(5,10)]
alpha_upper_bounds_0 = [0.4, 0.42, 0.6,0.65,0.98,1,1.1,1.22]
# plot_param_modeled_vs_alpha('COP_star_Sbc', T_amb_C_0, RAW_DATA, alpha_upper_bounds=alpha_upper_bounds_0,
#                             point_stride=4, save_fig=False)

# model_and_sample_db('COP_star_Sbc', RAW_DATA, poly_reg_degree=3, plot_reg=False, save_data=True)
plot_modeled_param_vs_Tamb_and_DMS_3D(MODELED_DATA, style='surface', save_fig=True)

















# def complete_db(T_start, T_stop, T_step, db_path=DATA_3D_DB_PATH):
#     """Creates one CSV per `T_amb` value. After finishing each `T_amb`, writes its CSV.
#     CSV columns: 'T_amb';'alpha';'P_h_Sbc';'delta_T_sc_DMS';'COP_CO2_Sbc';'COP_DMS_CO2';'COP_star_Sbc'."""

#     T_amb_range = np.arange(T_start, T_stop, T_step)

#     for T_amb in T_amb_range:
#         rows = []
#         for alpha in ALPHA_RANGE:
#             if T_amb <= T_AMB_MAX_SUBCRITICAL:
#                 T_gc_out = get_T_gc_out_min_subcritical(T_amb, max_iter=50, required_pinch=PINCH_AIR)[0]
#                 P_h = prp.PropsSI('P', 'T', T_gc_out, 'Q', 0.5, "CarbonDioxide")
#             else:
#                 T_gc_out = T_amb + PINCH_AIR
#                 P_h = optimize_Ph_supercritical_cycle_with_DMS(T_EV, T_gc_out, T_amb, alpha=alpha)[0]

#             sbc_cycle = ComplexSystem(
#                 fluid="CarbonDioxide",
#                 T_ev=T_EV,
#                 P_h=P_h,
#                 T_gc_out=T_gc_out,
#                 T_amb_air=T_amb,
#                 alpha=alpha
#             )
#             sbc_cycle.compute_cycle()

#             COP_star_Sbc = sbc_cycle.get_COP()
#             COP_DMS_CO2 = sbc_cycle.get_DMS_COP()
#             COP_CO2_Sbc = sbc_cycle.get_CO2_COP()
#             delta_T_sc_DMS = sbc_cycle.get_delta_T_sc_DMS()

#             rows.append({
#                 'T_amb': T_amb,
#                 'alpha': float(alpha),
#                 'P_h_Sbc': float(P_h),
#                 'delta_T_sc_DMS': float(delta_T_sc_DMS),
#                 'COP_CO2_Sbc': float(COP_CO2_Sbc),
#                 'COP_DMS_CO2': float(COP_DMS_CO2),
#                 'COP_star_Sbc': float(COP_star_Sbc),
#             })

#         # Write CSV for this T_amb (semicolon-delimited)
#         df_out = pd.DataFrame(rows, columns=[
#             'T_amb','alpha','P_h_Sbc','delta_T_sc_DMS','COP_CO2_Sbc','COP_DMS_CO2','COP_star_Sbc'
#         ])
#         T_amb_C = T_amb - 273.15  # filename in °C for readability
#         fname = f"T_amb_{T_amb_C:.2f}C.csv".replace(' ', '')
#         fpath = os.path.join(db_path, fname)
#         df_out.to_csv(fpath, sep=';', index=False)
#         print(f"Computation done: {T_amb_C:.2f} °C")

# def complete_db_alpha(alpha_list, T_start, T_stop, T_step, use_Ph_opt_correlation=False, db_path=DATA_3D_DB_PATH, alpha_interpolation=False):
#     """Add missing alpha rows into each existing T_amb CSV.
#     For every T_amb in [T_start, T_stop) with step T_step, load the existing CSV
#     named T_amb_<Tcelsius>C.csv in db_path. For each alpha in alpha_list that is
#     not already present, recompute the cycle (subcritical or supercritical
#     depending on T_amb) and append the new rows, then rewrite the CSV sorted by
#     alpha. Skips temperatures whose CSV is absent.
#     use_Ph_opt_correlation : bool, optional
#         If True, use the P_h_opt_1 vs T_amb correlation for supercritical cycles
#         instead of optimizing P_h for each alpha. Default is False.
#     alpha_interpolation : bool, optional
#         If False (default), use the provided alpha_list for all temperatures.
#         If True, dynamically generate alpha_list for each temperature using linear interpolation:
#         alpha_max = M * T_amb + P, and create range np.arange(0.45, alpha_max, 0.02).
#         This allows temperature-dependent alpha ranges if valid alpha values vary with T_amb.
#     """
#     T_amb_range = np.arange(T_start, T_stop, T_step)

#     if use_Ph_opt_correlation:
#         interpolation_Ph_opt_1_vs_Tamb = get_interpolation_P_h_opt_1_vs_Tamb()
#         print("[P_h_opt_1 = f(T_amb) correlation sucessfully obtained from M1 settings]")

#     for T_amb in T_amb_range:
#         T_amb_C = T_amb - 273.15
#         fname = f"T_amb_{T_amb_C:.2f}C.csv".replace(' ', '')
#         fpath = os.path.join(db_path, fname)

#         if not os.path.exists(fpath):
#             print(f"File not found, skipped: {fpath}")
#             continue

#         df = pd.read_csv(fpath, sep=';')
#         existing_alphas = df['alpha'].astype(float).values

#         if alpha_interpolation:
#             alpha_max = M * T_amb + P + 0.02
#             print(f"alpha_max (interpolated) for {T_amb_C:.2f} °C: {alpha_max:.4f}")
#             alpha_list = np.arange(0.45, alpha_max, 0.02)

#         new_rows = []
#         for alpha in alpha_list:
#             if np.isclose(existing_alphas, alpha).any():
#                 continue

#             if T_amb <= T_AMB_MAX_SUBCRITICAL:
#                 T_gc_out = get_T_gc_out_min_subcritical(T_amb, max_iter=50, required_pinch=PINCH_AIR)[0]
#                 P_h = prp.PropsSI('P', 'T', T_gc_out, 'Q', 0.5, "CarbonDioxide")
#             else:
#                 T_gc_out = T_amb + PINCH_AIR
#                 if use_Ph_opt_correlation:
#                     P_h = interpolation_Ph_opt_1_vs_Tamb(T_amb)
#                 else:
#                     P_h = optimize_Ph_supercritical_cycle_with_DMS(T_EV, T_gc_out, T_amb, alpha=alpha)[0]

#             sbc_cycle = ComplexSystem(
#                 fluid="CarbonDioxide",
#                 T_ev=T_EV,
#                 P_h=P_h,
#                 T_gc_out=T_gc_out,
#                 T_amb_air=T_amb,
#                 alpha=alpha
#             )
#             sbc_cycle.compute_cycle()

#             COP_star_Sbc = sbc_cycle.get_COP()
#             COP_DMS_CO2 = sbc_cycle.get_DMS_COP()
#             COP_CO2_Sbc = sbc_cycle.get_CO2_COP()
#             delta_T_sc_DMS = sbc_cycle.get_delta_T_sc_DMS()

#             new_rows.append({
#                 'T_amb': T_amb,
#                 'alpha': float(alpha),
#                 'P_h_Sbc': float(P_h),
#                 'delta_T_sc_DMS': float(delta_T_sc_DMS),
#                 'COP_CO2_Sbc': float(COP_CO2_Sbc),
#                 'COP_DMS_CO2': float(COP_DMS_CO2),
#                 'COP_star_Sbc': float(COP_star_Sbc),
#             })

#         if not new_rows:
#             print(f"No new alpha to add for {T_amb_C:.2f} °C")
#             continue

#         df_out = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True)
#         df_out = df_out.sort_values('alpha').reset_index(drop=True)
#         df_out.to_csv(fpath, sep=';', index=False)
#         print(f"Updated CSV with {len(new_rows)} alphas at {T_amb_C:.2f} °C")

###################################################################################



# def plot_param_vs_Tamb(param, alpha_value, db_path=DATA_3D_DB_PATH, save_fig=False):
#     """Plot parameter vs T_amb for one or multiple alpha values."""
#     if param not in DB_PARAMS:
#         raise ValueError(f"Parameter must be one of {DB_PARAMS}, got '{param}'")

#     # Convert single alpha to list for uniform handling
#     if isinstance(alpha_value, (int, float)):
#         alpha_list = [alpha_value]
#     else:
#         alpha_list = list(alpha_value)

#     csv_files = sorted([f for f in os.listdir(db_path) if f.endswith('.csv')])
#     if not csv_files:
#         raise FileNotFoundError(f"No CSV files found in {db_path}")

#     data = [pd.read_csv(os.path.join(db_path, f), sep=';') for f in csv_files]
#     df = pd.concat(data, ignore_index=True)
    
#     unit_map = {'P_h_Sbc': 'Pa', 'delta_T_sc_DMS': '°C', 'COP_CO2_Sbc': '–', 'COP_DMS_CO2': '–', 'COP_star_Sbc': '–'}
#     unit = unit_map.get(param, '–')
    
#     # Create color map (blue to green gradient)
#     cmap = plt.cm.viridis if len(alpha_list) > 1 else plt.cm.Blues
#     colors = cmap(np.linspace(0.3, 0.9, len(alpha_list)))
    
#     plt.figure(figsize=(10, 6))
    
#     alpha_used_list = []
#     for idx, alpha_target in enumerate(alpha_list):
#         df_sel = df[np.isclose(df['alpha'], alpha_target)].sort_values('T_amb')
        
#         if df_sel.empty:
#             print(f"Warning: No rows found for alpha = {alpha_target:.2f}, skipping")
#             continue
        
#         T_amb_K = df_sel['T_amb'].values
#         T_amb_C = T_amb_K - 273.15
#         y = df_sel[param].values
#         alpha_used_list.append(alpha_target)
        
#         label = f'α = {alpha_target:.2f}'
#         plt.plot(T_amb_C, y, marker='o', label=label, color=colors[idx], linewidth=2, markersize=6)
    
#     plt.xlabel(r'$T_{\mathrm{amb}}$ (°C)', fontsize=11)
#     plt.ylabel(f'{param} ({unit})', fontsize=11)
    
#     if len(alpha_list) == 1:
#         plt.title(f'{param} vs $T_{{\\mathrm{{amb}}}}$ (α = {alpha_used_list[0]:.2f})', fontsize=12)
#     else:
#         plt.title(f'{param} vs $T_{{\\mathrm{{amb}}}}$ (multiple α values)', fontsize=12)
    
#     plt.grid(True, alpha=0.3)
#     plt.legend(fontsize=10)
#     plt.tight_layout()
    
#     if save_fig:
#         os.makedirs(EXPLICATIVE_PLOTS_SAVING_DIR, exist_ok=True)
#         if len(alpha_list) == 1:
#             fname = f'Tamb_curve_{param}_alpha{alpha_used_list[0]:.2f}.png'.replace(' ', '')
#         else:
#             fname = f'Tamb_curve_{param}_multi_alpha.png'
#         fpath = os.path.join(EXPLICATIVE_PLOTS_SAVING_DIR, fname)
#         plt.savefig(fpath, dpi=300, bbox_inches='tight')
#         print(f"Figure saved: {fpath}")
    
#     plt.show()

########################################################""

# ## CORRECTION PLOT FOR ARTICLE ##
# """Goal = erase some non-physical behaviors (like the variations around T_AMB_MAX_SUBCRITICAL)"""






# ################################# EXECUTION ZONE #################################

# #### DB CONSTRUCTION ####
# """Select the right DATA_3D_DB_PATH at the top of the file before running this part !"""
# T_START_Celcius = 25.5
# T_STOP_Celcius = 41.1
# # complete_db(T_start=273.15 + T_START_Celcius, T_stop=273.15 + T_STOP_Celcius, T_step=0.5)
# # complete_db_alpha(ALPHA_RANGE_ADDITIONAL, 273.15 + T_START_Celcius, 273.15 + T_STOP_Celcius, 0.5, use_Ph_opt_correlation=True, alpha_interpolation=True)

# #### CORRECTION FOR PLOT ARTICLE ####
# """Create a modeled and smoothed DB for better plot rendering in the article."""
# # model_and_sample_db_for_article(param='COP_star_Sbc', poly_reg_degree=3, plot_reg=True, save_data=True)
# FILE_PATH_MODELED_DB = os.path.join(os.path.dirname(DATA_3D_DB_PATH), 'sampled_COP_star_Sbc_poly3.csv')
# # cut_rows_csv_model(file_path=FILE_PATH_MODELED_DB, T_start_C=18.0)

# #### PLOTS ####
# # plot_modelled_param_vs_Tamb_and_DMS_3D(file_path=FILE_PATH_MODELED_DB, style='surface', save_fig=False)
# # plot_param_vs_Tamb_and_DMS_3D(param='COP_star_Sbc', style='surface', variable='alpha', save_fig=True)
# # plot_param_vs_Tamb_and_DMS_3D(param='COP_star_Sbc', style='surface', variable='delta_T_sc_DMS', save_fig=True)

# # plot_param_vs_Tamb_and_DMS_3D(param='COP_star_Sbc', db_path=DATA_3D_DB_PATH, style='surface', variable='alpha', save_fig=False)

