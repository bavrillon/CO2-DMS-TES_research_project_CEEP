### File: system_model.mod ###

# Sets
set DAYS := {'Low', 'Medium', 'High', 'Worst_day'};
set HOURS := 0..23;

/*************************************************/
# PARAMETERS (mutable data)
/*************************************************/

param Q_dot_load{DAYS, HOURS} >= 0; # kW
param C_elec{DAYS, HOURS} >= 0; # €/kWh 
param alpha_2{DAYS, HOURS} >= 0; # (-)
param COP_CO2_1{DAYS, HOURS} >= 0; # (-)
param COP_CO2_2{DAYS, HOURS} >= 0; # (-)
param COP_DMS_CO2{DAYS, HOURS} >= 0; # (-)
param COP_DMS_TES{DAYS, HOURS} >= 0; # (-)
param delta_h_CO2_1{DAYS, HOURS} >= 0; # kJ/kg
param delta_h_CO2_2{DAYS, HOURS} >= 0; # kJ/kg
param beta_1_max{DAYS, HOURS} >= 0; # (-)
param beta_2_max{DAYS, HOURS} >= 0; # (-)

param Delta_T_w >= 0;  
param cp_w >= 0;  
param rho_w >= 0;  
param Delta_t >= 0; 

param weight_low >=0;
param weight_medium >=0;
param weight_high >=0;
param weight_worst_day >=0;

param c_CO2 >= 0; 
param c_DMS >= 0; 
param c_TES >= 0; 
param cte >= 0;
param rate_of_return >= 0;
param number_of_years >= 0;

param M_big >= 0; 

/*************************************************/
# BOUNDS
/*************************************************/
param lower_bounds_w_dot >= 0;
param upper_bounds_w_dot >= 0;
param lower_bounds_v_TES >= 0;
param upper_bounds_v_TES >= 0;
param bound_V_TES_abs_diff >= 0;

/*************************************************/
# DECISION VARIABLES
/*************************************************/
var Q_dot_CO2{DAYS, HOURS} >= 0; # kW
var W_dot_comp_CO2{DAYS, HOURS} >= 0; # kW
var Q_dot_DMS_CO2{DAYS, HOURS} >= 0; # kW
var W_dot_comp_DMS{DAYS, HOURS} >= 0; # kW
var Q_dot_TES_CO2{DAYS, HOURS} >= 0; # kW
var Q_dot_DMS_TES{DAYS, HOURS} >= 0; # kW
var M_dot_CO2{DAYS, HOURS} >= 0; # kg/s
var w_tot >= 0; # kWh

var M_dot_TES_charge{DAYS, HOURS} >= 0; # kg/s
var M_dot_TES_discharge{DAYS, HOURS} >= 0; # kg/s
var V_TES_hot{DAYS, HOURS} >= 0; # m3
var V_TES_cold{DAYS, HOURS} >= 0; # m3

var z_comp_CO2 >= lower_bounds_w_dot, <= upper_bounds_w_dot; # kW
var z_comp_DMS >= lower_bounds_w_dot, <= upper_bounds_w_dot; # kW
var v_TES >= 0, <= 0; # m3

var C_capex >= 0; # €
var C_opex >= 0; # €
var C_npv >= 0; # €
var C_total >= 0; # €

# Auxiliary variables
var b_excl1{DAYS, HOURS} binary;
var b_excl2{DAYS, HOURS} binary;
var b_charge{DAYS, HOURS} binary;           
var b_discharge{DAYS, HOURS} binary;
var b_mode{DAYS, HOURS} binary;
# b_mode: 0 = MODE 1 (DMS off) | 1 = MODE 2 (DMS on)

# Mode linearization
var Q_dot_CO2_1{DAYS, HOURS} >= 0; # kW
var Q_dot_CO2_2{DAYS, HOURS} >= 0; # kW
var Q_dot_DMS_CO2_opt{DAYS, HOURS} >= 0; # kW

/*************************************************/
# CONSTRAINTS
/*************************************************/

