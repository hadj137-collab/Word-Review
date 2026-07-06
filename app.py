# === 模式 1：單字卡模式 ===
if mode == "🃏 單字卡模式":
    st.header("單字卡翻頁")
    
    vocab_list = st.session_state.vocab_list
    current_idx = st.session_state.current_index
    current_vocab = vocab_list[current_idx]
    
    # 取得當前資料
    target_word = str(current_vocab['Word']).strip()
    full_sentence = str(current_vocab['Sentence'])
    
    # 處理挖空邏輯
    pattern = re.compile(rf'\b{re.escape(target_word)}\b', re.IGNORECASE)
    if not pattern.search(full_sentence):
        pattern = re.compile(re.escape(target_word), re.IGNORECASE)
    hidden_sentence = pattern.sub(" `_______` ", full_sentence)
    
    # 顯示單字卡
    with st.container(border=True):
        # 1. 未翻轉狀態：顯示例句題目（單字挖空）
        if not st.session_state.show_definition:
            st.markdown("<h3 style='text-align: center; color: #888888;'>📝 請猜猜空格中的單字：</h3>", unsafe_allow_html=True)
            st.info(hidden_sentence)
            st.markdown(f"<p style='text-align: center; color: #888888; margin-top: 15px;'>Score：{current_vocab['Score']}</p>", unsafe_allow_html=True)
            st.write("---")
            st.write("*(點擊下方按鈕查看答案單字)*")
            
        # 2. 已翻轉狀態：顯示解答（完整單字與完整句子）
        else:
            st.markdown(f"<h1 style='text-align: center; color: #4A90E2;'>{target_word}</h1>", unsafe_allow_html=True)
            st.markdown(f"<p style='text-align: center; color: #888888;'>Score：{current_vocab['Score']}</p>", unsafe_allow_html=True)
            st.write("---")
            st.write(f"**💡 完整句子：**")
            st.success(full_sentence)

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
