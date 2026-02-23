
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import os

os.chdir(os.path.dirname(__file__))
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
grandparent_dir = os.path.dirname(parent_dir)

HOURLY_T_OVER_2024_PATH = "hourly_T_2024_Madrid.csv"
CLUSTERING_CSV_PATH = "day_type_clustering.csv"
HOURLY_AVG_T_CLUSTERED_CSV_PATH = os.path.join(parent_dir, "outputs_external_time_series", "hourly_avg_T_clustered.csv")
HOURLY_Q_LOAD_CLUSTERED_CSV_PATH = os.path.join(parent_dir, "outputs_external_time_series", "hourly_Qload_clustered.csv")
PLOTS_DIR = os.path.join(grandparent_dir, "explicative_plots", "clustered_external_time_series")


def get_df_hourly_T_over_2024(save_path=None, verbose=True):
    """
    Retrieves the hourly 2m temperatures in Madrid for 2024, 
    pivots (index=date, columns=H00..H23) and returns the DataFrame. 
    If save_path is provided, saves the CSV file to that location (UTF-8, two decimal places).
    """
    import openmeteo_requests
    import requests_cache
    from retry_requests import retry

    cache_session = requests_cache.CachedSession(".cache", expire_after=-1)
    retry_session = retry(cache_session, retries=5, backoff_factor=0.2)
    client = openmeteo_requests.Client(session=retry_session)

    url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": 40.416775,
        "longitude": -3.703790,
        "start_date": "2024-01-01",
        "end_date": "2024-12-31",
        "hourly": "temperature_2m",
    }
    responses = client.weather_api(url, params=params)
    response = responses[0]

    if verbose:
        print(f"Coordinates {response.Latitude()}°N {response.Longitude()}°E")
        print(f"Elevation {response.Elevation()} m asl")
        print(f"Timezone {response.Timezone()} {response.TimezoneAbbreviation()}")
        print(f"Timezone difference to GMT+0 {response.UtcOffsetSeconds()} s")

    hourly = response.Hourly()
    hourly_temperature_2m = hourly.Variables(0).ValuesAsNumpy()

    hourly_data = {
        "date": pd.date_range(
            start=pd.to_datetime(hourly.Time(), unit="s", utc=True),
            end=pd.to_datetime(hourly.TimeEnd(), unit="s", utc=True),
            freq=pd.Timedelta(seconds=hourly.Interval()),
            inclusive="left",
        ),
        "temperature_2m": hourly_temperature_2m,
    }

    hourly_df = pd.DataFrame(hourly_data)
    dt_format = "%Y-%m-%d %H:%M:%S:%f"
    hourly_df["Datetime"] = pd.to_datetime(hourly_df["date"], format=dt_format)
    hourly_df = hourly_df.set_index(pd.DatetimeIndex(hourly_df["Datetime"]))
    hourly_df = hourly_df.drop(["date", "Datetime"], axis=1).astype(
        {"temperature_2m": "float"}
    )

    hourly_df["date"] = hourly_df.index.date
    hourly_df["hour"] = hourly_df.index.hour

    pivoted_hourly_df = hourly_df.pivot_table(
        index="date", columns="hour", values="temperature_2m"
    )
    pivoted_hourly_df.columns = [
        f"H{str(h).zfill(2)}" for h in pivoted_hourly_df.columns
    ]

    if save_path is not None:
        pivoted_hourly_df.to_csv(
            save_path,
            float_format="%.2f",
            index=True,
            index_label="Date",
            encoding="utf-8",
        )
        print(f"Hourly temperature data for 2024 saved to {save_path}")

    return pivoted_hourly_df

