import streamlit as st
import pandas as pd
import random
import re
import requests

# === 標題設定 ===
st.title("📚 雲端同步單字複習 App")
st.caption("依 Score 由低到高排序（同分隨機） ＋ 例句智慧挖空卡")

# ===================================================
# 🔗 請填入你的 Google 試算表 CSV 連結與你部署的 App Script 網址
# ===================================================
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1p4wj-mOuIDYFU81JAIwYOhDfVF5PPrDyidCtMLtowGs/export?format=csv"
API_URL = "https://script.google.com/macros/s/這裡替換成你複製的網頁應用程式網址/exec" 

# === 核心邏輯：自動從雲端下載資料 ===
@st.cache_data(ttl=600)
def load_data_from_drive(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce')
        df = df.dropna(subset=['Word', 'Score'])
        return df
    except Exception as e:
        st.error(f"連線至 Google Drive 失敗: {e}")
        return None

df = load_data_from_drive(GOOGLE_SHEET_CSV_URL)

# 雲端同步改分函式
def update_score_in_cloud(word, action):
    with st.spinner("正在同步修改雲端分數..."):
        try:
            res = requests.get(API_URL, params={"word": word, "action": action})
            if "Success" in res.text:
                st.toast(f"✅ 雲端同步成功！單字 [{word}] 分數已變更。")
                st.cache_data.clear() # 清除快取，確保下次能抓到最新狀態
            else:
                st.error(f"雲端改分失敗: {res.text}")
        except Exception as e:
            st.error(f"連線至雲端修改失敗: {e}")

if df is not None:
    required_columns = ['Word', 'Sentence', 'Score']
    if not all(col in df.columns for col in required_columns):
        st.error("❌ 雲端檔案欄位不符！您的試算表必須包含：'Word'、'Sentence'、'Score'")
        st.stop()
        
    # 側邊欄簡化：同步功能與分數篩選
    st.sidebar.header("⚙️ 設定與功能")
    if st.sidebar.button("🔄 同步雲端最新單字"):
        st.cache_data.clear()
        st.rerun()

    all_scores = sorted(df['Score'].unique().tolist())
    selected_scores = st.sidebar.multiselect("篩選你要複習的 Score", options=all_scores, default=all_scores)
    
    filtered_df = df[df['Score'].isin(selected_scores)]
    if filtered_df.empty:
        st.warning("⚠️ 目前選取的 Score 條件下沒有任何單字。")
        st.stop()

    # 初始化排序邏輯
    state_key = f"vocab_drive_{str(selected_scores)}"
    if st.session_state.get("current_state_key") != state_key:
        raw_list = filtered_df.to_dict(orient='records')
        random.shuffle(raw_list)  # 同分抽樣隨機化
        st.session_state.vocab_list = sorted(raw_list, key=lambda x: x['Score'])  # 由低到高排序
        st.session_state.current_index = 0
        st.session_state.show_definition = False
        st.session_state.current_state_key = state_key

    vocab_list = st.session_state.vocab_list
    current_idx = st.session_state.current_index
    current_vocab = vocab_list[current_idx]
    
    target_word = str(current_vocab['Word']).strip()
    full_sentence = str(current_vocab['Sentence'])
    
    # 正規表達式智慧挖空
    pattern = re.compile(rf'\b{re.escape(target_word)}\b', re.IGNORECASE)
    if not pattern.search(full_sentence):
        pattern = re.compile(re.escape(target_word), re.IGNORECASE)
    hidden_sentence = pattern.sub(" `_______` ", full_sentence)
    
    # === 顯示單字卡內容 ===
    with st.container(border=True):
        if not st.session_state.show_definition:
            # 💡 已移除原先的提示標頭，直接顯示例句題目
            st.info(hidden_sentence)
            st.markdown(f"<p style='text-align: center; color: #FF4B4B; font-weight: bold; margin-top: 15px;'>當前單字 Score：{current_vocab['Score']}</p>", unsafe_allow_html=True)
            st.write("---")
            st.write("*(點擊下方「翻轉單字卡」查看答案)*")
        else:
            st.markdown(f"<h1 style='text-align: center; color: #4A90E2;'>{target_word}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; color: #888888;'>Score：{current_vocab['Score']}</p>", unsafe_allow_html=True)
            st.write("---")
            st.write(f"**💡 完整句子：**")
            st.success(full_sentence)

    # 調整分數按鈕（直接連動雲端）
    score_col1, score_col2 = st.columns(2)
    with score_col1:
        if st.button("👍 太簡單了！Score + 1", use_container_width=True):
            update_score_in_cloud(target_word, "up")
            st.session_state.vocab_list[current_idx]['Score'] += 1
            st.rerun()
    with score_col2:
        if st.button("👎 還不熟練...Score - 1", use_container_width=True):
            update_score_in_cloud(target_word, "down")
            st.session_state.vocab_list[current_idx]['Score'] -= 1
            st.rerun()

    st.write("") # 留空行

    # 單字卡切換控制按鈕
    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("⬅️ 上一個", use_container_width=True):
            if st.session_state.current_index > 0:
                st.session_state.current_index -= 1
                st.session_state.show_definition = False
                st.rerun()
    with col2:
        if st.button("🔄 翻轉單字卡", type="primary", use_container_width=True):
            st.session_state.show_definition = not st.session_state.show_definition
            st.rerun()
    with col3:
        if st.button("下一個 ➡️", use_container_width=True):
            if st.session_state.current_index < len(vocab_list) - 1:
                st.session_state.current_index += 1
                st.session_state.show_definition = False
                st.rerun()

    # 進度條提示
    st.progress((current_idx + 1) / len(vocab_list), text=f"進度: {current_idx + 1} / {len(vocab_list)}")
