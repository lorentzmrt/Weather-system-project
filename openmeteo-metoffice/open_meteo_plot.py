import matplotlib.pyplot as plt
import seaborn
from datetime import datetime, date, time
import pandas as pd 
import numpy as np
from scipy import stats



def plot_temperature_and_precipitation(hourly_data: pd.DataFrame):

	precipitation = hourly_data["precipitation"]
	temperature   = hourly_data["temperature_2m"]
	t             = hourly_data["date"].dt.tz_localize(None) # strips timezone — actual values

	mask_cold     = temperature <= 10.0
	time_cold     = t.where(mask_cold)
	temp_cold     = temperature.where(mask_cold)
	time_warm     = t.where(~mask_cold)
	temp_warm     = temperature.where(~mask_cold)

	fig, ax1 = plt.subplots(figsize=(10, 4))

	# --- left axis: temperature as a line ---
	ax1.plot(time_warm, temp_warm, color="red")
	ax1.plot(time_cold, temp_cold, color="blue")
	ax1.set_ylabel("Temperature [°C]")

	# --- right axis: precipitation as bars ---
	ax2 = ax1.twinx()   # shares x with ax1, new y on the right
	ax2.bar(t, precipitation, width=1/24, color = "black", alpha = 0.5, bottom=None)
	ax2.set_ylabel("Precipitation [mm]")

	plt.show()

def plot_temperature_and_humidity(hourly_data: pd.DataFrame):

	humidity      = hourly_data["relative_humidity_2m"]
	temperature   = hourly_data["temperature_2m"]
	t             = hourly_data["date"].dt.tz_localize(None) # strips timezone — actual values

	mask_cold     = temperature <= 10.0
	time_cold     = t.where(mask_cold)
	temp_cold     = temperature.where(mask_cold)
	time_warm     = t.where(~mask_cold)
	temp_warm     = temperature.where(~mask_cold)

	fig, ax1 = plt.subplots(figsize=(10, 4))

	# --- left axis: temperature as a line ---
	ax1.plot(time_warm, temp_warm, color="red")
	ax1.plot(time_cold, temp_cold, color="blue")
	ax1.set_ylabel("Temperature [°C]")

	# --- right axis: precipitation as bars ---
	ax2 = ax1.twinx()   # shares x with ax1, new y on the right
	ax2.plot(t, humidity, color = "black")
	ax2.set_ylim(0, 100)
	ax2.set_ylabel("Relative humitdity 2m [%]")

	plt.show()


def plot_wind_and_solar_irradiation_correlation(hourly_data: pd.DataFrame):
	
	direct_radiation   = hourly_data["direct_radiation"]
	diffuse_radiation  = hourly_data["diffuse_radiation"]
	wind               = hourly_data["wind_speed_10m"]
	daylight           = hourly_data["is_day"]

	# boolean indexing approach — actually removes the rows entirely
	mask               = daylight == 1
	day_rad            = direct_radiation[mask]
	day_wind           = wind[mask]

	time               = hourly_data["date"].dt.tz_localize(None)[mask]
	# extract just the hour (0-23) from each timestamp
	hour               = time.dt.hour   

	fig, ax = plt.subplots(figsize=(10, 4))
	ax.scatter(day_rad, day_wind, c=hour, cmap="plasma", alpha=0.6)
	# color dots as function of the hour of the day
	plt.colorbar(ax.collections[0], ax=ax, label="Hour of day")
	ax.set_ylabel("Wind speed 10 m [km/h]")
	ax.set_xlabel("Direct solar irradiation [W/m$^2$]")

	# fit a straight line (linear regression) to the data
	slope, intercept, r_value, p_value, std_err = stats.linregress(day_rad, day_wind)
	r_squared = r_value ** 2

	# only plot the correlation if actually at least weakly present
	if r_squared > 0.3:
		x_line    = np.linspace(day_rad.min(), day_rad.max(), 100)
		ax.plot(x_line, x_line*slope + intercept, color="red", linewidth=1.5,
				linestyle = '--', label=f"R$^2$ = {'%.3f'%r_squared}")
		ax.legend()

	plt.show()


def plot_solar_irradiation_and_cloud_coverage_correlation(hourly_data: pd.DataFrame):
	
	direct_radiation   = hourly_data["direct_radiation"]
	diffuse_radiation  = hourly_data["diffuse_radiation"]
	cloud_coverage     = hourly_data["cloud_cover"]
	daylight           = hourly_data["is_day"]

	# boolean indexing approach — actually removes the rows entirely
	mask               = daylight == 1
	day_rad            = direct_radiation[mask]
	day_cloud          = cloud_coverage[mask]

	time               = hourly_data["date"].dt.tz_localize(None)[mask]
	# extract just the hour (0-23) from each timestamp
	hour               = time.dt.hour   

	fig, ax = plt.subplots(figsize=(10, 4))
	ax.scatter(day_rad, day_cloud, c=hour, cmap="plasma", alpha=0.6)
	# color dots as function of the hour of the day
	plt.colorbar(ax.collections[0], ax=ax, label="Hour of day")
	ax.set_ylabel("Cloud coverage [%]")
	ax.set_xlabel("Direct solar irradiation [W/m$^2$]")

	# fit a straight line (linear regression) to the data
	slope, intercept, r_value, p_value, std_err = stats.linregress(day_rad, day_cloud)
	r_squared = r_value ** 2

	# only plot the correlation if actually at least weakly present
	if r_squared > 0.2:
		x_line    = np.linspace(day_rad.min(), day_rad.max(), 100)
		ax.plot(x_line, x_line*slope + intercept, color="red", linewidth=1.5,
				linestyle = '--', label=f"R$^2$ = {'%.3f'%r_squared}")
		ax.legend()

	plt.show()



