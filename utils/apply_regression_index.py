import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler

def regression_score(
    ch_df: pd.DataFrame,
    daily_subs: float,
    days: int = 14
):
    long_df = ch_df[ch_df['is_short'] == False].copy()
    long_df["timestamp"] = pd.to_datetime(long_df["timestamp"], utc=True)

    # Pivot cumulative views (timestamp × video_id)
    pivot_df = long_df.pivot_table(
        index="timestamp",
        columns="video_id",
        values="view_count",
        aggfunc="first"
    ).fillna(0).astype(int)

    ## only for 0 error, delete after corrected=============
    # Ensure datetime index
    pivot_df.index = pd.to_datetime(pivot_df.index)

    # Shifted previous values
    prev = pivot_df.shift(1)

    # Compute raw diff
    diff = pivot_df - prev

    # Make diff = 0 if either prev or curr is 0
    diff[(pivot_df == 0) | (prev == 0)] = 0
    diff[diff < 0] = 0
    ## =============================


    # Calculate daily view counts
    #daily_views_df = pivot_df.diff().fillna(0).clip(lower=0).astype(int)
    daily_views_df = diff.fillna(0).clip(lower=0).astype(int) #replace it to upper line after corrected
    daily_views_df.index = pd.to_datetime(daily_views_df.index)
    daily_views_df["Date"] = daily_views_df.index.date

    # use this line to check
    #daily_views_df.to_csv("data/daily.csv", index=False)

    # Group by calendar day
    grouped_views = daily_views_df.groupby("Date").sum()
    grouped_views["Day"] = range(1, len(grouped_views) + 1)
    grouped_views.reset_index(inplace=True)

    grouped_views["Date"] = pd.to_datetime(grouped_views["Date"])
    #erase random after getting daily sub correctly
    grouped_views["Daily Subscribers"] = daily_subs + np.random.normal(0, 0.5, size=len(grouped_views))

    #grouped_views["Daily Subscribers"] = grouped_views["Daily Subscribers"].fillna(0).astype(int)
    grouped_views["Day"] = range(1, len(grouped_views) + 1)
    df_filtered = grouped_views[grouped_views["Day"] <= days]

    # use this line to check
    # grouped_views.to_csv("data/temp.csv", index=False)

    # Prepare data for regression
    X = df_filtered.drop(columns=["Date", "Day", "Daily Subscribers"])
    y = df_filtered["Daily Subscribers"]

    # Standardize -  deleted due to Daily Subscribers problems
    #scaler_X = StandardScaler()
    #scaler_y = StandardScaler()
    #X_scaled = scaler_X.fit_transform(X)
    #y_scaled = scaler_y.fit_transform(y.values.reshape(-1, 1)).ravel()

    # Fit model
    model_std = LinearRegression()
    model_std.fit(X, y)

    raw_betas = model_std.coef_
    beta_total = raw_betas.sum()

    if beta_total != 0:
        normalized_betas = raw_betas / beta_total
    else:
        normalized_betas = [0] * len(raw_betas)

    regression_results = pd.DataFrame({
        "video_id": X.columns,
        "βᵢ / β_total": normalized_betas,
        "regression_subs_contrib": np.nan_to_num(normalized_betas * daily_subs)
    })

    return regression_results