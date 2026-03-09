import streamlit as st
from db import init_db, add_subject, get_all_subjects, add_cards, get_card_for_review, update_card_progress, get_recommended_cards, get_dashboard_stats, get_top_priority_cards
from extractor import read_pdf, extract_knowledge, evaluate_answer

# Initialize database
init_db()

st.sidebar.title("导航")
page = st.sidebar.radio("选择页面", ["主页", "开始复习", "学科设置", "导入知识"])

if page == "主页":
    st.title("知识复习 Agent - Dashboard")
    
    stats = get_dashboard_stats()
    
    # 1. Core Metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📚 总知识点", stats['total_cards'])
    with col2:
        st.metric("📝 今日已复习", stats['today_reviews'])
    with col3:
        st.metric("🎓 总体掌握度", f"{stats['avg_mastery']} / 5.0")
        
    st.divider()
    
    # 2. Subject Progress
    col_left, col_right = st.columns([2, 3])
    
    with col_left:
        st.subheader("📊 学科复习进度")
        if not stats['subject_progress'].empty:
            for index, row in stats['subject_progress'].iterrows():
                st.write(f"**{row['name']}** ({int(row['card_count'])} 个知识点)")
                st.progress(min(row['progress'], 1.0))
        else:
            st.info("暂无学科数据")
            
    # 3. Top Priority Cards
    with col_right:
        st.subheader("🔥 今日待办推荐")
        top_cards = get_top_priority_cards(limit=5)
        
        if top_cards:
            for i, card in enumerate(top_cards):
                st.info(f"**{i+1}. [{card['subject_name']}]** {card['question']}")
        else:
            st.success("🎉 太棒了！目前没有急需复习的知识点。")

elif page == "开始复习":
    st.title("开始复习")
    
    # Initialize session state for review
    if 'current_card' not in st.session_state:
        st.session_state.current_card = get_recommended_cards()
        st.session_state.review_submitted = False
        st.session_state.user_answer = ""
        st.session_state.evaluation = None

    # Function to load next card
    def load_next_card():
        st.session_state.current_card = get_recommended_cards()
        st.session_state.review_submitted = False
        st.session_state.user_answer = ""
        st.session_state.evaluation = None

    if st.session_state.current_card:
        card = st.session_state.current_card
        
        # Display recommendation reason
        if 'reason' in card:
             st.caption(f"💡 推荐理由：{card['reason']}")

        st.subheader("问题")
        st.markdown(f"### {card['question']}")
        
        if not st.session_state.review_submitted:
             user_answer = st.text_area("你的回答", height=150, key="answer_input")
             
             if st.button("提交回答"):
                if user_answer.strip():
                    st.session_state.user_answer = user_answer
                    with st.spinner("AI 正在判卷..."):
                        evaluation = evaluate_answer(card['question'], card['answer'], user_answer)
                        st.session_state.evaluation = evaluation
                        st.session_state.review_submitted = True
                        
                        # Update database
                        update_card_progress(card['id'], evaluation['score'])
                        st.rerun()
                else:
                    st.warning("请输入回答内容")
        
        else:
            st.text_area("你的回答", value=st.session_state.user_answer, height=150, disabled=True)
            # Show evaluation results
            st.divider()
            evaluation = st.session_state.evaluation
            
            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric("得分", f"{evaluation['score']} / 5")
            with col2:
                st.info(f"**AI 评价**：{evaluation['feedback']}")
            
            st.success(f"**标准答案**：\n\n{card['answer']}")
            
            if st.button("下一题"):
                load_next_card()
                st.rerun()
            
    else:
        st.info("恭喜！目前没有需要复习的卡片（所有卡片掌握度均已达到 5 或题库为空）。")
        if st.button("刷新"):
            load_next_card()
            st.rerun()

elif page == "学科设置":
    st.title("学科设置")
    
    with st.form("add_subject_form"):
        st.subheader("添加新学科")
        name = st.text_input("学科名称")
        difficulty = st.slider("难度系数", min_value=1.0, max_value=5.0, value=3.0, step=0.1)
        credits = st.number_input("学分 (Credit)", min_value=0.0, step=0.5)
        ddl = st.date_input("考试日期 (DDL)")
        
        submitted = st.form_submit_button("保存")
        
        if submitted:
            if name:
                add_subject(name, difficulty, credits, str(ddl))
                st.success(f"成功添加学科：{name}")
                st.rerun()
            else:
                st.error("请输入学科名称")
    
    st.divider()
    st.subheader("已添加学科")
    subjects_df = get_all_subjects()
    st.dataframe(subjects_df)

elif page == "导入知识":
    st.title("导入知识")
    
    # 获取学科列表用于下拉选择
    subjects_df = get_all_subjects()
    
    if subjects_df.empty:
        st.warning("请先在“学科设置”页面添加至少一个学科。")
    else:
        subject_options = subjects_df.set_index('id')['name'].to_dict()
        selected_subject_id = st.selectbox(
            "选择学科", 
            options=list(subject_options.keys()), 
            format_func=lambda x: subject_options[x]
        )
        
        uploaded_file = st.file_uploader("上传 PDF 文件", type=["pdf"])
        
        if uploaded_file is not None:
            if st.button("开始分析"):
                with st.spinner("正在读取 PDF 并提取知识点，请稍候..."):
                    try:
                        # 读取 PDF 内容
                        text = read_pdf(uploaded_file)
                        st.info(f"成功读取 PDF，文本长度：{len(text)} 字符")
                        
                        # 提取知识点
                        knowledge_points = extract_knowledge(text)
                        
                        if knowledge_points:
                            st.success(f"成功提取 {len(knowledge_points)} 个知识点！")
                            
                            # 插入数据库
                            add_cards(selected_subject_id, knowledge_points)
                            st.success("知识点已保存到数据库。")
                            
                            # 展示提取结果
                            st.subheader("提取结果预览")
                            st.json(knowledge_points)
                        else:
                            st.warning("未能提取到有效的知识点，请检查 PDF 内容或重试。")
                            
                    except Exception as e:
                        st.error(f"发生错误：{str(e)}")
