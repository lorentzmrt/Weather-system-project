# Import necessary libraries
import pandas as pd  # Data processing: https://pandas.pydata.org/docs/
import os.path
import pathlib
import requests
from   datetime import datetime, timezone

BASE_URL   = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn"
CACHE_DIR  = pathlib.Path(".meteoswiss_cache")

# Map a human-readable period to the MeteoSwiss "type" folder name
PERIOD_MAP = {
    "now":        "now",        # yesterday 12UTC → now, updated every 10min
    "recent":     "recent",     # 1 Jan this year → yesterday, updated daily
    "historical": "historical", # start of record → 31 Dec last year, updated yearly
}

# Map a human-readable granularity to the MeteoSwiss single-letter code
GRANULARITY_MAP = {
    "10min":   "t",
    "hourly":  "h",
    "daily":   "d",
    "monthly": "m",
    "yearly":  "y",
}


METADATA_URL = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/ogd-smn_meta_parameters.csv"

def get_parameter_metadata(use_cache: bool = True) -> pd.DataFrame | None:
    """
    Load the MeteoSwiss SMN parameter metadata as a DataFrame.
    Uses the same ETag-based caching as station data.

    Columns returned:
        parameter_shortname        ← the identifier used in station CSVs (e.g. 'tre200s0')
        parameter_description_en   ← human-readable English description
        parameter_group_en         ← group (Temperature, Wind, Radiation, ...)
        parameter_granularity      ← T / H / D / M / Y
        parameter_unit             ← unit string (°C, mm, W/m², ...)
        parameter_decimals         ← number of decimal places
        parameter_datatype         ← Float or Integer
        (+ DE / FR / IT descriptions and groups)
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(METADATA_URL)
    headers = {}

    if use_cache and cache_file.exists():
        etag = _load_etag(cache_file)
        if etag:
            headers["If-None-Match"] = etag

    try:
        response = requests.get(METADATA_URL, headers=headers, timeout=30)

        if response.status_code == 304:
            print("[cache hit] parameter metadata is up-to-date.")
        else:
            response.raise_for_status()
            cache_file.write_bytes(response.content)
            if "ETag" in response.headers:
                _save_etag(cache_file, response.headers["ETag"])
            print("[downloaded] parameter metadata.")

        return pd.read_csv(
            cache_file,
            delimiter=";",
            encoding="Windows-1252",
            quotechar='"',
            engine="python",
        )

    except Exception as e:
        print(f"Error loading parameter metadata: {e}")
        return None


def get_human_readable_name(param_id: str, meta_df: pd.DataFrame) -> str:
    """
    Look up the human-readable description for a parameter identifier.
    Falls back to the raw identifier if not found.
    """
    match = meta_df[meta_df["param_id"] == param_id]  # adjust column name after inspecting the CSV
    if not match.empty:
        return match.iloc[0]["description"]           # adjust column name after inspecting the CSV
    return param_id


def search_parameters(query: str,
                       meta_df: pd.DataFrame,
                       granularity: str = "10min") -> pd.DataFrame:
    """
    Search the parameter metadata for a query string across all description
    columns (EN, DE, FR, IT) and optionally all group columns.
    Case-insensitive. Returns a filtered DataFrame of matching rows.

    Parameters
    ----------
    query       : Free-text search string, e.g. "precipitation", "Niederschlag", "pioggia"
    meta_df     : DataFrame from get_parameter_metadata()
    granularity : Optional filter: "10min" | "hourly" | "daily" | "monthly" | "yearly"
                  If provided, only parameters of that granularity are returned.

    Returns
    -------
    pd.DataFrame with columns: shortname, EN description, group, granularity, unit
    """
    desc_cols = [
        "parameter_description_en",
        "parameter_description_de",
        "parameter_description_fr",
        "parameter_description_it",
    ]

    # Build a boolean mask: True for rows where ANY description column matches
    mask = (
        meta_df[desc_cols]
        .apply(lambda col: col.str.contains(query, case=False, na=False))
        .any(axis=1)  # True if at least one column matched
    )

    result = meta_df[mask].copy()

    # Optional granularity filter (convert our human label to MeteoSwiss letter code)
    if granularity is not None:
        gran_code = GRANULARITY_MAP.get(granularity, granularity).upper()
        result = result[result["parameter_granularity"] == gran_code]

    if result.empty:
        print(f"No parameters found matching '{query}'.")
        return result

    # Return a tidy subset of columns
    return result[[
        "parameter_shortname",
        "parameter_description_en",
        "parameter_group_en",
        "parameter_granularity",
        "parameter_unit",
    ]].reset_index(drop=True), result["parameter_shortname"]

# == URL builder =======================================================

def get_station_url(station: str,
                    granularity: str = "10min",
                    period: str | None = None) -> str:
    """
    Build the direct CSV download URL for a MeteoSwiss SMN station.

    Parameters
    ----------
    station     : Three-letter station code, e.g. "BER" (Bern), "LUG" (Lugano), "PUY" (Pully).
    granularity : One of "10min" | "hourly" | "daily" | "monthly" | "yearly".
                  Defaults to "10min".
    period      : One of "now" | "recent" | "historical", or None to auto-select.
                  - None (default): picks "now" for 10min/hourly, "recent" for coarser.

    Returns
    -------
    str : Full URL to the CSV file.

    Examples
    --------
    >>> get_station_url("BER")
    'https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/ber/ogd-smn_BER_t_now.csv'
    >>> get_station_url("LUG", granularity="daily", period="historical")
    'https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/lug/ogd-smn_LUG_d_historical.csv'
    """
    station = station.lower()

    if granularity not in GRANULARITY_MAP:
        raise ValueError(f"granularity must be one of {list(GRANULARITY_MAP)}, got {granularity!r}")

    gran_code = GRANULARITY_MAP[granularity]

    # Auto-select period when not provided
    if period is None:
        # "now" is only available for 10min and hourly
        period = "now" if granularity in ("10min", "hourly") else "recent"

    if period not in PERIOD_MAP:
        raise ValueError(f"period must be one of {list(PERIOD_MAP)}, got {period!r}")

    filename = f"{station}/ogd-smn_{station}_{gran_code}_{period}.csv"
    return f"{BASE_URL}/{filename}"



# == Cache helpers ===================================================
def _cache_path(url: str) -> pathlib.Path:
    """Derive a local cache file path from a URL."""
    filename = url.rsplit("/", 1)[-1]
    return CACHE_DIR / filename


def _load_etag(cache_file: pathlib.Path) -> str | None:
    """Return the stored ETag for a cached file, or None if not found."""
    etag_file = cache_file.with_suffix(".etag")
    if etag_file.exists():
        return etag_file.read_text().strip()
    return None


def _save_etag(cache_file: pathlib.Path, etag: str) -> None:
    """Persist an ETag alongside a cached file."""
    etag_file = cache_file.with_suffix(".etag")
    etag_file.write_text(etag)



# == Core download ====================================================

def get_current_data(url: str,
                     use_cache: bool = True,
                     encoding: str = "Windows-1252") -> pd.DataFrame | None:
    """
    Download a MeteoSwiss CSV, using ETag-based conditional requests to avoid
    unnecessary traffic (as recommended by MeteoSwiss / swisstopo).

    The file is cached locally under CACHE_DIR. On subsequent calls the server
    is asked whether the remote file changed; if not (HTTP 304) the local copy
    is returned immediately.

    Parameters
    ----------
    url        : Direct CSV URL, e.g. the output of get_station_url().
    use_cache  : Set to False to always fetch from the network (not recommended).
    encoding   : MeteoSwiss CSVs use Windows-1252 by default.

    Returns
    -------
    pd.DataFrame | None
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(url)

    headers = {}
    if use_cache and cache_file.exists():
        etag = _load_etag(cache_file)
        if etag:
            # Send the stored ETag; server returns 304 if nothing changed
            headers["If-None-Match"] = etag

    try:
        response = requests.get(url, headers=headers, timeout=30)

        if response.status_code == 304:
            # Not Modified → serve from cache
            print(f"[cache hit] {cache_file.name} is up-to-date.")
            return pd.read_csv(cache_file, delimiter=";", encoding=encoding)

        response.raise_for_status()

        # New data received → update cache
        cache_file.write_bytes(response.content)
        if "ETag" in response.headers:
            _save_etag(cache_file, response.headers["ETag"])
            print(f"[downloaded] {cache_file.name} (ETag saved).")
        else:
            print(f"[downloaded] {cache_file.name} (no ETag in response).")

        return pd.read_csv(cache_file, delimiter=";", encoding=encoding)

    except requests.HTTPError as e:
        print(f"HTTP error fetching {url}: {e}")
    except requests.RequestException as e:
        print(f"Network error fetching {url}: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")

    return None


