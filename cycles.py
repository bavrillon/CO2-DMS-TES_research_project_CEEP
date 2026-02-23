
"""
Cycle model that can represent both subcritical or transcritical cycles. The class 
encapsulates the cycle inputs and provides a method to compute cycle states, COP 
and the condenser-air pinch residual used for matching a given minimum approach temperature.
"""
import os
import matplotlib.pyplot as plt
import numpy as np
import CoolProp.CoolProp as prp
from scipy.optimize import bisect

plt.close('all')

def get_fluid_property(x, y, y_0, z, z_0, fluid):
    """Get the property x of the fluid in the state (x,y) = (y_0,z_0),
    and avoid the error if the fluid is in a saturated state."""
    try:
        return prp.PropsSI(x, y, y_0, z, z_0, fluid)
    except ValueError:
        if (y == 'P' and z == 'T'):
            # Near saturation P,T → use Q=0 or Q=1
            try:
                return prp.PropsSI(x, 'P', y_0, 'Q', 0.0, fluid)
            except:
                return prp.PropsSI(x, 'P', y_0, 'Q', 1.0, fluid)
        elif (y == 'T' and z == 'P'):
            # Same for T,P
            try:
                return prp.PropsSI(x, 'P', z_0, 'Q', 0.0, fluid)
            except:
                return prp.PropsSI(x, 'P', z_0, 'Q', 1.0, fluid)
        else:
            # Other combinations → |twophase
            return prp.PropsSI(x, y + '|twophase', y_0, z, z_0, fluid)

