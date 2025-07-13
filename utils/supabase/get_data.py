# utils/supabase/get_data.py
from datetime import datetime
import streamlit as st
import pandas as pd
from utils.supabase.supabase_client import supabase
from utils.metrics import parse_published_at


def fetch_channel() -> dict:
    """Supabase의 channels 테이블에서 채널 메타데이터 가져오기"""
    res = supabase.table("channels").select("*").execute()
    
    if not res.data:
        raise RuntimeError("❌ channels 테이블에서 데이터를 불러올 수 없습니다.")
    
    return {row['id']: row for row in res.data}

def fetch_channel_snapshots() -> pd.DataFrame:
    """Supabase의 channel_snapshots 테이블에서 채널 스냅샷 가져오기"""
    all_snaps = []
    range_size = 1000
    from_idx = 0

    while True:
        res = (
            supabase.table("channel_snapshots")
            .select("*")
            .range(from_idx, from_idx + range_size - 1)
            .execute()
        )
        data = res.data or []
        if not data:
            break
        all_snaps.extend(data)
        from_idx += range_size
    
    df_snaps = pd.DataFrame(all_snaps)
    
    return df_snaps
        
def fetch_videos() -> pd.DataFrame:
    """Supabase의 videos 테이블에서 영상 메타데이터 가져오기"""
    all_videos = []
    range_size = 1000
    from_idx = 0

    while True:
        res = (
            supabase.table("videos")
            .select("*")
            .range(from_idx, from_idx + range_size - 1)
            .execute()
        )
        data = res.data or []
        if not data:
            break
        all_videos.extend(data)
        from_idx += range_size
    
    df_videos = pd.DataFrame(all_videos)
    
    return df_videos


def fetch_all_video_snapshots(): ##현자 사용 하지 않음.

    # 1. snapshot 1000개씩 가져오기 (pagination)
    all_snaps = []
    range_size = 1000
    from_idx = 0

    while True:
        res = (
            supabase.table("video_snapshots")
            .select("*")
            .range(from_idx, from_idx + range_size - 1)
            .execute()
        )
        data = res.data or []
        if not data:
            break
        all_snaps.extend(data)
        from_idx += range_size

    df_snaps = pd.DataFrame(all_snaps)
    df_snaps = df_snaps.drop(columns=["id"])

    # 2. video_id 기준으로 병합용 videos도 fetch
    video_ids = list(set(df_snaps["video_id"]))  #set(리스트) : 리스트의 고유 값만 저장
    all_videos = []

    for i in range(0, len(video_ids), 1000):
        chunk = video_ids[i:i + 1000]
        res = (
            supabase.table("videos")
            .select("*")
            .in_("id", chunk)
            .execute()
        )
        if res.data:
            all_videos.extend(res.data)

    df_videos = pd.DataFrame(all_videos)

    # 3. 병합
    df = df_snaps.merge( # df_snaps에 df_videos를 병합.
        df_videos, 
        left_on="video_id", 
        right_on="id",
        suffixes=("", "_video") # 같은 column은 video에 _video붙여서 표시.
        )

    # 4. 추가 전처리 😌😌😌😌😌😌😌😌😌
    df["timestamp"] = parse_published_at(df["collected_at"])
    df = df.drop(columns=["collected_at", "id_video"], errors="ignore")
    
    df["published_at"] = pd.to_datetime(df["published_at"])
    df["day_since_pub"] = (df["timestamp"] - df["published_at"]).dt.days

    return df

def get_channel_video_snapshots(channel_id):
    '''
    1. videos 테이블에서 해당 channel_id에 해당하는 행 추출
    2. video_snapshots 테이블에서 videos의 id와 일치하는 video_id들 row만 가져옴
    2.5. video_snapshots에서 'id' 열은 제거
    3. 추출한 videos와 video_snapshots를 df로 병합하여 반환
    '''

    # 1. 해당 채널의 영상들 가져오기
    videos = []
    range_size = 1000
    from_idx = 0

    while True:
        res = (
            supabase.table("videos")
            .select("*")
            .eq("channel_id", channel_id)
            .range(from_idx, from_idx + range_size - 1)
            .execute()
        )
        data = res.data or []
        if not data:
            break
        videos.extend(data)
        from_idx += range_size

    df_videos = pd.DataFrame(videos)
    if df_videos.empty:
        return pd.DataFrame()

    # 2. videos.id → video_snapshots.video_id와 매칭되는 row만 추출 (페이징 포함)
    video_ids = list(df_videos["id"].unique())
    snapshots = []

    for i in range(0, len(video_ids), 1000):
        chunk = video_ids[i:i + 1000]
        snap_from = 0

        while True:
            res = (
                supabase.table("video_snapshots")
                .select("*")
                .in_("video_id", chunk)
                .range(snap_from, snap_from + range_size - 1)
                .execute()
            )
            data = res.data or []
            if not data:
                break
            snapshots.extend(data)
            snap_from += range_size

    df_snaps = pd.DataFrame(snapshots)
    if df_snaps.empty:
        return pd.DataFrame()

    # 2.5. 병합 전 전처리 video_snapshots에서 'id' 열 제거
    df_snaps = df_snaps.drop(columns=["id"], errors="ignore")
    df_snaps = df_snaps.rename(columns={"collected_at": "timestamp"})
    df_snaps["timestamp"] = parse_published_at(df_snaps["timestamp"])

    df_videos = df_videos.drop(columns=["saved_at"], errors="ignore")

    # 3. 병합: video_snapshots + videos
    df = df_snaps.merge(df_videos, left_on="video_id", right_on="id", suffixes=("", "_video"))
    df = df.drop(columns=["id_video"], errors="ignore")  # 'id', saved_at 열 제거

    df["published_at"] = parse_published_at(df["published_at"])
    df["day_since_pub"] = (df["timestamp"] - df["published_at"]).dt.days

    return df