# == Convenience wrapper =================================================

def get_station_data(station: str,
                     granularity: str = "10min",
                     period: str | None = None,
                     use_cache: bool = True) -> pd.DataFrame | None:
    """
    High-level helper: build the URL and download data for a given station
    and moment in one call.

    Parameters
    ----------
    station     : Three-letter station code, e.g. "BER".
    granularity : "10min" | "hourly" | "daily" | "monthly" | "yearly".
    period      : "now" | "recent" | "historical" | None (auto).
    use_cache   : Whether to use ETag-based caching.

    Returns
    -------
    pd.DataFrame | None

    Examples
    --------
    # Latest 10-min values for Bern (= "now")
    >>> df = get_station_data("BER")

    # Today's hourly values from this year so far
    >>> df = get_station_data("LUG", granularity="hourly", period="recent")
    """
    url = get_station_url(station, granularity=granularity, period=period)
    print(f"[url] {url}")
    return get_current_data(url, use_cache=use_cache)



# == Existing helpers (unchanged except minor fixes) ===========================

def sanitize_column_names(df: pd.DataFrame, obj_col: str) -> pd.DataFrame | None:
    new_column_names = {col: col.replace("'", "") for col in df.columns}
    df_cleaned = df.rename(columns=new_column_names)
    if "REFERENCE_TS" in df_cleaned.columns:
        df_cleaned = df_cleaned.rename(columns={"REFERENCE_TS": "reference_timestamp"})
    if obj_col not in df_cleaned.columns:
        print(f"Error: Column '{obj_col}' not found!")
        return None
    return df_cleaned


