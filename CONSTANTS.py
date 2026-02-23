import os

T_EV = 273.15 - 10  # K
P_CRIT = 7.3773e6  # Pa
T_CRIT = 304.118  # K
PINCH_AIR = 5  # K
PINCH_TES = 3 # K
T_AMB_MAX_SUBCRITICAL = 273.15 + 25.398 # K
DELTA_T_W = 5  # K
T_TES = {"Mono": {"hot": -3, "cold": -8}, 
        "Low": {"hot": -3, "cold": -8}, "Medium": {"hot": -3, "cold": -8},
        "High": {"hot": -3, "cold": -8}, "Worst_day": {"hot": -3, "cold": -8}}
 
COP_VS_ALPHA_REGRESSION_DEGREE = 6
ALPHA_STEP = 0.02
ALPHA_CAPPED_MAX = 0.45
ALPHA_UNCAPPED_MAX = 1.0

# Index, variables & parameters
DAY_TYPES = ["Low", "Medium", "High", "Worst_day"]
SETTINGS_M1 = ['T_amb', 'T_gc_out', 'P_h_1', 'COP_CO2_1', 'delta_h_CO2_1', 'beta_1_max', 'COP_DMS_TES']
SETTINGS_M2 = ['T_amb', 'T_gc_out', 'P_h_2', 'alpha_2', 'delta_h_CO2_2', 'beta_2_max', 'COP_star_2', 'COP_CO2_2', 'COP_DMS_CO2']
SETTINGS_M1_IN_DAT_FILE = ['delta_h_CO2_1', 'beta_1_max', 'COP_CO2_1', 'COP_DMS_TES']
SETTINGS_M2_IN_DAT_FILE = ['delta_h_CO2_2', 'beta_2_max', 'alpha_2', 'COP_CO2_2', 'COP_DMS_CO2']
OUTPUT_OPTIM_VARIABLES = ['b_mode', 'Q_dot_CO2', 'Q_dot_DMS_CO2', 'Q_dot_TES_CO2', 'Q_dot_DMS_TES',
                         'M_dot_CO2', 'M_dot_TES_charge', 'M_dot_TES_discharge', 'V_TES_hot', 'V_TES_cold']
OUTPUT_OPTIM_SCALAR = ['z_comp_CO2', 'z_comp_DMS', 'v_TES', 'C_capex', 'C_opex', 'C_npv','C_total', 'w_tot']
EXTERNAL_PARAMETERS = ['C_elec', 'Q_dot_load']
DAT_PARAMETERS = EXTERNAL_PARAMETERS + ['beta_1_max', 'COP_CO2_1', 'COP_DMS_TES', 'alpha_2', 'beta_2_max', 'COP_CO2_2', 'COP_DMS_CO2']
OUTPUT_VARIABLES = ['b_mode', 'Q_dot_CO2', 'Q_dot_DMS_CO2', 'Q_dot_TES_CO2', 'Q_dot_DMS_TES','W_dot_comp_CO2',
             'W_dot_comp_DMS', 'M_dot_CO2', 'M_dot_TES_charge', 'M_dot_TES_discharge', 'V_TES_hot', 'V_TES_cold','M_dot_CO2']
DEDUCED_RATIOS = ['alpha', 'beta']
VARIABLES = OUTPUT_VARIABLES + DEDUCED_RATIOS
COMPUTED_PARAMETERS = ['P_h', 'beta_max', 'COP_CO2', 'COP_DMS','COP_star']  # Obtained according to the strategy adopted by the optimization ('b_mode')
ALL_PARAMETERS = ['T_amb', 'T_gc_out'] + COMPUTED_PARAMETERS + DAT_PARAMETERS + VARIABLES

# Paths
T_FILE = os.path.join(os.path.dirname(__file__), "external_time_series", "outputs_external_time_series", "hourly_avg_T_clustered.csv")
M1_SETTINGS_FILE_PATH = os.path.join(os.path.dirname(__file__), "data", "thermo_settings_M1.csv")
EXPLICATIVE_PLOTS_SAVING_DIR = os.path.join(os.path.dirname(__file__), 'explicative_plots', 'plots')
DATA_3D_SAVING_DIR = os.path.join(os.path.dirname(__file__), "explicative_plots", "data_plots_3D")
CASE_STUDIES_SAVING_DIR = os.path.join(os.path.dirname(__file__), 'case_studies')
VENV_BASE_PATH = os.path.join(r"C:\miniconda", "python.exe")
VENV_CPLEX_PATH = os.path.join(r"C:\miniconda", "envs", "optim_cplex", "python.exe")




