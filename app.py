import streamlit as st
import pandas as pd
from components.channel_card import render_channel_card
from utils.supabase.get_data import fetch_channel, fetch_all_channel_snapshots, fetch_videos

st.set_page_config(
    page_title="VPI",
    page_icon="📺",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 1) 데이터 불러오기 & 통계 계산
ch_snaps = fetch_all_channel_snapshots()  #channel_snapshots : 
# channel_id | collected_at | subscriber_count | total_view_count | video_count

channel_meta = fetch_channel()  #channels table 불러오기
# id | title | description | handle | category | joindate | total_view_count, video_count(삭제예정)

videos_data = fetch_videos()  #videos table 불러오기
# id | channel_id | title | published_at | is_short | thumbnail_url | saved_at 

latest = ch_snaps.sort_values(by='collected_at').groupby('channel_id').last()
earliest = ch_snaps.sort_values(by='collected_at').groupby('channel_id').first()

# 정렬 기준 맵
subs_diff    = latest['subscriber_count'] - earliest['subscriber_count']
avg_views    = latest['total_view_count'] / latest['video_count']
short_ratio  = videos_data.groupby('channel_id')['is_short'].mean()
subscriber_count = latest['subscriber_count']

sort_column_map = {
    "구독자 내림차순": latest['subscriber_count'],
    "구독자 오름차순": latest['subscriber_count'],
    "구독자 급상승": subs_diff,
    "Shorts 비율": short_ratio
}

# 카테고리 리스트
categories = ["전체"] + sorted({meta["category"]
                               for meta in channel_meta.values()
                               if "category" in meta and meta["category"]})

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
            if search_query in channel_meta[cid]["title"].lower()
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
            index=0,                            #기본 인덱스 1번
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