def process_data(df_recent, df_historical, obj_col,
                 start_month, end_month,
                 start_year,  end_year) -> pd.DataFrame:
    df = pd.concat(
        [df_historical[["reference_timestamp", obj_col]],
         df_recent    [["reference_timestamp", obj_col]]],
        ignore_index=True,
    )
    df = df.drop_duplicates(ignore_index=True)
    df["timestamp"] = pd.to_datetime(df["reference_timestamp"],
                                     format="%d.%m.%Y %H:%M", errors="raise")
    df["year"]      = df["timestamp"].dt.year
    df["month"]     = df["timestamp"].dt.month
    df["month_str"] = df["timestamp"].dt.strftime("%B")
    df = df[df["month"].between(start_month, end_month)
          & df["year"].between(start_year, end_year)]
    return df


# ============================================================================== #
# ============================================================================== #
# =========================== FORECASTS DATA IMPORT ============================ #
# ============================================================================== #
# ============================================================================== #

# ── Forecast constants ─────────────────────────────────────────────────────────

FORECAST_BASE_URL      = "https://data.geo.admin.ch/ch.meteoschweiz.ogd-local-forecasting"
FORECAST_METADATA_URL  = f"{FORECAST_BASE_URL}/ogd-local-forecasting_meta_parameters.csv"
FORECAST_POINTS_URL    = f"{FORECAST_BASE_URL}/ogd-local-forecasting_meta_point.csv"

