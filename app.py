import streamlit as st
import pandas as pd
import random
import re
import requests

# === 🌟 網頁全域設定 ===
st.set_page_config(
    page_title="英文單字複習",
    page_icon="📚",
)

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

    /* 讓 components.v1.html 產生的 iframe 區塊跟其他按鈕間距一致 */
    div[data-testid="stIFrame"] { display: block !important; }
    div[data-testid="stIFrame"] + div,
    div:has(> div[data-testid="stIFrame"]) {
        margin-top: 0 !important;
        margin-bottom: 0 !important;
    }
    div[data-testid="element-container"]:has(iframe) {
        margin-top: 0.25rem !important;
        margin-bottom: 0.25rem !important;
    }
    
    .sentence-container { 
        color: #ffffff !important; 
        font-size: 17px !important; 
        line-height: 1.8 !important; 
        text-align: left !important; 
        padding: 5px 10px !important; 
        word-break: break-word !important;
    }
    
    .blank-placeholder { 
        font-size: 20px !important; 
        font-weight: bold !important; 
        color: #888888 !important; 
        background-color: rgba(255, 255, 255, 0.08) !important; 
        padding: 2px 6px !important; 
        border-radius: 4px !important; 
        margin: 0 2px !important; 
        display: inline !important;
        white-space: pre !important;
    }
    
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

    /* 原生 HTML 發音按鈕樣式優化，使其與 Streamlit 按鈕一致 */
    .tts-button {
        display: block;
        width: 100%;
        background-color: #262730;
        color: #ffffff;
        border: 1px solid rgba(250, 250, 250, 0.2);
        padding: 0.45rem 0.5rem;
        font-size: 14px;
        border-radius: 0.5rem;
        cursor: pointer;
        text-align: center;
        box-sizing: border-box;
        margin-bottom: 0.25rem;
        transition: background-color 0.1s ease;
    }
    .tts-button:active {
        background-color: #5294e2;
        border-color: #5294e2;
    }
    </style>
