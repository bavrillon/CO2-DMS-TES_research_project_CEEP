"""
This code implements different computations linked to the TES limits and design.
"""
from CONSTANTS import *
from cycles import *
import pandas as pd

################################### BETA_MAX - PHYSICAL LIMITS OF THE TES SUBCOOLING ###################################

def compute_beta_max(T_TES_in: float, P_h: float, delta_h_CO2: float, day_type: str =None, gas_pinch_TES: float = PINCH_TES) -> float:
    """Compute the maximal beta (dh_DMS/dh_CO2) that can be achieved considering the TES cold temperature level.
    day_type: "Low", "Medium", "High", "Worst_day", None → If None, the storage temperatures remains fixed. 
    Otherwise, they are adapted to the day type."""

    if day_type is None:
        day_type = "Mono" # momo-thermal storage
    hot_T_TES = 273.15 + T_TES[day_type]["hot"]
    cold_T_TES = 273.15 + T_TES[day_type]["cold"]

    if T_TES_in < (hot_T_TES + gas_pinch_TES):
        delta_h_TES_max = 0  # The case where CO2 warms up before cooling down is excluded
    else:
        T_TES_out = cold_T_TES + gas_pinch_TES
        h_TES_IN = get_fluid_property('H', 'T', T_TES_in, 'P', P_h, 'CarbonDioxide')
        h_TES_OUT = get_fluid_property('H', 'T', T_TES_out, 'P', P_h, 'CarbonDioxide')
        delta_h_TES_max = max(0, h_TES_IN - h_TES_OUT) / 1000  # in kJ/kg, The case where CO2 warms up is excluded
    beta_1_max = delta_h_TES_max / delta_h_CO2
    
    return beta_1_max

################################### COP_DMS_TES FOR CHARGING THE TEX ###################################

