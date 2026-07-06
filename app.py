import streamlit as st
import pandas as pd
import random
import re
import requests  # 用來發送分數修改請求給 Google Drive

# === 標題與側邊欄設定 ===
st.title("📚 雲端同步單字複習 App")
st.caption("依 Score 由低到高排序 ＋ 按鈕即時連動雲端試算表分數")

# ===================================================
# 🔗 請填入你的 Google 試算表 CSV 連結與剛剛部署的 App Script 網址
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
                st.cache_data.clear() # 清除快取，讓下一次載入時抓到最新分數
            else:
                st.error(f"雲端改分失敗: {res.text}")
        except Exception as e:
            st.error(f"連線至雲端修改失敗: {e}")

if df is not None:
    required_columns = ['Word', 'Sentence', 'Score']
    if not all(col in df.columns for col in required_columns):
        st.error("❌ 雲端檔案欄位不符！")
        st.stop()
        
    st.sidebar.header("⚙️ 設定與功能")
    if st.sidebar.button("🔄 同步雲端最新單字"):
        st.cache_data.clear()
        st.rerun()

    all_scores = sorted(df['Score'].unique().tolist())
    selected_scores = st.sidebar.multiselect("1. 篩選你要複習的 Score", options=all_scores, default=all_scores)
    
    filtered_df = df[df['Score'].isin(selected_scores)]
    if filtered_df.empty:
        st.warning("⚠️ 目前選取的 Score 條件下沒有任何單字。")
        st.stop()
        
    mode = st.sidebar.radio("2. 請選擇模式", ["🃏 單字卡模式", "✍️ 填空測驗模式"])

    state_key = f"vocab_drive_{str(selected_scores)}"
    if st.session_state.get("current_state_key") != state_key:
        raw_list = filtered_df.to_dict(orient='records')
        random.shuffle(raw_list)
        st.session_state.vocab_list = sorted(raw_list, key=lambda x: x['Score'])
        st.session_state.current_index = 0
        st.session_state.show_definition = False
        st.session_state.quiz_current = 0
        st.session_state.selected_options = None
        st.session_state.has_submitted = False
        st.session_state.current_state_key = state_key

    vocab_list = st.session_state.vocab_list

    # === 模式 1：單字卡模式 ===
    if mode == "🃏 單字卡模式":
        st.header("單字卡翻頁")
        
        current_idx = st.session_state.current_index
        current_vocab = vocab_list[current_idx]
        
        target_word = str(current_vocab['Word']).strip()
        full_sentence = str(current_vocab['Sentence'])
        
        pattern = re.compile(rf'\b{re.escape(target_word)}\b', re.IGNORECASE)
        if not pattern.search(full_sentence):
            pattern = re.compile(re.escape(target_word), re.IGNORECASE)
        hidden_sentence = pattern.sub(" `_______` ", full_sentence)
        
        with st.container(border=True):
            if not st.session_state.show_definition:
                st.markdown("<h3 style='text-align: center; color: #888888;'>📝 請猜猜空格中的單字：</h3>", unsafe_allow_html=True)
                st.info(hidden_sentence)
                st.markdown(f"<p style='text-align: center; color: #FF4B4B; font-weight: bold; margin-top: 15px;'>當前單字 Score：{current_vocab['Score']}</p>", unsafe_allow_html=True)
                st.write("---")
            else:
                st.markdown(f"<h1 style='text-align: center; color: #4A90E2;'>{target_word}</h1>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align: center; color: #888888;'>Score：{current_vocab['Score']}</p>", unsafe_allow_html=True)
                st.write("---")
                st.write(f"**💡 完整句子：**")
                st.success(full_sentence)

        # 🔺 新增功能：調整分數按鈕 🔺
        score_col1, score_col2 = st.columns(2)
        with score_col1:
            if st.button("👍 太簡單了！Score + 1", use_container_width=True):
                update_score_in_cloud(target_word, "up")
                # 即時更新本地狀態的分數
                st.session_state.vocab_list[current_idx]['Score'] += 1
                st.rerun()
        with score_col2:
            if st.button("👎 還不熟練...Score - 1", use_container_width=True):
                update_score_in_cloud(target_word, "down")
                st.session_state.vocab_list[current_idx]['Score'] -= 1
                st.rerun()

        st.write("") # 留空行

        # 控制按鈕
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

        st.progress((current_idx + 1) / len(vocab_list), text=f"進度: {current_idx + 1} / {len(vocab_list)}")

    # === 模式 2：填空測驗模式 ===
    elif mode == "✍️ 填空測驗模式":
        st.header("🧠 智慧單字填空測驗")
        
        quiz_current = st.session_state.quiz_current
        if quiz_current >= len(vocab_list):
            st.success("🎉 太厲害了！你已經答完全部的題目了！")
            if st.button("重新挑戰"):
                st.session_state.current_state_key = ""
                st.rerun()
            st.stop()
            
        correct_vocab = vocab_list[quiz_current]
        target_word = str(correct_vocab['Word']).strip()
        full_sentence = str(correct_vocab['Sentence'])
        
        pattern = re.compile(rf'\b{re.escape(target_word)}\b', re.IGNORECASE)
        if not pattern.search(full_sentence):
            pattern = re.compile(re.escape(target_word), re.IGNORECASE)
        hidden_sentence = pattern.sub(" `_______` ", full_sentence)
        
        st.subheader("📝 請選出最適合填入空格的單字：")
        st.info(hidden_sentence)
        st.markdown(f"<p style='color: #FF4B4B; font-weight: bold;'>此題單字 Score：{correct_vocab['Score']}</p>", unsafe_allow_html=True)
        
        if st.session_state.selected_options is None or st.session_state.has_submitted == False:
            wrong_options = [str(v['Word']).strip() for v in vocab_list if str(v['Word']).strip() != target_word]
            wrong_options = list(set(wrong_options))
            sample_size = min(3, len(wrong_options))
            quiz_options = random.sample(wrong_options, sample_size) + [target_word]
            random.shuffle(quiz_options)
            st.session_state.selected_options = quiz_options

        user_choice = st.radio("選擇正確的單字：", st.session_state.selected_options, index=None, placeholder="請選擇...", key=f"quiz_{quiz_current}")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("提交答案", type="primary", use_container_width=True):
                if user_choice is None:
                    st.warning("請先選擇一個答案！")
                else:
                    st.session_state.has_submitted = True
                    
        if st.session_state.has_submitted:
            if user_choice == target_word:
                st.success("🎉 答對了！非常完美！")
            else:
                st.error(f"❌ 答錯了！正確答案應該是：**{target_word}**")
            st.markdown(f"**完整正確句子 (Sentence)：**\n> {full_sentence}")
            
            # 🔺 新增功能：測驗模式下也可以一鍵加減雲端分數 🔺
            quiz_score_col1, quiz_score_col2 = st.columns(2)
            with quiz_score_col1:
                if st.button("👍 太簡單了！Score + 1", key=f"qup_{quiz_current}"):
                    update_score_in_cloud(target_word, "up")
                    correct_vocab['Score'] += 1
                    st.rerun()
            with quiz_score_col2:
                if st.button("👎 還不熟練...Score - 1", key=f"qdown_{quiz_current}"):
                    update_score_in_cloud(target_word, "down")
                    correct_vocab['Score'] -= 1
                    st.rerun()
                    
            with col2:
                if st.button("下一題 ➡️", use_container_width=True):
                    st.session_state.quiz_current += 1
                    st.session_state.has_submitted = False
                    st.session_state.selected_options = None
                    st.rerun()
                    