s.t. Capacity_comp_DMS{d in DAYS, h in HOURS}:
    W_dot_comp_DMS[d, h] <= z_comp_DMS;

s.t. Capacity_comp_CO2{d in DAYS, h in HOURS}:
    W_dot_comp_CO2[d, h] <= z_comp_CO2;

s.t. Capacity_TES_hot{d in DAYS, h in HOURS}:
    V_TES_hot[d, h] <= v_TES;

s.t. Capacity_TES_cold{d in DAYS, h in HOURS}:
    V_TES_cold[d, h] <= v_TES;

# TES volume continuity 
s.t. V_continuity_c1 {d in DAYS}:
    bound_V_TES_abs_diff >= V_TES_hot[d, 23] - V_TES_hot[d, 0];
s.t. V_continuity_c2 {d in DAYS}:
    bound_V_TES_abs_diff >= -(V_TES_hot[d, 23] - V_TES_hot[d, 0]);
s.t. V_continuity_c3 {d in DAYS}:
    bound_V_TES_abs_diff >= V_TES_cold[d, 23] - V_TES_cold[d, 0];
s.t. V_continuity_c4 {d in DAYS}:
    bound_V_TES_abs_diff >= -(V_TES_cold[d, 23] - V_TES_cold[d, 0]);

s.t. Cold_flux_balance{d in DAYS, h in HOURS}:
    Q_dot_load[d, h] = Q_dot_DMS_CO2[d, h] + Q_dot_TES_CO2[d, h] + Q_dot_CO2[d, h];

s.t. TES_CO2_flux{d in DAYS, h in HOURS}:
    Q_dot_TES_CO2[d, h] = cp_w * Delta_T_w * M_dot_TES_discharge[d, h];

s.t. DMS_TES_flux{d in DAYS, h in HOURS}:
    Q_dot_DMS_TES[d, h] = cp_w * Delta_T_w * M_dot_TES_charge[d, h];

# Exclusivity Q_dot_TES_CO2 * Q_dot_DMS_TES = 0
s.t. Exclusivity_charge_discharge_TES_1{d in DAYS, h in HOURS}:
    Q_dot_TES_CO2[d, h] <= M_big * (1 - b_excl1[d, h]);
s.t. Exclusivity_charge_discharge_TES_2{d in DAYS, h in HOURS}:
    Q_dot_DMS_TES[d, h] <= M_big * b_excl1[d, h];

# Exclusivity Q_dot_DMS_CO2 * Q_dot_DMS_TES = 0
s.t. Exclusivity_DMS_1{d in DAYS, h in HOURS}:
    Q_dot_DMS_CO2[d, h] <= M_big * (1 - b_excl2[d, h]);
s.t. Exclusivity_DMS_2{d in DAYS, h in HOURS}:
    Q_dot_DMS_TES[d, h] <= M_big * b_excl2[d, h];  

# Linearized max for M_dot_TES_charge during the day
s.t. M_dot_TES_charge_c1{d in DAYS, h in HOURS: h < 23}:
    M_dot_TES_charge[d, h] >= (rho_w/Delta_t) * (V_TES_hot[d, h+1] - V_TES_hot[d, h]);
s.t. M_dot_TES_charge_c2{d in DAYS, h in HOURS: h < 23}:
    M_dot_TES_charge[d, h] <= 0 + M_big * b_charge[d, h];
s.t. M_dot_TES_charge_c3{d in DAYS, h in HOURS: h < 23}:
    M_dot_TES_charge[d, h] <= (rho_w/Delta_t) * (V_TES_hot[d, h+1] - V_TES_hot[d, h]) + M_big * (1 - b_charge[d, h]);
s.t. M_dot_TES_charge_c4{d in DAYS, h in HOURS: h < 23}:
    M_dot_TES_charge[d, h] >= (rho_w/Delta_t) * (V_TES_cold[d, h] - V_TES_cold[d, h+1]);
s.t. M_dot_TES_charge_c5{d in DAYS, h in HOURS: h < 23}:
    M_dot_TES_charge[d, h] <= (rho_w/Delta_t) * (V_TES_cold[d, h] - V_TES_cold[d, h+1]) + M_big * (1 - b_charge[d, h]);

