from .supabase_client import supabase_me
import pandas as pd

def fetch_channel_meta():
    res = supabase_me.table("channels").select("*").execute()
    if res.error:
        raise Exception(res.error.message)
    return {row['id']: row for row in res.data}


def fetch_video_snapshots():
    videos = supabase_me.table("videos").select("*").execute()
    snaps = supabase_me.table("video_snapshots").select("*").execute()
    if videos.data is None or snaps.data is None:
        raise Exception("Video 혹은 snaps이 None.")

    df_videos = pd.DataFrame(videos.data)
    df_snaps  = pd.DataFrame(snaps.data)

    # Merge snapshots + videos
    df = df_snaps.merge(
        df_videos,
        left_on="video_id", right_on="id",
        suffixes=("", "_video")
    )

    df["timestamp"] = pd.to_datetime(df["collected_at"])
    df["published_at"] = pd.to_datetime(df["published_at"])
    df["day_since_pub"] = (df["timestamp"] - df["published_at"]).dt.days + 1

    return df
