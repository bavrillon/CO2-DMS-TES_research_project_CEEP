
import matplotlib.pyplot as plt
import numpy as np
import CoolProp.CoolProp as prp
import os
import sys
import pandas as pd

gdparent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(gdparent_dir)
from CONSTANTS import *
DELTA_T_SH = 2 # Superheating in K
SAVING_PATH = os.path.join(os.path.dirname(__file__), 'plots')


def plot_isobarics_coolings_alpha(T_gc_out, alpha, P_cooling_range, T_ev=273.15-10, delta_T_sh=2, N_pts=80, saving=False):
    """Plot a CO2 P-h diagram with isobaric cooling and subcooling."""
    fig, ax = plt.subplots(figsize=(12, 8))
    
    F = "CarbonDioxide"
    P_crit = prp.PropsSI('PCRIT', F)
    P_ev = prp.PropsSI('P', 'T', T_ev, 'Q', 0.5, F)
    T_comp_in = T_ev + delta_T_sh
    h_comp_in = prp.PropsSI('H', 'P', P_ev, 'T', T_comp_in, F)
    s_comp_in = prp.PropsSI('S', 'P', P_ev, 'H', h_comp_in, F)
    P_range = np.linspace(20e5, 130e5, 400)

    # isotherm
    h_iso = np.array([prp.PropsSI('H', 'T', T_gc_out, 'P', p, F) for p in P_range])
    ax.plot(h_iso/1000, P_range/1e5, 'g-', alpha=0.7, linewidth=1.5, label=f'Isotherm T = {T_gc_out-273.15:.1f}°C')
    
    isotherm_label_done = False
    subcool_label_done = False
    cooling_label_done = False

    for P_h_i in P_cooling_range:
        r_i = P_h_i / P_ev
        eta_comp_i = 0.95 - 0.1 * r_i
        h_comp_out_isentropic_i = prp.PropsSI('H', 'P', P_h_i, 'S', s_comp_in, F)
        h_comp_out_i = h_comp_in + (h_comp_out_isentropic_i - h_comp_in) / eta_comp_i
        
        # Isobaric cooling from h_comp_out to the isotherm
        h_isotherm_i = prp.PropsSI('H', 'T', T_gc_out, 'P', P_h_i, F)
        h_cooling_range_i = np.linspace(h_comp_out_i, h_isotherm_i, N_pts)
        P_cooling_range_i = np.full_like(h_cooling_range_i, P_h_i)
        cooling_label = 'Cooling (air contact)' if not cooling_label_done else None
        ax.plot(h_cooling_range_i/1000, P_cooling_range_i/1e5, 'b-', linewidth=1.5, label=cooling_label)
        cooling_label_done = True
        
        # Subcooling phase (proportional to first cooling phase)
        delta_h_cooling_i = h_comp_out_i - h_isotherm_i 
        delta_h_subcooling_i = alpha * delta_h_cooling_i
        h_final_i = h_isotherm_i - delta_h_subcooling_i
        h_subcooling_range_i = np.linspace(h_isotherm_i, h_final_i, N_pts)
        P_subcooling_range_i = np.full_like(h_subcooling_range_i, P_h_i)
        subcool_label = 'DMS subcooling' if not subcool_label_done else None
        ax.plot(h_subcooling_range_i/1000, P_subcooling_range_i/1e5, 'r-', linewidth=1.5, label=subcool_label)
        subcool_label_done = True

        # Isotherm passing through subcooling end point, plotted once in legend
        T_subcooling_end_i = prp.PropsSI('T', 'P', P_h_i, 'H', h_final_i, F)
        h_iso_sub_i = np.array([prp.PropsSI('H', 'T', T_subcooling_end_i, 'P', p, F) for p in P_range])
        iso_label = 'Isotherms' if not isotherm_label_done else None
        ax.plot(h_iso_sub_i/1000, P_range/1e5, color='pink', alpha=0.7, linewidth=1.5, label=iso_label)
        isotherm_label_done = True
    
    # Saturation curves
    P_sat = np.linspace(20e5, P_crit, 300)
    h_l = np.array([prp.PropsSI('H', 'P', p, 'Q', 0, F) for p in P_sat])  # Liquid phase
    h_v = np.array([prp.PropsSI('H', 'P', p, 'Q', 1, F) for p in P_sat])  # Vapor phase
    ax.plot(h_l/1000, P_sat/1e5, 'm--', linewidth=1.5, label='Saturation curves')
    ax.plot(h_v/1000, P_sat/1e5, 'm--', linewidth=1.5)
    ax.set_ylim(20, 150)  # Set pressure scale from 20 to 150 bars  

     # Horizontal line for evaporation from saturation curve to compressor inlet
    P_ev = prp.PropsSI('P', 'T', T_ev, 'Q', 0.5, F)
    h_sat_mid = prp.PropsSI('H', 'P', P_ev, 'Q', 0.3, F)  # in of saturation zone
    h_evaporation = np.linspace(h_sat_mid, h_comp_in, 100)
    P_evaporation = np.full_like(h_evaporation, P_ev)
    ax.plot(h_evaporation/1000, P_evaporation/1e5, 'grey', linestyle='--', linewidth=1.5)

    # Dotted gray curve for compression
    P_comp_out_max = P_cooling_range[-1]
    P_comp_range = np.linspace(P_ev, P_comp_out_max, 50)
    h_comp_range = []
    for i in range(len(P_comp_range)):
        P_comp_i = P_comp_range[i]
        r_i = P_comp_i / P_ev
        eta_comp_i = 0.95 - 0.1 * r_i
        h_comp_i_isentropic = prp.PropsSI('H', 'P', P_comp_i, 'S', s_comp_in, F)
        h_comp_i = h_comp_in + (h_comp_i_isentropic - h_comp_in) / eta_comp_i
        h_comp_range.append(h_comp_i)
    h_comp_range = np.array(h_comp_range)
    ax.plot(h_comp_range/1000, P_comp_range/1e5, 'grey', linestyle='--', linewidth=1.5)
    
    ax.set_xlabel('Enthalpy (kJ/kg)')
    ax.set_ylabel('Pressure (bar)')
    ax.set_title(f'CO2 P-h diagram – isobaric cooling (alpha={alpha:.2f} & T_gas-cooler_out={T_gc_out-273.15:.1f}°C)')
    ax.grid(True)
    ax.legend()
    
    if saving:
        os.makedirs(SAVING_PATH, exist_ok=True)
        filename = f'CO2_Ph_diagram_alpha_{alpha:.2f}_Tgc_{T_gc_out-273.15:.1f}C.png'
        filepath = os.path.join(SAVING_PATH, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {filepath}")
    
    plt.show()

def plot_isobarics_coolings_SUB_DMS(T_gc_out, SUB_DMS, P_cooling_range, T_ev=273.15-10, delta_T_sh=2, N_pts=80, saving=False):
    """Plot a CO2 P-h diagram with isobaric cooling and subcooling defined by a temperature offset."""

    fig, ax = plt.subplots(figsize=(12, 8))

    F = "CarbonDioxide"
    P_crit = prp.PropsSI('PCRIT', F)
    P_ev = prp.PropsSI('P', 'T', T_ev, 'Q', 0.5, F)
    T_comp_in = T_ev + delta_T_sh
    h_comp_in = prp.PropsSI('H', 'P', P_ev, 'T', T_comp_in, F)
    s_comp_in = prp.PropsSI('S', 'P', P_ev, 'H', h_comp_in, F)
    P_range = np.linspace(20e5, 130e5, 400)

    # Reference isotherm at gas cooler outlet temperature
    h_iso_main = np.array([prp.PropsSI('H', 'T', T_gc_out, 'P', p, F) for p in P_range])
    ax.plot(h_iso_main/1000, P_range/1e5, 'g-', alpha=0.7, linewidth=1.5,
            label=f'Isotherm T = {T_gc_out-273.15:.1f}°C')

    # Isotherm corresponding to subcooling end temperature
    T_sub = T_gc_out - SUB_DMS
    h_iso_sub = np.array([prp.PropsSI('H', 'T', T_sub, 'P', p, F) for p in P_range])
    ax.plot(h_iso_sub/1000, P_range/1e5, color='pink', alpha=0.7, linewidth=1.5,
            label=f'Subcool end isotherm T = {T_sub-273.15:.1f}°C')

    cooling_label_done = False
    subcool_label_done = False

    for P_h_i in P_cooling_range:
        r_i = P_h_i / P_ev
        eta_comp_i = 0.95 - 0.1 * r_i
        h_comp_out_isentropic_i = prp.PropsSI('H', 'P', P_h_i, 'S', s_comp_in, F)
        h_comp_out_i = h_comp_in + (h_comp_out_isentropic_i - h_comp_in) / eta_comp_i

        # Isobaric cooling from h_comp_out to the main isotherm (unchanged)
        h_isotherm_i = prp.PropsSI('H', 'T', T_gc_out, 'P', P_h_i, F)
        h_cooling_range_i = np.linspace(h_comp_out_i, h_isotherm_i, N_pts)
        P_cooling_range_i = np.full_like(h_cooling_range_i, P_h_i)
        cooling_label = 'Cooling (air contact)' if not cooling_label_done else None
        ax.plot(h_cooling_range_i/1000, P_cooling_range_i/1e5, 'b-', linewidth=1.5, label=cooling_label)
        cooling_label_done = True

        # Subcooling: end point on T_gc_out - SUB_DMS isotherm at same pressure
        h_final_i = prp.PropsSI('H', 'T', T_sub, 'P', P_h_i, F)
        h_subcooling_range_i = np.linspace(h_isotherm_i, h_final_i, N_pts)
        P_subcooling_range_i = np.full_like(h_subcooling_range_i, P_h_i)
        subcool_label = 'DMS subcooling' if not subcool_label_done else None
        ax.plot(h_subcooling_range_i/1000, P_subcooling_range_i/1e5, 'r-', linewidth=1.5, label=subcool_label)
        subcool_label_done = True

    # Saturation curves
    P_sat = np.linspace(20e5, P_crit, 300)
    h_l = np.array([prp.PropsSI('H', 'P', p, 'Q', 0, F) for p in P_sat])
    h_v = np.array([prp.PropsSI('H', 'P', p, 'Q', 1, F) for p in P_sat])
    ax.plot(h_l/1000, P_sat/1e5, 'm--', linewidth=1.5, label='Saturation curves')
    ax.plot(h_v/1000, P_sat/1e5, 'm--', linewidth=1.5)
    ax.set_ylim(20, 150)

    # Horizontal line for evaporation from saturation curve to compressor inlet
    P_ev = prp.PropsSI('P', 'T', T_ev, 'Q', 0.5, F)
    h_sat_mid = prp.PropsSI('H', 'P', P_ev, 'Q', 0.3, F)
    h_evaporation = np.linspace(h_sat_mid, h_comp_in, 100)
    P_evaporation = np.full_like(h_evaporation, P_ev)
    ax.plot(h_evaporation/1000, P_evaporation/1e5, 'grey', linestyle='--', linewidth=1.5)

    # Dotted gray curve for compression
    P_comp_out_max = P_cooling_range[-1]
    P_comp_range = np.linspace(P_ev, P_comp_out_max, 50)
    h_comp_range = []
    for i in range(len(P_comp_range)):
        P_comp_i = P_comp_range[i]
        r_i = P_comp_i / P_ev
        eta_comp_i = 0.95 - 0.1 * r_i
        h_comp_i_isentropic = prp.PropsSI('H', 'P', P_comp_i, 'S', s_comp_in, F)
        h_comp_i = h_comp_in + (h_comp_i_isentropic - h_comp_in) / eta_comp_i
        h_comp_range.append(h_comp_i)
    h_comp_range = np.array(h_comp_range)
    ax.plot(h_comp_range/1000, P_comp_range/1e5, 'grey', linestyle='--', linewidth=1.5)

    ax.set_xlabel('Enthalpy (kJ/kg)')
    ax.set_ylabel('Pressure (bar)')
    ax.set_title(f'CO2 P-h diagram – isobaric cooling (SUB_DMS={SUB_DMS:.2f} K & T_gas-cooler_out={T_gc_out-273.15:.1f}°C)')
    ax.grid(True)
    ax.legend()
    
    if saving:
        os.makedirs(SAVING_PATH, exist_ok=True)
        filename = f'CO2_Ph_diagram_SUB_DMS_{SUB_DMS:.2f}K_Tgc_{T_gc_out-273.15:.1f}C.png'
        filepath = os.path.join(SAVING_PATH, filename)
        plt.savefig(filepath, dpi=300, bbox_inches='tight')
        print(f"Figure saved: {filepath}")
    
    plt.show()

P_COOLING_RANGE = np.linspace(90e5, 105e5, 5)
plot_isobarics_coolings_alpha(T_gc_out=35+273.15, alpha=0.2, P_cooling_range=P_COOLING_RANGE, saving=True)
plot_isobarics_coolings_SUB_DMS(T_gc_out=35+273.15, SUB_DMS=15, P_cooling_range=P_COOLING_RANGE, saving=True)