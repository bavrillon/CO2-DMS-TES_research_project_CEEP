import xml.etree.ElementTree as ET
import itertools
import pandas as pd
import re
import sys
import os

# Navigate to the root directory (codes_bastien)
root_dir = os.path.dirname(os.path.abspath(__file__))
for _ in range(4):  # 4 levels up
    root_dir = os.path.dirname(root_dir)
sys.path.insert(0, root_dir)

from CONSTANTS import *

os.chdir(os.path.dirname(__file__))
parent_dir = os.path.dirname(os.path.abspath(__file__))
grandparent_dir = os.path.dirname(parent_dir)
greatgrandparent_dir = os.path.dirname(grandparent_dir)
SOLUTION_XML_PATH = os.path.join(grandparent_dir, "Solution.xml")
OUTPUT_EXCEL_PATH = os.path.join(greatgrandparent_dir, "outputs_optim.xlsx")
MOD_FILE_PATH = os.path.join(grandparent_dir, 'system_model.mod')

# Load and parse the XML file
tree = ET.parse(SOLUTION_XML_PATH)
root = tree.getroot()

# Extract values from the XML
variables = root.find('variables')
values = {}

for variable in variables.findall('variable'):
    name = variable.get('name')
    value = variable.get('value')
    values[name] = value

# Extract the variables of interest
variables_needed = OUTPUT_OPTIM_VARIABLES
days = ['Low', 'Medium', 'High', 'Worst_day']
hours = [i for i in range(24)]

# Create a dictionary to hold DataFrames for each variable
dataframes = {}
for var in variables_needed:
    dataframes[var] = pd.DataFrame(index=hours, columns=days)
    dataframes[var].index.name = 'Hour'

for var, day, hour in itertools.product(variables_needed, days, hours):
    key = f"{var}({day},{hour})"
    dataframes[var].at[hour, day] = values.get(key, None)

# Cast variable sheets to numeric where possible
for var in variables_needed:
    dataframes[var] = dataframes[var].apply(pd.to_numeric, errors='coerce')


def parse_units_from_mod(mod_path):
    units = {}
    if not os.path.exists(mod_path):
        return units
    # Regex to capture var/param name at start of declaration line
    decl_re = re.compile(r"^\s*(var|param)\s+([A-Za-z0-9_]+)")
    with open(mod_path, 'r', encoding='utf-8') as f:
        for line in f:
            m = decl_re.match(line)
            if not m:
                continue
            name = m.group(2)
            if '#' in line:
                comment = line.split('#', 1)[1].strip()
                units[name] = comment
    # Some binaries may have no unit comment; add helpful defaults
    units.setdefault('b_mode', 'binary (mode selector)')
    return units

units_map = parse_units_from_mod(MOD_FILE_PATH)


# Save each DataFrame to an Excel file
with pd.ExcelWriter(OUTPUT_EXCEL_PATH) as writer:
    # Build Status info with descriptions
    header = root.find('header')
    quality = root.find('quality')
    status = {}
    if header is not None:
        for k in (
            'problemName', 'objectiveValue', 'solutionTypeString', 'solutionStatusValue',
            'solutionStatusString', 'solutionMethodString', 'primalFeasible', 'dualFeasible',
            'MIPNodes', 'MIPIterations', 'writeLevel'
        ):
            v = header.get(k)
            if v is not None:
                status[k] = v
        # Convenience flags
        status['is_feasible'] = str(header.get('primalFeasible') == '1')
        status['is_optimal'] = str('optimal' in (header.get('solutionStatusString') or '').lower())
    if quality is not None:
        for k in ('epInt', 'epRHS', 'maxIntInfeas', 'maxPrimalInfeas', 'maxX', 'maxSlack'):
            v = quality.get(k)
            if v is not None:
                status[k] = v

    status_descriptions = {
        'problemName': 'Name of the model solved (usually the .lp file).',
        'objectiveValue': 'Objective value at the reported solution (min or max per model sense).',
        'solutionTypeString': 'Type of solution (e.g., primal, dual).',
        'solutionStatusValue': 'Numeric status code of the solution.',
        'solutionStatusString': 'Solver status (e.g., integer optimal, tolerance).',
        'solutionMethodString': 'Algorithm used (e.g., mip for mixed-integer).',
        'primalFeasible': '1 if primal constraints are satisfied (feasible), else 0.',
        'dualFeasible': '1 if dual feasibility holds (LP context), else 0.',
        'MIPNodes': 'Number of branch-and-bound nodes explored.',
        'MIPIterations': 'Total solver iterations (e.g., simplex iterations).',
        'writeLevel': 'Detail level in this solution file.',
        'is_feasible': 'Derived flag: True if primalFeasible == 1.',
        'is_optimal': 'Derived flag: True if status string contains "optimal".',
        'epInt': 'Integrality tolerance for integer variables.',
        'epRHS': 'Constraint right-hand-side feasibility tolerance.',
        'maxIntInfeas': 'Max integrality violation across integer variables (≈ 0 if OK).',
        'maxPrimalInfeas': 'Max constraint violation (≈ 0 if OK).',
        'maxX': 'Maximum magnitude among decision variables.',
        'maxSlack': 'Maximum slack across constraints.'
    }
    status_rows = []
    for k, v in status.items():
        status_rows.append({'field': k, 'value': v, 'description': status_descriptions.get(k, '')})
    status_df = pd.DataFrame(status_rows, columns=['field', 'value', 'description'])
    status_df.to_excel(writer, sheet_name='Status', index=False)

    # Scalars first (second sheet), with descriptions
    scalar_desc = {
        'z_comp_CO2': 'Optimal CO2 compressor sizing/capacity.',
        'v_TES': 'Thermal Energy Storage (TES) volume.',
        'C_capex': 'Capital expenditure (CAPEX).',
        'C_opex': 'Operational expenditure (OPEX).',
        'C_npv': 'Net Present Value (NPV).',
        'C_total': 'Total cost (objective).'
    }
    scalar_values = {}
    for s in OUTPUT_OPTIM_SCALAR:
        scalar_values[s] = values.get(s, None)
    scalars_df = pd.DataFrame(
        [{
            'variable': k,
            'value': v,
            'unit': units_map.get(k, ''),
            'description': scalar_desc.get(k, '')
        } for k, v in scalar_values.items()],
        columns=['variable', 'value', 'unit', 'description']
    )
    # Cast scalar values to numeric where possible
    scalars_df['value'] = pd.to_numeric(scalars_df['value'], errors='coerce')
    scalars_df.to_excel(writer, sheet_name='Scalars', index=False)

    # Compute beta = Q_dot_TES_CO2 / Q_dot_CO2
    beta_df = dataframes['Q_dot_TES_CO2'] / dataframes['Q_dot_CO2']
    beta_df.columns = days
    
    # Then write all time-indexed variable sheets
    for var, df in dataframes.items():
        df.columns = days
        df.to_excel(writer, sheet_name=var)
    
    # Add beta sheet
    beta_df.to_excel(writer, sheet_name='beta')

    # Units sheet (mapping for quick reference)
    names_for_units = list(variables_needed) + OUTPUT_OPTIM_SCALAR
    units_rows = [{'name': n, 'unit': units_map.get(n, '')} for n in names_for_units]
    units_df = pd.DataFrame(units_rows, columns=['name', 'unit'])
    units_df.to_excel(writer, sheet_name='Units', index=False)

print("Optimization output processing complete.")
