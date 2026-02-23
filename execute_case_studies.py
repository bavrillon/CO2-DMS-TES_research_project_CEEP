"""
This script is the script to be executed to perform the thermodynamic 
settings computations and the optimization for a given case study. 
"""

from CONSTANTS import *
from shutil import copytree, copy
import subprocess
from compute_all_settings import compute_all_settings_M1_cycle, compute_all_settings_M2_cycle, aggregate_all_settings_M2_cycle
from optim_tools.settings_fitting_DAT import complete_final_dat_file


def setup_optim(case_name, dico_force_alpha_max, mono_T_TES=True, compute_M1_settings=False, plot_pinch=False, plot_COP_vs_alpha=False):
    """Set up the optimization for a given case study by computing the thermodynamic settings for M1 and M2 cycles,
    and by completing the .dat file with the computed settings and the external parameters"""
    print(f"############ Creating directories for case '{case_name}' ############")
    parent_dir = os.path.dirname(__file__)
    case_folder = os.path.join(parent_dir,"case_studies", case_name)
    os.makedirs(case_folder, exist_ok=True)

    thermo_folder = os.path.join(case_folder, "thermo_optim_inputs")
    plots_folder = os.path.join(case_folder, "plots")
    m2_db_saving_dir = os.path.join(thermo_folder, "db_thermo_settings_M2")
    os.makedirs(thermo_folder, exist_ok=True)
    os.makedirs(plots_folder, exist_ok=True)
    os.makedirs(m2_db_saving_dir, exist_ok=True)

    m1_saving_path = os.path.join(thermo_folder, "thermo_settings_M1.csv")
    if compute_M1_settings:
        if plot_pinch:
            m1_pinch_air_co2_saving_path = os.path.join(thermo_folder, "pinch_air_co2_M1")
        else:
            m1_pinch_air_co2_saving_path = None
        compute_all_settings_M1_cycle(final_saving_path=m1_saving_path, mono_T_TES=mono_T_TES, 
                                        pinch_air_co2_saving_path=m1_pinch_air_co2_saving_path)
    else:
        copy(M1_SETTINGS_FILE_PATH, m1_saving_path)
    print(f"############ M1 thermodynamic settings computation completed ############")

    m2_saving_path = os.path.join(thermo_folder, "thermo_settings_M2.csv")
    if plot_pinch:
        m2_pinch_air_co2_saving_path = os.path.join(thermo_folder, "pinch_air_co2_M2")
        m2_pinch_air_prop_saving_path = os.path.join(thermo_folder, "pinch_air_prop_M2")
    else:
        m2_pinch_air_co2_saving_path = None
        m2_pinch_air_prop_saving_path = None
    if plot_COP_vs_alpha:
        cop_vs_alpha_saving_dir = os.path.join(plots_folder, "COP_vs_alpha")
    else:
        cop_vs_alpha_saving_dir = None
    compute_all_settings_M2_cycle(M1_settings_path=m1_saving_path, files_saving_dir=m2_db_saving_dir, aggregate_final_saving_path=m2_saving_path, 
                                  dico_force_alpha_max=dico_force_alpha_max, mono_T_TES=mono_T_TES, use_Ph_opt_correlation=True,
                                  is_alpha_capped=True, COP_vs_alpha_saving_dir=cop_vs_alpha_saving_dir,
                                  pinch_air_co2_saving_dir=m2_pinch_air_co2_saving_path, 
                                  pinch_air_prop_saving_dir=m2_pinch_air_prop_saving_path)
    print(f"############ M2 thermodynamic settings computation completed ############")

    # aggregate_all_settings_M2_cycle(m2_saving_path, m2_db_saving_dir)
    optim_folder = copytree("./optim_tools/solver_CPLEX", os.path.join(case_folder, "optim_solver"))
    dat_file = os.path.join(optim_folder, "system_data.dat")
    complete_final_dat_file(dat_file, m1_saving_path, m2_saving_path)
    print(f"############ Optimization setup completed (M1 and M2) ############")

def compute_optim(case_name):
    """Run the optimization for a given case study and perform 
    the post-processing of the results (extraction of the solution and plotting)"""
    
    parent_dir = os.path.dirname(__file__)
    case_folder = os.path.join(parent_dir,"case_studies", case_name)
    optim_runner = os.path.join(case_folder, "optim_solver", "optim_runner.py")
    m1_saving_path = os.path.join(case_folder, "thermo_optim_inputs", "thermo_settings_M1.csv")
    m2_saving_path = os.path.join(case_folder, "thermo_optim_inputs", "thermo_settings_M2.csv")

    print(f"############ Starting linear optimization computation for case '{case_name}' ############")
    subprocess.run([VENV_CPLEX_PATH, optim_runner], check=True)
    print(f"############ Linear optimization completed ############")

    # Plots
    solution_extractor = os.path.join(case_folder, "optim_solver", "optim_outputs_processing", "solution_extractor.py")
    solution_plots = os.path.join(case_folder, "optim_solver", "optim_outputs_processing", "solution_plots.py")
    print(f"############ Extraction of the solution ############")
    os.system(f'python "{solution_extractor}"')
    print(f"############ Plotting of the solution ############")
    os.system(f'python "{solution_plots}" "{m1_saving_path}" "{m2_saving_path}"')
    print(f"############ Solution extraction and plotting completed for case '{case_name}' ############")

##################### EXECUTION ###########################
CASE_NAME = "mono4_45"
MONO_T_TES = True
COMPUTE_M1_SETTINGS = True
DICO_FORCED_ALPHA_MAX_STEPS = {
    "Low": [],
    "Medium": [],
    "High": [],
    "Worst_day": []
    }

setup_optim(CASE_NAME, DICO_FORCED_ALPHA_MAX_STEPS, mono_T_TES=MONO_T_TES, compute_M1_settings=COMPUTE_M1_SETTINGS)
compute_optim(CASE_NAME)



