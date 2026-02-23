"""
This module contains functions to convert optimization settings from CSV format to AMPL DAT format for both M1 and M2 cycles.
"""
import pandas as pd
import sys
import os

# Navigate to the root directory (codes_bastien)
root_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(root_dir)
sys.path.insert(0, root_dir)

from CONSTANTS import *

def get_dat_format(params, input_path, output_path, output_filename="optim_settings.dat"):
    """
    Converts CSV columns to AMPL DAT format and writes to a single file.
    The expected CSV structure has a multi-level index (day_type, parameter),
    with hours as rows.
    
    Parameters:
    -----------
    params : str or list
        Parameter name(s) to convert (e.g., 'T_amb' or ['T_amb', 'P_h_1'])
    input_path : str
        Path to the input CSV file
    output_filename : str
        Name of the output DAT file (e.g., 'M1_optim_settings.dat')
    output_path : str
        Directory path for output file 
    
    Output format (example for T_amb):
    param T_amb :=
    [ 'Low', 0] 5.69425616173212
    [ 'Low', 1] 5.61202479560267...
    """
    if isinstance(params, str):
        params = [params]
    df = pd.read_csv(input_path, header=[0, 1], index_col=0)
    dat_content = ""
    
    for param in params:
        if param == 'COP_DMS':
            dat_content += f"param {param}_CO2 :=\n"
        else:
            dat_content += f"param {param} :=\n"
        dp =0
        for day_type in DAY_TYPES:
            dp +=1
            if (day_type, param) in df.columns:
                col = df[(day_type, param)]
                for hour in range(len(col)):
                    value = col.iloc[hour]
                    dat_content += f"[ '{day_type}', {hour}] {value}\n"
                # Blank line between day types
                if dp < len(DAY_TYPES):
                    dat_content += "\n"
                else:
                    dat_content = dat_content[:-1]

            else:
                print(f"Warning: Parameter '{param}' not found for day type '{day_type}'")
        
        # Add terminator for this parameter
        dat_content += ";\n\n"
    
    if output_path is not None:
        # Write all parameters to a single output file
        output_file = os.path.join(output_path, output_filename)
        with open(output_file, 'w') as f:
            f.write(dat_content)
        print(f"DAT file generated: {output_file}")

    return dat_content

def complete_final_dat_file(intro_file_path, input_M1_path, input_M2_path):
    """Reads M1 and M2 CSV files, converts specified parameters to DAT format, and appends to the intro DAT file."""

    M1_dat_content = get_dat_format(SETTINGS_M1_IN_DAT_FILE, input_M1_path, output_path=None)
    M2_dat_content = get_dat_format(SETTINGS_M2_IN_DAT_FILE, input_M2_path, output_path=None)

    # Add all parameters in the intro file 
    with open(intro_file_path, 'a') as f:
        f.write(M1_dat_content + M2_dat_content)
    print(f"DAT file completed: {intro_file_path}")