class StandardCycle:
    """Describes a refrigeration standard theoretical cycle (whose hot source is ambient air → pinch calculation).
    gc = either a condenser (subcritical cycle) or a gas-cooler (transcritical cycle).
    The unsubcooled cycle is completely defined by the minimum parameters :
        - (T_ev, T_gc_out) if it is subcritical
        - (T_ev, P_h) if it is subcritical
        - (T_ev, P_h, T_gc_out) if it is transcritical
    The subcooling and superheating are added as independent parameters. The sucooling degree 
    can be set either by delta_T_sc (K) or by sc_ratio (-), defined below.
    T_amb_air is then used to compute the pinch in the condenser/gas-cooler.

    Attributes :
    - fluid: CoolProp fluid name (string)
    - T_ev: evaporator temperature (K)
    - P_h: hot source (condenser / gas cooler) pressure (Pa)
    - T_amb_air: ambient air inlet temperature (K)
    - T_gc_out: temperature at the outlet of condenser/gas-cooler 
        (before any subcooling, at the bubble point or in a supercritical state) (K)
    - delta_T_sh: superheat added at compressor inlet, independent from T_ev (K)
    - delta_T_sc: subcooling added at condenser/gas-cooler outlet, independent from T_amb_air (K)
    - sc_ratio: subcooling ratio = delta_h_sc / delta_h_ev_without_sc = (h_gc_out - h_sc_out) / (h_comp_in - h_gc_out) (-)
    - coefs_eta_comp: coefficients of the polynomial expressing compressor efficiency as a function of pressure ratio
    - mu: mass flow rate ratio between fluid and ambient air in condenser/gas-cooler
    - N_gc_nodes: number of nodes for discretizing condenser/gas-cooler
    """

    def __init__(self,
                fluid,
                T_ev,
                P_h=None,
                T_gc_out=None,
                T_amb_air=None,
                delta_T_sh=5,
                delta_T_sc=0,
                sc_ratio=0,
                coefs_eta_comp=[1.003,-0.121],
                mu=1/50,
                N_gc_nodes=20):

        # Check minimum parameter requirements
        has_T_gc_out = T_gc_out is not None
        has_P_h = P_h is not None
        if has_P_h:
            if not (has_T_gc_out) and (P_h <= prp.PropsSI(fluid, 'Pcrit')):
                # (T_ev, P_h) for subcritical is acceptable
                pass    # Valid subcritical case
            elif has_T_gc_out:
                pass    # Valid transcritical cases
            else:
                raise ValueError("For transcritical cycles, provide T_gc_out with P_h")
        else:
            if not has_T_gc_out:     # Invalid subcritical case
                raise ValueError("For subcritical cycles, provide (T_ev, T_gc_out) or (T_ev, P_h)")
            if has_T_gc_out and (T_gc_out > prp.PropsSI(fluid, 'Tcrit')):     # Invalid supercritical case
                raise ValueError("For a supercritical cycle (T_gc_out > T_crit), provide (T_ev, P_h, T_gc_out)")
        if (delta_T_sc > 0) and (sc_ratio > 0):
            raise ValueError("Provide either delta_T_sc or sc_ratio, not both.")

        # Core working fluid and thermodynamic inputs
        self.fluid = fluid
        self.T_ev = T_ev
        self.P_h = P_h
        self.T_gc_out = T_gc_out

        # Heat exchange parameters
        self.delta_T_sh = delta_T_sh
        self.delta_T_sc = delta_T_sc
        self.sc_ratio = sc_ratio

        # Machine/flow parameters
        self.T_amb_air = T_amb_air
        self.coefs_eta_comp = coefs_eta_comp

        # Numerical discretization in condenser/gas-cooler
        self.N_gc_nodes = N_gc_nodes
        self.mu = mu    # mu = m_dot_fluid / m_dot_air 
        self.is_pinch_computed = False
        self.pinch_gc = None

        # Cycle properties
        self.transcritical_cycle = self.is_transcritical()
        self.is_cycle_computed = False
        self.state_h, self.state_s, self.state_p, self.state_T = None, None, None, None
        self.COP = None

    def get_eta_comp(self, r: float) -> float:
        """Return compressor efficiency for a given pressure ratio r."""
        deg = len(self.coefs_eta_comp) - 1
        eta_comp = 0
        for i in range(deg+1):
            eta_comp += self.coefs_eta_comp[i] * r**i
        return eta_comp
    
    def is_transcritical(self):
        """Determine if the cycle is transcritical."""
        F = self.fluid
        P_crit = prp.PropsSI(F, 'Pcrit')        
        if self.P_h is not None:
            if self.P_h > P_crit:
                return True
            else:
                return False  
        else:
                return False
  
    def compute_cycle(self):
        """Compute the appropriate subcritical or transcritical cycle,
        return cycle states : h, s, P, T arrays at key points."""
        self.is_cycle_computed = True

        F = self.fluid

        if self.P_h is None:    # Subcritical case defined by (T_ev, T_gc_out)
            P_h = get_fluid_property('P', 'T', self.T_gc_out, 'Q', 0.5, F)
        else:                   # Subcritical case defined by (T_ev, P_h) or transcritical case defined by (T_ev, P_h, T_gc_out)
            P_h = self.P_h

        if self.T_gc_out is None:    # Subcritical case defined by (T_ev, P_h)
            T_gc_out = get_fluid_property('T', 'P', self.P_h, 'Q', 0.5, F)
        else:                       # Transcritical case defined by (T_ev, P_h, T_gc_out)
            T_gc_out = self.T_gc_out

        # Compressor inlet state
        P_ev = get_fluid_property('P', 'T', self.T_ev, 'Q', 1, F)
        T_comp_in = self.T_ev + self.delta_T_sh
        h_comp_in = get_fluid_property('H', 'P', P_ev, 'T', T_comp_in, F)
        s_comp_in = get_fluid_property('S', 'P', P_ev, 'T', T_comp_in, F)

        # Compression efficiency 
        r = P_h / P_ev
        
        # Compressor outlet state
        h_comp_out_isentropic = get_fluid_property('H', 'P', P_h, 'S', s_comp_in, F)
        h_comp_out = h_comp_in + (h_comp_out_isentropic - h_comp_in) / self.get_eta_comp(r)
        T_comp_out = get_fluid_property('T', 'P', P_h, 'H', h_comp_out, F)
        s_comp_out = get_fluid_property('S', 'P', P_h, 'H', h_comp_out, F)

        # Gas-cooler / condenser outlet state
        h_gc_out = get_fluid_property('H', 'P', P_h, 'T', T_gc_out, F)

        # Expansion inlet state
        if self.sc_ratio > 0:
            h_exp_in = h_gc_out - self.sc_ratio * (h_comp_in - h_gc_out)
            T_exp_in = get_fluid_property('T', 'P', P_h, 'H', h_exp_in, F)
        else:
            T_exp_in = T_gc_out - self.delta_T_sc
            h_exp_in = get_fluid_property('H', 'P', P_h, 'T', T_exp_in, F)
        
        # For the computation of subcooling ratio and delta_T_sc
        self.h_gc_out = h_gc_out
        self.h_exp_in = h_exp_in
        self.h_comp_in = h_comp_in
        self.T_exp_in = T_exp_in

        # Expansion outlet state 
        h_exp_out = h_exp_in # isenthalpic expansion
        s_exp_out = get_fluid_property('S', 'P', P_ev, 'H', h_exp_out, F)
        T_exp_out = get_fluid_property('T', 'P', P_ev, 'H', h_exp_out, F)
        self.delta_h_ev = h_comp_in - h_exp_out

        # Dew point point state
        h_ev_vap = get_fluid_property('H', 'P', P_ev, 'Q', 1, F)
        s_ev_vap = get_fluid_property('S', 'P', P_ev, 'Q', 1, F)
        T_ev_vap = get_fluid_property('T', 'P', P_ev, 'Q', 1, F)

        # Discretize path in condenser/gas-cooler and subcooler
        H_nodes = np.linspace(h_comp_out, h_exp_in, self.N_gc_nodes)
        T_cond_nodes = [T_comp_out]
        S_cond_nodes = [s_comp_out]
        for i in range(1, self.N_gc_nodes):
            T_cond_nodes.append(get_fluid_property('T', 'P', P_h, 'H', H_nodes[i], F))
            S_cond_nodes.append(get_fluid_property('S', 'P', P_h, 'H', H_nodes[i], F))
        self.h_cond_nodes = H_nodes
        self.T_cond_nodes = np.array(T_cond_nodes)

        # State points of the full cycle
        H_points = [h_comp_in]
        P_points = [P_ev]
        S_points = [s_comp_in]
        T_points = [T_comp_in]     
        H_points.extend(list(H_nodes))
        H_points.extend([h_exp_out, h_ev_vap, h_comp_in])
        P_points.extend([P_h] * self.N_gc_nodes)
        P_points.extend([P_ev] * 3)
        S_points.extend(S_cond_nodes)
        S_points.extend([s_exp_out, s_ev_vap, s_comp_in])
        T_points.extend(T_cond_nodes)
        T_points.extend([T_exp_out, T_ev_vap, T_comp_in])

        self.state_h, self.state_s, self.state_p, self.state_T = np.array(H_points), np.array(S_points), np.array(P_points), np.array(T_points)

    def get_sc_ratio(self):
        """Return the subcooling ratio of the last computed cycle."""
        if self.sc_ratio > 0:
            return self.sc_ratio
        if not self.is_cycle_computed:
            self.compute_cycle()
        sc_ratio = (self.h_gc_out - self.h_exp_in) / (self.h_comp_in - self.h_gc_out)
        return sc_ratio

    def get_delta_T_sc(self):
        """Return the subcooling degree of the last computed cycle."""
        if self.delta_T_sc > 0:
            return self.delta_T_sc
        if not self.is_cycle_computed:
            self.compute_cycle()
        delta_T_sc = self.T_gc_out - self.T_exp_in
        return delta_T_sc

    def get_COP(self):
        if self.COP is not None:
            return self.COP
        if not self.is_cycle_computed:
            self.compute_cycle()
        cycle_COP = (self.state_h[0] - self.state_h[-3]) / (self.state_h[1] - self.state_h[0])
        return cycle_COP
    
    def get_pinch_air(self, show=False, saving_path=None):
        """Return the minimum temperature difference between the fluid and ambient air
        in the condenser/gas-cooler for the last computed cycle."""
        if not self.is_cycle_computed:
            self.compute_cycle()
        if self.is_pinch_computed and (not show):
            return self.pinch_gc
        
        F = self.fluid
        T_air_gc = np.ones(self.N_gc_nodes) * self.T_amb_air
        cp_air = get_fluid_property('Cpmass', 'P', 101325, 'T', self.T_amb_air, 'Air')  # J/kg/K, assumed constant
        h_out_fluid = self.h_cond_nodes[-1]
        for i in range(1, self.N_gc_nodes):
            delta_h_fluid = self.h_cond_nodes[self.N_gc_nodes - 1 - i] - h_out_fluid  # >0
            T_air_gc[i] +=  delta_h_fluid * self.mu / cp_air
        
        # Find the node where pinch occurs
        pinch_node = np.argmin(self.T_cond_nodes - T_air_gc[::-1])
        self.pinch_gc = self.T_cond_nodes[pinch_node] - T_air_gc[::-1][pinch_node]
        
        if show or (saving_path is not None):
            plt.figure()
            x_normalized = np.linspace(0, 1, self.N_gc_nodes)
            plt.plot(x_normalized, self.T_cond_nodes - 273.15, marker='o', color='red', label='Fluid temperature')
            plt.plot(x_normalized, T_air_gc[::-1] - 273.15, marker='s', color='blue', label='Air temperature')
            
            plt.plot(x_normalized[pinch_node], self.T_cond_nodes[pinch_node] - 273.15, marker='*', markersize=15, color='green', label=f'Pinch point (ΔT = {self.pinch_gc:.2f} °C)')
            plt.axvline(x=x_normalized[pinch_node], color='green', linestyle='--', alpha=0.5)
            
            plt.xlabel('Condenser/Gas-cooler normalized length (0 = fluid inlet, 1 = fluid outlet)')
            plt.ylabel('Temperature [°C]')
            plt.title('Temperature profiles')
            plt.grid(True)
            plt.legend()
            if saving_path is not None:
                plt.savefig(saving_path, dpi=300)
            if show:
                plt.show()

        return self.pinch_gc
        
    def plot_TS(self, show=True):
        """Plot T-S diagram using computed results.
        """
        if not self.is_cycle_computed:
            self.compute_cycle()

        F = self.fluid
        P_ev = get_fluid_property('P', 'T', self.T_ev, 'Q', 1, F)
    
        # Critical properties
        P_crit = prp.PropsSI(F, 'Pcrit')
        T_crit = prp.PropsSI(F, 'Tcrit')

        # Saturation curves
        vectP = np.linspace(P_ev * 0.8, P_crit, num=80)
        Tsat_liq = get_fluid_property('T', 'P', vectP, 'Q', 0, F)
        Ssat_liq = get_fluid_property('S', 'P', vectP, 'Q', 0, F)
        Tsat_vap = get_fluid_property('T', 'P', vectP, 'Q', 1, F)
        Ssat_vap = get_fluid_property('S', 'P', vectP, 'Q', 1, F) 
                
        plt.figure()
        plt.plot(Ssat_liq, Tsat_liq - 273.15, color='purple', label='sat liquid')
        plt.plot(Ssat_vap, Tsat_vap - 273.15, color='blue', label='sat vapour')
        plt.plot(self.state_s, self.state_T - 273.15, color='red', label='Cycle path')
        ymin = np.min(self.state_T) - 273.15 -10
        ymax = max(np.max(self.state_T) - 273.15 + 10, T_crit - 273.15 + 10)
        plt.ylim(ymin,ymax)
        plt.xlabel('Entropy [J/kg/K]')
        plt.ylabel('Temperature [°C]')
        plt.legend()
        plt.grid(True)
        if show:
            plt.show()

    def plot_HP(self, show=True):
        """Plot H-P diagram using last computed results.
        """
        if not self.is_cycle_computed:
            self.compute_cycle()

        F = self.fluid
    
        # Critical properties
        P_crit = prp.PropsSI(F, 'Pcrit')
        T_crit = prp.PropsSI(F, 'Tcrit')

        # Saturation curves
        vectT = np.linspace(self.T_ev * 0.8, T_crit, num=80)
        Psat_liq = get_fluid_property('P', 'T', vectT, 'Q', 0, F)
        Hsat_liq = get_fluid_property('H', 'T', vectT, 'Q', 0, F)
        Psat_vap = get_fluid_property('P', 'T', vectT, 'Q', 1, F)
        Hsat_vap = get_fluid_property('H', 'T', vectT, 'Q', 1, F)
                
        plt.figure()
        plt.plot(Hsat_liq, Psat_liq, color='purple', label='sat liquid')
        plt.plot(Hsat_vap, Psat_vap, color='blue', label='sat vapour')
        plt.plot(self.state_h, self.state_p, color='red', label='Cycle path')
        ymin = np.min(self.state_p)*0.85
        ymax = max(np.max(self.state_p)*1.15,P_crit*1.15)
        plt.ylim(ymin,ymax)
        plt.xlabel('Enthalpy [J/kg]')
        plt.ylabel('Pressure [Pa]')
        plt.legend()
        plt.grid(True)
        if show:
            plt.show()

