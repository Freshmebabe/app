import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import random
from database import get_db_connection
from utils.display import show_food_result


def cook_or_order_page():
    st.write("### ⚖️ 做饭 vs 外卖")
    st.caption("根据你的懒惰值推荐")
    
    lazy_level = st.slider(
        "今天的懒惰指数",
        min_value=0,
        max_value=10,
        value=st.session_state.lazy_level,
        help="0=想动手做饭, 10=只想躺平"
    )
    
    st.session_state.lazy_level = lazy_level
    
    if lazy_level <= 3:
        st.write("#### 💪 推荐：自己做饭")
        st.info("冰箱里有这些食材可以做：")
        user_id = st.session_state.current_user['username']
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pantry WHERE user_id = %s AND quantity > 0 LIMIT 5", (user_id,))
        items = cursor.fetchall()
        
        if items:
            for item in items:
                st.write(f"• {item['food_name']} x {item['quantity']}")
        else:
            st.caption("冰箱空空如也，去超市扫货吧！")
    
    elif lazy_level <= 6:
        st.write("#### 🚶 推荐：简单速食")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM foods WHERE category = '速食' AND active = 1")
        foods = [dict(row) for row in cursor.fetchall()]
        
        if foods:
            food = random.choice(foods)
            st.write(f"### {food['name']}")
            st.caption(f"{food['cost_level']} | 快速简单")
    
    else:
        st.write("#### 🛋️ 推荐：直接外卖")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM foods WHERE category IN ('快餐', '大餐') AND active = 1")
        foods = [dict(row) for row in cursor.fetchall()]
        
        if foods:
            food = random.choice(foods)
            show_food_result(food, key_prefix="cook_or_order")