# Linearized max for M_dot_TES_charge between 2 days
s.t. M_dot_TES_charge_h23_c1{d in DAYS}:
    M_dot_TES_charge[d, 23] >= (rho_w/Delta_t) * (V_TES_hot[d, 0] - V_TES_hot[d, 23]);
s.t. M_dot_TES_charge_h23_c2{d in DAYS}:
    M_dot_TES_charge[d, 23] <= 0 + M_big * b_charge[d, 23];
s.t. M_dot_TES_charge_h23_c3{d in DAYS}:
    M_dot_TES_charge[d, 23] <= (rho_w/Delta_t) * (V_TES_hot[d, 0] - V_TES_hot[d, 23]) + M_big * (1 - b_charge[d, 23]);
s.t. M_dot_TES_charge_h23_c4{d in DAYS}:
    M_dot_TES_charge[d, 23] >= (rho_w/Delta_t) * (V_TES_cold[d, 23] - V_TES_cold[d, 0]);
s.t. M_dot_TES_charge_h23_c5{d in DAYS}:
    M_dot_TES_charge[d, 23] <= (rho_w/Delta_t) * (V_TES_cold[d, 23] - V_TES_cold[d, 0]) + M_big * (1 - b_charge[d, 23]);

# Linearized max for M_dot_TES_discharge during the day
s.t. M_dot_TES_discharge_c1{d in DAYS, h in HOURS: h < 23}:
    M_dot_TES_discharge[d, h] >= (rho_w/Delta_t) * (V_TES_hot[d, h] - V_TES_hot[d, h+1]);
s.t. M_dot_TES_discharge_c2{d in DAYS, h in HOURS: h < 23}:
    M_dot_TES_discharge[d, h] <= 0 + M_big * b_discharge[d, h];
s.t. M_dot_TES_discharge_c3{d in DAYS, h in HOURS: h < 23}:
    M_dot_TES_discharge[d, h] <= (rho_w/Delta_t) * (V_TES_hot[d, h] - V_TES_hot[d, h+1]) + M_big * (1 - b_discharge[d, h]);
s.t. M_dot_TES_discharge_c4{d in DAYS, h in HOURS: h < 23}:
    M_dot_TES_discharge[d, h] >= (rho_w/Delta_t) * (V_TES_cold[d, h+1] - V_TES_cold[d, h]);
s.t. M_dot_TES_discharge_c5{d in DAYS, h in HOURS: h < 23}:
    M_dot_TES_discharge[d, h] <= (rho_w/Delta_t) * (V_TES_cold[d, h+1] - V_TES_cold[d, h]) + M_big * (1 - b_discharge[d, h]);

# Linearized max for M_dot_TES_discharge between 2 days
s.t. M_dot_TES_discharge_h23_c1{d in DAYS}:
    M_dot_TES_discharge[d, 23] >= (rho_w/Delta_t) * (V_TES_hot[d, 23] - V_TES_hot[d, 0]);
s.t. M_dot_TES_discharge_h23_c2{d in DAYS}:
    M_dot_TES_discharge[d, 23] <= 0 + M_big * b_discharge[d, 23];
s.t. M_dot_TES_discharge_h23_c3{d in DAYS}:
    M_dot_TES_discharge[d, 23] <= (rho_w/Delta_t) * (V_TES_hot[d, 23] - V_TES_hot[d, 0]) + M_big * (1 - b_discharge[d, 23]);
s.t. M_dot_TES_discharge_h23_c4{d in DAYS}:
    M_dot_TES_discharge[d, 23] >= (rho_w/Delta_t) * (V_TES_cold[d, 0] - V_TES_cold[d, 23]);
s.t. M_dot_TES_discharge_h23_c5{d in DAYS}:
    M_dot_TES_discharge[d, 23] <= (rho_w/Delta_t) * (V_TES_cold[d, 0] - V_TES_cold[d, 23]) + M_big * (1 - b_discharge[d, 23]);

