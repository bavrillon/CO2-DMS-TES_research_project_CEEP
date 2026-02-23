"""This module contains functions for computing optimal settings for M1 and M2 cycles, for all day types and hours."""

import pandas as pd
import glob
from cycles import *
from CONSTANTS import *
from pinch_study.compute_pinch_air import get_T_gc_out_min_subcritical
from opti_Ph import optimize_Ph_supercritical_std_cycle, optimize_Ph_supercritical_cycle_with_DMS, get_interpolation_P_h_opt_1_vs_Tamb
from opti_alpha import get_alpha_opt_subcritical, get_alpha_opt_supercritical
from TES_settings import compute_beta_max, compute_COP_DMS_TES

def compute_all_settings_M1_cycle(final_saving_path, mono_T_TES: bool = True,
                                  pinch_air_co2_saving_path=None) -> pd.DataFrame:
    """Compute optimal settings when there is no DMS (M1) for all day types and hours.
    mono_T_TES: if True, use the same TES temperatures for all day types."""
    df_t = pd.read_csv(T_FILE, index_col=0)

    multi_cols = pd.MultiIndex.from_product([DAY_TYPES, SETTINGS_M1])
    df_params = pd.DataFrame(index=df_t.index, columns=multi_cols, dtype=float)

    for day_type in DAY_TYPES:
        df_params[(day_type, "T_amb")] = df_t[day_type].values + 273.15 # K
        for hour in range(24):
            T_amb = df_params.loc[hour, (day_type, "T_amb")]

            if pinch_air_co2_saving_path is not None:
                file_name = os.path.join(pinch_air_co2_saving_path, f"pinch_air_co2_M1_{day_type}_{hour:02d}h.png") 
            else:
                file_name = None
            
            # Compute optimal settings for standard cycle
            if T_amb <= T_AMB_MAX_SUBCRITICAL:
                T_gc_out = get_T_gc_out_min_subcritical(T_amb, max_iter=50, required_pinch=PINCH_AIR)[0]
                P_h = prp.PropsSI('P', 'T', T_gc_out, 'Q', 0.5, "CarbonDioxide") 
                sub_cycle = StandardCycle(fluid="CarbonDioxide",
                                         T_ev=T_EV,
                                         T_gc_out=T_gc_out,
                                         T_amb_air=T_amb)
                COP_CO2_M1 = sub_cycle.get_COP()
                delta_h_CO2 = sub_cycle.delta_h_ev / 1000  # in kJ/kg
                if file_name is not None:
                    pinch = sub_cycle.get_pinch_air(show=False, saving_path=file_name)

            else:
                T_gc_out = T_amb + PINCH_AIR
                P_h, COP_CO2_M1 = optimize_Ph_supercritical_std_cycle(T_EV, T_gc_out)
                sup_cycle = StandardCycle(fluid="CarbonDioxide",
                                         T_ev=T_EV,
                                         P_h=P_h,
                                         T_gc_out=T_gc_out,
                                         T_amb_air=T_amb)
                sup_cycle.compute_cycle()
                delta_h_CO2 = sup_cycle.delta_h_ev / 1000  # in kJ/kg
                if file_name is not None:
                    pinch = sup_cycle.get_pinch_air(show=False, saving_path=file_name)
            
            if mono_T_TES:
                day_type_name = None
            else:
                day_type_name = day_type
            beta_1_max = compute_beta_max(T_gc_out, P_h, delta_h_CO2, day_type=day_type_name)
            
            # Compute COP_DMS_TES for eventual charging the TES
            COP_DMS_TES = compute_COP_DMS_TES(T_amb, day_type=day_type_name)
            
            df_params.loc[hour, (day_type, 'P_h_1')] = P_h
            df_params.loc[hour, (day_type, 'T_gc_out')] = T_gc_out
            df_params.loc[hour, (day_type, 'COP_CO2_1')] = COP_CO2_M1
            df_params.loc[hour, (day_type, 'delta_h_CO2_1')] = delta_h_CO2
            df_params.loc[hour, (day_type, 'beta_1_max')] = beta_1_max
            df_params.loc[hour, (day_type, 'COP_DMS_TES')] = COP_DMS_TES
            print(f"[Computed settings for: {day_type} - {hour} h]")
    
    df_params.to_csv(final_saving_path)
    return df_params