def cluster_and_export_temperatures(df, output_classification_csv=None, output_hourly_avg_csv=None):
    """
    Performs k-means clustering on 366 days based on hourly temperature profiles (24 dimensions).
    This minimizes intra-cluster variance of hourly profiles, not just daily means.
    """
    from sklearn.cluster import KMeans
    
    # K-means clustering on full hourly profiles (366 days × 24 hours)
    kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
    cluster_labels = kmeans.fit_predict(df.values)  # Use the 24 hourly temps as features
    
    # Assign cluster names based on mean temperature of clusters
    daily_mean_temp = df.mean(axis=1)
    cluster_mean_temps = []
    for i in range(3):
        cluster_mean_temps.append(daily_mean_temp[cluster_labels == i].mean())
    
    cluster_order = {
        np.argsort(cluster_mean_temps)[0]: "Low",
        np.argsort(cluster_mean_temps)[1]: "Medium",
        np.argsort(cluster_mean_temps)[2]: "High"
    }
        
    # Map cluster indices to names
    day_types = [cluster_order[label] for label in cluster_labels]
    
    # Find worst day (highest daily mean temperature)
    worst_day_idx = daily_mean_temp.idxmax()
    worst_day_type = "Worst_day"
    print(f"Worst day identified: {worst_day_idx} with mean temperature {daily_mean_temp.max():.2f}°C")

    classification_df = pd.DataFrame({
        "day_type": day_types
    }, index=df.index)

    # Overwrite worst day classification
    classification_df.loc[worst_day_idx, "day_type"] = worst_day_type

    # Export classification
    if output_classification_csv is not None:
        classification_df.to_csv(output_classification_csv, index=True, index_label="Date")
        print(f"Classification exported to {output_classification_csv}")
    
    # Compute hourly mean temperature by day type
    hourly_by_type = {}
    
    for day_type in ["Low", "Medium", "High"]:
        mask = (classification_df["day_type"] == day_type)
        type_df = df[mask]
        if len(type_df) > 0:
            hourly_by_type[day_type] = type_df.mean(axis=0)
        else:
            hourly_by_type[day_type] = pd.Series([0] * 24)
    
    # Add worst day hourly temperatures
    hourly_by_type["Worst_day"] = df.loc[worst_day_idx]
    
    # Create output DataFrame with hour as first column
    hour_index = list(range(24))
    output_data = {
        "hour": hour_index,
        "Low": [hourly_by_type["Low"].iloc[h] for h in hour_index],
        "Medium": [hourly_by_type["Medium"].iloc[h] for h in hour_index],
        "High": [hourly_by_type["High"].iloc[h] for h in hour_index],
        "Worst_day": [hourly_by_type["Worst_day"].iloc[h] for h in hour_index]
    }
    
    hourly_avg_df = pd.DataFrame(output_data)
    
    # Export hourly averages
    if output_hourly_avg_csv is not None:
        hourly_avg_df.to_csv(output_hourly_avg_csv, index=False)
        print(f"Hourly temperature averages exported to {output_hourly_avg_csv}")
    
    return classification_df, hourly_avg_df

