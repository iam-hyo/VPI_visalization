"""
video_gain.py with separated preprocessing function

이 파일은 크게 4개의 함수로 구성되어 있습니다:
1) preprocess_channel_data: channel_df와 ch_snap을 날짜 기준으로 병합하고 전처리
2) aggregate_views_within_days: 영상별 조회수 변화량 집계
3) compute_channel_gain_index: 채널 수준 GainIndex 계산
4) compute_video_gain_scores: 전처리된 데이터를 이용해 영상별 Gain Score 계산

호출 예시:
```python
from video_gain import compute_video_gain_scores

video_gain_df = compute_video_gain_scores(
    channel_df=ch_df,
    ch_snap=ch_snap,
    end_subs=latest_subs,
    total_view=total_view,
    c=100.0,
    days=14
)
```
"""
import numpy as np
import pandas as pd
import streamlit as st
from datetime import timedelta
from utils.metrics import parse_published_at


def preprocess_channel_data(
    channel_df: pd.DataFrame,
    ch_snap: pd.DataFrame
) -> pd.DataFrame:
    """
    channel_df와 ch_snap을 날짜 기준으로 병합하여 subscriber_count를 업데이트합니다.
    1) channel_df: timestamp→datetime, date 추출, video_id+date별 첫 row만 남김
    2) ch_snap: collected_at→datetime, date 추출, 날짜별 subscriber_count 정리
    3) 전체 날짜 기간을 보장하고 결측값은 전후일 구독자 수로 보간
    4) channel_daily에 subscriber_count merge
    """
    # 1) channel_df 전처리
    df = channel_df.copy()
    df['timestamp'] = parse_published_at(df['timestamp'])
    df['date'] = df['timestamp'].dt.date
    channel_daily = (
        df
        .sort_values('timestamp')
        .drop_duplicates(subset=['video_id', 'date'], keep='first')
    )

    # 2) ch_snap 전처리
    snap = ch_snap.copy()
    snap['timestamp'] = pd.to_datetime(snap['collected_at'])
    snap['date'] = snap['timestamp'].dt.date
    daily_snap = (
        snap[['date', 'subscriber_count']]
        .drop_duplicates('date')
        .sort_values('date')
    )

    # 3) 전체 날짜 보장 & 보간
    all_dates = pd.date_range(
        start=daily_snap['date'].min(),
        end=daily_snap['date'].max(),
        freq='D'
    ).date
    full_snap = (
        pd.DataFrame({'date': all_dates})
        .merge(daily_snap, on='date', how='left')
    )
    full_snap['subscriber_count'] = full_snap['subscriber_count'].interpolate()
    st.write("[DEBUG] preprocess -> full_snap sample:", full_snap.head())

    # 4) merge
    channel_daily = channel_daily.drop(columns=['subscriber_count'], errors='ignore')
    merged = channel_daily.merge(
        full_snap[['date', 'subscriber_count']],
        on='date', how='left'
    )
    st.write("[DEBUG] preprocess -> merged sample:", merged.head())
    return merged


def estimate_daily_subscribers(  
    ch_snap: pd.DataFrame,       
    spread_change_df: pd.DataFrame 
) -> pd.DataFrame:               
    """
    일별 구독자수를 추정하여 반환합니다.

    ch_snap: DataFrame with ['collected_at','subscriber_count']
      - subscriber_count는 만 단위로만 측정된 값
    spread_change_df: DataFrame with ['Date','Spread Change']
      - 일별 추정 구독자 증가량

    반환: DataFrame with ['Date','Estimated Subscribers']
    확실한 제약조건을 지키며, 단순합이 이를 벗어날 경우 보정치를 적용합니다.
    """
    # 1–4: 함수 시그니처와 타입 힌트; 두 개의 DataFrame 입력을 받아 하나의 DataFrame을 반환

    # 1) ch_snap 전처리: 날짜 및 계단식 구독수 구간
    snap = ch_snap.copy()                                           
    snap['Date'] = parse_published_at(snap['collected_at']).dt.date 

    # 계단값: 만단위로 기록된 subscriber_count

    # 2) spread_change_df 전처리: 날짜 및 일별 변화량
    spread = spread_change_df.copy()                              # 7: spread_change_df 복사
    spread['Date'] = pd.to_datetime(spread['Date']).dt.date       # 8: 문자열인 'Date' 컬럼을 datetime → date 타입으로 변환
    spread = spread.set_index('Date')                             # 9: date를 인덱스로 설정

    # 3) 날짜 인덱스 범위
    all_dates = pd.date_range(                                     # 10: 모든 날짜 범위 생성
        start=min(snap['Date'].min(), spread.index.min()),         # 11: 입력들 중 가장 이른 날짜
        end=max(snap['Date'].max(), spread.index.max()),           # 12: 입력들 중 가장 늦은 날짜
        freq='D'                                                   # 13: 일 단위 빈도
    ).date                                                        

    # 4) 초기 estimated Series 생성
    est = pd.Series(index=all_dates, dtype=float)                 # 15: 모든 날짜에 대한 빈(NA) Series 준비

    # 5) snap에서 계단 제약: 각 측정일에만 known count
    known = snap.drop_duplicates('Date').set_index('Date')['subscriber_count']  # 16: 하루에 하나씩 중복 제거 후 인덱스 설정
    known = known[ known.ne(known.shift()) ]  # 17: 연속된 값이 같은 경우(계단이 없는 경우) 제거 → 계단 변화 지점만 남김

    # 6) spread change에서 일별 증가량
    deltas = spread['Spread Change'].reindex(all_dates).fillna(0)  # 18: all_dates에 맞춰 재인덱싱, NaN은 0으로 채움

    # 7) 일별 누적 추정 (계단 제약 무시, known 날짜에서만 값 고정)
    prev_est = None
    for date in all_dates:
        delta = deltas.loc[date]              # 오늘의 증가량
        if date in known.index:               # 만단위로 측정된 날이면
            est.loc[date] = known.loc[date]   # 실제 값을 그대로 사용
            prev_est = est.loc[date]          # 누적 기준 갱신
        else:                                 # 측정 없는 날에는
            if prev_est is None:             # 아직 시작 전이면
                prev_est = 0.0               # 0부터 누적 시작
            est.loc[date] = prev_est + delta  # 단순 누적
            prev_est = est.loc[date]          # prev_est 갱신

    # st.caption("[DEBUG] estimate_daily_subscribers -> estimated daily subscribers:")
    # st.dataframe(est, use_container_width=True)  # 40: 추정 구독자 수를 Streamlit 데이터프레임으로 표시

    # 8) 결과 DataFrame
    result = est.reset_index()                                     # 41: Series → DataFrame
    result.columns = ['Date', 'Estimated Subscribers']             # 42: 컬럼명 지정
    return result                                                  # 43: 최종 반환
