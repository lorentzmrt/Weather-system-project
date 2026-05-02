import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry

from open_meteo_import import * 

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo     = openmeteo_requests.Client(session = retry_session)

# Make sure all required weather variables are listed here
# The order of variables in hourly or daily is important to assign them correctly below
url = "https://api.open-meteo.com/v1/forecast"
params = {
	"latitude"      : 51.7522,
	"longitude"     : -1.256,
	"daily"         : ["weather_code", "temperature_2m_max", "temperature_2m_min", 
					   "rain_sum",     "precipitation_sum"],
	"hourly"        : ["temperature_2m",  "relative_humidity_2m", "precipitation", 
					   "rain", "showers", "weather_code",         "cloud_cover", 
					   "direct_radiation", "diffuse_radiation", "temperature_20m"],
	"models"        : "ukmo_seamless",
	"forecast_hours": 24,
	"past_hours"    : 24,
}
print(f"downloading data from {url}")
responses = openmeteo.weather_api(url, params = params)
print("download completed")

# Process first location. Add a for-loop for multiple locations or weather models
response  = responses[0]

df_hourly, df_daily = parse_opnemeteo_response(response, params)

print(df_hourly.head())
print(df_daily.head())

#access columns by name:
print(df_hourly["temperature_2m"])
print(f"other keys: {df_hourly.keys()}")