class ComplexSystem:
    """Models the system under study. The main component is a sub/trans-critical refrigeration cycle 
    (whose hot source is ambient air → pinch calculation). This cycle is coupled with system that can
    provide a DMS (whose part is characterized by alpha) as well as a TES system (whose part is characterized by beta).
    gc = either a condenser (subcritical cycle) or a gas-cooler (transcritical cycle).
    The cycle is completely defined by the minimum parameters :
        - (T_ev, T_gc_out) if it is subcritical
        - (T_ev, P_h) if it is subcritical
        - (T_ev, P_h, T_gc_out) if it is transcritical
    T_amb_air is then used to compute the pinch in the condenser/gas-cooler. A special attention is given to the respect
    of pinch requirements in the different heat exchangers.

    Attributes :
    - fluid: CoolProp fluid name (string)
    - T_ev: evaporator temperature (K)
    - P_h: hot source (condenser / gas cooler) pressure (Pa)
    - T_amb_air: ambient air inlet temperature (K)
    - T_gc_out: temperature at the outlet of condenser/gas-cooler 
        (before any subcooling, at the bubble point or in a supercritical state) (K)
    - delta_T_sh: superheat added at compressor inlet, independent from T_ev (K)
    - alpha: DMS parameter, defined as a ratio (Q_sc_DMS / Q_CO2)
    - beta: TES parameter, defined as a ratio (Q_sc_TES / Q_CO2)
    - coefs_eta_comp: coefficients of the polynomial expressing compressor efficiency as a function of pressure ratio
    - mu: mass flow rate ratio between fluid and ambient air in condenser/gas-cooler
    - N_gc_nodes: number of nodes for discretizing condenser/gas-cooler

    """
    def __init__(self,
                fluid,
                T_ev,
                P_h,
                T_gc_out,
                T_amb_air=None,
                delta_T_sh=5,
                alpha=0.0,
                beta=0.0,
                coefs_eta_comp=[1.003,-0.121],
                fluid_DMS='n-Propane',
                delta_T_sh_prop=7,
                delta_T_sc_prop=5,
                gas_pinch_DMS=5,
                coefs_eta_comp_DMS=[0.3774,0.1405,-0.0201,0.0008],
                mu=1/50,
                mu_DMS=1/30,
                N_gc_nodes=20):
        
        # Core working fluid and main cycle
        self.fluid = fluid
        self.T_ev = T_ev
        self.T_amb_air = T_amb_air
        self.P_h = P_h
        self.T_gc_out = T_gc_out
        self.beta = beta
        self.delta_T_sh = delta_T_sh
        self.coefs_eta_comp = coefs_eta_comp

        # Numerical discretization
        self.N_gc_nodes = N_gc_nodes
        self.mu = mu    # mu = m_dot_fluid / m_dot_air
        self.mu_DMS = mu_DMS  # mu_DMS = m_dot_fluid_DMS / m_dot_air

        # DMS cycle
        self.fluid_DMS = fluid_DMS
        self.alpha = alpha
        self.gas_pinch_DMS = gas_pinch_DMS
        self.delta_T_sh_prop = delta_T_sh_prop
        self.delta_T_sc_prop = delta_T_sc_prop
        self.coefs_eta_comp_DMS = coefs_eta_comp_DMS
        self.h_DMS_cycle_states = []
        self.s_DMS_cycle_states = []
        self.T_DMS_cycle_states = []
        self.P_DMS_cycle_states = []
        self.COP_DMS = None

        # Cycle properties
        self.is_cycle_computed = False
        self.is_pinch_computed = False
        self.is_pinch_DMS_computed = False
        self.h_cycle_states = []
        self.s_cycle_states = []
        self.T_cycle_states = []
        self.P_cycle_states = []
        self.COP_CO2 = None   #COP of the main CO2 cycle 
        self.COP = None   #COP of the entire system including the DMS and CTES 

    def get_eta_comp(self, r: float) -> float:
        """Return compressor efficiency for a given pressure ratio r."""
        deg = len(self.coefs_eta_comp) - 1
        eta_comp = 0
        for i in range(deg+1):
            eta_comp += self.coefs_eta_comp[i] * r**i
        return eta_comp
    
    def get_eta_comp_DMS(self, r: float) -> float:
        """Return compressor efficiency for a given pressure ratio r."""
        deg = len(self.coefs_eta_comp_DMS) - 1
        eta_comp_DMS = 0
        for i in range(deg+1):
            eta_comp_DMS += self.coefs_eta_comp_DMS[i] * r**i
        return eta_comp_DMS
    
    def get_P_cond_min_propane(self, P_ev, h_comp_in, s_comp_in, max_iter=50, plot_T_profile=False) -> float:
        """Compute the minimum condensing pressure for the propane DMS cycle
        to achieve the required pinch with ambient air at T_amb."""

        F = self.fluid_DMS
        N_nodes = self.N_gc_nodes

        def evaluate_pinch(P_cond, plot_T_profile_i=False):
            # Propane states
            T_cond = get_fluid_property('T', 'P', P_cond, 'Q', 0.5, F)
            r_DMS = P_cond / P_ev
            eta_comp_DMS = self.get_eta_comp_DMS(r_DMS)
            h_comp_out_isentropic = get_fluid_property('H', 'P', P_cond, 'S', s_comp_in, F)
            h_comp_out = h_comp_in + (h_comp_out_isentropic - h_comp_in) / eta_comp_DMS
            T_comp_out = get_fluid_property('T', 'P', P_cond, 'H', h_comp_out, F)
            h_cond_out = get_fluid_property('H', 'P', P_cond, 'T', T_cond - self.delta_T_sc_prop, F)  

            h_cond_nodes = np.linspace(h_comp_out, h_cond_out, N_nodes)
            T_cond_nodes = [T_comp_out]
            for i in range(1, N_nodes):
                T_node = get_fluid_property('T', 'P', P_cond, 'H', h_cond_nodes[i], F)
                T_cond_nodes.append(T_node)
            T_cond_nodes = np.array(T_cond_nodes)
            
            # Air states
            T_air_cond = np.ones(N_nodes) * self.T_amb_air 
            cp_air = get_fluid_property('Cpmass', 'P', 101325, 'T', self.T_amb_air, 'Air')  # J/kg/K, assumed constant
            h_out_fluid = h_cond_nodes[-1]
            for i in range(1, N_nodes):
                delta_h_fluid = h_cond_nodes[N_nodes - 1 - i] - h_out_fluid  # >0
                T_air_cond[i] +=  delta_h_fluid * self.mu_DMS / cp_air
            
            # Find the node where pinch occurs
            pinch_node = np.argmin(T_cond_nodes - T_air_cond[::-1])
            pinch_value = T_cond_nodes[pinch_node] - T_air_cond[::-1][pinch_node]

            return pinch_value

        ### Using a root-finding method from scipy
        P_low = get_fluid_property('P', 'T', self.T_amb_air + self.gas_pinch_DMS, 'Q', 0.5, self.fluid_DMS)
        P_high = 42.2e5 # P_crit_propane
        P_mid = bisect(lambda P: evaluate_pinch(P) - self.gas_pinch_DMS, P_low, P_high, xtol=600, maxiter=max_iter)
        
        if plot_T_profile:
            pinch_mid = evaluate_pinch(P_mid, plot_T_profile_i=True)
        else:
            pinch_mid = evaluate_pinch(P_mid)

        self.P_cond_DMS = P_mid
        return P_mid, pinch_mid

    def get_DMS_COP(self):
        """Give COP of the DMS subcycle"""
        if self.COP_DMS is not None:
            return self.COP_DMS
        if self.is_cycle_computed == False:
            self.compute_cycle()

        F = self.fluid_DMS
        T_ev_DMS = min(self.T_DMS_out, self.T_DMS_in - self.delta_T_sh_prop) - self.gas_pinch_DMS
        self.P_ev_DMS = get_fluid_property('P', 'T', T_ev_DMS, 'Q', 0.5, F)
        
        # Compressor states
        if self.delta_T_sh_prop > 0:
            T_comp_in = T_ev_DMS + self.delta_T_sh_prop
            h_comp_in = get_fluid_property('H', 'P', self.P_ev_DMS, 'T', T_comp_in, F)
            s_comp_in = get_fluid_property('S', 'P', self.P_ev_DMS, 'T', T_comp_in, F)
        else:
            h_comp_in = get_fluid_property('H', 'P', self.P_ev_DMS, 'Q', 1, F)
            s_comp_in = get_fluid_property('S', 'P', self.P_ev_DMS, 'Q', 1, F)
            T_comp_in = T_ev_DMS
        self.h_comp_in_DMS = h_comp_in
        self.s_comp_in_DMS = s_comp_in
        P_cond_DMS, _ = self.get_P_cond_min_propane(self.P_ev_DMS, h_comp_in, s_comp_in)
        self.T_cond_DMS = get_fluid_property('T', 'P', P_cond_DMS, 'Q', 0.5, F)
        r_DMS = P_cond_DMS / self.P_ev_DMS
        eta_comp_DMS = self.get_eta_comp_DMS(r_DMS)
        h_comp_out_isentropic = get_fluid_property('H', 'P', P_cond_DMS, 'S', s_comp_in, F)
        h_comp_out = h_comp_in + (h_comp_out_isentropic - h_comp_in) / eta_comp_DMS
        T_comp_out = get_fluid_property('T', 'P', P_cond_DMS, 'H', h_comp_out, F)
        s_comp_out = get_fluid_property('S', 'P', P_cond_DMS, 'H', h_comp_out, F)

        # Condenser states
        h_cond_out = get_fluid_property('H', 'P', P_cond_DMS, 'T', self.T_cond_DMS - self.delta_T_sc_prop, F)      
        s_cond_out = get_fluid_property('S', 'P', P_cond_DMS, 'T', self.T_cond_DMS - self.delta_T_sc_prop, F)    
        
        # Evaporator states
        h_ev_in = h_cond_out # isenthalpic expansion
        s_ev_in = get_fluid_property('S', 'P', self.P_ev_DMS, 'H', h_ev_in, F)

        self.h_DMS_cycle_states = [h_comp_in, h_comp_out, h_cond_out, h_ev_in,h_comp_in]
        self.s_DMS_cycle_states = [s_comp_in, s_comp_out, s_cond_out, s_ev_in, s_comp_in]
        self.P_DMS_cycle_states = [self.P_ev_DMS, P_cond_DMS, P_cond_DMS, self.P_ev_DMS, self.P_ev_DMS]
        self.T_DMS_cycle_states = [T_comp_in, T_comp_out, self.T_cond_DMS - self.delta_T_sc_prop, T_ev_DMS, T_comp_in]

        self.COP_DMS = (h_comp_in - h_ev_in) / (h_comp_out - h_comp_in)
        return self.COP_DMS

    def compute_cycle(self):
        self.is_cycle_computed = True
        F = self.fluid
        P_ev = get_fluid_property('P', 'T', self.T_ev, 'Q', 0.5, F)

        # Compressor states
        T_comp_in = self.T_ev + self.delta_T_sh 
        if self.delta_T_sh > 0:
            h_comp_in = get_fluid_property('H', 'P', P_ev, 'T', T_comp_in, F)
        else:
            h_comp_in = get_fluid_property('H', 'P', P_ev, 'Q', 1, F)
        s_comp_in = get_fluid_property('S', 'P', P_ev, 'H', h_comp_in, F)
        r = self.P_h / P_ev
        h_comp_out_isentropic = get_fluid_property('H', 'P', self.P_h, 'S', s_comp_in, F)
        h_comp_out = h_comp_in + (h_comp_out_isentropic - h_comp_in) / self.get_eta_comp(r)
        s_comp_out = get_fluid_property('S', 'P', self.P_h, 'H', h_comp_out, F)
        T_comp_out = get_fluid_property('T', 'P', self.P_h, 'H', h_comp_out, F)

        # Condenser/gas-cooler states
        h_sc_in = get_fluid_property('H', 'P', self.P_h, 'T', self.T_gc_out, F)
        delta_h_ev_without_sc = h_comp_in - h_sc_in # >0 if fluid cannot condense in subcoolers
        h_sc_DMS_out = h_sc_in - self.alpha * delta_h_ev_without_sc
        T_DMS_out = get_fluid_property('T', 'P', self.P_h, 'H', h_sc_DMS_out, F)
        self.h_sc_in = h_sc_in
        self.T_DMS_in = self.T_gc_out
        self.h_sc_DMS_out = h_sc_DMS_out
        self.T_DMS_out = T_DMS_out

        # Expander states
        h_exp_in = h_sc_DMS_out - self.beta * delta_h_ev_without_sc
        T_exp_in = get_fluid_property('T', 'P', self.P_h, 'H', h_exp_in, F)
        self.T_TES_in = T_DMS_out
        self.T_TES_out = T_exp_in

        # Discretize path in condenser/gas-cooler and subcooler
        h_nodes = np.linspace(h_comp_out, h_exp_in, self.N_gc_nodes)
        T_cond_nodes = [T_comp_out]
        s_cond_nodes = [s_comp_out]
        for i in range(1, self.N_gc_nodes):
            T_cond_nodes.append(get_fluid_property('T', 'P', self.P_h, 'H', h_nodes[i], F))
            s_cond_nodes.append(get_fluid_property('S', 'P', self.P_h, 'H', h_nodes[i], F))

        # TEMPORARY: Discretize path in gas-cooler/condenser
        h_nodes_gc = np.linspace(h_comp_out, h_sc_in, self.N_gc_nodes)
        T_nodes_gc = [T_comp_out]
        for i in range(1, self.N_gc_nodes):
            T_nodes_gc.append(get_fluid_property('T', 'P', self.P_h, 'H', h_nodes_gc[i], F))
        self.T_nodes_gc = np.array(T_nodes_gc)
        self.h_nodes_gc = h_nodes_gc

        # Evaporator states
        h_ev_in = h_exp_in    # isenthalpic expansion
        s_ev_in = get_fluid_property('S', 'P', P_ev, 'H', h_ev_in, F)
        T_ev_in = get_fluid_property('T', 'P', P_ev, 'H', h_ev_in, F)
        T_ev_out = T_comp_in
        h_ev_out = h_comp_in
        s_ev_out = s_comp_in

        # Relevant states
        self.delta_h_ev_without_sc = delta_h_ev_without_sc
        self.w_comp = h_comp_out - h_comp_in
        self.h_cycle_states = [h_comp_in] + h_nodes.tolist() + [h_ev_in,h_ev_out]
        self.s_cycle_states = [s_comp_in] + s_cond_nodes + [s_ev_in,s_ev_out]
        self.T_cycle_states = [T_comp_in] + T_cond_nodes + [T_ev_in,T_ev_out]
        self.P_cycle_states = [P_ev] + [self.P_h]* (self.N_gc_nodes) + [P_ev,P_ev]
    
    def get_COP(self):
        """
        COP of the entire system including the DMS and CTES systems 
        COP = Q_ev / (W_comp + W_comp_DMS)
        COP = Q_ev / (W_comp + Q_sc_DMS / COP_DMS)
        """
        if self.COP is not None:
            return self.COP
        if not self.is_cycle_computed:
            self.compute_cycle()
        if self.COP_DMS is None:
            self.get_DMS_COP()
        if self.COP_CO2 is None:
            self.get_CO2_COP()
        self.COP = (1 + self.alpha + self.beta) / (1 / self.COP_CO2 + self.alpha / self.COP_DMS) 
        return self.COP

    def get_CO2_COP(self):
        """
        COP of the CO2 cycle:
        COP_CO2 = (Q_ev -Q_DMS -Q_CTES) / W_comp_CO2
        """
        if self.COP_CO2 is not None:
            return self.COP_CO2
        if not self.is_cycle_computed:
            self.compute_cycle()
        self.COP_CO2 = abs(self.delta_h_ev_without_sc / self.w_comp)
        return self.COP_CO2  
    
    def get_delta_T_sc_DMS(self):
        """Return the subcooling degree provided by the DMS to the main cycle"""
        if not self.is_cycle_computed:
            self.compute_cycle()
        SUB_DMS = self.T_DMS_in - self.T_DMS_out
        return SUB_DMS

    def get_delta_T_sc_TES(self):
        """Return the subcooling degree provided by the TES to the main cycle"""
        if not self.is_cycle_computed:
            self.compute_cycle()
        SUB_TES = self.T_TES_in - self.T_TES_out
        return SUB_TES

    def get_pinch_air(self, show=False, saving_path=None):
        """Return the minimum temperature difference between the fluid and ambient air
        in the condenser/gas-cooler for the last computed cycle."""
        if not self.is_cycle_computed:
            self.compute_cycle()
        if self.is_pinch_computed and (not show):
            return self.pinch_gc
        
        F = self.fluid
        T_air_gc = np.ones(self.N_gc_nodes) * self.T_amb_air
        cp_air = get_fluid_property('Cpmass', 'P', 101325, 'T', self.T_amb_air, 'Air')  # J/kg/K, assumed constant
        h_out_fluid = self.h_nodes_gc[-1]
        for i in range(1, self.N_gc_nodes):
            delta_h_fluid = self.h_nodes_gc[self.N_gc_nodes - 1 - i] - h_out_fluid  # >0
            T_air_gc[i] +=  delta_h_fluid * self.mu / cp_air
        
        # Find the node where pinch occurs
        pinch_node = np.argmin(self.T_nodes_gc - T_air_gc[::-1])
        self.pinch_gc = self.T_nodes_gc[pinch_node] - T_air_gc[::-1][pinch_node]
        
        if show or (saving_path is not None):
            plt.figure()
            x_normalized = np.linspace(0, 1, self.N_gc_nodes)
            plt.plot(x_normalized, self.T_nodes_gc - 273.15, marker='o', color='red', label='Fluid temperature')
            plt.plot(x_normalized, T_air_gc[::-1] - 273.15, marker='s', color='blue', label='Air temperature')
            
            plt.plot(x_normalized[pinch_node], self.T_nodes_gc[pinch_node] - 273.15, marker='*', markersize=15, color='green', label=f'Pinch point (ΔT = {self.pinch_gc:.2f} °C)')
            plt.axvline(x=x_normalized[pinch_node], color='green', linestyle='--', alpha=0.5)
            
            plt.xlabel('Condenser/Gas-cooler normalized length (0 = fluid inlet, 1 = fluid outlet)')
            plt.ylabel('Temperature [°C]')
            plt.title('Temperature profiles')
            plt.grid(True)
            plt.legend()
            if saving_path is not None:
                plt.savefig(saving_path, dpi=300)
            if show:
                plt.show()

        return self.pinch_gc 

    def get_pinch_air_DMS(self, show=False, saving_path=None):
        """Return the minimum temperature difference between the fluid and ambient air
        in the condenser/gas-cooler for the last computed cycle."""
        if not self.is_cycle_computed:
            self.compute_cycle()
        if self.is_pinch_DMS_computed and (not show):
            return self.pinch_air_DMS
        
        F = self.fluid_DMS
        N_nodes = self.N_gc_nodes
        
        # Propane states
        r_DMS = self.P_cond_DMS / self.P_ev_DMS
        eta_comp_DMS = self.get_eta_comp_DMS(r_DMS)
        h_comp_out_isentropic = get_fluid_property('H', 'P', self.P_cond_DMS, 'S', self.s_comp_in_DMS, F)
        h_comp_out = self.h_comp_in_DMS + (h_comp_out_isentropic - self.h_comp_in_DMS) / eta_comp_DMS
        T_comp_out = get_fluid_property('T', 'P', self.P_cond_DMS, 'H', h_comp_out, F)
        h_cond_out = get_fluid_property('H', 'P', self.P_cond_DMS, 'T', self.T_cond_DMS - self.delta_T_sc_prop, F)  
        h_cond_nodes = np.linspace(h_comp_out, h_cond_out, N_nodes)
        T_cond_nodes = [T_comp_out]
        for i in range(1, N_nodes):
            T_node = get_fluid_property('T', 'P', self.P_cond_DMS, 'H', h_cond_nodes[i], F)
            T_cond_nodes.append(T_node)
        T_cond_nodes = np.array(T_cond_nodes)
        
        # Air states
        T_air_cond = np.ones(N_nodes) * self.T_amb_air 
        cp_air = get_fluid_property('Cpmass', 'P', 101325, 'T', self.T_amb_air, 'Air')  # J/kg/K, assumed constant
        h_out_fluid = h_cond_nodes[-1]
        for i in range(1, N_nodes):
            delta_h_fluid = h_cond_nodes[N_nodes - 1 - i] - h_out_fluid  # >0
            T_air_cond[i] +=  delta_h_fluid * self.mu_DMS / cp_air
        
        # Find the node where pinch occurs
        pinch_node = np.argmin(T_cond_nodes - T_air_cond[::-1])
        self.pinch_air_DMS = T_cond_nodes[pinch_node] - T_air_cond[::-1][pinch_node]

        if show or (saving_path is not None):
            plt.figure()
            x_normalized = np.linspace(0, 1, N_nodes)
            plt.plot(x_normalized, T_cond_nodes - 273.15, marker='o', color='red', label='Fluid temperature')
            plt.plot(x_normalized, T_air_cond[::-1] - 273.15, marker='s', color='blue', label='Air temperature')
            
            plt.plot(x_normalized[pinch_node], T_cond_nodes[pinch_node] - 273.15, marker='*', markersize=15, color='green', label=f'Pinch point (ΔT = {self.pinch_air_DMS:.2f} °C)')
            plt.axvline(x=x_normalized[pinch_node], color='green', linestyle='--', alpha=0.5)
            
            plt.xlabel('Propane condenser normalized length (0 = fluid inlet, 1 = fluid outlet)')
            plt.ylabel('Temperature [°C]')
            plt.title('Temperature profiles Air-Propane')
            plt.grid(True)
            plt.legend()
            if saving_path is not None:
                plt.savefig(saving_path, dpi=300)
            if show:
                plt.show()

        return self.pinch_air_DMS
    
    def plot_HP(self, show=True, save=False):
        """Plot H-P diagram of the main cycle"""
        F = self.fluid
    
        # Critical properties
        P_crit = prp.PropsSI(F, 'Pcrit')
        T_crit = prp.PropsSI(F, 'Tcrit')

        # Saturation curves
        vectT = np.linspace(self.T_ev * 0.8, T_crit, num=80)
        Psat_liq = get_fluid_property('P', 'T', vectT, 'Q', 0, F)
        Hsat_liq = get_fluid_property('H', 'T', vectT, 'Q', 0, F)
        Psat_vap = get_fluid_property('P', 'T', vectT, 'Q', 1, F)
        Hsat_vap = get_fluid_property('H', 'T', vectT, 'Q', 1, F)
                
        plt.figure()
        plt.plot(Hsat_liq, Psat_liq, color='purple', label='sat liquid')
        plt.plot(Hsat_vap, Psat_vap, color='blue', label='sat vapour')
        plt.plot(self.h_cycle_states, self.P_cycle_states, color='red', label='CO2 cycle path')
        ymin = min(self.P_cycle_states)*0.85
        ymax = max(max(self.P_cycle_states)*1.15,P_crit*1.15)
        plt.ylim(ymin,ymax)
        plt.xlabel('Enthalpy [J/kg]')
        plt.ylabel('Pressure [Pa]')
        plt.legend()
        plt.grid(True)
        if show:
            plt.show()
        elif save:
            path = os.path.join(os.path.abspath(__file__), 'explicative_plots', 'plots', 'cycles', 'generated_cycles')
            plt.savefig(os.path.join(path, f"HP-Tamb_{self.T_amb_air - 273.15:.1f}-alpha{self.alpha:.3f}-beta{self.beta:.3f}.png"), dpi=300)
            if not show:  
                plt.close()
    
    def plot_TS(self, show=True, save=False):
        """Plot T-S diagram of the main cycle"""
        F = self.fluid
        P_ev = get_fluid_property('P', 'T', self.T_ev, 'Q', 0.5, F)
    
        # Critical properties
        P_crit = prp.PropsSI(F, 'Pcrit')
        T_crit = prp.PropsSI(F, 'Tcrit')

        # Saturation curves
        vectP = np.linspace(P_ev * 0.8, P_crit, num=80)
        Tsat_liq = get_fluid_property('T', 'P', vectP, 'Q', 0, F)
        Ssat_liq = get_fluid_property('S', 'P', vectP, 'Q', 0, F)
        Tsat_vap = get_fluid_property('T', 'P', vectP, 'Q', 1, F)
        Ssat_vap = get_fluid_property('S', 'P', vectP, 'Q', 1, F)
                
        plt.figure()
        plt.plot(Ssat_liq, Tsat_liq, color='purple', label='sat liquid')
        plt.plot(Ssat_vap, Tsat_vap, color='blue', label='sat vapour')
        plt.plot(self.s_cycle_states, self.T_cycle_states, color='red', label='CO2 cycle path')
        ymin = min(self.T_cycle_states)*0.85
        ymax = max(max(self.T_cycle_states)*1.15,T_crit*1.15)
        plt.ylim(ymin,ymax)
        plt.xlabel('Entropy [J/kg.K]')
        plt.ylabel('Temperature [K]')
        plt.legend()
        plt.grid(True)
        if show:
            plt.show()
        elif save:
            path = os.path.join(os.path.abspath(__file__), 'explicative_plots', 'plots', 'cycles', 'generated_cycles')
            plt.savefig(os.path.join(path, f"TS-Tamb_{self.T_amb_air - 273.15:.1f}-alpha{self.alpha:.3f}-beta{self.beta:.3f}.png"), dpi=300)
            if not show:  
                plt.close()
            
    def plot_HP_DMS(self, show=True, save=False):
        """Plot H-P diagram of the DMS cycle"""
        F = self.fluid_DMS
    
        # Critical properties
        P_crit = prp.PropsSI(F, 'Pcrit')
        T_crit = prp.PropsSI(F, 'Tcrit')
        T_ev_DMS = min(self.T_DMS_out, self.T_DMS_in - self.delta_T_sh_prop) - self.gas_pinch_DMS

        # Saturation curves
        vectT = np.linspace(T_ev_DMS * 0.8, T_crit, num=80)
        Psat_liq = get_fluid_property('P', 'T', vectT, 'Q', 0, F)
        Hsat_liq = get_fluid_property('H', 'T', vectT, 'Q', 0, F)
        Psat_vap = get_fluid_property('P', 'T', vectT, 'Q', 1, F)
        Hsat_vap = get_fluid_property('H', 'T', vectT, 'Q', 1, F)
                
        plt.figure()
        plt.plot(Hsat_liq, Psat_liq, color='purple', label='sat liquid')
        plt.plot(Hsat_vap, Psat_vap, color='blue', label='sat vapour')
        plt.plot(self.h_DMS_cycle_states, self.P_DMS_cycle_states, color='red', label='DMS cycle path')
        ymin = min(self.P_DMS_cycle_states)*0.85
        ymax = max(max(self.P_DMS_cycle_states)*1.15,P_crit*1.15)
        plt.ylim(ymin,ymax)
        plt.xlabel('Enthalpy [J/kg]')
        plt.ylabel('Pressure [Pa]')
        plt.legend()
        plt.grid(True)
        if show:
            plt.show()
        elif save:
            path = os.path.join(os.path.abspath(__file__), 'explicative_plots', 'plots', 'cycles', 'generated_cycles')
            plt.savefig(os.path.join(path, f"HP-DMS-Tamb_{self.T_amb_air - 273.15:.1f}-alpha{self.alpha:.3f}-beta{self.beta:.3f}.png"), dpi=300)
            # if random.random() <= 0.001:  # 0.1% de chance
            #     timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            #     plt.savefig(os.path.join(path,f'cycle_DMS_plot_{timestamp}.png'), dpi=300)
            if not show:  
                plt.close()

    def plot_TS_DMS(self, show=True, save=False):
        """Plot T-S diagram of the DMS cycle"""
        F = self.fluid_DMS
        T_ev_DMS = min(self.T_DMS_out, self.T_DMS_in - self.delta_T_sh_prop) - self.gas_pinch_DMS
        P_ev_DMS = get_fluid_property('P', 'T', T_ev_DMS, 'Q', 0.5, F)

    
        # Critical properties
        P_crit = prp.PropsSI(F, 'Pcrit')
        T_crit = prp.PropsSI(F, 'Tcrit')

        # Saturation curves
        vectP = np.linspace(self.P_ev_DMS * 0.8, P_crit, num=80)
        Tsat_liq = get_fluid_property('T', 'P', vectP, 'Q', 0, F)
        Ssat_liq = get_fluid_property('S', 'P', vectP, 'Q', 0, F)
        Tsat_vap = get_fluid_property('T', 'P', vectP, 'Q', 1, F)
        Ssat_vap = get_fluid_property('S', 'P', vectP, 'Q', 1, F)
                
        plt.figure()
        plt.plot(Ssat_liq, Tsat_liq, color='purple', label='sat liquid')
        plt.plot(Ssat_vap, Tsat_vap, color='blue', label='sat vapour')
        plt.plot(self.s_DMS_cycle_states, self.T_DMS_cycle_states, color='red', label='DMS cycle path')
        ymin = min(self.T_DMS_cycle_states)*0.85
        ymax = max(max(self.T_DMS_cycle_states)*1.15,T_crit*1.15)
        plt.ylim(ymin,ymax)
        plt.xlabel('Entropy [J/kg.K]')
        plt.ylabel('Temperature [K]')
        plt.legend()
        plt.grid(True)
        if show:
            plt.show()
        elif save:
            path = os.path.join(os.path.abspath(__file__), 'explicative_plots', 'plots', 'cycles', 'generated_cycles')
            plt.savefig(os.path.join(path, f"TS_DMS-Tamb_{self.T_amb_air - 273.15:.1f}-alpha{self.alpha:.3f}-beta{self.beta:.3f}.png"), dpi=300)
            # if random.random() <= 0.001:  # 0.1% de chance
            #     timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            #     plt.savefig(os.path.join(path,f'cycle_DMS_plot_{timestamp}.png'), dpi=300)
            if not show:  
                plt.close()

