import streamlit as st
import pandas as pd
import random
import re
import requests

# === 🛠️ 頂部空間與排版精確優化（徹底拔除 Block 元素，強制全 inline 渲染） ===
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
    
    /* 🎯 句子容器：純文字流排版，不允許內部有任何塊級分隔 */
    .sentence-container { 
        color: #ffffff !important; 
        font-size: 18px !important; 
        line-height: 1.6 !important; 
        text-align: left !important; 
        padding: 5px 10px !important; 
        display: block !important;
        word-wrap: break-word !important;
    }
    
    /* 🎯 正面未翻轉的空白框樣式：改成 inline-block 緊跟文字 */
    .blank-placeholder { 
        font-size: 18px !important; 
        font-weight: bold !important; 
        color: #888888 !important; 
        background-color: rgba(255, 255, 255, 0.12) !important; 
        padding: 0px 6px !important; 
        border-radius: 4px !important; 
        display: inline-block !important; 
        vertical-align: baseline !important;
    }
    
    /* 🎯 反面翻轉後的高亮單字：徹底扁平化，當作普通單字塞在句子裡，絕不跳行 */
    .highlight-word { 
        font-size: 18px !important; 
        font-weight: bold !important; 
        color: #5294e2 !important; 
        background-color: rgba(82, 148, 226, 0.18) !important; 
        padding: 2px 4px !important; 
        border-radius: 4px !important; 
        display: inline !important; 
    }
    </style>
""", unsafe_allow_html=True)

# ===================================================
# 🔗 雲端基本設定
# ===================================================
GOOGLE_SHEET_ID = "1p4wj-mOuIDYFU81JAIwYOhDfVF5PPrDyidCtMLtowGs"
API_URL = "https://script.google.com/macros/s/AKfycbwrsmtA9J308YWT0DhxI9Qn57nza7kOICzzfL5T6rEnHN1VrB-dUlKKzxR9zvKIG-p1/exec" 

# === 透過 API 撈取所有分頁名稱 ===
@st.cache_data(ttl=600)
def fetch_all_sheet_names(api_url):
    try:
        res = requests.get(api_url, params={"action": "getSheets"})
        if res.status_code == 200 and res.text and "Error" not in res.text:
            return [name.strip() for name in res.text.split(",")]
        return ["Sheet1"]
    except Exception:
        return ["Sheet1"]

# === 動態下載指定工作表資料 ===
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

# 雲端同步改分函式
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

# 讀取資料
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

    # 初始化排序邏輯
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
    
    # 確保前後多餘空格完全被剔除
    target_word = str(current_vocab['Word']).strip()
    full_sentence = str(current_vocab['Sentence']).strip()
    
    # 🎯 終極優化：改用「寬鬆邊界正則匹配」，不論前後是空格、標點還是直接連著，都能精準捕捉
    pattern = re.compile(re.escape(target_word), re.IGNORECASE)
        
    blank_html = '<span class="blank-placeholder">&nbsp;_______&nbsp;</span>'
    hidden_sentence_html = pattern.sub(blank_html, full_sentence)
    
    def make_highlight(match):
        # 保持原句子的大小寫，同時包覆在純 inline 標籤中
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
