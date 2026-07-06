import streamlit as st
import pandas as pd
import random
import re
import requests

# === 🛠️ 頂部空間與排版精確優化（徹底解決翻轉跳行問題） ===
st.markdown("""
    <style>
    .block-container { padding-top: 2.5rem !important; padding-bottom: 0.5rem !important; }
    header[data-testid="stHeader"] { background: transparent !important; height: 1.5rem !important; }
    .score-container [data-testid="column"] {
        width: calc(50% - 6px) !important; flex: 1 1 calc(50% - 6px) !important; min-width: calc(50% - 6px) !important;
    }
    .element-container { margin-bottom: 0.05rem !important; }
    [data-testid="stVerticalBlock"] { gap: 0.25rem !important; }
    [data-testid="stVerticalBlockBorderWrapper"] { padding: 0.4rem !important; }
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] { justify-content: center !important; height: 100% !important; }
    div.stButton > button { padding: 0.25rem 0.5rem !important; min-height: 2.2rem !important; line-height: 1.2 !important; }
    div[data-testid="stProgress"] { margin-top: 0 !important; margin-bottom: 0 !important; }
    
    /* 🎯 句子容器：允許文字在正常邊界內自然換行 */
    .sentence-container { 
        color: #ffffff !important; 
        font-size: 17px !important; 
        line-height: 1.8 !important; 
        text-align: left !important; 
        padding: 5px 10px !important; 
        word-break: break-word !important;
    }
    
    /* 🎯 正面未翻轉的動態等長空白框 */
    .blank-placeholder { 
        font-size: 20px !important; 
        font-weight: bold !important; 
        color: #888888 !important; 
        background-color: rgba(255, 255, 255, 0.08) !important; 
        padding: 2px 6px !important; 
        border-radius: 4px !important; 
        margin: 0 2px !important; 
        display: inline !important;
        white-space: pre !important; /* 確保空格或底線不會被瀏覽器壓縮 */
    }
    
    /* 🎯 反面翻轉後的高亮單字：與正面框框大小、邊距完美對齊 */
    .highlight-word { 
        font-size: 20px !important; 
        font-weight: bold !important; 
        color: #5294e2 !important; 
        background-color: rgba(82, 148, 226, 0.18) !important; 
        padding: 2px 6px !important; 
        border-radius: 4px !important; 
        margin: 0 2px !important; 
        display: inline !important; 
        white-space: normal !important;
    }
    </style>
""", unsafe_allow_html=True)

# ===================================================
# 🔗 雲端基本設定
# ===================================================
GOOGLE_SHEET_ID = "1p4wj-mOuIDYFU81JAIwYOhDfVF5PPrDyidCtMLtowGs"
API_URL = "https://script.google.com/macros/s/AKfycbwrsmtA9J308YWT0DhxI9Qn57nza7kOICzzfL5T6rEnHN1VrB-dUlKKzxR9zvKIG-p1/exec" 

@st.cache_data(ttl=600)
def fetch_all_sheet_names(api_url):
    try:
        res = requests.get(api_url, params={"action": "getSheets"})
        if res.status_code == 200 and res.text and "Error" not in res.text:
            return [name.strip() for name in res.text.split(",")]
        return ["Sheet1"]
    except Exception:
        return ["Sheet1"]

@st.cache_data(ttl=600)
def load_data_from_sheet(sheet_id, sheet_name):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={requests.utils.quote(sheet_name)}"
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        df['Score'] = pd.to_numeric(df['Score'], errors='coerce')
        df = df.dropna(subset=['Word', 'Score'])
        return df
    except Exception as e:
        st.error(f"讀取分頁 [{sheet_name}] 失敗: {e}")
        return None

def update_score_in_cloud(word, action, sheet_name):
    with st.spinner("正在同步修改雲端分數..."):
        try:
            res = requests.get(API_URL, params={"word": word, "action": action, "sheetName": sheet_name})
            if "Success" in res.text:
                st.toast(f"✅ 雲端同步成功！[{sheet_name}] 的單字 [{word}] 分數已變更。")
                st.cache_data.clear() 
            else:
                st.error(f"雲端改分失敗: {res.text}")
        except Exception as e:
            st.error(f"連線至雲端修改失敗: {e}")

# === ⚙️ 側邊欄設定 ===
st.sidebar.header("⚙️ 設定與功能")

available_sheets = fetch_all_sheet_names(API_URL)
selected_sheet = st.sidebar.selectbox("請選擇要複習的分頁", options=available_sheets, index=0)

if st.sidebar.button("🔄 同步雲端最新單字"):
    st.cache_data.clear()
    st.rerun()

df = load_data_from_sheet(GOOGLE_SHEET_ID, selected_sheet)

if df is not None:
    required_columns = ['Word', 'Sentence', 'Score']
    if not all(col in df.columns for col in required_columns):
        st.error(f"❌ 雲端欄位不符！分頁 '{selected_sheet}' 必須包含：'Word'、'Sentence'、'Score'")
        st.stop()

    all_scores = sorted(df['Score'].unique().tolist())
    selected_scores = st.sidebar.multiselect("篩選你要複習的 Score", options=all_scores, default=all_scores)
    
    filtered_df = df[df['Score'].isin(selected_scores)]
    if filtered_df.empty:
        st.warning("⚠️ 目前選取的 Score 條件下沒有任何單字。")
        st.stop()

    state_key = f"vocab_drive_{selected_sheet}_{str(selected_scores)}"
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
    
    # 正則表達式精確匹配
    pattern = re.compile(rf'\b{re.escape(target_word)}\b', re.IGNORECASE)
    if not pattern.search(full_sentence):
        pattern = re.compile(re.escape(target_word), re.IGNORECASE)
        
    # 🎯 核心修正：讓正面空白框的底線長度「等於單字實際長度」！
    # 這樣正面預留的空間就和反面一模一樣，絕對不會造成排版二次跳行
    def make_dynamic_blank(match):
        word_len = len(match.group(0))
        dynamic_underlines = "_" * max(word_len, 5) # 至少保持5個底線美觀度
        return f'<span class="blank-placeholder">{dynamic_underlines}</span>'
        
    hidden_sentence_html = pattern.sub(make_dynamic_blank, full_sentence)
    
    def make_highlight(match):
        return f'<span class="highlight-word">{match.group(0)}</span>'
    revealed_sentence_html = pattern.sub(make_highlight, full_sentence)
    
    # 顯示字卡
    with st.container(height=180, border=True):
        if not st.session_state.show_definition:
            st.markdown(f'<div class="sentence-container">{hidden_sentence_html}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="sentence-container">{revealed_sentence_html}</div>', unsafe_allow_html=True)

    # 分數加減按鈕
    st.markdown('<div class="score-container">', unsafe_allow_html=True)
    score_col1, score_col2 = st.columns(2, gap="small")
    with score_col1:
        if st.button("👍 Score+1", use_container_width=True):
            update_score_in_cloud(target_word, "up", selected_sheet)
            st.session_state.vocab_list[current_idx]['Score'] += 1
            st.rerun()
    with score_col2:
        if st.button("👎 Score-1", use_container_width=True):
            update_score_in_cloud(target_word, "down", selected_sheet)
            st.session_state.vocab_list[current_idx]['Score'] -= 1
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 底部控制按鈕
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
