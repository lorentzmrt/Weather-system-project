import pandas as pd

def extract_variables(block, names: list[str]) -> pd.DataFrame:
    """
    Generic helper: given an hourly or daily block and the list of
    requested parameter names, return a DataFrame with a 'date' column
    and one column per parameter.

    This works because the API returns Variables in the same order as
    the names list — so we zip them together to avoid positional indexing.
    """
    # Build the time axis from the block's metadata
    dates = pd.date_range(
        start     = pd.to_datetime(block.Time(),    unit="s", utc=True),
        end       = pd.to_datetime(block.TimeEnd(), unit="s", utc=True),
        freq      = pd.Timedelta(seconds=block.Interval()),
        inclusive = "left",
    )
    data = {"date": dates}

    # zip names and indices together — this is the key fix.
    # i is the position, name is the string from params["hourly"/"daily"]
    for i, name in enumerate(names):
        data[name] = block.Variables(i).ValuesAsNumpy()

    return pd.DataFrame(data)

def parse_opnemeteo_response(response, params:dict): # -> tuple(pd.DataFrame, pd.DataFrame):
	"""
	Safely parse an Open-Meteo API response into hourly and daily DataFrames.
	Uses parameter names as keys instead of fragile positional indices.

	Parameters
	----------
	response : Single Open-Meteo response object (from responses[0])
	params   : The same params dict you passed to the API call.
	           Must contain "hourly" and/or "daily" keys with parameter name lists.

	Returns
	-------
	(df_hourly, df_daily) : tuple of DataFrames.
	                        Either can be empty if not requested.
	"""
	df_hourly = pd.DataFrame()
	df_daily  = pd.DataFrame()

	if "hourly" in params:
	    df_hourly = extract_variables(response.Hourly(), params["hourly"])

	if "daily" in params:
	    df_daily = extract_variables(response.Daily(), params["daily"])

	return df_hourly, df_daily