def plot_clustering_summary(classification_df, hourly_T_df, save_path=None):
    """
    Creates a comprehensive figure showing:
    - Distribution of days by type (pie chart)
    - Daily mean temperature statistics by type (box plot)
    - Distribution of daily mean temperatures (histogram)
    Statistics are printed to the terminal.
    """
    daily_mean_temp = hourly_T_df.mean(axis=1)
    classification_with_temps = classification_df.copy()
    classification_with_temps['daily_mean_temp'] = daily_mean_temp.values
    
    fig, axes = plt.subplots(3, 1, figsize=(6, 10))
    # fig.suptitle('Clustering analysis - summary using average daily temperatures', fontsize=16, fontweight='bold')
    
    # 1. Hourly temperature profiles by day type
    day_type_counts = classification_df['day_type'].value_counts()
    colors_map = {'Low': 'darkturquoise', 'Medium': 'goldenrod', 'High': 'coral', 'Worst_day': 'red'}
    pct_colors_map = {'Low': 'teal', 'Medium': 'darkgoldenrod', 'High': 'firebrick'}

    for day_type in ['Low', 'Medium', 'High', 'Worst_day']:
        axes[2].plot(
            hourly_avg_df['hour'],
            hourly_avg_df[day_type],
            label=day_type,
            color=colors_map[day_type],
            linewidth=2.0
        )
    axes[2].set_xlabel('Hour of Day', fontweight='bold', fontsize=10)
    axes[2].set_ylabel('Temperature (°C)', fontweight='bold', fontsize=10)
    axes[2].set_title('Hourly Temperature Profiles by Day Type', fontweight='bold')
    axes[2].grid(True, alpha=0.3, linestyle='--')
    axes[2].legend(fontsize=8, loc='best')
    axes[2].set_xticks(range(0, 24, 2))
    
    # 2. Box plot: Temperature statistics by type
    data_for_box = [classification_with_temps[classification_with_temps['day_type'] == dtype]['daily_mean_temp'].values 
                    for dtype in ['Low', 'Medium', 'High']]
    bp = axes[1].boxplot(data_for_box, labels=['Low', 'Medium', 'High'], patch_artist=True,
                         medianprops=dict(color='black', linewidth=2.5))
    for patch, dtype in zip(bp['boxes'], ['Low', 'Medium', 'High']):
        patch.set_facecolor(colors_map[dtype])
    axes[1].set_ylabel('Daily Mean Temperature (°C)', fontweight='bold')
    axes[1].set_title('Temperature Distribution by Type', fontweight='bold')
    axes[1].grid(axis='y', alpha=0.3)
    
    # 3. Histogram: Daily mean temperatures
    group_total = day_type_counts[['Low', 'Medium', 'High']].sum()
    pct_by_type = {
        'Low': day_type_counts['Low'] / group_total * 100,
        'Medium': day_type_counts['Medium'] / group_total * 100,
        'High': day_type_counts['High'] / group_total * 100
    }

    for dtype in ['Low', 'Medium', 'High']:
        temps = classification_with_temps[classification_with_temps['day_type'] == dtype]['daily_mean_temp']
        axes[0].hist(temps, alpha=0.5, label=dtype, color=colors_map[dtype], bins=10)
        
        # Calculate mean and std for annotation
        mean_temp = temps.mean()
        std_temp = temps.std()
        
        # Add text annotations in the histogram area
        y_pos = axes[0].get_ylim()[0] + (axes[0].get_ylim()[1] - axes[0].get_ylim()[0]) * 0.1
        axes[0].text(mean_temp, y_pos, 
                    f'μ={mean_temp:.2f}°C\nσ={std_temp:.2f}°C',
                    bbox=dict(boxstyle='round', facecolor=colors_map[dtype], alpha=0.7),
                    ha='center', va='bottom', fontsize=9, fontweight='bold', color='white')
        y_pos_pct = axes[0].get_ylim()[0] + (axes[0].get_ylim()[1] - axes[0].get_ylim()[0]) * 0.85
        axes[0].text(
            mean_temp,
            y_pos_pct,
            f"{pct_by_type[dtype]:.1f}%",
            ha='center',
            va='center',
            fontsize=10,
            fontweight='bold',
            color=pct_colors_map[dtype]
        )
    
    axes[0].set_xlabel('Daily Mean Temperature (°C)', fontweight='bold')
    axes[0].set_ylabel('Frequency', fontweight='bold')
    axes[0].set_title('Histogram of Daily Mean Temperatures', fontweight='bold')
    # axes[0].legend()
    axes[0].grid(axis='y', alpha=0.3)
    
    # Print statistics to terminal
    print("\n" + "="*60)
    print("Temperature Statistics by Type (°C)")
    print("="*60)
    for dtype in ['Low', 'Medium', 'High']:
        subset = classification_with_temps[classification_with_temps['day_type'] == dtype]['daily_mean_temp']
        print(f"\n{dtype}:")
        print(f"  Count:      {len(subset)}")
        print(f"  Mean:       {subset.mean():.2f}°C")
        print(f"  Median:     {subset.median():.2f}°C")
        print(f"  Std Dev:    {subset.std():.2f}°C")
        print(f"  Min:        {subset.min():.2f}°C")
        print(f"  Max:        {subset.max():.2f}°C")
    
    worst_day_temp = classification_with_temps[classification_with_temps['day_type'] == 'Worst_day']['daily_mean_temp'].values[0]
    print(f"\nWorst_day:")
    print(f"  Temperature: {worst_day_temp:.2f}°C")
    print("="*60 + "\n")
    
    plt.tight_layout(h_pad=2.0)
    
    if save_path is not None:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {save_path}")
    
    plt.show()

