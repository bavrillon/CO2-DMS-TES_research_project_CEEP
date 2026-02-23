import datetime as dt
import pandas as pd
from OMIEData.DataImport.omie_marginalprice_importer import OMIEMarginalPriceFileImporter
from OMIEData.Enums.all_enums import DataTypeInMarginalPriceFile

# 1. Define the download period for ALL of 2024
date_ini = dt.datetime(2024, 1, 1)
date_end = dt.datetime(2024, 12, 31)

# 2. Automatically download all .1 files for 2024
print("Starting data download for 2024... This may take several minutes.")
downloader = OMIEMarginalPriceFileImporter(date_ini=date_ini, date_end=date_end)
df_complet = downloader.read_to_dataframe(verbose=True)

print(f"Download completed. {len(df_complet)} lines of raw data imported.")

# 3. Filter to get only Spain prices (not Portugal)
str_price_spain = str(DataTypeInMarginalPriceFile.PRICE_SPAIN)
df_spain = df_complet[df_complet['CONCEPT'] == str_price_spain].copy()

# 4. Convert DATE column to datetime and remove empty H25 column
df_spain['DATE'] = pd.to_datetime(df_spain['DATE'])
df_spain = df_spain.drop(columns=['H25'])  # Removes empty H25 column

# 5. Pivot table: from 24 columns (H1..H24) to 1 column 'Hour' and 1 column 'Price'
#    Note: Columns are H1 to H24 (without zero), convert them to hours 0-23
df_long = df_spain.melt(id_vars=['DATE', 'CONCEPT'],  # Keep CONCEPT temporarily
                         value_vars=[f'H{h}' for h in range(1, 25)],  # H1 to H24
                         var_name='Hour',
                         value_name='Price')

# Convert 'H1' to 0, 'H2' to 1, etc. to get hours 0-23
df_long['Hour'] = df_long['Hour'].str[1:].astype(int) - 1

# Create complete datetime column (Date + Hour)
df_long['DateTime'] = df_long['DATE'] + pd.to_timedelta(df_long['Hour'], unit='h')

# Sort by date and hour
df_long = df_long.sort_values('DateTime').reset_index(drop=True)

# Remove temporary columns
df_long = df_long.drop(columns=['CONCEPT'])

# 6. Create final table per specification: days in rows, hours (00 to 23) in columns
df_final = df_long.pivot_table(index='DATE', columns='Hour', values='Price')

# Rename columns to have "HH:00" format (ex: 00:00, 01:00, etc.)
df_final.columns = [f'{h:02d}:00' for h in range(24)]
df_final.index.name = 'Date'

# 7. Save as CSV (days × hours)
output_filename = 'Gross_prices_2024.csv'
df_final.to_csv(output_filename, float_format='%.3f')  # 3 decimals

print(f"\nProcessing completed successfully")
print(f"File created: {output_filename}")
print(f"Dimensions: {df_final.shape[0]} days × {df_final.shape[1]} hours.")
print(f"Date range: {df_final.index.min()} to {df_final.index.max()}")