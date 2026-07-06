import streamlit as st
import pandas as pd
import random
import re
import requests

# === 🛠️ 頂部空間與排版精確優化 ===
st.markdown("""
    <style>
    /* 移除 Streamlit 頂部區塊多餘空白 */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 1rem !important;
    }
    /* 精緻標題樣式：確保文字絕對不被切到 */
    .custom-title {
        font-size: 20px !important;
        font-weight: bold;
        margin-bottom: 12px !important;
        line-height: 1.5 !important;
        color: #FFFFFF;
    }
    /* 🎯 修正：只有在特定的分數按鈕容器內，才強制左右並排 50% */
    .score-container [data-testid="column"] {
        width: calc(50% - 6px) !important;
        flex: 1 1 calc(50% - 6px) !important;
        min-width: calc(50% - 6px) !important;
    }
    /* 緊縮所有元件的上下間距，騰出更多垂直空間 */
    .element-container {
        margin-bottom: 0.3rem !important;
    }
    </style>
""", unsafe_allow_html=True)

# 顯示例落大方的標題
st.markdown('<p class="custom-title">單字複習APP</p>', unsafe_allow_html=True)

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
                st.cache_data.clear() 
            else:
                st.error(f"雲端改分失敗: {res.text}")
        except Exception as e:
            st.error(f"連線至雲端修改失敗: {e}")

if df is not None:
    required_columns = ['Word', 'Sentence', 'Score']
    if not all(col in df.columns for col in required_columns):
        st.error("❌ 雲端檔案欄位不符！您的試算表必須包含：'Word'、'Sentence'、'Score'")
        st.stop()
        
    # 側邊欄簡化
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
        random.shuffle(raw_list)  
        st.session_state.vocab_list = sorted(raw_list, key=lambda x: x['Score'])  
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
            st.info(hidden_sentence)
            st.markdown(f"<p style='text-align: center; color: #FF4B4B; font-weight: bold; margin-top: 5px; margin-bottom: 5px;'>當前單字 Score：{current_vocab['Score']}</p>", unsafe_allow_html=True)
        else:
            st.markdown(f"<h2 style='text-align: center; color: #4A90E2; margin-top: 5px; margin-bottom: 5px;'>{target_word}</h2>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; color: #888888; margin-bottom: 5px;'>Score：{current_vocab['Score']}</p>", unsafe_allow_html=True)
            st.write("---")
            st.success(full_sentence)

    # 🛠️ 使用客製化容器包裹，確保左右並排的網頁底層死指令只適用於這兩個加減分按鈕
    st.markdown('<div class="score-container">', unsafe_allow_html=True)
    score_col1, score_col2 = st.columns(2, gap="small")
    with score_col1:
        if st.button("👍 Score+1", use_container_width=True):
            update_score_in_cloud(target_word, "up")
            st.session_state.vocab_list[current_idx]['Score'] += 1
            st.rerun()
    with score_col2:
        if st.button("👎 Score-1", use_container_width=True):
            update_score_in_cloud(target_word, "down")
            st.session_state.vocab_list[current_idx]['Score'] -= 1
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 單字卡切換控制按鈕
    col1, col2, col3 = st.columns(3, gap="small")
    with col1:
        if st.button("⬅️ 上一個", use_container_width=True):
            if st.session_state.current_index > 0:
                st.session_state.current_index -= 1
                st.session_state.show_definition = False
                st.rerun()
    with col2:
        if st.button("🔄 翻轉", type="primary", use_container_width=True):
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