def plot_hourly_temperature_profiles(hourly_avg_df, save_path=None):
    """
    Plots hourly temperature profiles for all four day types:
    - Low, Medium, High, and Worst_day
    Shows how temperature varies throughout the day for each category.
    """
    colors_map = {'Low': 'darkturquoise', 'Medium': 'goldenrod', 'High': 'coral', 'Worst_day': 'red'}
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    for day_type in ['Low', 'Medium', 'High', 'Worst_day']:
        ax.plot(hourly_avg_df['hour'], hourly_avg_df[day_type], 
               label=day_type, color=colors_map[day_type], 
               linewidth=2.5)
    
    ax.set_xlabel('Hour of Day', fontweight='bold', fontsize=12)
    ax.set_ylabel('Temperature (°C)', fontweight='bold', fontsize=12)
    ax.set_title('Hourly Temperature Profiles by Day Type', fontweight='bold', fontsize=14)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=11, loc='best')
    ax.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    
    if save_path is not None:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {save_path}")
    
    plt.show()

def plot_temperature_variance_by_type(hourly_T_df, classification_df, save_path=None):
    """
    Plots hourly temperature variance (standard deviation) within each day type.
    Shows consistency/variability of each category.
    """
    colors_map = {'Low': 'darkturquoise', 'Medium': 'goldenrod', 'High': 'coral'}
    
    fig, ax = plt.subplots(figsize=(12, 7))
    
    for day_type in ['Low', 'Medium', 'High']:
        mask = (classification_df['day_type'] == day_type)
        subset = hourly_T_df[mask]
        std_by_hour = subset.std(axis=0)
        
        ax.plot(range(24), std_by_hour, label=f'{day_type} (n={mask.sum()})',
               color=colors_map[day_type], linewidth=2.5)
    
    ax.set_xlabel('Hour of Day', fontweight='bold', fontsize=12)
    ax.set_ylabel('Standard Deviation (°C)', fontweight='bold', fontsize=12)
    ax.set_title('Hourly Temperature Variability by Day Type', fontweight='bold', fontsize=14)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(fontsize=11, loc='best')
    ax.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    
    if save_path is not None:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {save_path}")
    
    plt.show()

def plot_daily_temperature_evolution(hourly_T_df, classification_df, save_path=None):
    """
    Plots the daily mean temperature evolution throughout the year,
    colored by day type. Shows when each type occurs.
    """
    daily_mean = hourly_T_df.mean(axis=1)
    colors_map = {'Low': 'darkturquoise', 'Medium': 'goldenrod', 'High': 'coral', 'Worst_day': 'red'}
    
    fig, ax = plt.subplots(figsize=(14, 6))
    
    # Plot background line
    ax.plot(daily_mean.index, daily_mean.values, color='lightgray', alpha=0.5, linewidth=1)
    
    # Color points by day type
    for day_type in ['Low', 'Medium', 'High', 'Worst_day']:
        mask = (classification_df['day_type'] == day_type)
        indices = mask.values.nonzero()[0]
        dates = daily_mean.index[indices]
        temps = daily_mean.values[indices]
        ax.scatter(dates, temps, label=day_type, color=colors_map[day_type], s=30, alpha=0.7)
    
    ax.set_xlabel('Date', fontweight='bold', fontsize=12)
    ax.set_ylabel('Daily Mean Temperature (°C)', fontweight='bold', fontsize=12)
    ax.set_title('Daily Temperature Evolution Through 2024', fontweight='bold', fontsize=14)
    ax.grid(True, alpha=0.3, linestyle='--')
    ax.legend(title='Day Types', fontsize=11, loc='best')
    
    # Rotate date labels for better readability
    plt.xticks(rotation=45, ha='right')
    
    plt.tight_layout()
    
    if save_path is not None:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {save_path}")
    
    plt.show()

