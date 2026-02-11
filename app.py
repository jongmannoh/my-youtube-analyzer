import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pandas as pd

# 화면 설정
st.set_page_config(page_title="종맨의 유튜브 트렌드 분석기", layout="wide")
st.title("📊 유튜브 트렌드 분석기")

# 사이드바 설정
with st.sidebar:
    st.header("🔍 검색 필터")
    
    # 비밀 금고(Secrets)에서 키를 먼저 찾아보고, 없으면 빈칸으로 둡니다.
    default_api_key = st.secrets.get("YOUTUBE_API_KEY", "")
    api_key = st.text_input("YouTube API 키", value=default_api_key, type="password")
    
    keyword = st.text_input("검색어", value="여행 유튜브")
    days_limit = st.select_slider("업로드 날짜 (며칠 이내)", options=[10, 20, 30], value=10)
    min_views = st.number_input("최소 조회수", value=10000, step=10000)
    max_results = st.slider("가져올 영상 개수", 1, 50, 20)
    
    duration = st.selectbox("영상 길이", ["전체", "short (<4분)", "medium (4~20분)", "long (>20분)"])
    duration_map = {"전체": "any", "short (<4분)": "short", "medium (4~20분)": "medium", "long (>20분)": "long"}

if st.button("분석 시작!"):
    if not api_key:
        st.error("API 키를 입력하거나 Secrets에 등록해주세요!")
    else:
        try:
            youtube = build('youtube', 'v3', developerKey=api_key)
            target_date = (datetime.utcnow() - timedelta(days=days_limit)).isoformat() + "Z"
            
            search_res = youtube.search().list(
                q=keyword, part="snippet", publishedAfter=target_date,
                videoDuration=duration_map[duration], maxResults=max_results, type="video"
            ).execute()
            
            v_ids = [item['id']['videoId'] for item in search_res.get('items', [])]
            
            if not v_ids:
                st.warning("검색 결과가 없습니다.")
            else:
                stats_res = youtube.videos().list(
                    part="statistics,snippet", id=",".join(v_ids)
                ).execute()
                
                final_data = []
                for item in stats_res.get('items', []):
                    views = int(item['statistics'].get('viewCount', 0))
                    if views >= min_views:
                        final_data.append({
                            "제목": item['snippet']['title'],
                            "채널": item['snippet']['channelTitle'],
                            "조회수": views,
                            "업로드일": item['snippet']['publishedAt'][:10],
                            "링크": f"https://youtu.be/{item['id']}"
                        })
                
                if final_data:
                    df = pd.DataFrame(final_data)
                    st.dataframe(df.sort_values(by="조회수", ascending=False), use_container_width=True)
                    st.success(f"총 {len(final_data)}개의 영상을 찾았습니다!")
                else:
                    st.warning("조회수 조건에 맞는 영상이 없습니다.")
        except Exception as e:
            st.error(f"오류 발생: {e}")
