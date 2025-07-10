import streamlit as st
import pandas as pd
from utils.data_loader import load_processed_data, load_channel_meta
from components.channel_card import render_channel_card
from utils.supabase.get_data import fetch_channel_meta, fetch_video_snapshots

st.set_page_config(
    page_title="VPI",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 1) 데이터 불러오기 & 통계 계산
df = fetch_video_snapshots()          #processed_data_v2.csv 불러오기
channel_meta = fetch_channel_meta()  #channel_meta.json 불러오기

latest = df.groupby('channel_id').last()
earliest = df.groupby('channel_id').first()

# 카테고리 리스트
categories = ["전체"] + sorted({meta["category"]
                               for meta in channel_meta.values()
                               if "category" in meta and meta["category"]})

# 정렬 기준 맵
subs_diff    = latest['subscriber_count'] - earliest['subscriber_count']
avg_views    = df.groupby('channel_id')['view_count'].mean()
short_ratio  = df.groupby('channel_id')['is_short'].mean()
subscriber_count = latest['subscriber_count']

sort_column_map = {
    "구독자순": latest['subscriber_count'],
    "구독자 오름차순": latest['subscriber_count'],
    "구독자 급상승": subs_diff,
    "평균 조회수": avg_views,
    "Shorts 비율": short_ratio
}

# 세션 스테이트 초기화
if 'selected_cats' not in st.session_state:
    st.session_state.selected_cats      = ['전체']
    st.session_state.prev_selected_cats = ['전체']

# 카테고리 pills 콜백
def on_cats_change():
    selected = st.session_state.selected_cats
    prev     = st.session_state.prev_selected_cats

    if not selected:
        new = ['전체']
    elif '전체' in selected and '전체' not in prev:
        new = ['전체']
    elif '전체' in prev and any(c != '전체' for c in selected):
        new = [c for c in selected if c != '전체']
    else:
        new = selected

    st.session_state.selected_cats      = new
    st.session_state.prev_selected_cats = new

# ———— Page 렌더링 ————
non1, main, non2 = st.columns([0.5, 10, 0.5])
with main:
    s1, s2 = st.columns(2)
    with s1:
        st.metric(value="📺VPI", label="Video Performance Indicator")
        st.caption("가장 강력한 유튜브 분석 도구")
    
    with s2:
        search_query = st.text_input(
            label="검색어 입력",
            placeholder="🔍 검색 : 채널명·설명·핸들",
            key="search_query"
        ).strip().lower()

    # — 카테고리 pills —
    selected_categories = st.pills(
        label="카테고리 선택",
        options=categories,
        selection_mode="multi",
        key='selected_cats',
        on_change=on_cats_change,
        help="여러 카테고리 선택 가능"
    )

    # — 필터링: 카테고리 →
    selected = st.session_state.selected_cats
    if '전체' in selected:
        filtered_ids = list(channel_meta.keys())
    else:
        filtered_ids = [
            cid for cid, meta in channel_meta.items()
            if meta.get("category", "") in selected
        ]

    # — 추가 필터: 검색어 →
    if search_query:
        filtered_ids = [
            cid for cid in filtered_ids
            if search_query in channel_meta[cid]["channel_title"].lower()
            or search_query in channel_meta[cid].get("channel_description", "").lower()
            or search_query in channel_meta[cid].get("handle", "").lower()
        ]

    # — 결과 개수 및 정렬 기준 선택 —
    col1, col2 = st.columns([4, 1])
    col1.metric(label=f"결과 {len(filtered_ids)}명", value="Youtuber List")
    with col2:
        sort_key = st.selectbox(
            "정렬 기준",
            list(sort_column_map.keys()),
            index=1,                            #기본 인덱스 1번
            key=f"sort_{'_'.join(selected)}"
        )

    # — 소팅 & 렌더링 —
    sort_series = sort_column_map[sort_key] \
                  .loc[filtered_ids] \
                  .sort_values(ascending = (sort_key == "구독자 오름차순"))

    for cid in sort_series.index:
        meta = channel_meta[cid]
        stats = {
            "subs_diff":    subs_diff.get(cid, 0),
            "avg_views":    avg_views.get(cid, 0),
            "short_ratio":  short_ratio.get(cid, 0.0),
            "subscriber_count": subscriber_count.get(cid, 0.0),
        }
        render_channel_card(channel_id=cid, meta=meta, stats=stats)
