# components/charts.py
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

def render_avg_views_table(df_metrics):  # 일차별 평균조회수 테이블
    """
    df_metrics: ['day', '평균 누적 조회수']
    """
    df_metrics = df_metrics.map(lambda x: f"{int(x):,}")
    st.dataframe(df_metrics)

# def render_avg_views_line_chart(df_metrics, title: str = ""):
#     # 1) 일별 증분 계산
#     df_metrics['평균 증분 조회수'] = df_metrics['평균 누적 조회수'].diff().fillna(df_metrics['cumulative_view_count'])

#     # 전체 30일치 데이터
#     fig = px.line(
#         df_metrics,
#         x='day',
#         y='avg_view_count',
#         markers=True
#     )

#     # tick 값과 레이블 생성 (예: 1일,2일,…,30일)
#     tickvals = list(df_metrics['day'])
#     ticktext = [f"{int(d)}일" for d in tickvals]

#     # 레이아웃 업데이트
#     fig.update_layout(
#         xaxis=dict(
#             tickmode='array',
#             tickvals=tickvals,
#             ticktext=ticktext,
#             range=[1, 30],               # 초기 뷰: [1, 30]일
#             rangeslider=dict(visible=True),
#             title=None                   # x축 제목 제거
#         ),
#         yaxis=dict(
#             tickformat=',.0f',           # 천 단위 콤마 (예: 200,000)
#             range=[0, df_metrics['avg_view_count'].max() * 1.1],
#             title=None                   # y축 제목 제거
#         ),
#         margin=dict(l=40, r=20, t=20, b=40)
#     )

#     st.plotly_chart(fig, use_container_width=True)

def render_avg_views_line_chart(df_metrics, title: str = ""):
    """ 
    df_metrics: ['day', 'cumulative_view_count']
    """
    # 1) 일별 증분 계산
    df = df_metrics.copy()
    df['평균 증분 조회수'] = df['cumulative_view_count'].diff().fillna(df['cumulative_view_count'])

    # 2) 서브플롯으로 secondary_y 축 생성
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # (a) cumulative_view_count (좌측 Y축)
    fig.add_trace(
        go.Scatter(
            x=df['day'],
            y=df['cumulative_view_count'],
            name='평균 누적 조회수',
            mode='lines+markers'
        ),
        secondary_y=False
    )

    # (b) 일별 평균 증분 조회수 (우측 Y축)
    fig.add_trace(
        go.Scatter(
            x=df['day'],
            y=df['평균 증분 조회수'],
            name='평균 증분 조회수',
            mode='lines+markers'
        ),
        secondary_y=True
    )

    # 3) 축 & 레이아웃 설정
    tickvals = df['day'].tolist()
    ticktext = [f"{int(d)}일" for d in tickvals]

    fig.update_layout(
        title=title or "일별 누적 조회수 및 증분 조회수",
        xaxis=dict(
            tickmode='array',
            tickvals=tickvals,
            ticktext=ticktext,
            range=[min(tickvals), max(tickvals)],
            rangeslider=dict(visible=True),
            title=None
        ),
        margin=dict(l=50, r=50, t=50, b=50),
        legend=dict(yanchor="top", y=0.99, xanchor="left", x=0.01)
    )

    # 좌측 Y축: cumulative_view_count (천 단위 콤마)
    fig.update_yaxes(
        title_text='평균 누적 조회수 (회)',
        tickformat=',.0f',
        range=[0, df['cumulative_view_count'].max() * 1.1],
        secondary_y=False
    )

    # 우측 Y축: 평균 증분 조회수 (회), 단위 포맷 다르게 지정
    fig.update_yaxes(
        title_text='평균 증분 조회수 (회)',
        tickformat=',.0f',
        range=[0, df['평균 증분 조회수'].max() * 1.1],
        secondary_y=True
    )

    st.plotly_chart(fig, use_container_width=True)


def render_estimated_subscribers_chart(df: pd.DataFrame) -> None:
    # Plotly Express를 사용해 일별 추정 구독자수를 라인 차트로 렌더링 (매일 포인트 포함)

    df_plot = df.copy()
    df_plot['Date'] = pd.to_datetime(df_plot['Date'])

    # y축 범위: 실제 최소/최대값
    y_min = df_plot['Estimated Subscribers'].min()
    y_max = df_plot['Estimated Subscribers'].max()

    # 라인 차트 생성 (매일 포인트 표시)
    fig = px.line(
        df_plot,
        x='Date',
        y='Estimated Subscribers',
        markers=True,
        title=''  # 제목 없음
    )
    # x축: MM월DD일 포맷, 라벨 각도
    fig.update_xaxes(
        tickformat='%m월%d일',
        tickangle=0,
        title_text=''
        )
    # y축: 범위 설정 및 제목
    fig.update_yaxes(
        range=[y_min, y_max],
        title_text='구독자 수',
        tickformat=',.0f',
    )
    # 범례 제거
    fig.update_layout(showlegend=False)

    st.plotly_chart(fig, use_container_width=True)