def plot_clustering_summary_2(classification_df, hourly_avg_df, hourly_T_df, save_path=None):
    """
    Creates a comprehensive figure showing:
    - Distribution of days by type (pie chart)
    - Daily mean temperature statistics by type (box plot)
    - Distribution of daily mean temperatures (histogram)
    Statistics are printed to the terminal.
    """
    daily_mean_temp = hourly_T_df.mean(axis=1)
    classification_with_temps = classification_df.copy()
    classification_with_temps['daily_mean_temp'] = daily_mean_temp.values
    
    fig, axes = plt.subplots(3, 1, figsize=(6, 10))
    # fig.suptitle('Clustering analysis - summary using average daily temperatures', fontsize=16, fontweight='bold')
    
    # 1. Hourly temperature profiles by day type
    day_type_counts = classification_df['day_type'].value_counts()
    colors_map = {'Low': 'darkturquoise', 'Medium': 'goldenrod', 'High': 'coral', 'Worst_day': 'red'}
    pct_colors_map = {'Low': 'teal', 'Medium': 'darkgoldenrod', 'High': 'firebrick'}

    for day_type in ['Low', 'Medium', 'High', 'Worst_day']:
        axes[2].plot(
            hourly_avg_df['hour'],
            hourly_avg_df[day_type],
            label=day_type,
            color=colors_map[day_type],
            linewidth=2.0
        )
    axes[2].set_xlabel('Hour of Day', fontsize=10)
    axes[2].set_ylabel('Temperature (°C)', fontsize=10)
    axes[2].set_title('Hourly temperature profiles by day type', fontweight='bold')
    axes[2].grid(True, alpha=0.3, linestyle='--')
    axes[2].legend(fontsize=8, loc='best')
    axes[2].set_xticks(range(0, 24, 2))
    
    # 2. Box plot: Temperature statistics by type
    data_for_box = [classification_with_temps[classification_with_temps['day_type'] == dtype]['daily_mean_temp'].values 
                    for dtype in ['Low', 'Medium', 'High']]
    bp = axes[1].boxplot(data_for_box, labels=['Low', 'Medium', 'High'], patch_artist=True,
                         medianprops=dict(color='black', linewidth=2.5))
    for patch, dtype in zip(bp['boxes'], ['Low', 'Medium', 'High']):
        patch.set_facecolor(colors_map[dtype])
    axes[1].set_ylabel('Daily mean temperature (°C)')
    axes[1].set_title('Temperature distribution by day type', fontweight='bold')
    axes[1].grid(axis='y', alpha=0.3)
    
    # 3. Histogram: Daily mean temperatures
    group_total = day_type_counts[['Low', 'Medium', 'High']].sum()
    pct_by_type = {
        'Low': day_type_counts['Low'] / group_total * 100,
        'Medium': day_type_counts['Medium'] / group_total * 100,
        'High': day_type_counts['High'] / group_total * 100
    }

    for dtype in ['Low', 'Medium', 'High']:
        temps = classification_with_temps[classification_with_temps['day_type'] == dtype]['daily_mean_temp']
        axes[0].hist(temps, alpha=0.5, label=dtype, color=colors_map[dtype], bins=10)
        
        # Calculate mean and std for annotation
        mean_temp = temps.mean()
        std_temp = temps.std()
        
        # Add text annotations in the histogram area
        y_pos = axes[0].get_ylim()[0] + (axes[0].get_ylim()[1] - axes[0].get_ylim()[0]) * 0.1
        axes[0].text(mean_temp, y_pos, 
                    f'μ={mean_temp:.2f}°C\nσ={std_temp:.2f}°C',
                    bbox=dict(boxstyle='round', facecolor=colors_map[dtype], alpha=0.7),
                    ha='center', va='bottom', fontsize=9, fontweight='bold', color='white')
        y_pos_pct = axes[0].get_ylim()[0] + (axes[0].get_ylim()[1] - axes[0].get_ylim()[0]) * 0.85
        axes[0].text(
            mean_temp,
            y_pos_pct,
            f"{pct_by_type[dtype]:.1f}%",
            ha='center',
            va='center',
            fontsize=10,
            fontweight='bold',
            color=pct_colors_map[dtype]
        )
    
    axes[0].set_xlabel('Daily mean temperature (°C)')
    axes[0].set_ylabel('Frequency')
    axes[0].set_title('Histogram of daily mean temperatures', fontweight='bold')
    # axes[0].legend()
    axes[0].grid(axis='y', alpha=0.3)
    
    # Print statistics to terminal
    print("\n" + "="*60)
    print("Temperature Statistics by Type (°C)")
    print("="*60)
    for dtype in ['Low', 'Medium', 'High']:
        subset = classification_with_temps[classification_with_temps['day_type'] == dtype]['daily_mean_temp']
        print(f"\n{dtype}:")
        print(f"  Count:      {len(subset)}")
        print(f"  Mean:       {subset.mean():.2f}°C")
        print(f"  Median:     {subset.median():.2f}°C")
        print(f"  Std Dev:    {subset.std():.2f}°C")
        print(f"  Min:        {subset.min():.2f}°C")
        print(f"  Max:        {subset.max():.2f}°C")
    
    worst_day_temp = classification_with_temps[classification_with_temps['day_type'] == 'Worst_day']['daily_mean_temp'].values[0]
    print(f"\nWorst_day:")
    print(f"  Temperature: {worst_day_temp:.2f}°C")
    print("="*60 + "\n")
    
    plt.tight_layout(h_pad=2.0)
    
    if save_path is not None:
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        print(f"Plot saved to {save_path}")
    
    plt.show()


