# Import necessary libraries
import pandas as pd  # Data processing: https://pandas.pydata.org/docs/

def download_csv(url):
    """
    Downloads a CSV file from a given URL and returns a Pandas DataFrame.
    """
    try:
        # in production, please check if a local copy of the files already exists. If so, please
        # send the ETag of the local resource (that you got in the response when initially
        # requesting the resource) in an If-None-Match header. The server will only send the file,
        # if the remote version is newer than your local file. This avoids unnecessary traffic.
        # (also check here: https://data.geo.admin.ch/api/stac/static/spec/v1/apitransactional.html#tag/Data/operation/getAssetObject)
        # For our short example, we don't need to do 4all this.
        df = pd.read_csv(url, delimiter=';')
        return df
    # too broad exception, I know. Please use better error handling in production ;-)
    except Exception as e:
        print(f"Error downloading {url}: {e}")
        return None

def sanitize_column_names(df, obj_col):
    """
    Removes single quotes from column names in a given Pandas DataFrame.
    Also rename "REFERENCE_TS" to "reference_timestamp".

    Args:
        df (pd.DataFrame): The input DataFrame.

    Returns:
        pd.DataFrame: A new DataFrame with cleaned column names.
    """
    new_column_names = {col: col.replace("'", "") for col in df.columns}
    df_cleaned = df.rename(columns=new_column_names)

    if "REFERENCE_TS" in df_cleaned.columns:
        df_cleaned = df_cleaned.rename(columns={"REFERENCE_TS": "reference_timestamp"})

    if not obj_col in df_cleaned.columns:
        print("Error: No valid global radiation column found!")
        return None


    return df_cleaned


def process_data(df_recent, df_historical, obj_col,
                 start_month, end_month, 
                 start_year,  end_year):
    """
    Process the data, i,e, concatenate the two data frames from the _historical and the _recent files.
    Also drop potential duplicates and only return data in the defined time range we want to analyse.

    Args:
        df_recent, df_historical (pd.DataFrame): The input DataFrames.

    Returns:
        pd.DataFrame: A new DataFrame with processed data.
    """


    # concatenate the two data frames of the historical and the recent data into one single data frame
    df = pd.concat([df_historical[['reference_timestamp', obj_col]], 
                    df_recent[['reference_timestamp', obj_col]]], 
                    ignore_index=True)
    # remove duplicates (there should be no duplicates, but just in case...)
    df = df.drop_duplicates(ignore_index=True)

    df["timestamp"] = pd.to_datetime(df["reference_timestamp"], 
                                     format="%d.%m.%Y %H:%M", errors="raise")
    df["year"]      = df["timestamp"].dt.year
    df["month"]     = df["timestamp"].dt.month
    df["month_str"] = df["timestamp"].dt.strftime("%B")


    df              = df[df["month"].between(start_month, end_month) 
                    & df["year"].between(start_year, end_year)]


    return df