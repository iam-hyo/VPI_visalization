import pandas as pd
from datetime import date, timedelta, datetime
import streamlit as st
from utils.supabase.supabase_client import supabase


def get_last_calculated_at(channel_id: str) -> date:
    resp = (
        supabase.table('video_metrics')
                .select('calculated_at')
                .eq('channel_id', channel_id)
                .order('calculated_at', desc=True)
                .limit(1)
                .execute()
    )
    data = resp.data
    if data:
        return pd.to_datetime(data[0]['calculated_at']).date()
    return None


def fetch_subs_contrib(channel_id: str) -> pd.DataFrame:
    today = datetime.combine(date.today(), datetime.min.time())
    tomorrow = today + timedelta(days=1)
    resp = (
    supabase.table('video_metrics')
        .select('video_id, subs_contrib')
        .eq('channel_id', channel_id)
        .gte('calculated_at', today.isoformat())
        .lt('calculated_at', tomorrow.isoformat())
        .execute()
    )
    return pd.DataFrame(resp.data)


def upsert_subs_contrib(df: pd.DataFrame):
    records = df.to_dict(orient='records')
    supabase.table('video_metrics').upsert(records, on_conflict=['video_id']).execute()
