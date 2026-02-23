"""
This module contains different function related to the computation of the pinch in the condenser/gas-cooler for CO2 cycles. 
The approach is different for subcritical and transcritical cycles, as the third part shows that the pinch location is 
different in the two cases.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cycles import *
from CONSTANTS import *

##################################### T_AMB_MAX_SUBCRITICAL COMPUTATION #####################################

def find_T_amb_limit_for_subcritical_cycle(max_iter=300, T_tol=0.001, plot_T_profile=False) -> float:
    """Find the maximum ambient temperature (K) for which a subcritical cycle can achieve the required pinch.
    For this ambient temperature, the minimum T_gc_out to achieve the pinch target is T_CRIT."""
    T_amb_low = 273.15 + 23  # K
    T_amb_high = T_CRIT - PINCH_AIR  # K

    def f_0(T_amb: float) -> float:
        cycle = StandardCycle(
            fluid='CarbonDioxide',
            T_ev=T_EV,
            T_gc_out=T_CRIT,
            T_amb_air=T_amb)
        res = cycle.get_pinch_air() - PINCH_AIR
        return res
    res = bisect(f_0, T_amb_low, T_amb_high, xtol=T_tol, maxiter=max_iter, full_output=True)
    T_amb_limit = res[0]

    print(res[1])  # Print convergence message
   
    if plot_T_profile:
        # Plot the temperature profiles at the found T_gc_out
        final_cycle = StandardCycle(
            fluid='CarbonDioxide',
            T_ev=T_EV,
            T_gc_out=T_CRIT,
            T_amb_air=T_amb_limit
        )
        final_cycle.get_pinch_air(show=True)

    return T_amb_limit

# T_amb_limit = find_T_amb_limit_for_subcritical_cycle(plot_T_profile=False)
# print(f"Maximum T_amb for subcritical cycle with {PINCH_AIR} K pinch: {T_amb_limit - 273.15:.3f}°C")
#### ----> MAXIMUM T_amb for subcritical cycle with 5 K pinch = (25.398 +/- 0.001) °C ####

##################################### CO2 SUBCRITICAL CYCLES T_gc_min = f(T_amb) #####################################

def get_T_gc_out_min_subcritical(T_amb, max_iter=50, T_tol=0.05, required_pinch=PINCH_AIR, plot_T_profile=False) -> float:
    """Return the smallest T_gc_out (K) that meets the gas/condenser pinch target for subcritical cycles."""

    def evaluate_pinch(T_gc_out: float) -> float:
        cycle = StandardCycle(
            fluid='CarbonDioxide',
            T_ev=T_EV,
            T_gc_out=T_gc_out,
            T_amb_air=T_amb
        )
        return cycle.get_pinch_air()
    
    ### Hand-made dichotomous method
    # # Initial guess respects at least the required pinch on the air side
    # T_low = T_amb + required_pinch
    # pinch_low = evaluate_pinch(T_low)
    # if pinch_low >= required_pinch:
    #     if plot_T_profile:
    #         final_cycle = StandardCycle(
    #             fluid='CarbonDioxide',
    #             T_ev=T_EV,
    #             T_gc_out=T_low,
    #             T_amb_air=T_amb
    #         )
    #         final_cycle.get_pinch_air(show=True)
    #     return T_low, pinch_low

    # # Grow the upper bound until the pinch requirement is satisfied
    # step = 1.0  # K increment for the bracketing phase
    # T_high = T_low + step
    # pinch_high = evaluate_pinch(T_high)
    # grow_iter = 0
    # while pinch_high < required_pinch and grow_iter < max_iter:
    #     T_low, pinch_low = T_high, pinch_high
    #     T_high += step
    #     pinch_high = evaluate_pinch(T_high)
    #     grow_iter += 1

    # if pinch_high < required_pinch:
    #     raise RuntimeError("Unable to satisfy condenser pinch within search bounds")
    # else:
    #     pinch_mid = pinch_high
    #     T_mid = T_high

    # # Binary search within the bracket to refine the minimum T_gc_out
    # for _ in range(max_iter):
    #     if T_high - T_low <= T_tol:
    #         break
    #     T_mid = 0.5 * (T_low + T_high)
    #     pinch_mid = evaluate_pinch(T_mid)
    #     if pinch_mid >= required_pinch:
    #         T_high = T_mid
    #     else:
    #         T_low = T_mid
    
    ### Using a root-finding method from scipy
    T_low = T_amb + required_pinch
    T_high = T_CRIT
    if evaluate_pinch(T_low) >= required_pinch:
        T_mid = T_low
    else:
        T_mid = bisect(lambda T: evaluate_pinch(T) - required_pinch, T_low, T_high, xtol=T_tol, maxiter=max_iter)
    pinch_mid = evaluate_pinch(T_mid)
   
    if plot_T_profile:
        # Plot the temperature profiles at the found T_gc_out
        final_cycle = StandardCycle(
            fluid='CarbonDioxide',
            T_ev=T_EV,
            T_gc_out=T_mid,
            T_amb_air=T_amb
        )
        final_cycle.get_pinch_air(show=True)

    return T_mid, pinch_mid
  
T_amb_test_sub = 273.15 + 25.38
# T_gc_out_min, pinch_value = get_T_gc_out_min_subcritical(T_amb_test_sub, plot_T_profile=False)
# print(f"Minimum T_gc_out for T_amb = {T_amb_test_sub - 273.15:.2f}°C to achieve {PINCH_AIR} K pinch: {T_gc_out_min - 273.15:.2f}°C with pinch value: {pinch_value:.2f} K")

##################################### CO2 TRANSCRITICAL CYCLES T_gc_min = f(P_h) at fixed T_amb #####################################

def get_T_gc_out_min_transcritical(T_amb, P_h, max_iter=50, T_tol=0.05, required_pinch=PINCH_AIR, plot_T_profile=False) -> float:
    """Return the smallest T_gc_out  (K) that meets the gas/condenser pinch target for transcritical cycles."""
    
    if T_amb < T_AMB_MAX_SUBCRITICAL:
        raise ValueError("Transcritical cycle not possible for T_amb below maximum subcritical limit computed in the previous section.")

    def evaluate_pinch(T_gc_out: float) -> float:
        cycle = StandardCycle(
            fluid='CarbonDioxide',
            T_ev=T_EV,
            P_h=P_h,
            T_gc_out=T_gc_out,
            T_amb_air=T_amb
        )
        return cycle.get_pinch_air()

    # # Initial guess respects at least the required pinch on the air side
    # T_low = T_amb + required_pinch
    # pinch_low = evaluate_pinch(T_low)
    # if pinch_low >= required_pinch:
    #     if plot_T_profile:
    #         final_cycle = StandardCycle(
    #             fluid='CarbonDioxide',
    #             T_ev=T_EV,
    #             P_h=P_h,
    #             T_gc_out=T_low,
    #             T_amb_air=T_amb
    #         )
    #         final_cycle.get_pinch_air(show=True)
    #     return T_low, pinch_low

    # # Grow the upper bound until the pinch requirement is satisfied
    # step = 1.0  # K increment for the bracketing phase
    # T_high = T_low + step
    # pinch_high = evaluate_pinch(T_high)
    # grow_iter = 0
    # while pinch_high < required_pinch and grow_iter < max_iter:
    #     T_low, pinch_low = T_high, pinch_high
    #     T_high += step
    #     pinch_high = evaluate_pinch(T_high)
    #     grow_iter += 1

    # if pinch_high < required_pinch:
    #     raise RuntimeError("Unable to satisfy condenser pinch within search bounds")
    # else:
    #     pinch_mid = pinch_high
    #     T_mid = T_high

    # # Binary search within the bracket to refine the minimum T_gc_out
    # tol = 0.1  # K tolerance on T_gc_out
    # for _ in range(max_iter):
    #     if T_high - T_low <= tol:
    #         break
    #     T_mid = 0.5 * (T_low + T_high)
    #     pinch_mid = evaluate_pinch(T_mid)
    #     if pinch_mid >= required_pinch:
    #         T_high = T_mid
    #     else:
    #         T_low = T_mid
    
    ### Using a root-finding method from scipy
    T_low = T_amb + required_pinch
    T_high = T_amb + 3 * required_pinch
    pinch_low = evaluate_pinch(T_low)
    if pinch_low >= required_pinch:
        if plot_T_profile:
            final_cycle = StandardCycle(
                fluid='CarbonDioxide',
                T_ev=T_EV,
                P_h=P_h,
                T_gc_out=T_low,
                T_amb_air=T_amb)
            final_cycle.get_pinch_air(show=True)
        return T_low, pinch_low
    else:
        T_mid = bisect(lambda T: evaluate_pinch(T) - required_pinch, T_low, T_high, xtol=T_tol, maxiter=max_iter)
    pinch_mid = evaluate_pinch(T_mid)

    if plot_T_profile:
        # Plot the temperature profiles at the found T_gc_out
        final_cycle = StandardCycle(
            fluid='CarbonDioxide',
            T_ev=T_EV,
            P_h=P_h,
            T_gc_out=T_mid,
            T_amb_air=T_amb
        )
        final_cycle.get_pinch_air(show=True)

    return T_mid, pinch_mid

def T_gc_min_vs_P_h_transcritical(T_amb, P_h_values, plot=False):
    """Compute the minimum T_gc_out (K) for a range of P_h (Pa) at fixed T_amb (K)."""
    T_gc_out_mins = []
    pinch_values = []
    for P_h in P_h_values:
        T_gc_out_min, pinch_value = get_T_gc_out_min_transcritical(T_amb, P_h, plot=False)
        T_gc_out_mins.append(T_gc_out_min)
        pinch_values.append(pinch_value)
    if plot:
        plt.figure()
        plt.plot(np.array(P_h_values)/1e5, np.array(T_gc_out_mins) - 273.15, marker='o')
        plt.xlabel("High pressure P_h (bar)")
        plt.ylabel("Minimum T_gc_out (°C)")
        plt.title(f"Minimum T_gc_out vs P_h at T_amb = {T_amb - 273.15:.1f}°C for {PINCH_AIR} K pinch")
        plt.grid()
        plt.show()
    return np.array(T_gc_out_mins), np.array(pinch_values)

T_amb_test_super = 273.15 + 26.5
P_h_test_super = 75e5  # Pa
# T_gc_out_min, pinch_value = get_T_gc_out_min_transcritical(T_amb_test_super, P_h_test_super, plot_T_profile=True)
# print(f"Minimum T_gc_out for T_amb = {T_amb_test_super - 273.15:.2f}°C to achieve {PINCH_AIR} K pinch: {T_gc_out_min - 273.15:.2f}°C with pinch value: {pinch_value:.2f} K")


#### It seems that for transcritical cycles (T_amb > T_AMB_MAX_SUBCRITICAL), at fixed T_amb and regardless 
# of P_h, T_gc_out = (T_amb + PINCH_AIR) is sufficient to achieve the pinch target (ie pinch
# point at the outlet of the gas-cooler). Let's verify this: ###

P_MIN = P_CRIT + 1e5  # Pa
P_MAX = 110e5  # Pa
P_h_values = np.linspace(P_MIN, P_MAX, 10)
T_amb_supercritical_values = np.linspace(T_AMB_MAX_SUBCRITICAL + 0.1, 273.15 + 40, 10)

def pinch_vs_Tamb_and_Ph_transcritical(P_h_range, T_amb_range, plot=False):
    """Compute the condenser/gas-cooler pinch for transcritical cycles over grids of
    high pressures and ambient temperatures.

    Returns a numpy array of shape (len(T_amb_range), len(P_h_range)) with each
    entry equal to the pinch value for the corresponding (T_amb, P_h) pair.

    For each transcritical cycle, T_gc_out is set to T_amb + PINCH_AIR
    to evaluate whether the pinch target is met (as hypothesized).
    """
    # Ensure inputs are numpy arrays for consistent handling
    P_h_vals = np.array(P_h_range, dtype=float)
    T_amb_vals = np.array(T_amb_range, dtype=float)

    pinch_matrix = np.zeros((len(T_amb_vals), len(P_h_vals)))

    for i, T_amb in enumerate(T_amb_vals):
        for j, P_h in enumerate(P_h_vals):
            # Build cycle with outlet at ambient + required pinch
            cycle = StandardCycle(
                fluid='CarbonDioxide',
                T_ev=T_EV,
                P_h=P_h,
                T_gc_out=T_amb + PINCH_AIR,
                T_amb_air=T_amb
            )
            pinch_matrix[i, j] = cycle.get_pinch_air(show=False)

    if plot:
        plt.figure()
        for i, T_amb in enumerate(T_amb_vals):
            plt.plot(P_h_vals / 1e5, pinch_matrix[i, :], marker='o', label=f"T_amb = {T_amb - 273.15:.1f}°C")
        plt.xlabel("High pressure P_h (bar)")
        plt.ylabel("Pinch (K)")
        plt.title("Pinch vs P_h for transcritical cycles at various T_amb")
        plt.grid(True)
        plt.legend()
        plt.show()

    return pinch_matrix

# pinches = pinch_vs_Tamb_and_Ph_transcritical(P_h_values, T_amb_supercritical_values, plot=True)
# print("Pinch matrix (K):")
# print(pinches)
# print(f"Min pinch value in matrix: {np.min(pinches):.2f} K")

#### Conclusion: For transcritical cycles, setting T_gc_out = T_amb + PINCH_AIR
# is sufficient to achieve at least the required pinch, regardless of P_h.

