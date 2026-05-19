import streamlit as st
from database import get_db_connection
from utils.display import show_food_result


def food_pk_page():
    st.write("### ⚔️ 美食大乱斗")
    st.caption("两两对决，选出你最想吃的！")
    
    if not st.session_state.pk_round:
        if st.button("🎮 开始PK", use_container_width=True):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM foods WHERE active = 1 ORDER BY RANDOM() LIMIT 8")
            foods = [dict(row) for row in cursor.fetchall()]
            
            st.session_state.pk_round = foods
            st.rerun()
    else:
        foods = st.session_state.pk_round
        
        if len(foods) == 1:
            winner = foods[0]
            st.markdown(f"""
            <div class="result-box">
                🏆 冠军出炉<br/>
                {winner['name']}
            </div>
            """, unsafe_allow_html=True)
            
            show_food_result(winner)
            
            if st.button("再来一轮"):
                st.session_state.pk_round = []
                st.rerun()
        else:
            st.write(f"#### 第 {9 - len(foods)} 轮对决")
            
            food1, food2 = foods[0], foods[1]
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.write(f"### {food1['name']}")
                st.caption(f"{food1['category']} | {food1['cost_level']}")
                if st.button(f"选择 {food1['name']}", key="pk1", use_container_width=True):
                    st.session_state.pk_round = [food1] + foods[2:]
                    st.rerun()
            
            with col2:
                st.write(f"### {food2['name']}")
                st.caption(f"{food2['category']} | {food2['cost_level']}")
                if st.button(f"选择 {food2['name']}", key="pk2", use_container_width=True):
                    st.session_state.pk_round = [food2] + foods[2:]
                    st.rerun()
