import base64
import requests
import streamlit.components.v1 as components

def img_url_to_base64(url):
    response = requests.get(url)
    return base64.b64encode(response.content).decode()

def render_name_card(channel_meta: dict, channel_id: str, ch_df):
    """
    유튜브 채널 프로필과 채널 정보를 렌더링하는 Streamlit HTML 컴포넌트.
    - channel_meta: 채널 메타 딕셔너리
    - channel_id: 현재 채널 ID
    - ch_df: 채널 일별 스냅샷 DataFrame (subscriber_count, category 등 컬럼 포함)
    """
    # 1) 프로필 이미지 URL → base64
    profile_url = channel_meta[channel_id]["profile_image"]
    img_base64 = img_url_to_base64(profile_url)

    # 2) HTML 템플릿
    html = f"""
    <div class="yt-profile">
        <img class="channel-img" src="data:image/jpeg;base64,{img_base64}" alt="채널 이미지">
        <div class="channel-info">
            <div class=Name-tag>
                <h2 class="channel-name">{channel_meta[channel_id]["channel_title"]}</h2>
                <p class="handle">{channel_meta[channel_id]["handle"]}</p>
            </div>
            <p class="category">#{ch_df['category'].iloc[-1]}</p>
        </div>
    </div>

    <style>
    .category {{
        font-size: 15px;
        width: min-content;
        color: #444;
        padding: 4px 10px;
        background-color: hsla(0, 0%, 20%, 0.2);
        border-radius: 8px;
        white-space: nowrap;
    }}

    .yt-profile {{
        display: flex;
        align-items: center;
        background-color: #f9f9f9;
        border-radius: 12px;
        padding: 0px;
        box-shadow: 0 2px 6px rgba(0,0,0,0.1);
    }}

    .Name-tag{{
        display: flex;
        gap: 10px;
    }}
    .channel-img {{
        width: 120px;
        height: 120px;
        object-fit: cover;
        margin-right: 20px;
        border: 2px solid #ccc;
        border-radius: 10px;
    }}

    .channel-info {{
        flex: 1;
    }}

    .channel-name {{
        margin: 0;
        font-size: 32px;
        font-weight: bold;
        color: #222;
    }}

    .handle {{
        font-size: 16px;
        color: #777;
    }}
    </style>
    """

    # 3) Streamlit에 렌더링
    components.html(html, height=160)