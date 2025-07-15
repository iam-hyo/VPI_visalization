import pandas as pd
import numpy as np
from scipy.optimize import nnls
# from sklearn.linear_model import LinearRegression

def regression_score(
    ch_df: pd.DataFrame,
    days: int = 14,
):

    # get subscriber info
    ch_df = ch_df[ch_df['thumbnail_url'].notna() & (ch_df['thumbnail_url'] != '')]
    sub_scrap = ch_df[['timestamp', 'subscriber_count']].copy()
    sub_scrap['Date'] = pd.to_datetime(sub_scrap['timestamp']).dt.date
    sub_scrap = sub_scrap.groupby('Date', as_index=False)['subscriber_count'].max()
    sub_scrap["Daily Subscribers"] = sub_scrap["subscriber_count"].diff().fillna(0).astype(int)
    sub_scrap["isChange"] = sub_scrap["Daily Subscribers"] != 0
    # use this line to check
    sub_scrap.to_csv("data/daily.csv", index=False)

    # Pivot cumulative views (timestamp × video_id)
    long_df = ch_df[ch_df['is_short'] == False].copy()
    long_df["timestamp"] = pd.to_datetime(long_df["timestamp"], utc=True)
    long_df["published_at"] = pd.to_datetime(long_df["published_at"], utc=True)
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

    # Group by calendar day
    grouped_views = daily_views_df.groupby("Date").sum()
    grouped_views["Day"] = range(1, len(grouped_views) + 1)
    grouped_views.reset_index(inplace=True)

    grouped_views["Date"] = pd.to_datetime(grouped_views["Date"])
    sub_scrap["Date"] = pd.to_datetime(sub_scrap["Date"])
    # erase random after getting daily sub correctly
    # grouped_views["Daily Subscribers"] = daily_subs + np.random.normal(0, 0.5, size=len(grouped_views))

    # Merge sub info into grouped_views
    merged_df = grouped_views.merge(
        sub_scrap[["Date", "Daily Subscribers", "isChange"]],
        on="Date",
        how="left"
    )

    merged_df["Spread Change"] = 0.0
    view_cols = [col for col in merged_df.columns if
                 col not in ["Date", "Day", "Daily Subscribers", "isChange", "Spread Change"]]
    is_change_idx = merged_df.index[merged_df["isChange"] == True].tolist()

    # Backward weighted spread
    for i in range(1, len(is_change_idx)):
        start_idx = is_change_idx[i - 1] + 1
        end_idx = is_change_idx[i]
        spread_range = merged_df.loc[start_idx:end_idx]
        total_subs = merged_df.loc[end_idx, "Daily Subscribers"]
        view_weights = spread_range[view_cols].sum(axis=1)
        total_views = view_weights.sum()

        if total_views > 0:
            merged_df.loc[start_idx:end_idx, "Spread Change"] = (view_weights / total_views * total_subs).values
        else:
            merged_df.loc[start_idx:end_idx, "Spread Change"] = total_subs / len(spread_range)

    # After last isChange=True → extend last spread
    if len(is_change_idx) > 0:
        last_idx = is_change_idx[-1]
        last_subs = merged_df.loc[last_idx, "Daily Subscribers"]
        tail = merged_df.loc[last_idx + 1:]
        if not tail.empty:
            tail_idx = tail.index
            spread_val = merged_df.loc[last_idx, "Spread Change"]
            if (spread_val * len(tail_idx)) > last_subs:
                merged_df.loc[tail_idx, "Spread Change"] = last_subs / len(tail_idx)
            else:
                merged_df.loc[tail_idx, "Spread Change"] = spread_val

    # Fill beginning if needed
    first_nonzero_idx = merged_df[merged_df["Spread Change"] > 0].index
    if merged_df.loc[0, "isChange"]:
        merged_df.loc[0, "Spread Change"] = merged_df.loc[0, "Daily Subscribers"]
    elif len(first_nonzero_idx) > 0 :
        first_idx = first_nonzero_idx[0]
        fill_value = merged_df.loc[first_idx, "Spread Change"]
        # Rows before this index
        fill_range = merged_df.loc[:first_idx - 1]
        # Check if sum exceeds first Daily Subscribers (isChange == True)
        first_sub_idx = merged_df[merged_df["isChange"] == True].index
        if len(first_sub_idx) > 0:
            target_idx = first_sub_idx[first_sub_idx >= first_idx]
            if len(target_idx) > 0:
                daily_subs = merged_df.loc[target_idx[0], "Daily Subscribers"]
                if fill_value * len(fill_range) > daily_subs:
                    # Divide evenly
                    spread_val = daily_subs / len(fill_range)
                else:
                    spread_val = fill_value
                # Apply the spread
                merged_df.loc[:first_idx - 1, "Spread Change"] = spread_val

    merged_df["Day"] = range(1, len(merged_df) + 1)
    df_filtered = merged_df.iloc[-days:]

    # use this line to check data
    df_filtered.to_csv("data/temp.csv", index=False)

    # Prepare data for regression
    X = df_filtered.drop(columns=["Date", "Day", "Daily Subscribers", "isChange", "Spread Change"])
    y = df_filtered["Spread Change"]

    X_np = X.to_numpy()
    y_np = y.to_numpy()

    # Fit model
    # model = LinearRegression()
    # model.fit(X, y)
    # raw_betas = model.coef_
    all_zero_mask = (X_np == 0).all(axis=0)
    raw_betas, _ = nnls(X_np, y_np)
    raw_betas = np.where(all_zero_mask, np.nan, raw_betas)

    beta_total = np.nansum(raw_betas)
    if beta_total != 0:
        normalized_betas = raw_betas / beta_total
    else:
        normalized_betas = np.zeros_like(raw_betas)

    # Gain Index
    beta_mean = np.nanmean(raw_betas)
    gain_betas = raw_betas / beta_mean

    # Retention Index
    long_df['days_since_pub'] = (long_df['timestamp'] - long_df['published_at']).dt.days
    long_df = long_df.sort_values(['video_id', 'timestamp'])
    long_df['view_gain'] = long_df.groupby('video_id')['view_count'].diff().fillna(0)
    N = 2 # days
    early_views = long_df[long_df['days_since_pub'] <= N].groupby('video_id')['view_gain'].sum()
    total_views = long_df.groupby('video_id')['view_gain'].sum()
    retention_df = pd.DataFrame({
        'early_views': early_views,
        'total_views': total_views
    }).fillna(0)
    retention_df['retention_index'] = retention_df['early_views'] / retention_df['total_views']
    retention_df = retention_df.fillna(0)
    retention_index_df = retention_df[['retention_index']].reset_index()

    regression_results = pd.DataFrame({
        "video_id": X.columns,
        "βᵢ / β_mean": gain_betas,
        "regression_subs_contrib": normalized_betas * y.sum()
    })
    regression_results = regression_results.astype(object)
    regression_results["βᵢ / β_mean"] = regression_results["βᵢ / β_mean"].apply(
        lambda x: "N/A" if pd.isna(x) else round(x, 2)
    )
    regression_results["regression_subs_contrib"] = regression_results["regression_subs_contrib"].apply(
        lambda x: "N/A명" if pd.isna(x) else int(round(x, 1))
    )
    regression_results = regression_results.merge(retention_index_df, on="video_id", how="left")

    spread_change_df = merged_df[["Date", "Spread Change"]].copy()
    return regression_results, spread_change_df