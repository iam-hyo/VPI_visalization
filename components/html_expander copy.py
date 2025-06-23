# components/html_utils.py
from streamlit.components.v1 import html as st_html
import streamlit as st
from datetime import datetime, timezone
import pandas as pd

def summary_card(
    thumbnail_url: str,
    title: str,
    badge: str,
    views_str: str,
    pub_str: str,
    days_since_pub: int,
    expected_str: str
):
    """카드 요약부만 HTML로 렌더링"""

    summary_html = f"""
    <style>
    .card-summary {{ display:flex; align-items:center; 
                    border:1px solid #ddd; border-radius:8px; 
                    padding:12px; margin-bottom:4px; }}
    .card-summary img {{ width:80px; height:80px; object-fit:cover; border-radius:4px; margin-right:12px; }}
    .card-summary .info {{ flex:1; }}
    .badge {{ display:inline-block; padding:2px 6px; border-radius:4px;
                font-size:0.75em; color:#fff; margin-left:8px; }}
    .badge-shorts {{ background:#ff5f5f; }}
    .badge-long   {{ background:#5f9aff; }}
    .card-summary h3 {{ margin:0 0 4px 0; font-size:1.1em; }}
    .card-summary p {{ margin:0; font-size:0.9em; color:#555; }}
    </style>
    <div class="card-summary">
    <img src="{thumbnail_url}" alt="thumbnail"/>
    <div class="info">
        <h3>{title}
        <span class="badge {'badge-shorts' if badge=='Shorts' else 'badge-long'}">{badge}</span>
        </h3>
        <p>조회수: {views_str}  |  공개일: {pub_str}  |  공개 {days_since_pub}일차</p>
        <p>기대 조회수: {expected_str}</p>
    </div>
    </div>
    """
    st_html(summary_html, height=100)  # summary 높이만큼만

def detail_expander(
    chart_html: str,
    like_count: int = None,
    comment_count: int = None,
    video_id: str = "",
    key: str = None
):
    """‘자세히 보기’ Expander 안에 상세 콘텐츠를 넣기"""
    with st.expander("▶ 자세히 보기", expanded=False):
        # 1) 차트
        st.components.v1.html(chart_html, height=400, scrolling=False)
        # 2) 메트릭
        st.markdown(f"👍 좋아요: {like_count if like_count is not None else '-'}회  |  💬 댓글: {comment_count if comment_count is not None else '-'}회")
        # 3) 버튼
        st.markdown(f"[▶ 유튜브에서 보기](https://www.youtube.com/watch?v={video_id})")
