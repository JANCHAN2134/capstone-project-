import matplotlib.pyplot as plt
# BUG FIX: Removed unused `import plotly.express as px` — plotly was imported
# at the top but matplotlib was actually used for all plotting.
# Also removed fig.show() which crashes in Streamlit context.


def plot_data(df):
    if df is None or not hasattr(df, "shape"):
        return None

    if df.shape[1] < 2:
        return None

    x = df.iloc[:, 0].astype(str)  # Ensure x-axis labels are strings
    y = df.iloc[:, 1]

    # Only plot if y column is numeric
    if not y.dtype.kind in ("i", "f"):
        return None

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.bar(x, y, color="steelblue")
    ax.set_xlabel(df.columns[0])
    ax.set_ylabel(df.columns[1])
    ax.set_title(f"{df.columns[1]} by {df.columns[0]}")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    return fig
