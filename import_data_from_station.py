# Import necessary libraries
import pandas as pd  # Data processing: https://pandas.pydata.org/docs/
import matplotlib.pyplot as plt  # Visualization: https://matplotlib.org/stable/contents.html
import seaborn as sns  # Also used for visualization: https://seaborn.pydata.org/
import os 

from meteoswiss.meteoswiss_data_import   import * 
from meteoswiss.meteoswiss_visualisation import * 

print(os.getcwd())

station     = "BER"
granularity = "10min"
print(f"Getting data frame for {station}, with granularity {granularity}...")
df = get_station_data(station, granularity=granularity)   # now, auto-cached

print(df.head(3))
print(df.columns)

# get metadata
df_metadata   = get_parameter_metadata()
print(df_metadata.columns)


# Find all precipitation parameters
query_str = "precipitation"
df_precipitation_en, short_name_query  = search_parameters(query_str, df_metadata)
print(df_precipitation_en.head())
print(f"short name {query_str}: {short_name_query}")

# Same search in Italian — finds the same rows
query_str2 = "precipitazioni"
df_precipitation_it, short_name_query2 = search_parameters(query_str2, df_metadata)
print(df_precipitation_it.head())
print(f"short name {query_str2}: {short_name_query2}")

# Only 10-min precipitation parameters
granularity_query = "hourly"
df_precipitation_en_hourly, short_name_query3 = search_parameters(query_str, df_metadata, granularity=granularity_query)
print(df_precipitation_en_hourly.head())
print(f"short name {query_str} and granularity {granularity_query}: {short_name_query3}")

#================================#

station_query     = "PUY"
granularity_query = "hourly"
period_query      = "recent"
print(f"Getting data frame for {station_query}, with granularity {granularity_query}, {period_query} period ...")
df = get_station_data(station_query,
				      granularity=granularity_query,
				      period     =period_query)
print(df.head(3))
print(df.columns)

parameter_query     = "precipitation"
matches, shortnames = search_parameters(parameter_query, df_metadata, granularity=granularity_query)
print(f"short name for {parameter_query} and {granularity_query} granularity : {shortnames}")


# If exactly one match, proceed automatically; otherwise warn
if len(shortnames) == 1:
    col = shortnames.iloc[0]
elif len(shortnames) > 1:
    print(f"Multiple matches — picking first. Consider a more specific query.")
    col = shortnames.iloc[0]
else:
    raise ValueError("No match found.")



df = plot_history(parameter   = "precipitation",
		          station     = "PUY",
		          granularity = "daily",
			      period      = "recent")



# Search by group keyword
search_parameters("radiation", df_metadata, granularity="hourly")





# Hourly temperature forecast for Pully
df_fcst = get_station_forecast("PUY", "tre200h0")

# Daily max temperature forecast for Zurich airport
df_fcst = get_station_forecast("ZRH", "tre200dx")

# Hourly precipitation with uncertainty band (10th/90th quantile)
df_mean = get_station_forecast("BER", "rre150h0")
df_p10  = get_station_forecast("BER", "rreq10h0")
df_p90  = get_station_forecast("BER", "rreq90h0")

# Browse available forecast points (stations, postal codes, mountain POIs)
points = get_forecast_points()
print(points[points["point_type_id"] == 1][["station_abbr", "point_name", "point_height_masl"]])

# Browse available forecast parameters
meta = get_forecast_metadata()
print(meta[["parameter_shortname", "parameter_description_en", "parameter_unit"]])




