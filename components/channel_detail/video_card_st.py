# components/video_card_st.py
import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
import numpy as np

def render_video_card(
    row: pd.Series,
    snapshot_df: pd.DataFrame,
    metrics_df: pd.DataFrame,
    tab_name: str
):
    col1, col2, col3 = st.columns([1.5, 4.5, 2])

    # ─── 1열: 썸네일 ─────────────────────────
    with col1:
        st.image(row["thumbnail_url"], use_container_width=True)

    # ─── 2열: 제목+태그 · info · 액션 버튼 ───────────────
    with col2:
        # (1) 제목 + 배지 (HTML로 묶어서 공백 없이)
        title, badge = row["title"], ("Shorts" if row["is_short"] else "Long-form")
        color = "#ff5f5f" if row["is_short"] else "#5f9aff"
        st.markdown(
            f'''
            <div style="display:flex; align-items:center; gap:8px; margin-bottom:4px;">
              <h3 style="margin:0; line-height:1.2;">{title}</h3>
              <span style="
                background:{color};
                color:#fff;
                padding:2px 6px;
                border-radius:4px;
                font-size:0.9em;
                white-space:nowrap;
              ">{badge}</span>
            </div>
            ''',
            unsafe_allow_html=True
        )

        # (2) info 행들: 덜 강조되는 caption으로
        info0, info1, info2 = st.columns([1,1,2])
        info0.caption(f"| 조회수 {row['view_count']:,}회")
        info1.caption(f"| 공개일 {row['published_at'].strftime('%Y-%m-%d')}")
        info2.caption(f"| D+{row['day_since_pub']}일")
        

        # (3) 댓글·좋아요·링크/버튼 행
        a0, a1, a2, a3 = st.columns(4)
        a0.caption(f"| 기대 조회수 {int(row['expected_views']):,}회")
        a1.caption(f"💬 {row.get('comment_count', 0):,}")
        a2.caption(f"👍 {row.get('like_count', 0):,}")
        
        # st.button으로 “영상 보러가기” → JS로 새 탭 열기
        btn = a3.button(
            "영상 보러가기",
            key=f"watch-{row.name}-{tab_name}"
        )
        if btn:
            url = f"https://www.youtube.com/watch?v={row['video_id']}"
            components.html(f"<script>window.open('{url}','_blank')</script>")

        # (4) Popover 차트
        pop_label = f"조회수 추이🔍)"
        with st.popover(pop_label, icon="📈", use_container_width=True):
            df_act = (
                snapshot_df.groupby("day_since_pub")["view_count"]
                           .mean()
                           .rename("actual")
            )
            df_exp = metrics_df.set_index("day")["cumulative_view_count"].rename("expected")
            df_plot = pd.concat([df_act, df_exp], axis=1).ffill()
            st.line_chart(df_plot, use_container_width=True)

    # ───── 3열: 지표 ─────────────────────────
    with col3:
        index0, index1, index2 = st.columns(3)
        with index0:
            st.markdown(f"""
                <span style="
                    background:#28a745;
                    color:#fff;
                    padding:2px 6px;
                    border-radius:4px;
                    font-size:0.9em;
                    white-space:nowrap;
                ">전환율 기반</span>
                """, unsafe_allow_html=True)
            retain = row['view_count'] / row['expected_views'] if row['expected_views'] else "-"
            subs_contrib = float(row["subs_contrib"])
            gain = row.get('gain_score')
            gain_display = "N/A" if not gain else f"{gain:.2f}"
            st.metric("Gain Index", f"{gain_display}")
            st.metric("추정 구독자 증분", f"{subs_contrib:.1f}명")     
            st.metric("Retention index", f"{retain:.2f}" if isinstance(retain, (int, float)) else "-")

        with index1:
            st.markdown(f"""
                <span style="
                    background:#28a745;
                    color:#fff;
                    padding:2px 6px;
                    border-radius:4px;
                    font-size:0.9em;
                    white-space:nowrap;
                ">조회수 기반</span>
                """, unsafe_allow_html=True)

            def safe_metric(val, float_fmt="{:.2f}", suffix=""):
                # 0도 N/A로 처리하려면 아래처럼
                if isinstance(val, (int, float, np.floating)) and not pd.isna(val) and val != 0:
                    return float_fmt.format(val) + suffix
                return "N/A" + suffix
            st.metric(label="Gain index", value=safe_metric(row.get('gain_score2')))
            st.metric(label='추정 구독자 기여', value=safe_metric(row.get('estimated_subs'), "{:.1f}", "명"))
            st.metric(label="Retention index", value=safe_metric(row.get('retention_score')))

        with index2:
            st.markdown(f"""
                <span style="
                    background:#28a745;
                    color:#fff;
                    padding:2px 6px;
                    border-radius:4px;
                    font-size:0.9em;
                    white-space:nowrap;
                ">회귀 기반</span>
                """, unsafe_allow_html=True)
            gain = row.get("βᵢ / β_mean", "N/A")
            contrib = row.get("regression_subs_contrib", "N/A")
            retain = row.get("retention_index", 0)

            st.metric("Gain Index", f"{gain:.2f}" if isinstance(gain, (int, float)) else str(gain))
            st.metric("추정 구독자 증분", f"{contrib:.1f}명" if isinstance(contrib, (int, float)) else str(contrib))
            st.metric("Retention index", f"{retain:.2f}")

    st.write("---")