def compute_COP_DMS_TES(T_amb_air: float, day_type: str=None, fluid_DMS: str = 'n-Propane', delta_T_sh_DMS: float = 7,
                        gas_pinch_TES: float = 3, gas_pinch_DMS: float = 5, coefs_eta_comp_DMS=[0.3774,0.1405,0.0201,0.0008], mu_DMS: float=1/30) -> float:
    """
    Compute COP of the DMS cycle charging the TES.
    day_type: "Low", "Medium", "High", "Worst_day", None → If None, the storage temperatures remains fixed. 
                                                    Otherwise, they are adapted to the day type.
    """
    if day_type is None:
        day_type = "Mono" # momo-thermal storage
    T_TES_cold = 273.15 + T_TES[day_type]["cold"]
    T_TES_hot = 273.15 + T_TES[day_type]["hot"]
    
    F = fluid_DMS
    T_ev_DMS = min(T_TES_cold, T_TES_hot - delta_T_sh_DMS) - gas_pinch_TES
    P_ev_DMS = get_fluid_property('P', 'T', T_ev_DMS, 'Q', 0.5, F)

    # Compressor states
    if delta_T_sh_DMS > 0:
        T_comp_in = T_ev_DMS + delta_T_sh_DMS
        h_comp_in = get_fluid_property('H', 'P', P_ev_DMS, 'T', T_comp_in, F)
        s_comp_in = get_fluid_property('S', 'P', P_ev_DMS, 'T', T_comp_in, F)
    else:
        h_comp_in = get_fluid_property('H', 'P', P_ev_DMS, 'Q', 1, F)
        s_comp_in = get_fluid_property('S', 'P', P_ev_DMS, 'Q', 1, F)
        T_comp_in = T_ev_DMS

    def get_eta_comp_DMS(r: float) -> float:
        """Return compressor efficiency for a given pressure ratio r."""
        deg = len(coefs_eta_comp_DMS) - 1
        eta_comp_DMS = 0
        for i in range(deg+1):
            eta_comp_DMS += coefs_eta_comp_DMS[i] * r**i
        return eta_comp_DMS

    def get_P_cond_min_propane(N_nodes=30, max_iter=50, plot_T_profile=False) -> float:
        """Compute the minimum condensing pressure for the propane DMS cycle
        to achieve the required pinch with ambient air at T_amb."""

        F = fluid_DMS

        def evaluate_pinch(P_cond, plot_T_profile_i=False):
            # Propane states
            r_DMS = P_cond / P_ev_DMS
            eta_comp_DMS = get_eta_comp_DMS(r_DMS)
            h_comp_out_isentropic = get_fluid_property('H', 'P', P_cond, 'S', s_comp_in, F)
            h_comp_out = h_comp_in + (h_comp_out_isentropic - h_comp_in) / eta_comp_DMS
            T_comp_out = get_fluid_property('T', 'P', P_cond, 'H', h_comp_out, F)
            h_cond_out = get_fluid_property('H', 'P', P_cond, 'Q', 0, F)  # No subcooling for DMS
            h_cond_nodes = np.linspace(h_comp_out, h_cond_out, N_nodes)
            T_cond_nodes = [T_comp_out]
            for i in range(1, N_nodes):
                T_node = get_fluid_property('T', 'P', P_cond, 'H', h_cond_nodes[i], F)
                T_cond_nodes.append(T_node)
            T_cond_nodes = np.array(T_cond_nodes)
            
            # Air states
            T_air_cond = np.ones(N_nodes) * T_amb_air 
            cp_air = get_fluid_property('Cpmass', 'P', 101325, 'T', T_amb_air, 'Air')  # J/kg/K, assumed constant
            h_out_fluid = h_cond_nodes[-1]
            for i in range(1, N_nodes):
                delta_h_fluid = h_cond_nodes[N_nodes - 1 - i] - h_out_fluid  # >0
                T_air_cond[i] +=  delta_h_fluid * mu_DMS / cp_air
            
            # Find the node where pinch occurs
            pinch_node = np.argmin(T_cond_nodes - T_air_cond[::-1])
            pinch_value = T_cond_nodes[pinch_node] - T_air_cond[::-1][pinch_node]

            return pinch_value
        
        ### Using a root-finding method from scipy
        P_low = get_fluid_property('P', 'T', T_amb_air + gas_pinch_DMS, 'Q', 0.5, fluid_DMS)
        P_high = 42.2e5 # P_crit_propane
        P_mid = bisect(lambda P: evaluate_pinch(P) - gas_pinch_DMS, P_low, P_high, xtol=600, maxiter=max_iter)

        if plot_T_profile:
            pinch_mid = evaluate_pinch(P_mid, plot_T_profile_i=True)
        else:
            pinch_mid = evaluate_pinch(P_mid)
        
        return P_mid, pinch_mid


    P_cond_DMS = get_P_cond_min_propane()[0]
    T_cond_DMS = get_fluid_property('T', 'P', P_cond_DMS, 'Q', 0.5, F)
    r_DMS = P_cond_DMS / P_ev_DMS
    eta_comp_DMS = get_eta_comp_DMS(r_DMS)
    h_comp_out_isentropic = get_fluid_property('H', 'P', P_cond_DMS, 'S', s_comp_in, F)
    h_comp_out = h_comp_in + (h_comp_out_isentropic - h_comp_in) / eta_comp_DMS

    # Condenser states
    h_cond_out = get_fluid_property('H', 'T', T_cond_DMS, 'Q', 0, F)       # No subcooling for DMS
    
    # Evaporator states
    h_ev_in = h_cond_out # isenthalpic expansion

    COP_DMS = (h_comp_in - h_ev_in) / (h_comp_out - h_comp_in)
    return COP_DMS

# ################################### DESIGNING THE TES ###################################
# # Choosing storage temperature levels T_TES_h (hot) and T_TES_c (cold), considering that the TES
# # can provid subcooling to the CO2 only when T_TES_h < T_TES_in - GAS_PINCH. The other condition 
# # T_TES_c < T_TES_out - GAS_PINCH can also be considered, for a better use of the TES, but is not compulsory
# # to ensure that a tiny part of subcooling is provided to the CO2.

def load_settings(path: str) -> pd.DataFrame:
    """Load the optimization settings produced."""
    if not os.path.exists(path):
        raise FileNotFoundError(f"Settings file not found: {path}")
    return pd.read_csv(path, header=[0, 1], index_col=0)

