import pandas as pd
import json
import streamlit as st


@st.cache_data #캐싱 데코레이터 : 함수의 실행결과를 메모리에 저장함.
def load_processed_data(path="data/processed_data_v2.csv"):
    """
    영상별 구독자/조회수/카테고리 로그 CSV 파일 불러오기
    """
    df = pd.read_csv(path, encoding='utf-8-sig', on_bad_lines='skip')  
    df['timestamp'] = pd.to_datetime(df['timestamp'])

      # 누락된 썸네일 채우기
    if 'thumbnail_url' in df.columns:
        thumbnail_map = df.dropna(subset=['video_id', 'thumbnail_url']) \
                          .drop_duplicates(subset=['video_id'], keep='last') \
                          .set_index('video_id')['thumbnail_url'].to_dict()

        df['thumbnail_url'] = df.apply(
            lambda row: thumbnail_map.get(row['video_id'], "") if pd.isna(row.get('thumbnail_url')) else row['thumbnail_url'],
            axis=1
        )
    else:
        df['thumbnail_url'] = ""  # 컬럼이 아예 없을 경우 기본 생성

    return df


@st.cache_data
def load_channel_meta(path="data/channel_meta.json"):
    """
    채널별 썸네일, 배너, 이름, 카테고리 등이 담긴 JSON
    """
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    return data  # list 또는 dict 구조


@st.cache_data
def load_video_meta(path="data/video_meta.json"):
    """
    각 영상의 is_short, title, published_at 등이 담긴 JSON
    """
    with open(path, "r", encoding="utf-8-sig") as f:
        data = json.load(f)
    return data  # list 또는 dict 구조

if __name__ == "__main__":
    df = load_processed_data()
    channel_meta = load_channel_meta()
    video_meta = load_video_meta()

    print(df.head())
    print(channel_meta[0])
    print(video_meta[0])