########################################################################################################################################

# if __name__ == '__main__':
    ################################# CycleStandard example usage ###################################
    # cycle2 = StandardCycle('CarbonDioxide',
    #                           273.15 - 10,           # evaporator temperature (K)
    #                           60e5,                  # P_h (condenser/gas-cooler pressure) (Pa)
    #                           273.15 + 25,           # ambient air temperature (K)
    #                           None)                  # T_exp_in 

    # T_amb_air_cycle = 273.15 + 16
    # T_gc_out_cycle = T_amb_air_cycle + 8
    # P_h_cycle = get_fluid_property('P', 'T', T_gc_out_cycle, 'Q', 0.5, 'CarbonDioxide')
    # cycle = StandardCycle('CarbonDioxide',
    #                         273.15 - 10,            # evaporator temperature (K)
    #                         P_h_cycle,
    #                         T_gc_out_cycle,
    #                         T_amb_air_cycle)        
                                    


    # cycle.plot_TS()
    # cycle.plot_HP()
    # cycle.get_pinch_air(show=True)

    ################################## ComplexSystem example usage ###################################

    # sbc_cycle = ComplexSystem('CarbonDioxide',
    #                           273.15 - 10,
    #                           P_h=7916829,
    #                           T_gc_out=305.80,
    #                             T_amb_air=300.80,
    #                             alpha=0.31,
    #                             beta=0.23)
    # # print(f"COP CO2 cycle: {sbc_cycle.get_CO2_COP():.3f}")
    # print(f"COP total cycle: {sbc_cycle.get_COP():.3f}")                                                
    # print(f"COP DMS cycle: {sbc_cycle.get_DMS_COP():.3f}")
    # sbc_cycle.plot_HP()
    # sbc_cycle.plot_HP_DMS()
    # sbc_cycle.get_pinch_air(show=True)
    # sbc_cycle.get_pinch_air_DMS(show=True)


    ################################## Literature Comparison ###################################

    # # validation data (T35°C only)
    # # https://www.sciencedirect.com/science/article/pii/S0140700715000754#sec3  
    # P_h_ref=[88.0127041742286,89.8094373865698,91.1978221415608,93.1851179673321,95.1724137931034,97.1324863883847,99.1470054446461,103.067150635208,108.375680580762,113.275862068965,116.950998185117,119.918330308529]
    # COP_ref=[1.25042372881355,1.38008474576271,1.45381355932203,1.51483050847457,1.54152542372881,1.54661016949152,1.54406779661016,1.51483050847457,1.45889830508474,1.3978813559322,1.35211864406779,1.31398305084745]
    
    # # our data
    # T_ambi=35+273.15
    # p_list=np.linspace(87e5,120e5,num=20)
    # COP_CO2=np.array([])
    # for p in p_list:
    #     cycle_i = cycle = StandardCycle('CarbonDioxide',
    #                         273.15 - 5,            # T_ev from the article (K)
    #                         p,                     # P_h from the article (Pa)
    #                         T_gc_out=T_ambi+5,     # from the article (K)
    #                         delta_T_sh=10,
    #                         coefs_eta_comp=[0.95,-0.1])         # from the article (K)
    #     COP_i = cycle_i.get_COP()
    #     COP_CO2=np.append(COP_CO2,COP_i)
    
    # print(p_list*1e-5)
    # print(COP_CO2)

    # # plot comparison
    # fig = plt.figure(figsize=(6, 4), dpi=150) 
    # plt.plot(p_list*1e-5,COP_CO2,label="Our Model")
    # plt.plot(P_h_ref,COP_ref,label="Reference (Llopis and al)", marker='*',linestyle="None")   
    # plt.xlim(75,120)
    # plt.legend(loc='upper right')
    # plt.xlabel('$P_h$(bar)')
    # plt.ylabel("$COP$")
    # plt.grid()
    # plt.show()
    # fig.tight_layout()