def plot_T_TES_in(mode, settings_path) -> pd.DataFrame:
    """Compute and plot the T_TES_in of CO2 for each day type and hour.
    It is desirable to have T_TES_in > T_TES_H + PINCH_TES, 
    to ensure that the TES can provide subcooling to the CO2 along all the HEX.
        mode: "M1" or "M2"
       settings_path: path to the settings csv file
    """
    if not os.path.exists(settings_path):
        raise FileNotFoundError(f"Settings file not found: {settings_path}")
    settings = pd.read_csv(settings_path, header=[0, 1], index_col=0)

    T_TES_in_df = pd.DataFrame(index=settings.index, columns=DAY_TYPES, dtype=float)

    for label in DAY_TYPES:
        Tamb_series = settings[(label, "T_amb")]
        Tgcout_series = settings[(label, "T_gc_out")]
        if mode == "M1":
            P_series = settings[(label, "P_h_1")]
            alpha_series = settings[(label, "P_h_1")] * 0  # alpha = 0 in M1
        elif mode == "M2":
            P_series = settings[(label, "P_h_2")]
            alpha_series = settings[(label, "alpha")]

        for hour in T_TES_in_df.index:
            alpha = float(alpha_series.loc[hour])
            T_amb = float(Tamb_series.loc[hour])
            T_gc_out=float(Tgcout_series.loc[hour])
            P_h=float(P_series.loc[hour])

            cycle = ComplexSystem(fluid="CarbonDioxide",
                                      T_ev=T_EV,
                                      P_h=P_h,
                                      T_gc_out=T_gc_out,
                                      T_amb_air=T_amb,
                                      alpha=alpha)
            cycle.compute_cycle()
            T_TES_in = cycle.T_TES_in
            T_TES_in_df.at[hour, label] = T_TES_in

    plt.figure(figsize=(12, 6))
    colors = ['#00BFFF', '#FFD700', '#FF7F50', '#8B0000']
    for idx, label in enumerate(DAY_TYPES):
        plt.plot(T_TES_in_df.index, T_TES_in_df[label] - 273.15, marker='o', label=label, color=colors[idx])
    plt.xlabel('Hour')
    plt.ylabel('Temperature (°C)')
    plt.title('HEX with TES inlet temperature of CO2 over hours - ' + mode)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()
    plt.show()

