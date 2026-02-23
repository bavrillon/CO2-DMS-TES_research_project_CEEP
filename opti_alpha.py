"""
This code is used to fing the optimal dedecated mechanical subcooling (DMS) share,
measured with the ratio alpha (dH_DMS/dH_CO2), for a given set of operating conditions,
in order to maximize the COP* of the system.
"""
import matplotlib.pyplot as plt
import numpy as np
from CONSTANTS import *
from cycles import *
from opti_Ph import optimize_Ph_supercritical_cycle_with_DMS

# ALPHA_UNCAPPED_MAX is used as the maximum alpha value when there is no upper bound on alpha,
# but it is also the maximum alpha value explored when looking for the optimal alpha 
# in both capped and uncapped cases. Thus, the polynomial regression is always performed on 
# the same alpha range [0, ALPHA_UNCAPPED_MAX].

def compute_COP_star(T_ev, T_gc_out, P_h, T_amb_air, alpha):
    """
    Compute COP* at fixed (T_gc_out, Ph, alpha)
    """
    system = ComplexSystem('CarbonDioxide',
                                  T_ev,
                                  P_h,
                                  T_gc_out=T_gc_out,
                                  T_amb_air=T_amb_air,
                                  alpha=alpha)
    COP_star = system.get_COP()
    return COP_star

def get_alpha_opt_given_Ph_values(T_ev, T_gc_out, T_amb_air, alpha_values, alpha_max, Ph_opt_values, regression_degree=COP_VS_ALPHA_REGRESSION_DEGREE, plot=False, save_path=None):
    """Find the optimal alpha that maximizes COP*, using a regression over a set of alpha values.
    alpha_values: array of alpha values to explore
    alpha_max: maximum alpha value allowed (for capping)
    Ph_opt_values: array of P_h values corresponding to each alpha value (to compute the corresponding cycle)
    """
    COP_star_values = []
    alpha_real_values = []
    for i, alpha in enumerate(alpha_values):
        P_h = Ph_opt_values[i]
        try:
            COP_star = compute_COP_star(T_ev, T_gc_out, P_h, T_amb_air, alpha)
        except Exception:
            break  # Stop the exploration: higher alpha values are not feasible
        COP_star_values.append(COP_star)
        alpha_real_values.append(alpha)

    # Use only the successfully computed alpha values
    alpha_values = np.array(alpha_real_values)
    upper_alpha = alpha_values[-1]

    # Polynomial regression
    coefficients = np.polyfit(alpha_values, COP_star_values, regression_degree)
    poly_func = np.poly1d(coefficients)

    # Find optimal alpha
    derivative = np.polyder(poly_func)
    critical_points = np.roots(derivative)
    real_critical_points = critical_points[np.isreal(critical_points)].real
    in_interval = [p for p in real_critical_points if 0 <= p <= min(upper_alpha, alpha_max)]
    if len(in_interval) == 0:
        points_to_check = np.array([0, min(upper_alpha, alpha_max)])
    else:
        points_to_check = np.concatenate([np.array([0, min(upper_alpha, alpha_max)]), in_interval])
    values_to_check = poly_func(points_to_check)
    max_idx = np.argmax(values_to_check)
    alpha_opt = points_to_check[max_idx]
    COP_max = values_to_check[max_idx]      # Not necessarily equal to COP*(alpha_opt) due to regression

    if plot or (save_path is not None):
        alpha_smooth = np.linspace(0, upper_alpha, 200)
        COP_smooth = poly_func(alpha_smooth)

        plt.figure(figsize=(8, 5))
        plt.plot(alpha_smooth, COP_smooth, label=f'Polynomial regression (degree {regression_degree})', color='blue')
        plt.scatter(alpha_values, COP_star_values, color='red', label='Computed COP*', zorder=5)
        plt.scatter(alpha_opt, COP_max, color='green', s=100, label='Optimal alpha', zorder=6)
        plt.xlabel('alpha (dh_DMS/dh_CO2)')
        plt.ylabel('COP*')
        plt.title(f'COP* vs alpha at T_gc_out = {T_gc_out - 273.15:.2f} °C')
        plt.legend()
        plt.grid(True)
        if (save_path is not None):
            plt.savefig(os.path.join(save_path, f"COP_vs_alpha_Tgcout={T_gc_out - 273.15:.2f}.png"))
        if plot:
            plt.show()
    
    return alpha_opt
    
def get_alpha_opt_subcritical(T_ev, T_gc_out, T_amb_air, Ph, is_alpha_capped=True, alpha_step=ALPHA_STEP, regression_degree=COP_VS_ALPHA_REGRESSION_DEGREE, plot=False, save_path=None):
    """At fixed T_gc_out, which imposes P_h in a subcritical cycle, find the optimal alpha that maximizes COP*, 
    using a regression over a set of alpha values."""
    if is_alpha_capped:
        alpha_max = ALPHA_CAPPED_MAX
    else:
        alpha_max = ALPHA_UNCAPPED_MAX
    
    alpha_values = np.arange(0, ALPHA_UNCAPPED_MAX, alpha_step)
    Ph_values = np.ones(len(alpha_values)) * Ph

    alpha_opt = get_alpha_opt_given_Ph_values(
        T_ev,
        T_gc_out,
        T_amb_air,
        alpha_values,
        alpha_max,
        Ph_values,
        regression_degree=regression_degree,
        plot=plot,
        save_path=save_path)
    
    return alpha_opt

def get_alpha_opt_supercritical(T_ev, T_gc_out, T_amb_air, Ph_opt_correlation=False, is_alpha_capped=True, alpha_step=ALPHA_STEP, regression_degree=COP_VS_ALPHA_REGRESSION_DEGREE, plot=False, save_path=None):
    """At fixed T_gc_out, calculate P_h_opt in a supercritical cycle, that maximizes COP* for each alpha of a set. It gives a set of (alpha, COP*) values.
    Then find the optimal alpha that maximizes COP*, using a regression over the set of alpha values.
    Ph_opt_correlation: if not None, a fonction which provides P_h_opt for a given T_amb."""
    COP_star_values = []
    if is_alpha_capped:
        alpha_max = ALPHA_CAPPED_MAX
    else:
        alpha_max = ALPHA_UNCAPPED_MAX
    alpha_values = np.arange(0, ALPHA_UNCAPPED_MAX, alpha_step)

    if Ph_opt_correlation is not None:
        Ph_opt_value = Ph_opt_correlation(T_amb_air)
        Ph_opt_values = [Ph_opt_value] * len(alpha_values)
    else:
        Ph_opt_values = []
        for alpha in alpha_values:
            P_h_opt, COP_opt = optimize_Ph_supercritical_cycle_with_DMS(T_ev, T_gc_out, T_amb_air, alpha=alpha)
            Ph_opt_values.append(P_h_opt)
            COP_star_values.append(COP_opt)

    alpha_opt = get_alpha_opt_given_Ph_values(
        T_ev,
        T_gc_out,
        T_amb_air,
        alpha_values,
        alpha_max,
        Ph_opt_values,
        regression_degree=regression_degree,
        plot=plot,
        save_path=save_path)
    
    return alpha_opt