import streamlit as st
from googleapiclient.discovery import build
from datetime import datetime, timedelta
import pandas as pd
from collections import Counter
import re

# 화면 설정
st.set_page_config(page_title="종맨의 유튜브 AI 전략 분석기", layout="wide")
st.title("🚀 유튜브 콘텐츠 벤치마킹 전략기")

def format_man(n):
    if n >= 10000: return f"{n/10000:.1f}만"
    return f"{n:,}"

# 사이드바 설정
with st.sidebar:
    st.header("🔍 분석 및 필터 설정")
    default_api_key = st.secrets.get("YOUTUBE_API_KEY", "")
    api_key = st.text_input("YouTube API 키", value=default_api_key, type="password")
    keyword = st.text_input("검색 키워드", value="AI 애니메이션")
    days_limit = st.select_slider("날짜 범위 (최근)", options=[10, 20, 30], value=10)
    min_views = st.number_input("최소 조회수", value=10000, step=10000)
    
    st.divider()
    # 벤치마킹 특화 필터
    only_viral = st.checkbox("🔥 바이럴 영상만 보기 (지수 5배 이상)")
    sort_by = st.selectbox("정렬 기준", ["조회수 높은 순", "바이럴 지수 높은 순"])
    
    max_results = st.slider("최대 분석 수", 4, 100, 40)
    duration = st.selectbox("영상 길이", ["전체", "short (<4분)", "medium (4~20분)", "long (>20분)"])
    duration_map = {"전체": "any", "short (<4분)": "short", "medium (4~20분)": "medium", "long (>20분)": "long"}

if st.button("전략 분석 시작!"):
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
                
                # 상세 정보(태그 포함) 가져오기
                stats_res = youtube.videos().list(part="statistics,snippet", id=",".join(v_ids)).execute()
                chan_res = youtube.channels().list(part="statistics", id=",".join(list(set(c_ids)))).execute()
                chan_map = {c['id']: int(c['statistics'].get('subscriberCount', 0)) for c in chan_res.get('items', [])}
                
                final_data = []
                all_tags = []
                titles_text = ""
                
                for item in stats_res.get('items', []):
                    views = int(item['statistics'].get('viewCount', 0))
                    if views >= min_views:
                        subs = chan_map.get(item['snippet']['channelId'], 0)
                        viral_score = views / subs if subs > 0 else 0
                        
                        # 필터 적용
                        if only_viral and viral_score < 5: continue
                        
                        tags = item['snippet'].get('tags', [])
                        all_tags.extend(tags)
                        title = item['snippet']['title']
                        titles_text += " " + title
                        
                        final_data.append({
                            "thumb": item['snippet']['thumbnails']['medium']['url'],
                            "title": title,
                            "channel": item['snippet']['channelTitle'],
                            "views": views,
                            "subs": subs,
                            "viral_score": viral_score,
                            "tags": ", ".join(tags[:5]), # 상위 5개 태그만 저장
                            "date": item['snippet']['publishedAt'][:10],
                            "link": f"https://youtu.be/{item['id']}"
                        })

                if final_data:
                    # 정렬 적용
                    if sort_by == "조회수 높은 순":
                        final_data = sorted(final_data, key=lambda x: x['views'], reverse=True)
                    else:
                        final_data = sorted(final_data, key=lambda x: x['viral_score'], reverse=True)

                    # --- 1. AI 벤치마킹 리포트 ---
                    st.subheader("📝 AI 벤치마킹 리포트")
                    c1, c2, c3 = st.columns(3)
                    
                    with c1:
                        top_keywords = re.findall(r'\w+', titles_text)
                        common_words = [w for w, c in Counter(top_keywords).most_common(5) if len(w) > 1]
                        st.info(f"🔑 **추천 제목 키워드**\n{', '.join(common_words)}")
                        
                    with c2:
                        common_tags = [t for t, c in Counter(all_tags).most_common(5)]
                        st.success(f"🏷️ **대박 영상 SEO 태그**\n{', '.join(common_tags)}")
                        
                    with c3:
                        st.download_button(
                            label="📥 분석 데이터 CSV 다운로드",
                            data=pd.DataFrame(final_data).drop(columns=['thumb']).to_csv(index=False).encode('utf-8-sig'),
                            file_name=f"youtube_analysis_{keyword}.csv",
                            mime='text/csv'
                        )
                    
                    st.divider()

                    # --- 2. 그리드 출력 ---
                    cols = st.columns(4)
                    for idx, video in enumerate(final_data):
                        with cols[idx % 4]:
                            st.markdown(f'<a href="{video["link"]}" target="_blank"><img src="{video["thumb"]}" style="width:100%; border-radius:8px;"></a>', unsafe_allow_html=True)
                            st.markdown(f"**[{video['title'][:35]}..]({video['link']})**")
                            st.caption(f"{video['channel']} | 👤 {format_man(video['subs'])}")
                            
                            score_color = "green" if video['viral_score'] > 5 else "white"
                            st.markdown(f"🔥 {format_man(video['views'])} | <span style='color:{score_color}; font-weight:bold;'>지수: {video['viral_score']:.1f}배</span>", unsafe_allow_html=True)
                            
                            if video['tags']:
                                st.caption(f"🏷️ {video['tags']}")
                            st.write("---")
                else:
                    st.warning("조건에 맞는 영상이 없습니다. 필터를 조절해 보세요.")
        except Exception as e:
            st.error(f"오류 발생: {e}")
