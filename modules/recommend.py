import streamlit as st
import random
import time
from datetime import datetime, timedelta
from database import get_db_connection, get_user_preferences
from utils.display import show_food_result_v2


def get_smart_recommendation_v2(time_of_day, mood, appetite, flavor_prefer, time_constraint, exclude_recent=False):
    """基于多维度问答的智能推荐算法 v3 (逻辑增强版)"""
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = st.session_state.current_user['username']
    user_prefs = get_user_preferences(conn, user_id)
    
    # 1. 构建基础查询，排除最近吃过的
    query = "SELECT * FROM foods WHERE active = 1"
    params = []
    if exclude_recent:
        three_days_ago = (datetime.now() - timedelta(days=3)).date()
        query += " AND id NOT IN (SELECT food_id FROM eat_history WHERE user_id = %s AND date >= %s)"
        params.extend([user_id, three_days_ago.isoformat()])
    
    cursor.execute(query, params)
    foods = [dict(row) for row in cursor.fetchall()]
    
    if not foods:
        return None
    
    # 2. 获取用户偏好和黑名单
    blacklist = user_prefs.get('blacklist', [])
    avoid_categories = user_prefs.get('avoid_category', [])
    favorite_categories = user_prefs.get('favorite_category', [])
    health_mode = user_prefs.get('health_mode', '普通模式')
    
    # 3. 智能评分系统
    scored_foods = []
    for food in foods:
        # 黑名单和分类过滤
        if food['name'] in blacklist or food['category'] in avoid_categories:
            continue
        
        score = 50  # 基础分
        reasons = []
        food_name = food['name']
        food_cat = food['category']
        food_tag = food.get('health_tag', '')

        # --- 组合规则 (高优先级) ---
        if time_of_day == "早餐时间" and time_constraint == "很赶时间":
            if food_cat in ['早餐', '速食', '轻食'] or any(k in food_name for k in ['包子', '面包', '三明治', '手抓饼']):
                score += 50
                reasons.append("为你找到了方便快捷的早餐")
        
        # --- 维度1: 时间段 (time_of_day) ---
        if time_of_day == "早餐时间":
            if food_cat in ['早餐', '速食'] or any(k in food_name for k in ['粥', '蛋', '包子', '面包']):
                score += 35
                reasons.append("这个当早餐很不错")
            elif food_cat in ['大餐', '火锅', '烧烤', '中餐']:
                score -= 50
        elif time_of_day == "午餐时间":
            if food_cat in ['中餐', '家常菜', '快餐'] or any(k in food_name for k in ['饭', '面']):
                score += 25
                reasons.append("午餐吃这个能补充能量")
        elif time_of_day == "下午茶":
            if food_cat in ['甜品', '零食饮料', '轻食', '小吃']:
                score += 40
                reasons.append("下午茶时间，享受片刻悠闲")
            elif food_cat in ['大餐', '家常菜']:
                score -= 20
        elif time_of_day == "晚餐时间":
            if food_cat in ['中餐', '西餐', '日料', '大餐', '家常菜', '烧烤']:
                score += 25
                reasons.append("晚餐值得吃顿好的")
        elif time_of_day == "夜宵时间":
            if food_cat in ['烧烤', '速食', '小吃', '零食饮料'] or '面' in food_name:
                score += 40
                reasons.append("深夜的美味最治愈")
            elif food_cat in ['大餐', '西餐']:
                score -= 20

        # --- 维度2: 心情 (mood) ---
        if mood == "开心愉悦":
            if food_cat in ['甜品', '大餐', '零食饮料']:
                score += 20
                reasons.append("开心就该吃点好的")
        elif mood == "有点累":
            if food_tag == 'Healthy' or '粥' in food_name or '汤' in food_name:
                score += 25
                reasons.append("有点累了，吃点健康的恢复一下")
        elif mood == "压力山大":
            if food_tag == 'CheatMeal' or food_cat in ['大餐', '快餐', '烧烤', '甜品']:
                score += 30
                reasons.append("用美食来释放所有压力吧")
        elif mood == "平静放松":
            if food_cat in ['家常菜', '轻食', '日料'] or food_tag == 'Light':
                score += 20
                reasons.append("平静的心情适合品尝细腻的味道")

        # --- 维度3: 食欲 (appetite) ---
        if appetite == "特别饿":
            if food_tag == 'CheatMeal' or food_cat in ['快餐', '大餐', '烧烤'] or any(k in food_name for k in ['饭', '面', '汉堡']):
                score += 30
                reasons.append("饿的时候，就该吃点管饱的")
        elif appetite == "不太饿":
            if food_cat in ['轻食', '甜品', '零食饮料', '小吃'] or food_tag == 'Light':
                score += 25
                reasons.append("不太饿？来点小吃或轻食刚刚好")
        elif appetite == "想吃点特别的":
            if food_cat in ['日料', '西餐', '大餐'] or food.get('cost_level') == '$$$':
                score += 30
                reasons.append("满足你对特别美食的渴望")

        # --- 维度4: 口味 (flavor_prefer) ---
        if flavor_prefer == "清淡健康":
            if food_tag in ['Healthy', 'Light']:
                score += 30
            elif food_tag in ['Spicy', 'CheatMeal'] or food_cat == '烧烤':
                score -= 25
        elif flavor_prefer == "重口味" or flavor_prefer == "香辣刺激":
            if food_tag == 'Spicy' or any(k in food_name for k in ['辣', '麻', '香锅', '火锅']):
                score += 40
                reasons.append("够味才过瘾")
        elif flavor_prefer == "酸甜口":
            if food_tag == 'Sweet' or any(k in food_name for k in ['糖醋', '咕咾', '番茄']):
                score += 25
                reasons.append("酸酸甜甜就是我")

        # --- 维度5: 时间约束 (time_constraint) ---
        if time_constraint == "很赶时间":
            if food_cat in ['快餐', '速食', '小吃', '轻食', '零食饮料']:
                score += 35
                reasons.append("时间紧，吃这个最快")
        elif time_constraint == "时间充裕":
            if food_cat in ['家常菜', '大餐', '西餐', '日料']:
                score += 15
                reasons.append("时间充裕，值得慢慢享受")

        # --- 维度6: 用户个人偏好 (user_prefs) ---
        if not user_prefs.get('spicy') and food_tag == 'Spicy':
            score -= 20
        if user_prefs.get('sweet') and food_tag == 'Sweet':
            score += 15
        if food_cat in favorite_categories:
            score += 20
            reasons.append(f"还是你最爱的{food_cat}")
        
        # --- 维度7: 健康模式 (health_mode) ---
        if health_mode == "健康模式":
            if food_tag == 'Healthy':
                score += 25
            elif food_tag == 'CheatMeal':
                score -= 20
        elif health_mode == "放纵模式":
            if food_tag == 'CheatMeal':
                score += 20
                reasons.append("今天就要放纵一下")
        
        scored_foods.append({'food': food, 'score': score, 'reasons': list(set(reasons))})
    
    if not scored_foods:
        return None
    
    # 4. 选择得分最高的候选者（加入随机性）
    scored_foods.sort(key=lambda x: x['score'], reverse=True)
    top_candidates = scored_foods[:5]
    
    if not top_candidates:
        return None

    scores = [c['score'] for c in top_candidates]
    weights = [max(s, 1) for s in scores]
    
    selected = random.choices(top_candidates, weights=weights, k=1)[0]
    
    reason_text = "这个应该不错"
    if selected['reasons']:
        primary_reason = selected['reasons'][0]
        other_reasons = [r for r in selected['reasons'][1:] if "你最爱" not in r]
        if other_reasons:
            reason_text = f"{primary_reason}，而且{random.choice(other_reasons)}"
        else:
            reason_text = primary_reason

    return {
        'food': selected['food'],
        'reason': f"💡 {reason_text}！",
        'score': selected['score']
    }