########################################## EXECUTION ZONE ##########################################

##### Save hourly temperature data for 2024 from Open-Meteo API
# hourly_T_over_2024_df = get_df_hourly_T_over_2024(save_path=HOURLY_T_OVER_2024_PATH)

hourly_T_over_2024_df = pd.read_csv(HOURLY_T_OVER_2024_PATH, parse_dates=["Date"], index_col="Date")

##### Perform clustering and save results
# cluster_and_export_temperatures(hourly_T_over_2024_df, 
#                                 output_classification_csv=CLUSTERING_CSV_PATH, 
#                                 output_hourly_avg_csv=HOURLY_AVG_T_CLUSTERED_CSV_PATH)
classification_df = pd.read_csv(CLUSTERING_CSV_PATH, parse_dates=["Date"], index_col="Date")
hourly_avg_clustered_df = pd.read_csv(HOURLY_AVG_T_CLUSTERED_CSV_PATH)

##### Generate plots
# plot_clustering_summary(classification_df, hourly_T_over_2024_df)
# plot_hourly_temperature_profiles(hourly_avg_clustered_df)
# plot_temperature_variance_by_type(hourly_T_over_2024_df, classification_df)
# plot_daily_temperature_evolution(hourly_T_over_2024_df, classification_df)
plot_clustering_summary_2(classification_df, hourly_avg_clustered_df, hourly_T_over_2024_df, save_path=None)