def plot_COP_DMS_TES_vs_Tamb_and_T_TES_hot(T_TES_hot_range, T_amb_range: list=[2,42], fluid_DMS: str = 'n-Propane', delta_T_sh_DMS: float = 7,
                             gas_pinch_TES: float = 3, gas_pinch_DMS: float = 5, coefs_eta_comp_DMS=[0.3774,0.1405,0.0201,0.0008], mu_DMS: float=1/30):
    """Plot COP of the DMS cycle charging the TES vs T_amb for different hot temperature of the storage (T_TES_hot),
    assuming that T_TES_cold = T_TES_hot - DELTA_T_W. Results = one curve per T_TES_hot value."""
    
    def compute_COP_custom_TES(T_amb_air: float, T_TES_cold: float, T_TES_hot: float) -> float:
        """Compute COP for custom TES temperatures."""
        F = fluid_DMS
        T_TES_cold_K = 273.15 + T_TES_cold
        T_TES_hot_K = 273.15 + T_TES_hot
        
        T_ev_DMS = min(T_TES_cold_K, T_TES_hot_K - delta_T_sh_DMS) - gas_pinch_TES
        P_ev_DMS = get_fluid_property('P', 'T', T_ev_DMS, 'Q', 0.5, F)

        # Compressor states
        if delta_T_sh_DMS > 0:
            T_comp_in = T_ev_DMS + delta_T_sh_DMS
            h_comp_in = get_fluid_property('H', 'P', P_ev_DMS, 'T', T_comp_in, F)
            s_comp_in = get_fluid_property('S', 'P', P_ev_DMS, 'T', T_comp_in, F)
        else:
            h_comp_in = get_fluid_property('H', 'P', P_ev_DMS, 'Q', 1, F)
            s_comp_in = get_fluid_property('S', 'P', P_ev_DMS, 'Q', 1, F)
            T_comp_in = T_ev_DMS

        def get_eta_comp_DMS(r: float) -> float:
            """Return compressor efficiency for a given pressure ratio r."""
            deg = len(coefs_eta_comp_DMS) - 1
            eta_comp_DMS = 0
            for i in range(deg+1):
                eta_comp_DMS += coefs_eta_comp_DMS[i] * r**i
            return eta_comp_DMS

        def get_P_cond_min_propane(N_nodes=30, max_iter=50) -> float:
            """Compute the minimum condensing pressure for the propane DMS cycle."""
            def evaluate_pinch(P_cond):
                # Propane states
                r_DMS = P_cond / P_ev_DMS
                eta_comp_DMS = get_eta_comp_DMS(r_DMS)
                h_comp_out_isentropic = get_fluid_property('H', 'P', P_cond, 'S', s_comp_in, F)
                h_comp_out = h_comp_in + (h_comp_out_isentropic - h_comp_in) / eta_comp_DMS
                T_comp_out = get_fluid_property('T', 'P', P_cond, 'H', h_comp_out, F)
                h_cond_out = get_fluid_property('H', 'P', P_cond, 'Q', 0, F)  # No subcooling for DMS
                h_cond_nodes = np.linspace(h_comp_out, h_cond_out, N_nodes)
                T_cond_nodes = [T_comp_out]
                for i in range(1, N_nodes):
                    T_node = get_fluid_property('T', 'P', P_cond, 'H', h_cond_nodes[i], F)
                    T_cond_nodes.append(T_node)
                T_cond_nodes = np.array(T_cond_nodes)
                
                # Air states
                T_air_cond = np.ones(N_nodes) * T_amb_air 
                cp_air = get_fluid_property('Cpmass', 'P', 101325, 'T', T_amb_air, 'Air')  # J/kg/K, assumed constant
                h_out_fluid = h_cond_nodes[-1]
                for i in range(1, N_nodes):
                    delta_h_fluid = h_cond_nodes[N_nodes - 1 - i] - h_out_fluid  # >0
                    T_air_cond[i] +=  delta_h_fluid * mu_DMS / cp_air
                
                # Find the node where pinch occurs
                pinch_node = np.argmin(T_cond_nodes - T_air_cond[::-1])
                pinch_value = T_cond_nodes[pinch_node] - T_air_cond[::-1][pinch_node]

                return pinch_value
            
            ### Using a root-finding method from scipy
            P_low = get_fluid_property('P', 'T', T_amb_air + gas_pinch_DMS, 'Q', 0.5, fluid_DMS)
            P_high = 42.2e5 # P_crit_propane
            P_mid = bisect(lambda P: evaluate_pinch(P) - gas_pinch_DMS, P_low, P_high, xtol=600, maxiter=max_iter)
            
            return P_mid

        P_cond_DMS = get_P_cond_min_propane()
        T_cond_DMS = get_fluid_property('T', 'P', P_cond_DMS, 'Q', 0.5, F)
        r_DMS = P_cond_DMS / P_ev_DMS
        eta_comp_DMS = get_eta_comp_DMS(r_DMS)
        h_comp_out_isentropic = get_fluid_property('H', 'P', P_cond_DMS, 'S', s_comp_in, F)
        h_comp_out = h_comp_in + (h_comp_out_isentropic - h_comp_in) / eta_comp_DMS

        # Condenser states
        h_cond_out = get_fluid_property('H', 'T', T_cond_DMS, 'Q', 0, F)       # No subcooling for DMS
        
        # Evaporator states
        h_ev_in = h_cond_out # isenthalpic expansion

        COP_DMS = (h_comp_in - h_ev_in) / (h_comp_out - h_comp_in)
        return COP_DMS
    
    # Generate T_amb array
    T_amb_array = np.linspace(T_amb_range[0], T_amb_range[1], 50)
    
    # Plot setup
    plt.figure(figsize=(10, 6))
    colors = plt.cm.viridis(np.linspace(0, 0.9, len(T_TES_hot_range)))
    
    # Compute and plot COP for each T_TES_hot
    for idx, T_TES_hot in enumerate(T_TES_hot_range):
        T_TES_cold = T_TES_hot - DELTA_T_W
        COP_array = []
        
        for T_amb in T_amb_array:
            try:
                COP = compute_COP_custom_TES(T_amb + 273.15, T_TES_cold, T_TES_hot)
                COP_array.append(COP)
            except:
                COP_array.append(np.nan)
        
        plt.plot(T_amb_array, COP_array,  
                label=f'T_TES_hot = {T_TES_hot}°C', color=colors[idx], linewidth=2)
    
    plt.xlabel('Ambient temperature T_amb (°C)', fontsize=12)
    plt.ylabel('COP_DMS_TES', fontsize=12)
    plt.title('COP of the propane cycle charging TES vs T_amb', fontsize=14)
    plt.legend(loc='best')
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()

# plot_COP_DMS_TES_vs_Tamb_and_T_TES_hot(T_TES_hot_range=[7, 12, 17, 22], T_amb_range=[2, 42])