def compute_settings_M2_cycle(day_type, hour, M1_settings_path, mono_T_TES: bool = True, Ph_opt_correlation=None, 
                              force_alpha_max=False, is_alpha_capped=True, COP_vs_alpha_saving_dir=None, 
                              pinch_air_co2_saving_dir=None, pinch_air_prop_saving_dir=None) -> dict:
    """Compute optimal settings for one subcooled cycle.
    force_alpha_max: if True, use alpha = ALPHA_CAPPED_MAX for all computations (for avoiding useless optimization)
    Ph_opt_correlation: if not None, a fonction which provides P_h_opt for a given T_amb, based on 
                        an interpolation of M1_optim_settings. Relevant since Ph_opt does not vary with alpha.
    mono_T_TES: if True, use the same TES temperatures for all day types.
    Return a dictionary with optimal settings."""

    # Only used to get T_amb and T_gc_out 
    df_settings_M1 = pd.read_csv(M1_settings_path, index_col=0, header=[0,1])

    T_amb = df_settings_M1.loc[hour, (day_type, 'T_amb')]
    T_gc_out = df_settings_M1.loc[hour, (day_type, 'T_gc_out')]

    if pinch_air_co2_saving_dir is not None:
        co2_file_name = os.path.join(pinch_air_co2_saving_dir, f"pinch_air_co2_M2_{day_type}_{hour:02d}h.png")
    else:
        co2_file_name = None

    if pinch_air_prop_saving_dir is not None:
        prop_file_name = os.path.join(pinch_air_prop_saving_dir, f"pinch_air_prop_M2_{day_type}_{hour:02d}h.png")
    else:
        prop_file_name = None

    if T_amb <= T_AMB_MAX_SUBCRITICAL:
        P_h = df_settings_M1.loc[hour, (day_type, 'P_h_1')]     # Subcritical cycle: P_h = P_sat(T_gc_out)
        if force_alpha_max:
            alpha = ALPHA_CAPPED_MAX
        else:
            alpha = get_alpha_opt_subcritical(T_EV, T_gc_out, T_amb, P_h, is_alpha_capped=is_alpha_capped, save_path=COP_vs_alpha_saving_dir)
    else:
        if force_alpha_max:
            alpha = ALPHA_CAPPED_MAX
        else:
            alpha = get_alpha_opt_supercritical(T_EV, T_gc_out, T_amb, Ph_opt_correlation=Ph_opt_correlation,
                                                is_alpha_capped=is_alpha_capped, save_path=COP_vs_alpha_saving_dir)
        if Ph_opt_correlation is not None:
            P_h = Ph_opt_correlation(T_amb)
        else:            
            P_h = optimize_Ph_supercritical_cycle_with_DMS(T_EV, T_gc_out, T_amb, alpha=alpha)[0]

    M2_cycle = ComplexSystem(fluid="CarbonDioxide",
                                    T_ev=T_EV,
                                    P_h=P_h,
                                    T_gc_out=T_gc_out,
                                    T_amb_air=T_amb,
                                    alpha=alpha)
    COP_star_M2 = M2_cycle.get_COP()
    COP_DMS_CO2 = M2_cycle.get_DMS_COP()
    COP_CO2_M2 = M2_cycle.get_CO2_COP()
    delta_h_CO2 = M2_cycle.delta_h_ev_without_sc / 1000  # in kJ/kg

    if co2_file_name is not None:
        pinch_CO2 = M2_cycle.get_pinch_air(show=False, saving_path=co2_file_name)
    if prop_file_name is not None:
        pinch_prop = M2_cycle.get_pinch_air_DMS(show=False, saving_path=prop_file_name)

    if mono_T_TES:
        day_type_name = None
    else:
        day_type_name = day_type
    beta_2_max = compute_beta_max(M2_cycle.T_DMS_out, P_h, delta_h_CO2, day_type=day_type_name)

    settings = {
        'T_amb': T_amb,
        'T_gc_out': T_gc_out,
        'P_h_2': P_h,
        'alpha_2': alpha,
        'delta_h_CO2_2': delta_h_CO2,
        'beta_2_max': beta_2_max,
        'COP_star_2': COP_star_M2,
        'COP_CO2_2': COP_CO2_M2,
        'COP_DMS_CO2': COP_DMS_CO2}
    
    return settings

