import seaborn as sns
import matplotlib.pyplot as plt

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