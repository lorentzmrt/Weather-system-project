import seaborn as sns
import matplotlib.pyplot as plt
import matplotlib.dates as mdates


from meteoswiss.meteoswiss_data_import   import * 

def create_histogram(df):
    """
    Plots global radiation monthly means
    """

    sns.set_theme(style="whitegrid")
    color_palette = sns.color_palette("deep", len(df["year"].unique()))

    plt.figure(figsize=(16, 9))
    ax = plt.gca()

    # Shading every 2nd Month for better readability.
    # Might need to be adapted for incomplete timeseries, or years with gaps, but works nice for our example
    for i in range(1, len(df["month_str"].unique()), 2):
        ax.axvspan(i - 0.5, i + 0.5, facecolor='gray', alpha=0.1)

    sns.barplot(data=df, x="month_str", y="gre000m0", hue="year", dodge=True, ax=ax, palette=color_palette)
    ax.set_xlabel("Month", fontsize=14, fontweight='bold')
    ax.set_ylabel("Mean Global Radiation [W/m²]", fontsize=14, fontweight='bold')
    ax.set_title("Monthly Mean Global Radiation\nSalen-Reutenen (station: HAI)", fontsize=16, fontweight='bold')

    ax.legend(title="Year", fontsize=12)

    plt.show()


def plot_history(parameter: str   = "precipitation",
                 station: str     = "PUY",
                 granularity: str = "daily",
                 period: str      = "recent",
                 ) -> pd.DataFrame:
    # ---- get station data ---- #
    print(f"Getting data frame for {station}, with granularity {granularity}, {period} period ...")
    df = get_station_data(station, granularity=granularity, period=period)

    # ---- get metadata ---- #
    df_metadata = get_parameter_metadata()
    matches, shortnames = search_parameters(parameter, df_metadata, granularity=granularity)

    if shortnames.empty:
        raise ValueError(f"No match found for '{parameter}' at granularity '{granularity}'.")
    if len(shortnames) > 1:
        print(f"Multiple matches — picking first. Consider a more specific query.")

    col  = shortnames.iloc[0]
    unit = matches["parameter_unit"].iloc[0]
    desc = matches["parameter_description_en"].iloc[0]

    # ---- prepare data ---- #
    df_select = df[["reference_timestamp", col]].copy()
    df_select["reference_timestamp"] = pd.to_datetime(
        df_select["reference_timestamp"], format="%d.%m.%Y %H:%M"
    )
    df_select = df_select.dropna(subset=[col])

    # ---- plot ---- #
    fig, ax = plt.subplots(figsize=(14, 5))

    ax.plot(
        df_select["reference_timestamp"],
        df_select[col],
        linewidth=0.8,
        color="#2196F3",
        zorder=2,
    )
    ax.scatter(
        df_select["reference_timestamp"],
        df_select[col],
        s=6,
        color="#2196F3",
        zorder=3,
    )

    # ---- labels & formatting ---- #
    ax.set_title(f"{desc}\nStation: {station.upper()} — {period.capitalize()}", fontsize=12, pad=12)
    ax.set_xlabel("Time (UTC)", fontsize=10)
    ax.set_ylabel(f"{parameter.capitalize()} [{unit}]", fontsize=10)

    # Smart x-axis tick formatting based on the time range
    time_range = df_select["reference_timestamp"].max() - df_select["reference_timestamp"].min()
    if time_range.days > 60:
        ax.xaxis.set_major_locator(mdates.MonthLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    elif time_range.days > 7:
        ax.xaxis.set_major_locator(mdates.WeekdayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))
    else:
        ax.xaxis.set_major_locator(mdates.DayLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%d %b"))

    fig.autofmt_xdate(rotation=30, ha="right")
    ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.7, zorder=1)
    ax.set_xlim(df_select["reference_timestamp"].min(), df_select["reference_timestamp"].max())

    plt.tight_layout()
    plt.show()

    return df_select