def compute_list_settings_M2_cycle(day_types, hours, M1_settings_path, files_saving_dir, mono_T_TES: bool = True, 
                                   use_Ph_opt_correlation=False, force_alpha_max=False, 
                                   is_alpha_capped=True,  COP_vs_alpha_saving_dir=None,
                                   pinch_air_co2_saving_dir=None, pinch_air_prop_saving_dir=None):
    """force_alpha_max: if True, use alpha = ALPHA_MAX for all computations (for avoiding useless optimization,
    when it is known that the maximum degree of subcooling is required).
    use_Ph_opt_correlation: if True, use the correlation P_h_opt_1 = f(T_amb) to get P_h_opt for supercritical cycles.
    mono_T_TES: if True, use the same TES temperatures for all day types.
    The correlation is obtained as an interpolation of M1_optim_settings.csv for supercritical cycles, 
    which is relevant since Ph_opt does not vary with alpha."""
    if use_Ph_opt_correlation:
        interpolation_Ph_opt_1_vs_Tamb = get_interpolation_P_h_opt_1_vs_Tamb(M1_csv_file_path=M1_settings_path)
        print("[P_h_opt_1 = f(T_amb) correlation sucessfully obtained from M1 settings]")
    else: 
        interpolation_Ph_opt_1_vs_Tamb = None
    for day_type in day_types:
        for hour in hours:
            settings_T_amb = compute_settings_M2_cycle(day_type, hour, mono_T_TES=mono_T_TES,
                                                       M1_settings_path=M1_settings_path,
                                                       Ph_opt_correlation=interpolation_Ph_opt_1_vs_Tamb, 
                                                       force_alpha_max=force_alpha_max, is_alpha_capped=is_alpha_capped, 
                                                       COP_vs_alpha_saving_dir=COP_vs_alpha_saving_dir, 
                                                       pinch_air_prop_saving_dir=pinch_air_prop_saving_dir,
                                                       pinch_air_co2_saving_dir=pinch_air_co2_saving_dir)
            df_settings_T_amb = pd.DataFrame([settings_T_amb])
            filename = f"settings-{day_type}-{hour:02d}.csv"
            filepath = os.path.join(files_saving_dir, filename)
            df_settings_T_amb.to_csv(filepath, index=False)
            print(f"[Computed M2 settings for: {day_type} - {hour} h]")

def compute_all_settings_M2_cycle(M1_settings_path, files_saving_dir, dico_force_alpha_max, mono_T_TES: bool = True, 
                                   use_Ph_opt_correlation=False, is_alpha_capped=True, aggregate_final_saving_path=None,
                                   COP_vs_alpha_saving_dir=None, pinch_air_co2_saving_dir=None, pinch_air_prop_saving_dir=None):
    if use_Ph_opt_correlation:
        interpolation_Ph_opt_1_vs_Tamb = get_interpolation_P_h_opt_1_vs_Tamb(M1_csv_file_path=M1_settings_path)
        print("[P_h_opt_1 = f(T_amb) correlation sucessfully obtained from M1 settings]")
    else: 
        interpolation_Ph_opt_1_vs_Tamb = None
    for day_type in DAY_TYPES:
        alpha_forced_hours = dico_force_alpha_max[day_type]
        for hour in range(24):
            if hour in alpha_forced_hours:
                is_alpha_max_forced = True
            else:
                is_alpha_max_forced= False
            settings_T_amb = compute_settings_M2_cycle(day_type, hour, mono_T_TES=mono_T_TES,
                                                       M1_settings_path=M1_settings_path,
                                                       Ph_opt_correlation=interpolation_Ph_opt_1_vs_Tamb, 
                                                       force_alpha_max=is_alpha_max_forced, is_alpha_capped=is_alpha_capped, 
                                                       COP_vs_alpha_saving_dir=COP_vs_alpha_saving_dir, 
                                                       pinch_air_prop_saving_dir=pinch_air_prop_saving_dir,
                                                       pinch_air_co2_saving_dir=pinch_air_co2_saving_dir)
            df_settings_T_amb = pd.DataFrame([settings_T_amb])
            filename = f"settings-{day_type}-{hour:02d}.csv"
            filepath = os.path.join(files_saving_dir, filename)
            df_settings_T_amb.to_csv(filepath, index=False)
            print(f"[Computed M2 settings for: {day_type} - {hour} h]")
    if aggregate_final_saving_path is not None:
        aggregate_all_settings_M2_cycle(aggregate_final_saving_path, files_saving_dir)

def aggregate_all_settings_M2_cycle(final_saving_path, files_to_aggregate_dir):
    """Aggregate all M2 settings files into a single csv file."""
    df_t = pd.read_csv(T_FILE, index_col=0)
    multi_cols = pd.MultiIndex.from_product([DAY_TYPES, SETTINGS_M2])
    df_combined = pd.DataFrame(index=df_t.index, columns=multi_cols)
    
    # Find all CSV files
    csv_files = glob.glob(os.path.join(files_to_aggregate_dir, "settings-*.csv"))

    for filepath in csv_files:

        # Extract day_type and hour from filename
        filename = os.path.basename(filepath)

        # Format: settings-{day_type}-{hour}.csv
        parts = filename.replace('settings-', '').replace('.csv', '').split('-')

        if len(parts) >= 2:
            day_type = parts[0]  # "Low", "Medium", ...
            hour_str = parts[1]  # "00", "01", ..., "23"
            hour = int(hour_str)
            df_temp = pd.read_csv(filepath)

            for param in SETTINGS_M2:
                df_combined.loc[hour, (day_type, param)] = df_temp[param].iloc[0]
    
    df_combined.to_csv(final_saving_path)
    print(f"[Aggregated M2 settings saved to: {final_saving_path}]")
    return df_combined

