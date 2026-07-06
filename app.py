import streamlit as st
import pandas as pd
import random
import re
import requests

# === 🛠️ 頂部空間與排版精確優化 ===
st.markdown("""
    <style>
    .block-container { padding-top: 2.5rem !important; padding-bottom: 0.5rem !important; }
    header[data-testid="stHeader"] { background: transparent !important; height: 1.5rem !important; }
    .score-container [data-testid="column"] { width: calc(50% - 6px) !important; flex: 1 1 calc(50% - 6px) !important; min-width: calc(50% - 6px) !important; }
    .element-container { margin-bottom: 0.05rem !important; }
    [data-testid="stVerticalBlock"] { gap: 0.25rem !important; }
    [data-testid="stVerticalBlockBorderWrapper"] { padding: 0.4rem !important; }
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] { justify-content: center !important; height: 100% !important; }
    div.stButton > button { padding: 0.25rem 0.5rem !important; min-height: 2.2rem !important; line-height: 1.2 !important; }
    div[data-testid="stProgress"] { margin-top: 0 !important; margin-bottom: 0 !important; }
    .sentence-container { color: #ffffff !important; font-size: 17px !important; line-height: 1.6 !important; text-align: left !important; padding: 5px 10px !important; }
    .blank-placeholder { font-size: 22px !important; font-weight: bold !important; color: #888888 !important; background-color: rgba(255, 255, 255, 0.08) !important; padding: 2px 8px !important; border-radius: 4px !important; margin: 0 4px !important; display: inline-block !important; }
    .highlight-word { font-size: 22px !important; font-weight: bold !important; color: #5294e2 !important; background-color: rgba(82, 148, 226, 0.15) !important; padding: 2px 8px !important; border-radius: 4px !important; margin: 0 4px !important; display: inline-block !important; }
    </style>
""", unsafe_allow_html=True)

# ===================================================
# 🔗 務必檢查這裡的 API_URL 是否與最新的部署網址一模一樣！
# ===================================================
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1p4wj-mOuIDYFU81JAIwYOhDfVF5PPrDyidCtMLtowGs/export?format=csv"
API_URL = "https://script.google.com/macros/s/AKfycbz1bTWj2bNkGHiUI-enlG9kmTV8eioFv7Igl58d_Fso4Sxisd3MXGEr2T7Na7xGo_vt/exec" 

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

# 雲端同步改分函式 (強化 Debug 訊息)
def update_score_in_cloud(word, action):
    with st.spinner("正在同步修改雲端分數..."):
        try:
            res = requests.get(API_URL, params={"word": word, "action": action}, timeout=10)
            # 只要 Apps script 回傳的字眼包含 Success，就代表成功
            if "Success" in res.text:
                st.toast(f"✅ 雲端同步成功！單字 [{word}] 分數已變更。")
                st.cache_data.clear() # 💡 成功後立刻清空快取，下次下載才會拿到最新分數
                return True
            else:
                st.error(f"❌ 雲端改分失敗，API回應: {res.text}")
                return False
        except Exception as e:
            st.error(f"💥 連線至雲端修改失敗: {e}。請檢查 API_URL 是否填寫正確。")
            return False

if df is not None:
    required_columns = ['Word', 'Sentence', 'Score']
    if not all(col in df.columns for col in required_columns):
        st.error("❌ 雲端檔案欄位不符！您的試算表必須包含：'Word'、'Sentence'、'Score'")
        st.stop()
        
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
    
    # 防止因篩選變動導致陣列越界
    if current_idx >= len(vocab_list):
        current_idx = 0
        st.session_state.current_index = 0
        
    current_vocab = vocab_list[current_idx]
    target_word = str(current_vocab['Word']).strip()
    full_sentence = str(current_vocab['Sentence'])
    
    pattern = re.compile(rf'\b{re.escape(target_word)}\b', re.IGNORECASE)
    if not pattern.search(full_sentence):
        pattern = re.compile(re.escape(target_word), re.IGNORECASE)
        
    blank_html = '<span class="blank-placeholder">_______</span>'
    hidden_sentence_html = pattern.sub(blank_html, full_sentence)
    
    highlighted_html = f'<span class="highlight-word">{target_word}</span>'
    revealed_sentence_html = pattern.sub(highlighted_html, full_sentence)
    
    with st.container(height=180, border=True):
        if not st.session_state.show_definition:
            st.markdown(f'<div class="sentence-container">{hidden_sentence_html}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="sentence-container">{revealed_sentence_html}</div>', unsafe_allow_html=True)

    # 🛠️ 分數按鈕與連動邏輯優化
    st.markdown('<div class="score-container">', unsafe_allow_html=True)
    score_col1, score_col2 = st.columns(2, gap="small")
    with score_col1:
        if st.button("👍 Score+1", use_container_width=True):
            if update_score_in_cloud(target_word, "up"):
                st.session_state.vocab_list[current_idx]['Score'] += 1
                st.rerun()
    with score_col2:
        if st.button("👎 Score-1", use_container_width=True):
            if update_score_in_cloud(target_word, "down"):
                st.session_state.vocab_list[current_idx]['Score'] -= 1
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

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

    st.progress((current_idx + 1) / len(vocab_list), text=f"進度: {current_idx + 1} / {len(vocab_list)}")
