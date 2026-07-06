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
    .score-container [data-testid="column"] {
        width: calc(50% - 6px) !important; flex: 1 1 calc(50% - 6px) !important; min-width: calc(50% - 6px) !important;
    }
    .element-container { margin-bottom: 0.05rem !important; }
    [data-testid="stVerticalBlock"] { gap: 0.25rem !important; }
    [data-testid="stVerticalBlockBorderWrapper"] { padding: 0.4rem !important; }
    [data-testid="stVerticalBlockBorderWrapper"] [data-testid="stVerticalBlock"] { justify-content: center !important; height: 100% !important; }
    div.stButton > button { padding: 0.25rem 0.5rem !important; min-height: 2.2rem !important; line-height: 1.2 !important; }
    div[data-testid="stProgress"] { margin-top: 0 !important; margin-bottom: 0 !important; }
    .sentence-container { color: #ffffff !important; font-size: 17px !important; line-height: 1.8 !important; text-align: left !important; padding: 5px 10px !important; display: inline-block !important; vertical-align: middle !important; }
    .blank-placeholder { font-size: 22px !important; font-weight: bold !important; color: #888888 !important; background-color: rgba(255, 255, 255, 0.08) !important; padding: 2px 8px !important; border-radius: 4px !important; margin: 0 4px !important; display: inline-block !important; vertical-align: middle !important; }
    .highlight-word { font-size: 22px !important; font-weight: bold !important; color: #5294e2 !important; background-color: rgba(82, 148, 226, 0.15) !important; padding: 2px 8px !important; border-radius: 4px !important; margin: 0 4px !important; display: inline-block !important; vertical-align: middle !important; }
    </style>
""", unsafe_allow_html=True)

# ===================================================
# 🔗 雲端基本設定（請確保填入正確的 ID 與 API 網址）
# ===================================================
GOOGLE_SHEET_ID = "1p4wj-mOuIDYFU81JAIwYOhDfVF5PPrDyidCtMLtowGs"
API_URL = "https://script.google.com/macros/s/AKfycbwrsmtA9J308YWT0DhxI9Qn57nza7kOICzzfL5T6rEnHN1VrB-dUlKKzxR9zvKIG-p1/exec" 

# === 🎯 核心自動化：自動抓取 Google 試算表內的所有分頁名稱 ===
@st.cache_data(ttl=600)
def fetch_all_sheet_names(sheet_id):
    try:
        # 透過 Google Sheet 內建的表單結構 JSON 節點直接讀取結構資訊
        url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:json"
        res = requests.get(url)
        # 清洗掉 Google 回傳的垃圾前綴字串，解出標準 json
        json_text = re.search(r'google\.visualization\.Query\.setResponse\((.*)\);', res.text).group(1)
        
        # 由於標準 tq 機制在某些共用設定下不方便直接拿分頁列表，我們改採最安全穩定的雲端導向讀取法：
        # 如果上方解析遇到分頁限制，最直接快速的做法是使用公開資訊節點，或者以下方的例外處理作為基底。
        # 這裡利用特殊網址結構直接解析全表單分頁名
        meta_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/edit"
        meta_res = requests.get(meta_url)
        # 用正則表達式撈取 Google 埋在網頁源碼裡的 `sheetName` 陣列
        names = re.findall(r'"sheetName"\s*:\s*"([^"]+)"', meta_res.text)
        
        if names:
            # 去除重複項並保持原本排序
            seen = set()
            return [x for x in names if not (x in seen or seen.add(x))]
        else:
            return ["Sheet1"] # 萬一沒抓到，預設返回第一頁
    except Exception:
        return ["Sheet1"]

# === 核心邏輯：動態下載指定工作表資料 ===
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

# 🎯 全自動化亮點：完全不需手動輸入，自動取得網路上該 Excel 表的所有最新分頁！
available_sheets = fetch_all_sheet_names(GOOGLE_SHEET_ID)
selected_sheet = st.sidebar.selectbox("請選擇要複習的分頁", options=available_sheets, index=0)

if st.sidebar.button("🔄 同步雲端最新單字"):
    st.cache_data.clear()
    st.rerun()

# 讀取選定分頁的資料
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

    # 初始化排序邏輯（將 selected_sheet 加入 key，切換分頁時自動重新隨列出牌）
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
    
    # 正則表達式匹配與首字母大小寫仿效
    pattern = re.compile(rf'\b{re.escape(target_word)}\b', re.IGNORECASE)
    if not pattern.search(full_sentence):
        pattern = re.compile(re.escape(target_word), re.IGNORECASE)
        
    blank_html = '<span class="blank-placeholder">_______</span>'
    hidden_sentence_html = pattern.sub(blank_html, full_sentence)
    
    def make_highlight(match):
        return f'<span class="highlight-word">{match.group(0)}</span>'
    revealed_sentence_html = pattern.sub(make_highlight, full_sentence)
    
    # 顯示字卡
    with st.container(height=180, border=True):
        if not st.session_state.show_definition:
            st.markdown(f'<div class="sentence-container">{hidden_sentence_html}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="sentence-container">{revealed_sentence_html}</div>', unsafe_allow_html=True)

    # 分數加減按鈕容器
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
        if st.button("⬅️ 上一個",
