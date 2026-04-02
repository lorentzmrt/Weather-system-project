# Import necessary libraries
import pandas as pd  # Data processing: https://pandas.pydata.org/docs/
import matplotlib.pyplot as plt  # Visualization: https://matplotlib.org/stable/contents.html
import seaborn as sns  # Also used for visualization: https://seaborn.pydata.org/

from meteoswiss/meteoswiss_data_import   import * 
from meteoswiss/meteoswiss_visualisation import * 


# Define file URLs
historical_url = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/hai/ogd-smn_hai_m.csv"
recent_url     = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/hai/ogd-smn_hai_m.csv"

# define the parameter we want to use
globrad_col    = "gre000m0" # global radiation 

# define time range we want to analyse
# for our example we want to compare the months september to december of the years 2023 and 2024
start_year    = 2023
end_year      = 2024

start_month   = 9
end_month     = 12

# download data
df_recent     = download_csv(recent_url)
print(f"downloading {recent_url}...")
df_historical = download_csv(historical_url)
print(f"downloading {historical_url}...")


# sanitize column names
print(f"sanitising data frame {df_recent}...")
df_recent     = sanitize_column_names(df_recent,     obj_col = globrad_col)
print(f"sanitising data frame {df_historical}...")
df_historical = sanitize_column_names(df_historical, obj_col = globrad_col)

# process data 
print("processing data...")
df            = process_data(df_recent, df_historical, 
							 obj_col     = globrad_col,
							 start_month = start_month, end_month = end_month,
							 start_year  = start_year,  end_year  = end_year)

# create histogram plot
print("creating histogram")
create_histogram(df)