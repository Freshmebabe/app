import streamlit as st
import time
from datetime import datetime, timedelta
from database import get_db_connection


def show_health_reminder():
    """显示健康提醒"""
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = st.session_state.current_user['username']
    
    # 检查最近3天的饮食
    three_days_ago = (datetime.now() - timedelta(days=3)).date()
    cursor.execute("""
        SELECT f.health_tag, COUNT(*) as cnt
        FROM eat_history e
        LEFT JOIN foods f ON e.food_id = f.id
        WHERE e.user_id = %s AND e.date >= %s
        GROUP BY f.health_tag
    """, (user_id, three_days_ago.isoformat()))
    
    tags = dict(cursor.fetchall())
    
    if tags.get('Spicy', 0) >= 3 or tags.get('CheatMeal', 0) >= 3:
        st.markdown("""
        <div class="health-tip">
            ⚠️ 最近吃得有点重口味哦，今天要不要试试清淡的？
        </div>
        """, unsafe_allow_html=True)


def show_food_result_v2(food, time_of_day):
    """展示选中的食物结果 - 智能推荐版本（不重复问哪一餐）"""
    st.markdown(f"""
    <div class="result-box">
        🍽️ 就吃这个！<br/>
        <span style="font-size: 2.5rem;">{food['name']}</span>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("分类", food['category'])
    with col2:
        st.metric("价格", food['cost_level'])
    with col3:
        # DictCursor 已支持 dict 访问，额外转换以确保兼容
        food_dict = dict(food)
        st.metric("标签", food_dict.get('health_tag') or "无")
    
    # 根据时间段自动推断哪一餐
    meal_time_map = {
        "早餐时间": "早餐",
        "午餐时间": "午餐",
        "下午茶": "午餐",
        "晚餐时间": "晚餐",
        "夜宵时间": "夜宵"
    }
    auto_meal_time = meal_time_map.get(time_of_day, "午餐")
    
    # 满意度
    col_r1, col_r2 = st.columns([3, 1])
    with col_r1:
        rating = st.slider("🌟 满意度", 1, 5, 5, key="rating_smart")
    with col_r2:
        st.write("")
        st.write("")
    
    col_b1, col_b2 = st.columns(2)
    with col_b1:
        if st.button("✅ 确认吃这个", key="confirm_smart", use_container_width=True):
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO eat_history (date, meal_time, food_id, food_name, user_id, rating, mode)
                VALUES (%s, %s, %s, %s, %s, %s, 'smart')
            """, (
                datetime.now().date().isoformat(),
                auto_meal_time,
                food['id'],
                food['name'],
                st.session_state.current_user['username'],
                rating
            ))
            conn.commit()
            
            st.success(f"✅ 已记录到饮食日历！（{auto_meal_time}）")
            # 清空推荐结果
            st.session_state.recommended_food = None
            time.sleep(1)
            st.rerun()
    
    with col_b2:
        if st.button("🔄 换一个", key="change_smart", use_container_width=True):
            st.session_state.recommended_food = None
            st.rerun()
    
    food_dict = dict(food)
    if food_dict.get('recipe_link'):
        st.write(f"📖 [查看菜谱]({food['recipe_link']})")


def show_food_result(food, key_prefix="general"):
    """展示选中的食物结果 - 通用版本"""
    st.markdown(f"""
    <div class="result-box">
        🍽️ 就吃这个！<br/>
        <span style="font-size: 2.5rem;">{food['name']}</span>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("分类", food['category'])
    with col2:
        st.metric("价格", food['cost_level'])
    with col3:
        # DictCursor 已支持 dict 访问，额外转换以确保兼容
        food_dict = dict(food)
        st.metric("标签", food_dict.get('health_tag') or "无")
    
    # 记录到历史
    meal_time = st.selectbox("🍴 哪一餐？", ["早餐", "午餐", "晚餐", "夜宵"], key=f"{key_prefix}_meal_time_select")
    rating = st.slider("🌟 满意度", 1, 5, 5, key=f"{key_prefix}_rating")
    
    if st.button("✅ 确认吃这个", key=f"{key_prefix}_confirm", use_container_width=True):
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO eat_history (date, meal_time, food_id, food_name, user_id, rating, mode)
            VALUES (%s, %s, %s, %s, %s, %s, 'random')
        """, (
            datetime.now().date().isoformat(),
            meal_time,
            food['id'],
            food['name'],
            st.session_state.current_user['username'],
            rating
        ))
        conn.commit()
        
        st.success("✅ 已记录到饮食日历！")
    
    if dict(food).get('recipe_link'):
        st.write(f"📖 [查看菜谱]({food['recipe_link']})")
