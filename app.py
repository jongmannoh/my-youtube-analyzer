import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pandas as pd
from collections import Counter
import re

# 화면 설정
st.set_page_config(page_title="종맨의 유튜브 AI 전략가", layout="wide")
st.title("🤖 유튜브 AI 트렌드 전략가")

def format_man(n):
    if n >= 10000: return f"{n/10000:.1f}만"
    return f"{n:,}"

# 사이드바 설정
with st.sidebar:
    st.header("🔍 분석 조건")
    default_api_key = st.secrets.get("YOUTUBE_API_KEY", "")
    api_key = st.text_input("YouTube API 키", value=default_api_key, type="password")
    keyword = st.text_input("검색어", value="AI 애니메이션")
    days_limit = st.select_slider("날짜 범위", options=[10, 20, 30], value=10)
    min_views = st.number_input("최소 조회수", value=10000, step=10000)
    max_results = st.slider("분석 영상 수", 4, 100, 40)
    duration = st.selectbox("영상 길이", ["전체", "short (<4분)", "medium (4~20분)", "long (>20분)"])
    duration_map = {"전체": "any", "short (<4분)": "short", "medium (4~20분)": "medium", "long (>20분)": "long"}

if st.button("AI 전략 분석 시작!"):
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
                st.warning("결과가 없습니다.")
            else:
                v_ids = [item['id']['videoId'] for item in v_items]
                c_ids = [item['snippet']['channelId'] for item in v_items]
                stats_res = youtube.videos().list(part="statistics,snippet", id=",".join(v_ids)).execute()
                chan_res = youtube.channels().list(part="statistics", id=",".join(list(set(c_ids)))).execute()
                chan_map = {c['id']: int(c['statistics'].get('subscriberCount', 0)) for c in chan_res.get('items', [])}
                
                final_data = []
                titles_text = ""
                for item in stats_res.get('items', []):
                    views = int(item['statistics'].get('viewCount', 0))
                    if views >= min_views:
                        subs = chan_map.get(item['snippet']['channelId'], 0)
                        # 바이럴 지수 계산
                        viral_score = views / subs if subs > 0 else 0
                        final_data.append({
                            "thumb": item['snippet']['thumbnails']['medium']['url'],
                            "title": item['snippet']['title'],
                            "channel": item['snippet']['channelTitle'],
                            "views": views,
                            "subs": subs,
                            "viral_score": viral_score,
                            "date": item['snippet']['publishedAt'][:10],
                            "link": f"https://youtu.be/{item['id']}"
                        })
                        titles_text += " " + item['snippet']['title']

                if final_data:
                    # 조회수 높은 순으로 정렬
                    final_data = sorted(final_data, key=lambda x: x['views'], reverse=True)
                    
                    # --- AI 인사이트 섹션 ---
                    st.subheader("💡 AI 전략 보고서")
                    words = re.findall(r'\w+', titles_text)
                    common_words = [word for word, count in Counter(words).most_common(5) if len(word) > 1]
                    
                    viral_videos = [v for v in final_data if v['viral_score'] > 5]
                    
                    c1, c2 = st.columns(2)
                    with c1:
                        st.info(f"✅ **핵심 키워드**: {', '.join(common_words)}")
                    with c2:
                        if viral_videos:
                            st.success(f"🔥 **바이럴 영상 발견**: 총 {len(viral_videos)}개의 영상이 구독자 수 대비 압도적인 조회수를 기록 중입니다.")
                        else:
                            st.warning("⚠️ 현재 대형 채널들이 점유 중인 키워드입니다.")
                    
                    st.divider()

                    # --- 4열 그리드 출력 ---
                    cols = st.columns(4)
                    for idx, video in enumerate(final_data):
                        with cols[idx % 4]:
                            # 썸네일 (클릭 시 링크)
                            st.markdown(f'<a href="{video["link"]}" target="_blank"><img src="{video["thumb"]}" style="width:100%; border-radius:8px;"></a>', unsafe_allow_html=True)
                            
                            # 제목
                            short_title = video['title'][:35] + ".." if len(video['title']) > 35 else video['title']
                            st.markdown(f"**[{short_title}]({video['link']})**")
                            
                            # 정보 표시
                            st.caption(f"{video['channel']} (👤 {format_man(video['subs'])})")
                            
                            # 조회수 및 바이럴 지수 표시
                            v_text = f"🔥 {format_man(video['views'])}"
                            score_text = f"📈 **지수**: {video['viral_score']:.1f}배"
                            
                            if video['viral_score'] > 5:
                                st.write(f"{v_text} | {score_text} 🚀")
                            else:
                                st.write(f"{v_text} | {score_text}")
                                
                            st.write(f"📅 {video['date']}")
                            st.write("---")
                else:
                    st.warning("조건에 맞는 영상이 없습니다.")
        except Exception as e:
            st.error(f"오류 발생: {e}")