# Conditional constraints 
s.t. Mode_detection{d in DAYS, h in HOURS}:
    Q_dot_DMS_CO2[d, h] <= M_big * b_mode[d, h];

s.t. Q_CO2_decomposition{d in DAYS, h in HOURS}:
    Q_dot_CO2[d, h] = Q_dot_CO2_1[d, h] + Q_dot_CO2_2[d, h];
s.t. Q_CO2_standard_limit{d in DAYS, h in HOURS}:
    Q_dot_CO2_1[d, h] <= M_big * (1 - b_mode[d, h]);
s.t. Q_CO2_subcooled_limit{d in DAYS, h in HOURS}:
    Q_dot_CO2_2[d, h] <= M_big * b_mode[d, h];
s.t. Power_CO2_relation{d in DAYS, h in HOURS}:
    W_dot_comp_CO2[d, h] = (1 / COP_CO2_1[d, h]) * Q_dot_CO2_1[d, h] 
                         + (1 / COP_CO2_2[d, h]) * Q_dot_CO2_2[d, h];

s.t. CO2_mass_flux{d in DAYS, h in HOURS}:
    M_dot_CO2[d, h] = Q_dot_CO2_1[d, h] / delta_h_CO2_1[d, h]
                    + Q_dot_CO2_2[d, h] / delta_h_CO2_2[d, h];

s.t. Power_DMS_relation{d in DAYS, h in HOURS}:
    W_dot_comp_DMS[d, h] = (1 / COP_DMS_TES[d, h]) * Q_dot_DMS_TES[d, h] 
                         + (1 / COP_DMS_CO2[d, h]) * Q_dot_DMS_CO2[d, h];

s.t. Maximal_cooling_TES_M1{d in DAYS, h in HOURS}:
    Q_dot_TES_CO2[d, h] <= beta_1_max[d, h] * Q_dot_CO2[d, h] + M_big * b_mode[d, h];

s.t. Maximal_cooling_TES_M2{d in DAYS, h in HOURS}:
    Q_dot_TES_CO2[d, h] <= beta_2_max[d, h] * Q_dot_CO2[d, h] + M_big * (1 - b_mode[d, h]);

s.t. Optimal_DMS_share_c1{d in DAYS, h in HOURS}:
    Q_dot_DMS_CO2_opt[d, h] = alpha_2[d, h] * Q_dot_CO2[d, h];
s.t. Optimal_DMS_share_c2{d in DAYS, h in HOURS}:
    Q_dot_DMS_CO2[d, h] - Q_dot_DMS_CO2_opt[d, h] <= M_big * (1 - b_mode[d, h]);
s.t. Optimal_DMS_share_c3{d in DAYS, h in HOURS}:
    Q_dot_DMS_CO2[d, h] - Q_dot_DMS_CO2_opt[d, h] >= -M_big * (1 - b_mode[d, h]);

s.t. Total_electricity_consumption:
    w_tot = sum{d in DAYS, h in HOURS} ((W_dot_comp_DMS[d, h] + W_dot_comp_CO2[d, h]) * 
    (Delta_t / 3600) * (if d == 'Low' then weight_low
            else if d == 'Medium' then weight_medium
            else if d == 'High' then weight_high
            else weight_worst_day));

/*************************************************/
# OBJECTIVE FUNCTION
/*************************************************/

s.t. Cost_capex:
    C_capex = z_comp_DMS * c_DMS + z_comp_CO2 * c_CO2 + v_TES * c_TES + cte;

s.t. Cost_opex:
    C_opex = sum{d in DAYS, h in HOURS} (C_elec[d,h] * (W_dot_comp_DMS[d, h] + W_dot_comp_CO2[d, h]) * 
    (Delta_t / 3600) * (if d == 'Low' then weight_low
            else if d == 'Medium' then weight_medium
            else if d == 'High' then weight_high
            else weight_worst_day));

s.t. Cost_net_present_value:
    C_npv = sum{i in 1..number_of_years} (C_opex / ((1 + rate_of_return) ^ i));

s.t. Total_cost_definition:
    C_total = C_capex + C_npv;

minimize Global_cost: C_total;

