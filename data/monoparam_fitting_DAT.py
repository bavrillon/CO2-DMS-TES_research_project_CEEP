import pandas as pd
import os

# Input file path
main_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_QLOAD_PATH = os.path.join(main_dir, 'external_time_series', 'outputs_external_time_series', 'hourly_avg_Qload_clustered.csv')
INPUT_CELEC_PATH = os.path.join(main_dir, 'external_time_series','outputs_external_time_series', 'hourly_elec_clustered_prices.csv')
OUTPUT_PATH = os.path.dirname(os.path.abspath(__file__))

DAY_TYPES = ['Low', 'Medium', 'High', 'Worst_day']

def get_dat_format_monoparam(input_path, param_name, output_filename, output_path=OUTPUT_PATH):
    """
    Converts CSV containing a single parameter (Q_load or C_elec for instance) to AMPL DAT 
    format and writes to a file. 
    The expected CSV structure has hours as rows and day types as columns.
    
    Parameters:
    -----------
    input_path : str
        Path to the input CSV file (e.g., INPUT_QLOAD_PATH or INPUT_CELEC_PATH)
    param_name : str
        Name of the parameter in the DAT file (e.g., 'Qload' or 'C_elec')
    output_filename : str
        Name of the output DAT file (e.g., 'Qload_clustered_fitted.dat')
    output_path : str
        Directory path for output file (default: fitted_for_DAT directory)
    
    Output format example:
    param Qload :=
    [ 'Low', 0] 36.04268758139499
    [ 'Low', 1] 39.398011058206244
    ...
    """
    df = pd.read_csv(input_path, index_col=0)
    
    dat_content = f"param {param_name} :=\n"
    
    dp = 0
    for day_type in DAY_TYPES:
        dp += 1
        if day_type in df.columns:
            col = df[day_type]
            for hour in range(len(col)):
                value = col.iloc[hour]
                dat_content += f"[ '{day_type}', {hour}] {value}\n"
            # Blank line between day types (except for the last one)
            if dp < len(DAY_TYPES):
                dat_content += "\n"
            else:
                # Remove the last newline before the terminator
                dat_content = dat_content[:-1]
        else:
            print(f"Warning: Day type '{day_type}' not found in {param_name} data")
    
    # Add terminator
    dat_content += ";\n"
    
    # Write to output file
    output_file = os.path.join(output_path, output_filename)
    with open(output_file, 'w') as f:
        f.write(dat_content)
    print(f"DAT file generated: {output_file}")

def get_dat_full_of_zeros(param_name, output_filename, output_path=OUTPUT_PATH):
    """
    Generates a DAT file with all zero values for a given parameter.
    param_name : str (e.g., 'beta_i_max'
    output_filename : str (e.g., 'beta_i_max_zeros.dat')
    output_path : str
        Directory path for output file (default: fitted_for_DAT directory)
    """
    dat_content = f"param {param_name} :=\n"
    
    dp = 0
    for day_type in DAY_TYPES:
        dp += 1
        for hour in range(24):
            dat_content += f"[ '{day_type}', {hour}] 0\n"
         # Blank line between day types (except for the last one)
        if dp < len(DAY_TYPES):
            dat_content += "\n"
        else:
            # Remove the last newline before the terminator
            dat_content = dat_content[:-1]
    
    # Add terminator
    dat_content += ";\n"
    
    # Write to output file
    output_file = os.path.join(output_path, output_filename)
    with open(output_file, 'w') as f:
        f.write(dat_content)
    print(f"DAT file with zeros generated: {output_file}")

############################ EXECUTION ############################

# get_dat_format_monoparam(INPUT_QLOAD_PATH, 'Q_dot_load', 'Qload_fitted.dat')
# get_dat_format_monoparam(INPUT_CELEC_PATH, 'C_elec', 'Celec_fitted.dat')
# get_dat_full_of_zeros('beta_i_max', 'beta_i_max_zeros.dat')