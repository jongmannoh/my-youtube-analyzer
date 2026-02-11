import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pandas as pd
from collections import Counter
import re

# 화면 설정
st.set_page_config(page_title="종맨의 유튜브 트렌드 분석기 Pro", layout="wide")
st.title("🚀 유튜브 트렌드 분석기 Pro")

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
            
            # 1. 영상 검색
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

                # 2. 영상 상세 정보(조회수) 및 채널 정보(구독자수) 가져오기
                stats_res = youtube.videos().list(part="statistics,snippet", id=",".join(v_ids)).execute()
                chan_res = youtube.channels().list(part="statistics", id=",".join(list(set(c_ids)))).execute()
                
                # 채널 구독자 수 매핑
                chan_map = {c['id']: c['statistics'].get('subscriberCount', '0') for c in chan_res.get('items', [])}
                
                final_data = []
                titles_text = ""
                
                for item in stats_res.get('items', []):
                    views = int(item['statistics'].get('viewCount', 0))
                    if views >= min_views:
                        sub_count = int(chan_map.get(item['snippet']['channelId'], 0))
                        title = item['snippet']['title']
                        titles_text += " " + title
                        
                        final_data.append({
                            "썸네일": item['snippet']['thumbnails']['medium']['url'],
                            "제목": title,
                            "채널명": item['snippet']['channelTitle'],
                            "조회수": views,
                            "구독자 수": sub_count,
                            "업로드일": item['snippet']['publishedAt'][:10],
                            "링크": f"https://youtu.be/{item['id']}"
                        })

                if final_data:
                    # 3. AI 트렌드 요약 (단어 빈도 분석)
                    words = re.findall(r'\w+', titles_text)
                    common_words = [word for word, count in Counter(words).most_common(5) if len(word) > 1]
                    
                    st.subheader("💡 최신 트렌드 핵심 요약")
                    st.info(f"현재 이 분야는 **'{', '.join(common_words)}'** 키워드를 중심으로 소비되고 있습니다. 이 키워드들을 썸네일이나 제목에 활용해 보세요!")

                    # 4. 결과 테이블 출력
                    df = pd.DataFrame(final_data)
                    st.data_editor(
                        df.sort_values(by="조회수", ascending=False),
                        column_config={
                            "썸네일": st.column_config.ImageColumn("썸네일", help="영상 썸네일"),
                            "링크": st.column_config.LinkColumn("링크", display_text="열기"),
                            "조회수": st.column_config.NumberColumn(format="%d 회"),
                            "구독자 수": st.column_config.NumberColumn(format="%d 명"),
                        },
                        hide_index=True,
                        use_container_width=True
                    )
                    st.success(f"조건에 맞는 영상 {len(final_data)}개를 찾았습니다.")
                else:
                    st.warning("조건에 맞는 영상이 없습니다.")
        except Exception as e:
            st.error(f"오류 발생: {e}")
