import streamlit as st
import pandas as pd
import random
import re  # ✨ 關鍵：必須匯入此套件，才不會報 NameError

# === 標題與側邊欄設定 ===
st.title("📚 專屬 Excel 單字複習 App")
st.caption("例句自動挖空填空題 ＋ Score 篩選")

# ==========================================
# 📌 請在此處貼上你從 Google 試算表發布取得的 CSV 網址
# ==========================================
GOOGLE_SHEET_CSV_URL = "https://docs.google.com/spreadsheets/d/1p4wj-mOuIDYFU81JAIwYOhDfVF5PPrDyidCtMLtowGs/export?format=csv" # 請替換成你實際的網址

# === 核心邏輯：自動從雲端下載 Excel/CSV 資料 ===
@st.cache_data(ttl=600)
def load_data_from_drive(url):
    try:
        df = pd.read_csv(url)
        df.columns = df.columns.str.strip()
        return df
    except Exception as e:
        st.error(f"連線至 Google Drive 失敗，請檢查網址。錯誤訊息: {e}")
        return None

# 執行自動讀取
df = load_data_from_drive(GOOGLE_SHEET_CSV_URL)

if df is not None:
    # 檢查指定的英文欄位是否存在
    required_columns = ['Word', 'Sentence', 'Score']
    if not all(col in df.columns for col in required_columns):
        st.error("❌ 雲端檔案欄位不符！您的試算表必須包含這三個欄位標題：'Word'、'Sentence'、'Score'")
        st.stop()
        
    # 側邊欄：進階篩選與模式選擇
    st.sidebar.header("⚙️ 設定與功能")
    
    if st.sidebar.button("🔄 同步雲端最新單字"):
        st.cache_data.clear()
        st.rerun()

    all_scores = sorted(df['Score'].dropna().unique().tolist())
    selected_scores = st.sidebar.multiselect(
        "1. 篩選你要複習的 Score 分數/級別", 
        options=all_scores, 
        default=all_scores
    )
    
    # 根據篩選過濾資料
    filtered_df = df[df['Score'].isin(selected_scores)]
    
    if filtered_df.empty:
        st.warning("⚠️ 目前選取的 Score 條件下沒有任何單字，請重新勾選。")
        st.stop()
        
    mode = st.sidebar.radio("2. 請選擇模式", ["🃏 單字卡模式", "✍️ 填空測驗模式"])

    # 狀態管理快取 Key
    state_key = f"vocab_drive_{str(selected_scores)}"
    if st.session_state.get("current_state_key") != state_key:
        st.session_state.vocab_list = filtered_df.to_dict(orient='records')
        st.session_state.current_index = 0
        st.session_state.show_definition = False
        
        # 測驗狀態初始化
        st.session_state.quiz_indices = list(range(len(st.session_state.vocab_list)))
        random.shuffle(st.session_state.quiz_indices)
        st.session_state.quiz_current = 0
        st.session_state.selected_options = None
        st.session_state.has_submitted = False
        
        st.session_state.current_state_key = state_key

    # === 模式 1：單字卡模式 ===
    if mode == "🃏 單字卡模式":
        st.header("單字卡翻頁")
        
        vocab_list = st.session_state.vocab_list
        current_idx = st.session_state.current_index
        current_vocab = vocab_list[current_idx]
        
        target_word = str(current_vocab['Word']).strip()
        full_sentence = str(current_vocab['Sentence'])
        
        # 挖空邏輯
        pattern = re.compile(rf'\b{re.escape(target_word)}\b', re.IGNORECASE)
        if not pattern.search(full_sentence):
            pattern = re.compile(re.escape(target_word), re.IGNORECASE)
        hidden_sentence = pattern.sub(" `_______` ", full_sentence)
        
        with st.container(border=True):
            if not st.session_state.show_definition:
                st.markdown("<h3 style='text-align: center; color: #888888;'>📝 請猜猜空格中的單字：</h3>", unsafe_allow_html=True)
                st.info(hidden_sentence)
                st.markdown(f"<p style='text-align: center; color: #888888; margin-top: 15px;'>Score：{current_vocab['Score']}</p>", unsafe_allow_html=True)
                st.write("---")
                st.write("*(點擊下方按鈕查看答案單字)*")
            else:
                st.markdown(f"<h1 style='text-align: center; color: #4A90E2;'>{target_word}</h1>", unsafe_allow_html=True)
                st.markdown(f"<p style='text-align: center; color: #888888;'>Score：{current_vocab['Score']}</p>", unsafe_allow_html=True)
                st.write("---")
                st.write(f"**💡 完整句子：**")
                st.success(full_sentence)

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
        
        vocab_list = st.session_state.vocab_list
        quiz_indices = st.session_state.quiz_indices
        quiz_current = st.session_state.quiz_current
        
        if quiz_current >= len(quiz_indices):
            st.success("🎉 太厲害了！你已經答完全部的題目了！")
            if st.button("重新挑戰"):
                random.shuffle(st.session_state.quiz_indices)
                st.session_state.quiz_current = 0
                st.session_state.has_submitted = False
                st.rerun()
            st.stop()
            
        correct_vocab = vocab_list[quiz_indices[quiz_current]]
        target_word = str(correct_vocab['Word']).strip()
        full_sentence = str(correct_vocab['Sentence'])
        
        pattern = re.compile(rf'\b{re.escape(target_word)}\b', re.IGNORECASE)
        if not pattern.search(full_sentence):
            pattern = re.compile(re.escape(target_word), re.IGNORECASE)
            
        hidden_sentence = pattern.sub(" `_______` ", full_sentence)
        
        st.subheader("📝 請選出最適合填入空格的單字：")
        st.info(hidden_sentence)
        
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
                    
            with col2:
                if st.button("下一題 ➡️", use_container_width=True):
                    st.session_state.quiz_current += 1
                    st.session_state.has_submitted = False
                    st.session_state.selected_options = None
                    st.rerun()
else:
    st.warning("請在程式碼第 11 行填入正確的 GOOGLE_SHEET_CSV_URL 網址。")