""", unsafe_allow_html=True)

# ===================================================
# 🔗 雲端基本設定
# ===================================================
GOOGLE_SHEET_ID = "1p4wj-mOuIDYFU81JAIwYOhDfVF5PPrDyidCtMLtowGs"
API_URL = "https://script.google.com/macros/s/AKfycbz1bTWj2bNkGHiUI-enlG9kmTV8eioFv7Igl58d_Fso4Sxisd3MXGEr2T7Na7xGo_vt/exec" 

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
                st.toast(f"✅ 雲端同步成功！")
            else:
                st.error(f"雲端改分失敗: {res.text}")
        except Exception as e:
            st.error(f"連線至雲端修改失敗: {e}")

# === ⚙️ 側邊欄設定 ===
st.sidebar.header("⚙️ 設定與功能")

available_sheets = fetch_all_sheet_names(API_URL)
selected_sheet = st.sidebar.selectbox("請選擇要複習的分頁", options=available_sheets, index=0)

# 🎯 點擊同步：清除舊快取，觸發重新排序邏輯
if st.sidebar.button("🔄 同步雲端最新單字"):
    st.cache_data.clear()
    if "current_state_key" in st.session_state:
        del st.session_state["current_state_key"]
    st.rerun()

df = load_data_from_sheet(GOOGLE_SHEET_ID, selected_sheet)

if df is not None:
    required_columns = ['Word', 'Sentence', 'Score']
    if not all(col in df.columns for col in required_columns):
        st.error(f"❌ 雲端欄位不符！")
        st.stop()

    all_scores = sorted(df['Score'].unique().tolist())
    selected_scores = st.sidebar.multiselect("篩選你要複習的 Score", options=all_scores, default=all_scores)
    
    filtered_df = df[df['Score'].isin(selected_scores)]
    if filtered_df.empty:
        st.warning("⚠️ 目前選取的 Score 條件下沒有任何單字。")
        st.stop()

    # 🎯 初始化與排序邏輯
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
    
    # 🎯 自動重開下一輪機制
    if current_idx >= len(vocab_list):
        st.cache_data.clear() 
        if "current_state_key" in st.session_state:
            del st.session_state["current_state_key"] 
        st.success("🎉 本輪複習完畢！已自動為您同步雲端最新分數，並從分數最低的單字重新開始！")
        if st.button("🚀 開始下一輪複習", type="primary", use_container_width=True):
            st.rerun()
        st.stop()

    current_vocab = vocab_list[current_idx]
    target_word = str(current_vocab['Word']).strip()
    full_sentence = str(current_vocab['Sentence'])
    
    pattern = re.compile(rf'\b{re.escape(target_word)}\b', re.IGNORECASE)
    if not pattern.search(full_sentence):
        pattern = re.compile(re.escape(target_word), re.IGNORECASE)
        
    def make_dynamic_blank(match):
        word_len = len(match.group(0))
        return f'<span class="blank-placeholder">{"_" * max(word_len, 5)}</span>'
        
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

    def move_to_next():
        st.session_state.current_index += 1
        st.session_state.show_definition = False

    # 分數加減按鈕
    st.markdown('<div class="score-container">', unsafe_allow_html=True)
    score_col1, score_col2 = st.columns(2, gap="small")
    with score_col1:
        if st.button("👍 Score+1", use_container_width=True):
            update_score_in_cloud(target_word, "up", selected_sheet)
            move_to_next()
            st.rerun()
    with score_col2:
        if st.button("👎 Score-1", use_container_width=True):
            update_score_in_cloud(target_word, "down", selected_sheet)
            move_to_next()
            st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # 🔊 原生 HTML/JS 發音按鈕（修正版：延遲呼叫 + 選擇英文語音 + 語音清單非同步載入容錯 + 樣式對齊）
    safe_sentence = full_sentence.replace("\\", "\\\\").replace("'", "\\'").replace('"', '\\"').replace('\n', ' ')
    html_button_code = f"""
        <html>
        <head>
        <style>
            html, body {{
                margin: 0;
                padding: 0;
                background: transparent;
            }}
            .tts-button {{
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 6px;
                width: 100%;
                box-sizing: border-box;
                background-color: #262730;
                color: #fafafa;
                border: 1px solid rgba(250, 250, 250, 0.2);
                padding: 0.5rem 0.75rem;
                font-size: 15px;
                font-family: "Source Sans Pro", -apple-system, BlinkMacSystemFont, sans-serif;
                border-radius: 0.5rem;
                cursor: pointer;
                transition: background-color 0.1s ease, border-color 0.1s ease;
            }}
            .tts-button:active {{
                background-color: #5294e2;
                border-color: #5294e2;
            }}
        </style>
        </head>
        <body>
            <button class="tts-button" id="ttsBtn" onclick="speakSentence()">
                <span>🔊</span><span>播放發音</span>
            </button>
            <script>
                function doSpeak() {{
                    var synth = window.speechSynthesis;
                    var u = new SpeechSynthesisUtterance('{safe_sentence}');
                    u.lang = 'en-US';
                    u.rate = 0.9;
                    u.volume = 1;

                    var voices = synth.getVoices();
                    if (voices.length > 0) {{
                        var enVoice = voices.find(function(v) {{
                            return v.lang && v.lang.toLowerCase().indexOf('en') === 0;
                        }});
                        if (enVoice) {{
                            u.voice = enVoice;
                        }}
                    }}

                    u.onerror = function(e) {{
                        console.error('TTS error:', e.error);
                    }};

                    synth.speak(u);
                }}

                function speakSentence() {{
                    var synth = window.speechSynthesis;
                    synth.cancel();

                    if (synth.getVoices().length === 0) {{
                        synth.onvoiceschanged = function() {{
                            setTimeout(doSpeak, 50);
                        }};
                        setTimeout(doSpeak, 300);
                    }} else {{
                        setTimeout(doSpeak, 100);
                    }}
                }}
            </script>
        </body>
        </html>
    """
    st.components.v1.html(html_button_code, height=48)

    # 🔄 翻轉按鈕
    if st.button("🔄 翻轉", type="primary", use_container_width=True):
        st.session_state.show_definition = not st.session_state.show_definition
        st.rerun()

    # 進度條
    display_idx = min(current_idx + 1, len(vocab_list))
    st.progress(display_idx / len(vocab_list), text=f"進度: {display_idx} / {len(vocab_list)}")
