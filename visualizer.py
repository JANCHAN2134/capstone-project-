import plotly.express as px

def plot_data(df):
    # If only one column → no chart
    if df.shape[1] < 2:
        return None

    # Get column names
    col1 = df.columns[0]
    col2 = df.columns[1]

    # Case 1: Date-based → Line chart
    if "date" in col1.lower() or "time" in col1.lower():
        fig = px.line(df, x=col1, y=col2, title=f"{col2} over {col1}")
    
    # Case 2: Category + value → Bar chart
    elif df.shape[1] == 2:
        fig = px.bar(df, x=col1, y=col2, title=f"{col2} by {col1}")
    
    # Case 3: Multiple columns → Scatter
    else:
        fig = px.scatter(df)

    return fig

if __name__ == "__main__":
    import pandas as pd

    df = pd.DataFrame({
        "state": ["SP", "RJ", "MG"],
        "revenue": [5000, 3000, 2000]
    })

    fig = plot_data(df)
    fig.show()