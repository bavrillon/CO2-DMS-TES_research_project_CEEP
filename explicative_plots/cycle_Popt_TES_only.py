"""
This code aims to compare the optimal high pressures (P_opt) obtained for a CO2 transcritical
standard cycle (without DMS) in case the fluid is subcooled by the TES with the P_opt obtained
when no subcooling is applied to the standard cycle without any TES.
The comparison is made using a subcooling ratio that can be physically achieved with the TES, 
given the temperature considered.
"""
import os
import sys
import numpy as np
import matplotlib.pyplot as plt

gdparent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(gdparent_dir)
from CONSTANTS import *
from opti_Ph import optimize_Ph_supercritical_std_cycle

T_AMB = np.linspace(T_AMB_MAX_SUBCRITICAL, 273.15 + 40, 30)  # K
T_EV = 273.15 - 10  # K

def get_P_h_opt(T_amb_list=T_AMB, sc_ratio=0):
    P_h_opt_dict = {}
    for T_amb in T_amb_list:
        T_gc_out = T_amb + PINCH_AIR   # Already proved for supercritical cycle (see compute_pinch_air.py)
        P_h_opt, _ = optimize_Ph_supercritical_std_cycle(T_EV, T_gc_out, sc_ratio=sc_ratio)
        P_h_opt_dict[T_amb] = P_h_opt
    print("Computed P_h_opt for sc_ratio =", sc_ratio)
    return P_h_opt_dict

def plot_P_h_opt_comparison(sc_ratio):
    """Plot reference vs TES-subcooled optimal high pressures on the same chart.
    sc_ratio: subcooling ratio induced by TES
    """
    data_ref = get_P_h_opt()  # Reference without subcooling
    data_sc = get_P_h_opt(sc_ratio=sc_ratio)  # With TES subcooling

    # Convert dicts to sorted arrays
    T_ref = np.array(sorted(data_ref.keys()))
    P_ref = np.array([data_ref[t] for t in T_ref])

    T_sc = np.array(sorted(data_sc.keys()))
    P_sc = np.array([data_sc[t] for t in T_sc])

    # Convert temperatures to Celsius for readability
    T_ref_C = T_ref - 273.15
    T_sc_C = T_sc - 273.15

    plt.figure(figsize=(10, 7))
    plt.plot(T_ref_C, P_ref, label='No subcooling (reference)', color='steelblue', linewidth=2)
    plt.plot(T_sc_C, P_sc, label=f'TES subcooling (sc_ratio={sc_ratio:.2f})', color='darkorange', linewidth=2, linestyle='--')

    plt.xlabel('Ambient air temperature T_amb (°C)', fontsize=12)
    plt.ylabel('Optimal high pressure P_h_opt (Pa)', fontsize=12)
    plt.title('Comparison of P_h_opt with and without TES subcooling, when no DMS is applied', fontsize=14, pad=12)
    plt.grid(True, alpha=0.3)
    plt.legend(loc='best', fontsize=11)
    plt.tight_layout()
    plt.show()

##############################################

SC_RATIO_TES = 0.45  # arbitrary, but <= 0.5 (see TES_max_degree_M1) to ensure such a subcooling can be achieved with TES
plot_P_h_opt_comparison(SC_RATIO_TES)


