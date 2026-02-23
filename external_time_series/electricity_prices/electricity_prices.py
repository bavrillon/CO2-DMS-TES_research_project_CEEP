"""
Electricity Price Processor
Converts wholesale electricity prices (€/MWh) to retail prices (€/kWh) by applying:
- Unit conversion from MWh to kWh
- Fixed supplier costs and margins
- Electricity tax (5.11%) and VAT (21%)
Input: Gross_prices_2024.csv (wholesale prices)
Output: Retail_prices_2024.csv (final retail prices)
"""
import pandas as pd

# Load wholesale price file (ex: days in rows, hours in columns)
df_wholesale = pd.read_csv('Gross_prices_2024.csv', index_col='Date')

# 1. Convert €/MWh to €/kWh
df_energy_eur_per_kwh = df_wholesale / 1000

# 2. Add fixed costs (supplier margin)
estimated_fixed_costs_per_kwh = 0.0165  # + 0.0165 €/kWh
df_subtotal = df_energy_eur_per_kwh + estimated_fixed_costs_per_kwh

# 3. Apply taxes (Electricity tax 5.11269632% + VAT 21%)
tax_multiplier = 1.0511269632 * 1.21
df_final_retail_price = df_subtotal * tax_multiplier

# 4. Save result
df_final_retail_price.to_csv('Retail_prices_2024.csv', float_format='%.4f')