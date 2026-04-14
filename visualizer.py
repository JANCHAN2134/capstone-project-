import plotly.express as px

def plot_data(df):
    if df is None or not hasattr(df, "shape"):
        return None

    if df.shape[1] < 2:
        return None

    import matplotlib.pyplot as plt

    x = df.iloc[:, 0]
    y = df.iloc[:, 1]

    fig, ax = plt.subplots()
    ax.bar(x, y)

    return fig

if __name__ == "__main__":
    import pandas as pd

    df = pd.DataFrame({
        "state": ["SP", "RJ", "MG"],
        "revenue": [5000, 3000, 2000]
    })

    fig = plot_data(df)
    fig.show()