def smart_recommendation_page():
    st.write("### 🎲 智能推荐")
    st.caption("像朋友一样聊聊天，帮你找到最适合今天的美食")
    
    st.write("#### 💬 让我了解一下你的需求")
    
    col1, col2 = st.columns(2)
    
    with col1:
        current_hour = datetime.now().hour
        if 5 <= current_hour < 10:
            default_time = "早餐时间"
        elif 10 <= current_hour < 14:
            default_time = "午餐时间"
        elif 14 <= current_hour < 17:
            default_time = "下午茶"
        elif 17 <= current_hour < 21:
            default_time = "晚餐时间"
        else:
            default_time = "夜宵时间"
        
        time_of_day = st.selectbox(
            "⏰ 现在是什么时间呢？",
            ["早餐时间", "午餐时间", "下午茶", "晚餐时间", "夜宵时间"],
            index=["早餐时间", "午餐时间", "下午茶", "晚餐时间", "夜宵时间"].index(default_time)
        )
    
    with col2:
        mood = st.selectbox(
            "😊 今天心情怎么样？",
            ["开心愉悦", "有点累", "压力山大", "平静放松", "兴奋期待"]
        )
    col3, col4 = st.columns(2)
    
    with col3:
        appetite = st.selectbox(
            "🍽️ 现在食欲如何？",
            ["特别饿", "一般般", "不太饿", "想吃点特别的"]
        )
    
    with col4:
        flavor_prefer = st.selectbox(
            "😋 今天想吃什么口味？",
            ["随便都行", "清淡健康", "重口味", "酸甜口", "香辣刺激"]
        )
    
    col5, col6 = st.columns(2)
    
    with col5:
        time_constraint = st.selectbox(
            "⏱️ 时间充裕吗？",
            ["很赶时间", "时间充裕", "可以等"]
        )
    
    with col6:
        exclude_recent = st.checkbox("排除最近3天吃过的", value=True)
    
    if st.button("🤖 帮我推荐", key="smart_rec", use_container_width=True):
        with st.spinner("正在分析你的需求..."):
            result = get_smart_recommendation_v2(
                time_of_day, mood, appetite, flavor_prefer, time_constraint, exclude_recent
            )
            
            if result:
                st.session_state.recommended_food = result['food']
                st.session_state.recommended_reason = result['reason']
                st.session_state.recommended_time = time_of_day
                st.rerun()
            else:
                st.warning("没有找到合适的食物，试试放宽条件？")
    
    if 'recommended_food' in st.session_state and st.session_state.recommended_food:
        st.divider()
        st.success(st.session_state.recommended_reason)
        show_food_result_v2(st.session_state.recommended_food, st.session_state.recommended_time)
