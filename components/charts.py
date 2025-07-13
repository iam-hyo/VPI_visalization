# components/charts.py
import streamlit as st
import pandas as pd
import plotly.express as px

def render_avg_views_table(df_metrics):  # 일차별 평균조회수 테이블
    """
    df_metrics: ['day', '평균 조회수']
    """
    df_metrics = df_metrics.map(lambda x: f"{int(x):,}")
    st.dataframe(df_metrics)

def render_avg_views_line_chart(df_metrics, title: str = ""):
    # 전체 30일치 데이터
    fig = px.line(
        df_metrics,
        x='day',
        y='avg_view_count',
        markers=True
    )

    # tick 값과 레이블 생성 (예: 1일,2일,…,30일)
    tickvals = list(df_metrics['day'])
    ticktext = [f"{int(d)}일" for d in tickvals]

    # 레이아웃 업데이트
    fig.update_layout(
        xaxis=dict(
            tickmode='array',
            tickvals=tickvals,
            ticktext=ticktext,
            range=[1, 10],               # 초기 뷰: 1~10일
            rangeslider=dict(visible=True),
            title=None                   # x축 제목 제거
        ),
        yaxis=dict(
            tickformat=',.0f',           # 천 단위 콤마 (예: 200,000)
            range=[0, df_metrics['avg_view_count'].max() * 1.1],
            title=None                   # y축 제목 제거
        ),
        margin=dict(l=40, r=20, t=20, b=40)
    )

    st.plotly_chart(fig, use_container_width=True)