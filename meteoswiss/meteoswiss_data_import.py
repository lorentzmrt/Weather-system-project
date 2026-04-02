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




# ── URL builder ────────────────────────────────────────────────────────────────

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
    'https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/ch.meteoschweiz.ogd-smn_BER_t_now.csv'
    >>> get_station_url("LUG", granularity="daily", period="historical")
    'https://data.geo.admin.ch/ch.meteoschweiz.ogd-smn/ch.meteoschweiz.ogd-smn_LUG_d_historical.csv'
    """
    station = station.upper()

    if granularity not in GRANULARITY_MAP:
        raise ValueError(f"granularity must be one of {list(GRANULARITY_MAP)}, got {granularity!r}")

    gran_code = GRANULARITY_MAP[granularity]

    # Auto-select period when not provided
    if period is None:
        # "now" is only available for 10min and hourly
        period = "now" if granularity in ("10min", "hourly") else "recent"

    if period not in PERIOD_MAP:
        raise ValueError(f"period must be one of {list(PERIOD_MAP)}, got {period!r}")

    filename = f"ch.meteoschweiz.ogd-smn_{station}_{gran_code}_{period}.csv"
    return f"{BASE_URL}/{filename}"



# ── Cache helpers ──────────────────────────────────────────────────────────────

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



# ── Core download ──────────────────────────────────────────────────────────────

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


# ── Convenience wrapper ────────────────────────────────────────────────────────

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


# ── Existing helpers (unchanged except minor fixes) ───────────────────────────

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