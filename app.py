import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pandas as pd
from collections import Counter
import re

# 화면 설정
st.set_page_config(page_title="종맨의 유튜브 트렌드 분석기 Pro", layout="wide")
st.title("🚀 유튜브 트렌드 분석기 Pro")

# 숫자 단위를 '만'으로 변환하는 함수
def format_man(n):
    if n >= 10000:
        return f"{n/10000:.1f}만"
    return f"{n:,}"

# 사이드바 설정
with st.sidebar:
    st.header("🔍 검색 필터")
    default_api_key = st.secrets.get("YOUTUBE_API_KEY", "")
    api_key = st.text_input("YouTube API 키", value=default_api_key, type="password")
    
    keyword = st.text_input("검색어", value="AI 애니메이션")
    days_limit = st.select_slider("업로드 날짜 (며칠 이내)", options=[10, 20, 30], value=10)
    min_views = st.number_input("최소 조회수", value=10000, step=10000)
    max_results = st.slider("가져올 영상 개수", 1, 50, 20)
    
    duration = st.selectbox("영상 길이", ["전체", "short (<4분)", "medium (4~20분)", "long (>20분)"])
    duration_map = {"전체": "any", "short (<4분)": "short", "medium (4~20분)": "medium", "long (>20분)": "long"}

if st.button("분석 시작!"):
    if not api_key:
        st.error("API 키를 등록해주세요!")
    else:
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            target_date = (datetime.utcnow() - timedelta(days=days_limit)).isoformat() + "Z"
            
            search_res = youtube.search().list(
                q=keyword, part="snippet", publishedAfter=target_date,
                videoDuration=duration_map[duration], maxResults=max_results, type="video"
            ).execute()
            
            v_items = search_res.get('items', [])
            if not v_items:
                st.warning("검색 결과가 없습니다.")
            else:
                v_ids = [item['id']['videoId'] for item in v_items]
                c_ids = [item['snippet']['channelId'] for item in v_items]

                stats_res = youtube.videos().list(part="statistics,snippet", id=",".join(v_ids)).execute()
                chan_res = youtube.channels().list(part="statistics", id=",".join(list(set(c_ids)))).execute()
                
                chan_map = {c['id']: c['statistics'].get('subscriberCount', '0') for c in chan_res.get('items', [])}
                
                titles_text = ""
                final_data = []
                
                for item in stats_res.get('items', []):
                    views = int(item['statistics'].get('viewCount', 0))
                    if views >= min_views:
                        sub_count = int(chan_map.get(item['snippet']['channelId'], 0))
                        title = item['snippet']['title']
                        titles_text += " " + title
                        
                        final_data.append({
                            "thumb": item['snippet']['thumbnails']['high']['url'], # 더 고화질 썸네일
                            "title": title,
                            "channel": item['snippet']['channelTitle'],
                            "views": views,
                            "subs": sub_count,
                            "date": item['snippet']['publishedAt'][:10],
                            "link": f"https://youtu.be/{item['id']}"
                        })

                if final_data:
                    # 1. AI 트렌드 요약
                    words = re.findall(r'\w+', titles_text)
                    common_words = [word for word, count in Counter(words).most_common(5) if len(word) > 1]
                    st.subheader("💡 최신 트렌드 핵심 요약")
                    st.info(f"현재 핵심 키워드: **{', '.join(common_words)}**")

                    # 2. 리스트형 결과 출력 (썸네일을 크게 보기 위함)
                    st.divider()
                    for video in final_data:
                        col1, col2 = st.columns([1, 2]) # 왼쪽 1: 오른쪽 2 비율
                        
                        with col1:
                            st.image(video['thumb'], use_container_width=True)
                        
                        with col2:
                            st.markdown(f"### [{video['title']}]({video['link']})")
                            st.write(f"📺 **채널**: {video['channel']} | 👥 **구독자**: {format_man(video['subs'])}")
                            st.write(f"🔥 **조회수**: {format_man(video['views'])} | 📅 **업로드**: {video['date']}")
                            st.link_button("영상 보러가기", video['link'])
                        st.divider()
                else:
                    st.warning("조건에 맞는 영상이 없습니다.")
        except Exception as e:
            st.error(f"오류 발생: {e}")