# All available forecast parameter identifiers (hourly and daily)
# Sourced from E4 documentation
FORECAST_PARAMS_HOURLY = [
    "dkl010h0", "fu3010h0", "fu3010h1",
    "fu3q10h0", "fu3q10h1", "fu3q90h0", "fu3q90h1",
    "gre000h0", "jww003i0",
    "nprohihs", "nprolohs", "npromths",
    "ods000h0",
    "rp0003i0", "rre003i0", "rre150h0", "rreq10h0", "rreq90h0",
    "sre000h0",
    "tre200h0", "treq10h0", "treq90h0",
    "zprfr0hs",
]
FORECAST_PARAMS_DAILY = [
    "jp2000d0",
    "rka150d0", "rka150p0", "rreq10p0", "rreq90p0",
    "tre200dn", "tre200dx", "tre200pn", "tre200px",
]


# ── Forecast metadata ──────────────────────────────────────────────────────────

def get_forecast_metadata(use_cache: bool = True) -> pd.DataFrame | None:
    """
    Load the E4 local forecast parameter metadata.
    Same columns as get_parameter_metadata() but only forecast parameters.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_file = _cache_path(FORECAST_METADATA_URL)
    headers    = {}

    if use_cache and cache_file.exists():
        etag = _load_etag(cache_file)
        if etag:
            headers["If-None-Match"] = etag

    try:
        response = requests.get(FORECAST_METADATA_URL, headers=headers, timeout=30)
        if response.status_code == 304:
            print("[cache hit] forecast parameter metadata is up-to-date.")
        else:
            response.raise_for_status()
            cache_file.write_bytes(response.content)
            if "ETag" in response.headers:
                _save_etag(cache_file, response.headers["ETag"])
            print("[downloaded] forecast parameter metadata.")

        return pd.read_csv(
            cache_file,
            delimiter=";",
            encoding="Latin1",
            quotechar='"',
            engine="python",
        )
    except Exception as e:
        print(f"Error loading forecast metadata: {e}")
        return None


def get_forecast_points(use_cache: bool = True) -> pd.DataFrame | None:
    """
    Load the E4 forecast points metadata (stations, postal codes, mountain POIs).

    Key columns:
        point_id            ← numeric ID (unique only within its type)
        point_type_id       ← 1=station, 2=postal code, 3=mountain POI
        station_abbr        ← three-letter code for type-1 points (e.g. "PUY")
        postal_code         ← for type-2 points
        point_name          ← human-readable name
        point_height_masl   ← altitude in metres
        point_coordinates_wgs84_lat / _lon
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # Note: MeteoSwiss has a typo in their URL ("forcasting" not "forecasting")
    url        = FORECAST_POINTS_URL
    cache_file = _cache_path(url)
    headers    = {}

    if use_cache and cache_file.exists():
        etag = _load_etag(cache_file)
        if etag:
            headers["If-None-Match"] = etag

    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code == 304:
            print("[cache hit] forecast points metadata is up-to-date.")
        else:
            response.raise_for_status()
            cache_file.write_bytes(response.content)
            if "ETag" in response.headers:
                _save_etag(cache_file, response.headers["ETag"])
            print("[downloaded] forecast points metadata.")

        return pd.read_csv(
            cache_file,
            delimiter=";",
            encoding="Latin1",
            engine="python",
        )
    except Exception as e:
        print(f"Error loading forecast points: {e}")
        return None


# ── Core forecast downloader ───────────────────────────────────────────────────

def get_forecast_data(parameter: str,
                      use_cache: bool = True) -> pd.DataFrame | None:
    """
    Download the full E4 local forecast CSV for one parameter.
    The file contains ALL forecast points (stations, postal codes, POIs).

    Parameters
    ----------
    parameter : Parameter shortname, e.g. "tre200h0", "rre150h0", "tre200dx".
                Must be one of FORECAST_PARAMS_HOURLY or FORECAST_PARAMS_DAILY.
    use_cache : Use ETag-based caching (recommended — files are large).

    Returns
    -------
    pd.DataFrame with columns:
        reference_timestamp (datetime, UTC)
        point_id, point_type_id
        <parameter>  ← the actual forecast values
    """
    valid = FORECAST_PARAMS_HOURLY + FORECAST_PARAMS_DAILY
    if parameter not in valid:
        raise ValueError(
            f"Unknown forecast parameter '{parameter}'.\n"
            f"Valid options: {valid}"
        )

    url        = f"{FORECAST_BASE_URL}/ogd-local-forecasting_{parameter}.csv"
    cache_file = _cache_path(url)
    headers    = {}

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    if use_cache and cache_file.exists():
        etag = _load_etag(cache_file)
        if etag:
            headers["If-None-Match"] = etag

    try:
        response = requests.get(url, headers=headers, timeout=60)
        if response.status_code == 304:
            print(f"[cache hit] {cache_file.name} is up-to-date.")
        else:
            response.raise_for_status()
            cache_file.write_bytes(response.content)
            if "ETag" in response.headers:
                _save_etag(cache_file, response.headers["ETag"])
            print(f"[downloaded] {cache_file.name}.")

        df = pd.read_csv(
            cache_file,
            delimiter=";",
            encoding="Latin1",
        )
        # Parse the YYYYMMDDHHMM timestamp into a proper datetime
        df["reference_timestamp"] = pd.to_datetime(
            df["reference_timestamp"].astype(str), format="%Y%m%d%H%M", utc=True
        )
        return df

    except Exception as e:
        print(f"Error downloading forecast for '{parameter}': {e}")
        return None


# ── Station forecast (high-level) ──────────────────────────────────────────────

def get_station_forecast(station: str,
                         parameter: str,
                         use_cache: bool = True) -> pd.DataFrame | None:
    """
    Get the E4 local forecast for a specific station and parameter.

    Parameters
    ----------
    station   : Three-letter station abbreviation, e.g. "PUY", "BER", "LUG".
    parameter : Parameter shortname, e.g. "tre200h0" (hourly temperature).

    Returns
    -------
    pd.DataFrame with columns: reference_timestamp, <parameter>
    Sorted by time, covering the next ~9 days from the latest model run.

    Examples
    --------
    >>> df = get_station_forecast("PUY", "tre200h0")   # hourly temperature
    >>> df = get_station_forecast("BER", "rre150h0")   # hourly precipitation
    >>> df = get_station_forecast("ZRH", "tre200dx")   # daily max temperature
    """
    # 1. Resolve station abbreviation → (point_type_id=1, point_id)
    points = get_forecast_points(use_cache=use_cache)
    if points is None:
        return None

    station_row = points[
        (points["point_type_id"] == 1) &
        (points["station_abbr"].str.upper() == station.upper())
    ]
    if station_row.empty:
        print(f"Station '{station}' not found in forecast points. "
              f"Check get_forecast_points() for valid station_abbr values.")
        return None

    point_id      = station_row.iloc[0]["point_id"]
    point_type_id = station_row.iloc[0]["point_type_id"]
    point_name    = station_row.iloc[0]["point_name"]
    print(f"[station] {station.upper()} → '{point_name}' "
          f"(point_id={point_id}, type={point_type_id})")

    # 2. Download the full parameter file
    df_all = get_forecast_data(parameter, use_cache=use_cache)
    if df_all is None:
        return None

    # 3. Filter to this station's point
    df_station = df_all[
        (df_all["point_type_id"] == point_type_id) &
        (df_all["point_id"]      == point_id)
    ][["reference_timestamp", parameter]].copy()

    return df_station.sort_values("reference_timestamp").reset_index(drop=True)
