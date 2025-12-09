import streamlit as st
import random
import time
import json
import base64
from collections import defaultdict
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import os
from database import (
    get_connection, initialize_and_seed_database, verify_user, 
    get_user_preferences, update_user_preferences, get_user_avatar, update_user_avatar, update_password
) 

# 页面配置
st.set_page_config(
    page_title="HoneyEat - 亲爱的今天吃什么",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 极简风格CSS
st.markdown("""
<style>
    /* 全局样式 */
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei";
        background: #f8f9fa;
    }
    
    /* 主标题 */
    .main-title {
        font-size: 2.5rem;
        font-weight: 300;
        color: #2c3e50;
        text-align: center;
        margin: 2rem 0 1rem;
        letter-spacing: 2px;
    }
    
    /* 卡片样式 */
    .card {
        background: white;
        border-radius: 12px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 2px 8px rgba(0,0,0,0.08);
    }
    
    /* 按钮样式 */
    .stButton>button {
        background: #ecf0f1;
        color: #2c3e50;
        border: none;
        border-radius: 8px;
        padding: 0.75rem 1.5rem;
        font-weight: 500;
        transition: all 0.3s;
        width: 100%;
    }
    
    .stButton>button:hover {
        background: #bdc3c7;
        transform: translateY(-2px);
    }
    
    /* 主操作按钮 */
    .primary-btn {
        background: #3498db !important;
        color: white !important;
        font-size: 1.1rem;
        padding: 1rem 2rem;
    }
    
    .primary-btn:hover {
        background: #2980b9 !important;
    }
    
    /* 结果展示 */
    .result-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 16px;
        text-align: center;
        font-size: 2rem;
        font-weight: 600;
        margin: 2rem 0;
        animation: fadeIn 0.5s;
    }
    
    @keyframes fadeIn {
        from { opacity: 0; transform: scale(0.95); }
        to { opacity: 1; transform: scale(1); }
    }
    
    /* 健康提示 */
    .health-tip {
        background: #fff3cd;
        border-left: 4px solid #ffc107;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }

    /* 头像样式 */
    .user-nav-container {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
    }
    .avatar-image {
        width: 108px;
        height: 108px;
        border-radius: 50%;
        object-fit: cover;
        margin-bottom: 0.5rem;
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
    .user-nav-logout-btn {
        width: 120px; /* 设置一个固定宽度或相对宽度 */
        margin-top: 0.5rem;
    }
    .user-nav-name {
        font-weight: bold;
        text-align: center;
    }
    
    /* 隐藏streamlit默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 移动端适配 */
    @media (max-width: 768px) {
        .main-title { font-size: 1.8rem; }
        .result-box { font-size: 1.5rem; padding: 1.5rem; }
    }
</style>
""", unsafe_allow_html=True)

# Session state 初始化
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'pk_round' not in st.session_state:
    st.session_state.pk_round = []
if 'lazy_level' not in st.session_state:
    st.session_state.lazy_level = 5
if 'recommended_food' not in st.session_state:
    st.session_state.recommended_food = None
if 'recommended_reason' not in st.session_state:
    st.session_state.recommended_reason = ""
if 'recommended_time' not in st.session_state:
    st.session_state.recommended_time = ""
if 'show_logout_confirmation' not in st.session_state:
    st.session_state.show_logout_confirmation = False

# ============ 数据库连接管理 ============
@st.cache_resource
def get_db_connection():
    """
    获取并缓存数据库连接。
    在首次调用时，会检查数据库是否存在，如果不存在，则执行完整的初始化。
    这个过程是阻塞的，确保在返回连接之前，数据库已准备就绪。
    """
    db_path = "honeyeat.db"
    db_exists = os.path.exists(db_path)
    
    # 无论是否存在，都先获取连接。如果文件不存在，sqlite3会自动创建。
    conn = get_connection()
    
    # 仅在数据库文件首次创建时，才执行建表和数据填充操作。
    if not db_exists:
        print("数据库文件不存在，正在进行首次初始化...")
        initialize_and_seed_database(conn)
        print("✅ 数据库初始化完成！")
        
    return conn

# ============ 登录界面 ============
def login_page():
    st.markdown('<h1 class="main-title">🍽️ HoneyEat</h1>', unsafe_allow_html=True)

    st.markdown('<p style="text-align:center; color:#7f8c8d;">亲爱的，今天吃什么？</p>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.write("### 请登录")
        username = st.text_input("用户名", key="login_username")
        password = st.text_input("密码", type="password", key="login_password")
        
        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("登录", use_container_width=True, key="login_btn"):
                if username and password:
                    # 直接使用缓存连接进行验证
                    conn = get_db_connection()
                    result = verify_user(conn, username, password)
                    if result["success"]:
                        user = result["user"]
                        st.session_state.logged_in = True
                        st.session_state.current_user = user
                        st.success(f"欢迎回来，{user['name']}！")
                        time.sleep(0.5)
                        st.rerun()
                    else:
                        st.error(result["message"]) # 显示更详细的错误信息
                else:
                    st.warning("请输入用户名和密码")
        
        with col_b:
            if st.button("游客模式", use_container_width=True, key="guest_btn"):
                st.session_state.logged_in = True
                st.session_state.current_user = {'username': 'guest', 'name': '游客'}
                st.rerun()
        
        st.divider()
        #st.caption("💡 默认账号: admin/admin123, bf/bf123, gf/gf123")

# ============ 主应用 ============
def main_app():
    # 防止 session 丢失
    if not st.session_state.get('logged_in') or not st.session_state.get('current_user'):
        st.warning("会话已过期，请重新登录")
        st.session_state.logged_in = False
        st.session_state.current_user = None
        time.sleep(1)
        st.rerun()
        return
    
    # 顶部导航
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f'<h1 class="main-title">🍽️ HoneyEat</h1>', unsafe_allow_html=True)
    with col2:
        with st.container():
            st.markdown('<div class="user-nav-container">', unsafe_allow_html=True)
            
            user_id = st.session_state.current_user['username']
            if user_id != 'guest':
                conn = get_db_connection()
                avatar = get_user_avatar(conn, user_id)
                if avatar:
                    img_str = base64.b64encode(avatar).decode()
                    st.markdown(
                        f'<img src="data:image/png;base64,{img_str}" class="avatar-image">',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown('<div style="font-size: 72px; text-align: center;">👤</div>', unsafe_allow_html=True) # 默认图标
                st.markdown(f"<div class='user-nav-name'>{st.session_state.current_user['name']}</div>", unsafe_allow_html=True)
            else:
                st.markdown('<div style="font-size: 72px; text-align: center;">👤</div>', unsafe_allow_html=True) # 游客图标
                st.markdown(f"<div class='user-nav-name'>{st.session_state.current_user['name']}</div>", unsafe_allow_html=True)
            
            if st.button("退出登录", key="logout_top_btn", use_container_width=True):
                st.session_state.show_logout_confirmation = True
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # 处理退出登录的确认对话框
    if st.session_state.get('show_logout_confirmation'):
        # 使用列布局来模拟居中弹窗
        _ , center_col, _ = st.columns([1, 1.5, 1])
        with center_col:
            # 使用带边框的容器，让它看起来像一个卡片/弹窗
            with st.container(border=True):
                st.write("#### **确认退出**")
                st.write("您确定要退出当前账号吗？")
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button("确认", key="confirm_logout_dialog", use_container_width=True, type="primary"):
                        st.session_state.logged_in = False
                        st.session_state.current_user = None
                        st.session_state.show_logout_confirmation = False
                        st.rerun()
                with btn_col2:
                    if st.button("取消", key="cancel_logout_dialog", use_container_width=True):
                        st.session_state.show_logout_confirmation = False
                        st.rerun()
        # 显示对话框时，不显示下面的内容
        return

    # 健康打卡栏
    show_health_checkin()
    
    # 主功能标签页
    tabs = st.tabs([
        "🎲 智能推荐",
        "⚔️ 美食大乱斗", 
        "⚖️ 做饭vs外卖",
        "🥗 数字冰箱",
        "📊 饮食日历",
        "⚙️ 设置"
    ])
    
    with tabs[0]:
        smart_recommendation_page()
    
    with tabs[1]:
        food_pk_page()
    
    with tabs[2]:
        cook_or_order_page()
    
    with tabs[3]:
        digital_pantry_page()
    
    with tabs[4]:
        calendar_page()
    
    with tabs[5]:
        settings_page()

# ============ 健康打卡 ============
def show_health_checkin():
    """首页健康打卡"""
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        st.write("### 今日健康打卡")
    
    conn = get_db_connection()
    cursor = conn.cursor()
    today = datetime.now().date()
    user_id = st.session_state.current_user['username']
    
    cursor.execute("""
        SELECT * FROM health_checkin 
        WHERE date = ? AND user_id = ?
    """, (today.isoformat(), user_id))
    
    checkin = cursor.fetchone()
    water_checked = checkin['water_checked'] if checkin else 0
    fruit_checked = checkin['fruit_checked'] if checkin else 0
    
    with col2:
        water = st.checkbox("💧 喝够水了", value=bool(water_checked), key="water_check")
    
    with col3:
        fruit = st.checkbox("🍎 吃水果了", value=bool(fruit_checked), key="fruit_check")
    
    # 只在值变化时才更新，并且不触发rerun
    if water != bool(water_checked) or fruit != bool(fruit_checked):
        if checkin:
            cursor.execute("""
                UPDATE health_checkin 
                SET water_checked = ?, fruit_checked = ?
                WHERE date = ? AND user_id = ?
            """, (int(water), int(fruit), today.isoformat(), user_id))
        else:
            cursor.execute("""
                INSERT INTO health_checkin (date, user_id, water_checked, fruit_checked)
                VALUES (?, ?, ?, ?)
            """, (today.isoformat(), user_id, int(water), int(fruit)))
        conn.commit() # 仅在数据变化时提交
    
    # 健康提醒
    show_health_reminder()

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
        WHERE e.user_id = ? AND e.date >= ?
        GROUP BY f.health_tag
    """, (user_id, three_days_ago.isoformat()))
    
    tags = dict(cursor.fetchall())
    
    if tags.get('Spicy', 0) >= 3 or tags.get('CheatMeal', 0) >= 3:
        st.markdown("""
        <div class="health-tip">
            ⚠️ 最近吃得有点重口味哦，今天要不要试试清淡的？
        </div>
        """, unsafe_allow_html=True)

# ============ 智能推荐 ============
def smart_recommendation_page():
    st.write("### 🎲 智能推荐")
    st.caption("像朋友一样聊聊天，帮你找到最适合今天的美食")
    
    # 智能问答区域
    st.write("#### 💬 让我了解一下你的需求")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # 自动检测当前时间段
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
                # 将结果存入 session_state
                st.session_state.recommended_food = result['food']
                st.session_state.recommended_reason = result['reason']
                st.session_state.recommended_time = time_of_day
                st.rerun()
            else:
                st.warning("没有找到合适的食物，试试放宽条件？")
    
    # 显示推荐结果
    if 'recommended_food' in st.session_state and st.session_state.recommended_food:
        st.divider()
        st.success(st.session_state.recommended_reason)
        show_food_result_v2(st.session_state.recommended_food, st.session_state.recommended_time)

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
        query += " AND id NOT IN (SELECT food_id FROM eat_history WHERE user_id = ? AND date >= ?)"
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
                score -= 50 # 大幅降低不合适早餐的权重
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
    top_candidates = scored_foods[:5] # 扩大候选范围
    
    if not top_candidates:
        return None

    # 从最高分的几个候选者中，根据分数加权随机选择一个，避免每次都推荐同一个
    scores = [c['score'] for c in top_candidates]
    # 简单处理，避免分数为0或负数
    weights = [max(s, 1) for s in scores]
    
    selected = random.choices(top_candidates, weights=weights, k=1)[0]
    
    reason_text = "这个应该不错"
    if selected['reasons']:
        # 优先选择与用户输入最相关的理由
        primary_reason = selected['reasons'][0]
        other_reasons = [r for r in selected['reasons'][1:] if "你最爱" not in r] # 过滤通用理由
        if other_reasons:
            reason_text = f"{primary_reason}，而且{random.choice(other_reasons)}"
        else:
            reason_text = primary_reason

    return {
        'food': selected['food'],
        'reason': f"💡 {reason_text}！",
        'score': selected['score']
    }

# ============ 美食大乱斗 ============
def food_pk_page():
    st.write("### ⚔️ 美食大乱斗")
    st.caption("两两对决，选出你最想吃的！")
    
    if not st.session_state.pk_round:
        if st.button("🎮 开始PK", use_container_width=True):
            # 随机选8个食物进行PK
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM foods WHERE active = 1 ORDER BY RANDOM() LIMIT 8")
            foods = [dict(row) for row in cursor.fetchall()]
            
            st.session_state.pk_round = foods
            st.rerun()
    else:
        foods = st.session_state.pk_round
        
        if len(foods) == 1:
            # 决出冠军
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
            
            # 取前两个进行PK
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

# ============ 做饭vs外卖 ============
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
        cursor.execute("SELECT * FROM pantry WHERE user_id = ? AND quantity > 0 LIMIT 5", (user_id,))
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

# ============ 基于冰箱食材推荐 ============
def recommend_from_pantry():
    """根据冰箱里的食材推荐菜谱 - v2.0 智能匹配版"""
    # 扩充菜谱库，增加更多可能性
    # v2.1: 大幅扩充菜谱库
    recipe_book = {
        # --- 经典家常 ---
        "番茄炒蛋": ["番茄", "鸡蛋"],
        "青椒肉丝": ["青椒", "猪肉"],
        "鱼香肉丝": ["猪肉", "木耳", "胡萝卜"],
        "红烧肉": ["五花肉", "姜", "葱"],
        "糖醋排骨": ["排骨"],
        "回锅肉": ["五花肉", "青椒"],
        "麻婆豆腐": ["豆腐", "牛肉"],
        "宫保鸡丁": ["鸡丁", "花生", "黄瓜"],
        "可乐鸡翅": ["鸡翅", "可乐"],
        "大盘鸡": ["鸡肉", "土豆", "青椒"],
        "水煮牛肉": ["牛肉", "豆芽"],
        "西红柿牛腩": ["牛腩", "番茄", "洋葱"],
        "清蒸鱼": ["鱼", "葱", "姜"],
        "红烧茄子": ["茄子", "猪肉"],
        "地三鲜": ["土豆", "茄子", "青椒"],
        "干煸豆角": ["四季豆", "猪肉"],
        "手撕包菜": ["包菜", "蒜"],
        "酸辣土豆丝": ["土豆"],
        # --- 健康&素菜&蛋类 ---
        "清炒西兰花": ["西兰花"],
        "蒜蓉西兰花": ["西兰花", "蒜"],
        "蚝油生菜": ["生菜", "蒜"],
        "凉拌黄瓜": ["黄瓜", "蒜"],
        "凉拌木耳": ["木耳", "蒜"],
        "黄瓜炒鸡蛋": ["黄瓜", "鸡蛋"],
        "洋葱炒蛋": ["洋葱", "鸡蛋"],
        "韭菜炒蛋": ["韭菜", "鸡蛋"],
        "秋葵炒蛋": ["秋葵", "鸡蛋"],
        "蒸鸡蛋羹": ["鸡蛋"],
        "皮蛋豆腐": ["皮蛋", "豆腐"],
        # --- 快手主食 (面食) ---
        "葱油拌面": ["面条", "葱"],
        "西红柿鸡蛋面": ["面条", "番茄", "鸡蛋"],
        "炸酱面": ["面条", "猪肉", "黄瓜"],
        "阳春面": ["面条", "葱"],
        "雪菜肉丝面": ["面条", "猪肉", "雪菜"],
        # --- 汤羹 ---
        "排骨汤": ["排骨", "玉米", "胡萝卜"],
        "冬瓜排骨汤": ["冬瓜", "排骨"],
        "紫菜蛋花汤": ["紫菜", "鸡蛋"],
        # --- 方便速成 ---
        "香煎鸡胸肉": ["鸡胸肉"],
        "白灼虾": ["虾"],
        "火腿炒蛋": ["火腿", "鸡蛋"],
        "咖喱鸡肉": ["鸡肉", "土豆", "胡萝卜", "洋葱"],
    }

    # 从数据库加载用户自定义菜谱
    user_id = st.session_state.current_user['username']
    conn_user_recipe = get_db_connection() # This is already cached, no need for a separate variable
    cursor_user_recipe = conn_user_recipe.cursor()
    cursor_user_recipe.execute("SELECT recipe_name, ingredients FROM user_recipes WHERE user_id = ?", (user_id,))
    user_recipes = cursor_user_recipe.fetchall()

    for rec in user_recipes:
        try:
            # 将内置菜谱与用户菜谱合并，用户菜谱优先级更高
            recipe_book[rec['recipe_name']] = json.loads(rec['ingredients'])
        except json.JSONDecodeError:
            continue # 如果JSON格式错误则跳过

    conn = get_db_connection()
    cursor = conn.cursor()
    # 修复：查询冰箱食材时必须指定当前用户
    cursor.execute("SELECT food_name FROM pantry WHERE quantity > 0 AND user_id = ?", (user_id,))
    # 将食材名称转换为集合以便快速查找
    available_ingredients = {item['food_name'] for item in cursor.fetchall()}

    if not available_ingredients:
        return []

    scored_dishes = []
    for dish, required in recipe_book.items():
        required_set = set(required)
        have_set = available_ingredients.intersection(required_set)
        missing_set = required_set - have_set
        
        # 计算匹配度
        match_score = len(have_set) / len(required_set)
        
        # 只要拥有至少一个核心食材，就加入推荐列表
        if match_score > 0:
            scored_dishes.append({
                'name': dish,
                'score': match_score,
                'have': list(have_set),
                'missing': list(missing_set)
            })
    
    # 按匹配度从高到低排序
    scored_dishes.sort(key=lambda x: x['score'], reverse=True)
    
    return scored_dishes

# ============ 数字冰箱 ============
def digital_pantry_page():
    st.write("### 🥗 数字冰箱")
    
    pantry_tabs = st.tabs(["库存管理", "智能配餐", "待买清单"])
    
    with pantry_tabs[0]:
        st.write("#### 当前库存")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        user_id = st.session_state.current_user['username']
        cursor.execute("SELECT * FROM pantry WHERE user_id = ? ORDER BY updated_at DESC", (user_id,))
        items = cursor.fetchall()
        
        if not items:
            st.info("冰箱空空如也")
        else:
            # 将数据转换为 Pandas DataFrame
            df = pd.DataFrame(items, columns=[desc[0] for desc in cursor.description])

            # 表头
            col_h1, col_h2, col_h3, col_h4 = st.columns([4, 2, 3, 1])
            with col_h1:
                st.caption("食材")
            with col_h2:
                st.caption("数量")
            with col_h3:
                st.caption("更新时间")
            with col_h4:
                st.caption("操作")
            st.divider()

            # 遍历 DataFrame 来显示每一行
            for index, item in df.iterrows():
                col1, col2, col3, col4 = st.columns([4, 2, 3, 1])
                with col1:
                    st.markdown(f"<div style='padding-top: 8px;'>{item['food_name']}</div>", unsafe_allow_html=True)
                with col2:
                    st.markdown(f"<div style='text-align: center; padding-top: 8px; font-weight: bold;'>{item['quantity']}</div>", unsafe_allow_html=True)
                with col3:
                    update_time = pd.to_datetime(item['updated_at']).strftime('%Y-%m-%d %H:%M')
                    st.markdown(f"<div style='padding-top: 8px; font-size: 0.9em; color: #888;'>{update_time}</div>", unsafe_allow_html=True)
                
                with col4:
                    # 使用 popover 来放置操作按钮，使界面更紧凑
                    with st.popover("操作", use_container_width=True):
                        if st.button("➕ 增加", key=f"incr_pantry_{item['id']}", use_container_width=True):
                            cursor.execute("UPDATE pantry SET quantity = quantity + 1, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (item['id'],))
                            conn.commit()
                            st.rerun()
                        if st.button("➖ 减少", key=f"decr_pantry_{item['id']}", use_container_width=True):
                            new_qty = item['quantity'] - 1
                            if new_qty > 0:
                                cursor.execute("UPDATE pantry SET quantity = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?", (new_qty, item['id']))
                            else: # 数量为0时直接删除
                                cursor.execute("DELETE FROM pantry WHERE id = ?", (item['id'],))
                            conn.commit()
                            st.rerun()
                        if st.button("🗑️ 删除", key=f"del_pantry_{item['id']}", use_container_width=True, type="primary"):
                            cursor.execute("DELETE FROM pantry WHERE id = ?", (item['id'],))
                            conn.commit()
                            st.rerun()
        
        st.divider()
        st.write("#### 添加库存")
        col_a, col_b, col_c = st.columns([5, 2, 2])
        with col_a:
            new_food = st.text_input("食材名称", label_visibility="collapsed", placeholder="输入食材名称...")
        with col_b:
            new_qty = st.number_input("数量", min_value=1, value=1, label_visibility="collapsed")
        with col_c:
            if st.button("➕ 添加到冰箱", key="add_pantry_item", use_container_width=True):
                if new_food:
                    cursor.execute("""
                        INSERT INTO pantry (food_name, quantity, status, user_id)
                        VALUES (?, ?, '充足', ?)
                    """, (new_food, new_qty, user_id))
                    conn.commit()
                    st.success(f"已添加 {new_food}")
                    st.rerun()
    
    with pantry_tabs[1]:
        st.write("#### 智能配餐")
        st.caption("根据你冰箱里的食材，看看今天能做什么好吃的！")

        if st.button("🍳 帮我看看能做什么", use_container_width=True):
            with st.spinner("正在翻看冰箱和菜谱..."):
                recommendations = recommend_from_pantry()
                if recommendations:
                    st.session_state.pantry_recommendations = recommendations
                else:
                    st.session_state.pantry_recommendations = []
                    st.warning("冰箱里的食材好像还不够做一道完整的菜哦，去“库存管理”看看吧！")
        
        if 'pantry_recommendations' in st.session_state and st.session_state.pantry_recommendations:
            st.write("---")
            
            # 安全检查：确保 session 中的数据结构是新的（包含 'score' 键）
            if 'score' not in st.session_state.pantry_recommendations[0]:
                st.session_state.pantry_recommendations = [] # 如果是旧数据，则清空
                st.rerun()

            # 分为“万事俱备”和“就差一点”
            ready_to_cook = [r for r in st.session_state.pantry_recommendations if r['score'] == 1.0]
            almost_ready = [r for r in st.session_state.pantry_recommendations if 0 < r['score'] < 1.0]

            if ready_to_cook:
                st.success("🎉 万事俱备！这些菜可以直接做：")
                for rec in ready_to_cook:
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"#### {rec['name']}")
                    with col2:
                        st.link_button("📕 小红书教程", f"https://www.xiaohongshu.com/search_result/?keyword={rec['name']} 做法", use_container_width=True)
            
            if almost_ready:
                st.info("💡 就差一点！补齐这些食材就能做：")
                for rec in almost_ready:
                    st.markdown(f"#### {rec['name']}")
                    
                    col1, col2 = st.columns([2,1])
                    with col1:
                        missing_str = ", ".join(rec['missing'])
                        st.caption(f"还差：<span style='color: red;'>**{missing_str}**</span>", unsafe_allow_html=True)
                    with col2:
                        if st.button("🛒 加入待买", key=f"add_missing_{rec['name']}", use_container_width=True):
                            conn = get_db_connection()
                            cursor = conn.cursor()
                            user_id = st.session_state.current_user['username']
                            for item in rec['missing']:
                                # 简单处理：如果不存在则添加
                                cursor.execute("INSERT OR IGNORE INTO shopping_list (item_name, user_id) VALUES (?, ?)", (item, user_id))
                            conn.commit()
                            st.toast(f"“{missing_str}” 已加入待买清单！")
                            time.sleep(0.5)

                    st.link_button("📕 去小红书找灵感", f"https://www.xiaohongshu.com/search_result/?keyword={rec['name']} 做法", use_container_width=True)
    
    with pantry_tabs[2]:
        st.write("#### 待买清单")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shopping_list WHERE is_bought = 0")
        user_id = st.session_state.current_user['username']
        items = cursor.execute("SELECT * FROM shopping_list WHERE is_bought = 0 AND user_id = ?", (user_id,)).fetchall()
        
        if items:
            for item in items:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"✅ {item['item_name']}")
                with col2:
                    st.caption(f"x{item['quantity']}")
                with col3:
                    if st.button("删除", key=f"del_shop_{item['id']}"):
                        cursor.execute("DELETE FROM shopping_list WHERE id = ?", (item['id'],))
                        conn.commit()
                        st.rerun()
        else:
            st.info("暂无待买项")
        
        st.divider()
        col_a, col_b = st.columns([2, 1])
        with col_a:
            new_item = st.text_input("添加到购物清单")
        with col_b:
            if st.button("➕ 添加", key="add_shopping_item"):
                if new_item:
                    cursor.execute("""
                        INSERT INTO shopping_list (item_name, user_id)
                        VALUES (?, ?)
                    """, (new_item, st.session_state.current_user['username']))
                    conn.commit()
                    st.success("已添加")
                    st.rerun()

# ============ 饮食日历 ============
def calendar_page():
    st.write("### 📅 饮食日历与统计")
    
    cal_tabs = st.tabs(["🗓️ 日历视图", "📊 统计图表"])
    user_id = st.session_state.current_user['username']

    with cal_tabs[0]:
        st.caption("查看过去30天的饮食记录")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # 获取最近30天的记录
        thirty_days_ago = (datetime.now() - timedelta(days=30)).date()
        cursor.execute("""
            SELECT date, food_name, meal_time, rating
            FROM eat_history
            WHERE user_id = ? AND date >= ?
            ORDER BY date DESC, created_at DESC
        """, (user_id, thirty_days_ago.isoformat()))
        
        records = cursor.fetchall()
        
        if records:
            # 按日期分组显示
            by_date = defaultdict(list)
            for rec in records:
                by_date[rec['date']].append(rec)
            
            for date in sorted(by_date.keys(), reverse=True):
                st.write(f"#### {date}")
                for rec in by_date[date]:
                    meal_emoji = {"早餐": "🌅", "午餐": "☀️", "晚餐": "🌙", "夜宵": "🌃"}.get(rec['meal_time'], "🍽️")
                    rating_stars = "⭐" * (rec['rating'] or 0)
                    st.write(f"{meal_emoji} {rec['meal_time']}: {rec['food_name']} {rating_stars}")
                st.divider()
        else:
            st.info("还没有饮食记录哦")

    with cal_tabs[1]:
        st.caption("通过图表回顾你的饮食习惯")
        
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT e.date, e.meal_time, e.food_name, e.rating, f.health_tag
            FROM eat_history e
            LEFT JOIN foods f ON e.food_name = f.name
            WHERE e.user_id = ?
        """, (user_id,))
        history_data = cursor.fetchall()
        column_names = [description[0] for description in cursor.description]

        if not history_data:
            st.info("还没有足够的饮食记录来生成统计图表哦。")
        else:
            df = pd.DataFrame(history_data, columns=column_names)
            df['date'] = pd.to_datetime(df['date'])

            st.write("#### 📅 最近30天饮食热力图")
            thirty_days_ago = pd.to_datetime(datetime.now() - timedelta(days=30))
            recent_df = df[df['date'] >= thirty_days_ago]
            
            if not recent_df.empty:
                daily_counts = recent_df.groupby(df['date'].dt.date).size().reset_index(name='counts')
                daily_counts['date'] = pd.to_datetime(daily_counts['date'])
                date_range = pd.date_range(start=daily_counts['date'].min(), end=daily_counts['date'].max())
                full_range_df = pd.DataFrame(date_range, columns=['date'])
                daily_counts = pd.merge(full_range_df, daily_counts, on='date', how='left').fillna(0)

                fig_heatmap = px.density_heatmap(daily_counts, x=daily_counts['date'].dt.dayofweek, y=daily_counts['date'].dt.isocalendar().week, z='counts', labels={'x': '星期', 'y': '周数', 'z': '记录数'}, title="每日记录数 (颜色越深记录越多)", text_auto=True, color_continuous_scale="Greens")
                fig_heatmap.update_layout(yaxis_title="周数", xaxis_title="星期", xaxis={'ticktext': ['一', '二', '三', '四', '五', '六', '日'], 'tickvals': list(range(7))})
                st.plotly_chart(fig_heatmap, use_container_width=True)
            else:
                st.info("最近30天没有饮食记录。")

            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                st.write("#### 🍽️ 餐次分布")
                meal_counts = df['meal_time'].value_counts().reset_index()
                fig_pie = px.pie(meal_counts, values='count', names='meal_time', title="各项餐次占比")
                st.plotly_chart(fig_pie, use_container_width=True)
            with col2:
                st.write("#### 🍔 健康标签分布")
                health_tag_counts = df['health_tag'].value_counts().reset_index()
                fig_bar = px.bar(health_tag_counts, x='health_tag', y='count', title="各类饮食标签占比", labels={'health_tag': '健康标签', 'count': '次数'})
                st.plotly_chart(fig_bar, use_container_width=True)

# ============ 设置页面 ============
def settings_page():
    st.write("### ⚙️ 设置")
    
    user_id = st.session_state.current_user['username']
    conn = get_db_connection()
    cursor = conn.cursor()
    prefs = get_user_preferences(conn, user_id) # get_user_preferences doesn't need the cursor, but other parts of the page do.
    
    # 创建标签页
    tabs = st.tabs(["🌶️ 口味偏好", "📖 我的菜谱", "🍽️ 食物管理", "🚫 黑名单", "👤 账户信息"])
    
    # ==== 口味偏好 ====
    with tabs[0]:
        st.write("#### 基本偏好")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            spicy = st.checkbox("🌶️ 喜欢吃辣", value=prefs.get('spicy', False))
        with col2:
            sweet = st.checkbox("🍭 喜欢甜食", value=prefs.get('sweet', False))
        with col3:
            vegetarian = st.checkbox("🥗 素食主义", value=prefs.get('vegetarian', False))
        
        st.write("#### 饮食习惯")
        col4, col5 = st.columns(2)
        with col4:
            favorite_category = st.multiselect(
                "最喜欢的类型（多选）",
                ["中餐", "西餐", "日料", "快餐", "家常菜", "甜品", "轻食"],
                default=prefs.get('favorite_category', [])
            )
        with col5:
            avoid_category = st.multiselect(
                "不想吃的类型（多选）",
                ["海鲜", "火锅", "烧烤", "油炒", "生食"],
                default=prefs.get('avoid_category', [])
            )
        
        st.write("#### 健康目标")
        col6, col7 = st.columns(2)
        with col6:
            health_mode = st.selectbox(
                "当前模式",
                ["普通模式", "健康模式", "放纵模式"],
                index=["普通模式", "健康模式", "放纵模式"].index(prefs.get('health_mode', '普通模式'))
            )
            st.caption("👉 健康模式：优先推荐清淡食物")
        with col7:
            daily_calorie_goal = st.number_input(
                "每日热量目标（千卡）",
                min_value=1000,
                max_value=3000,
                value=prefs.get('daily_calorie_goal', 2000),
                step=100
            )
        
        if st.button("💾 保存偏好", use_container_width=True):
            update_user_preferences(conn, user_id, {
                'spicy': spicy,
                'sweet': sweet,
                'vegetarian': vegetarian,
                'favorite_category': favorite_category,
                'avoid_category': avoid_category,
                'health_mode': health_mode,
                'daily_calorie_goal': daily_calorie_goal
            })
            st.success("✅ 已保存，下次推荐时生效！")

    # ==== 食物管理 ====
    with tabs[1]: # 我的菜谱
        st.write("#### 📖 我的菜谱")
        st.caption("在这里添加你的私房菜谱，让“智能配餐”更懂你！")


        # 显示已有菜谱
        cursor.execute("SELECT id, recipe_name, ingredients FROM user_recipes WHERE user_id = ?", (user_id,))
        my_recipes = cursor.fetchall()

        if my_recipes:
            for recipe in my_recipes:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"**{recipe['recipe_name']}**")
                    ingredients_list = json.loads(recipe['ingredients'])
                    st.caption(f"需要: {', '.join(ingredients_list)}")
                with col2:
                    if st.button("🗑️ 删除", key=f"del_recipe_{recipe['id']}", use_container_width=True):
                        cursor.execute("DELETE FROM user_recipes WHERE id = ?", (recipe['id'],))
                        conn.commit()
                        st.rerun()
                st.divider()
        else:
            st.info("你还没有添加任何私房菜谱。")

        # 添加新菜谱
        st.write("##### 添加新菜谱")
        new_recipe_name = st.text_input("菜谱名称", key="new_recipe_name")
        new_recipe_ingredients = st.text_input("所需食材（用逗号隔开）", key="new_recipe_ingredients", placeholder="例如: 猪肉, 青椒, 蒜")

        if st.button("💾 保存菜谱", key="add_my_recipe", use_container_width=True):
            if new_recipe_name and new_recipe_ingredients:
                ingredients_list = [item.strip() for item in new_recipe_ingredients.split(',')]
                ingredients_json = json.dumps(ingredients_list)
                try:
                    cursor.execute(
                        "INSERT INTO user_recipes (user_id, recipe_name, ingredients) VALUES (?, ?, ?)",
                        (user_id, new_recipe_name, ingredients_json)
                    )
                    conn.commit()
                    st.success(f"菜谱 “{new_recipe_name}” 已保存！")
                    st.rerun()
                except Exception as e:
                    st.error("保存失败，菜谱名称可能已存在。")

    with tabs[2]:
        st.write("#### 🍽️ 食物管理")
        
        # 顶部统计
        cursor.execute("SELECT COUNT(*) as total FROM foods")
        total_count = cursor.fetchone()['total']
        cursor.execute("SELECT COUNT(*) as active FROM foods WHERE active = 1")
        active_count = cursor.fetchone()['active']
        
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("🍴 总食物数", total_count)
        with col_stat2:
            st.metric("✅ 已启用", active_count)
        with col_stat3:
            st.metric("❌ 已禁用", total_count - active_count)
        
        st.divider()
        
        # 搜索和筛选区域
        col_s1, col_s2, col_s3 = st.columns([2, 1, 1])
        with col_s1:
            search_term = st.text_input("🔍 搜索食物名称", key="search_food")
        with col_s2:
            filter_category = st.selectbox(
                "🏷️ 筛选分类", 
                ["全部", "中餐", "西餐", "日料", "快餐", "家常菜", "甜品", "轻食", "烧烤", "零食饮料"]
            )
        with col_s3:
            filter_status = st.selectbox("🛡️ 状态", ["全部", "已启用", "已禁用"])
        
        # 排序选项
        col_s4, col_s5 = st.columns([2, 1])
        with col_s4:
            sort_by = st.selectbox(
                "🔄 排序方式",
                ["最新添加", "名称A-Z", "名称Z-A", "价格从低到高", "价格从高到低"]
            )
        with col_s5:
            limit = st.selectbox("📊 显示数量", [10, 20, 50, 100], index=1)
        
        # 构建查询
        query = "SELECT * FROM foods WHERE 1=1"
        params = []
        
        if search_term:
            query += " AND name LIKE ?"
            params.append(f"%{search_term}%")
        
        if filter_category != "全部":
            query += " AND category = ?"
            params.append(filter_category)
        
        if filter_status == "已启用":
            query += " AND active = 1"
        elif filter_status == "已禁用":
            query += " AND active = 0"
        
        # 添加排序
        if sort_by == "最新添加":
            query += " ORDER BY created_at DESC"
        elif sort_by == "名称A-Z":
            query += " ORDER BY name ASC"
        elif sort_by == "名称Z-A":
            query += " ORDER BY name DESC"
        elif sort_by == "价格从低到高":
            query += " ORDER BY cost_level ASC"
        elif sort_by == "价格从高到低":
            query += " ORDER BY cost_level DESC"
        
        query += f" LIMIT {limit}"
        
        cursor.execute(query, params)
        foods = cursor.fetchall()
        
        st.caption(f"🔎 共找到 **{len(foods)}** 个食物")
        
        # 食物列表
        if foods:
            for food in foods:
                with st.container():
                    col1, col2, col3, col4, col5, col6 = st.columns([3, 1, 1, 1, 1, 1])
                    with col1:
                        status_icon = "✅" if food['active'] else "❌"
                        st.write(f"{status_icon} **{food['name']}**")
                    with col2:
                        st.caption(f"🏷️ {food['category']}")
                    with col3:
                        st.caption(f"💰 {food['cost_level']}")
                    with col4:
                        # 将 sqlite3.Row 转换为字典以支持 get 方法
                        food_dict = dict(food)
                        tag_emoji = {
                            'Healthy': '🥗',
                            'Spicy': '🌶️',
                            'CheatMeal': '🍔',
                            'Normal': '🍽️'
                        }.get(food_dict.get('health_tag'), '🍽️')
                        st.caption(f"{tag_emoji} {food_dict.get('health_tag', 'Normal')}")
                    with col5:
                        if st.button("✏️", key=f"edit_{food['id']}"):
                            st.session_state[f"editing_{food['id']}"] = True
                            st.rerun()
                    with col6:
                        toggle_text = "❌ 禁用" if food['active'] else "✅ 启用"
                        if st.button(toggle_text, key=f"toggle_{food['id']}"):
                            new_status = 0 if food['active'] else 1
                            cursor.execute("UPDATE foods SET active = ? WHERE id = ?", (new_status, food['id']))
                            conn.commit()
                            st.rerun()
                    
                    # 编辑模式
                    if st.session_state.get(f"editing_{food['id']}", False):
                        with st.expander("📝 编辑食物信息", expanded=True):
                            col_e1, col_e2, col_e3, col_e4 = st.columns(4)
                            with col_e1:
                                edit_name = st.text_input("名称", value=food['name'], key=f"edit_name_{food['id']}")
                            with col_e2:
                                categories = ["中餐", "西餐", "日料", "快餐", "家常菜", "甜品", "轻食", "烧烤", "零食饮料"]
                                edit_cat = st.selectbox(
                                    "分类", 
                                    categories,
                                    index=categories.index(food['category']) if food['category'] in categories else 0,
                                    key=f"edit_cat_{food['id']}"
                                )
                            with col_e3:
                                costs = ["$", "$$", "$$$"]
                                edit_cost = st.selectbox(
                                    "价格",
                                    costs,
                                    index=costs.index(food['cost_level']) if food['cost_level'] in costs else 0,
                                    key=f"edit_cost_{food['id']}"
                                )
                            with col_e4:
                                tags = ["Healthy", "Spicy", "CheatMeal", "Normal"]
                                # 将 sqlite3.Row 转换为字典以支持 get 方法
                                food_dict = dict(food)
                                edit_tag = st.selectbox(
                                    "标签",
                                    tags,
                                    index=tags.index(food_dict.get('health_tag', 'Normal')) if food_dict.get('health_tag') in tags else 3,
                                    key=f"edit_tag_{food['id']}"
                                )
                            
                            col_b1, col_b2, col_b3 = st.columns([1, 1, 2])
                            with col_b1:
                                if st.button("✅ 保存", key=f"save_{food['id']}", use_container_width=True):
                                    cursor.execute("""
                                        UPDATE foods 
                                        SET name = ?, category = ?, cost_level = ?, health_tag = ?
                                        WHERE id = ?
                                    """, (edit_name, edit_cat, edit_cost, edit_tag, food['id']))
                                    conn.commit()
                                    st.session_state[f"editing_{food['id']}"] = False
                                    st.success("✅ 修改成功！")
                                    time.sleep(0.5)
                                    st.rerun()
                            with col_b2:
                                if st.button("❌ 取消", key=f"cancel_{food['id']}", use_container_width=True):
                                    st.session_state[f"editing_{food['id']}"] = False
                                    st.rerun()
                            with col_b3:
                                if st.button("🗑️ 删除该食物", key=f"delete_{food['id']}", type="secondary", use_container_width=True):
                                    cursor.execute("DELETE FROM foods WHERE id = ?", (food['id'],))
                                    conn.commit()
                                    st.session_state[f"editing_{food['id']}"] = False
                                    st.warning("⚠️ 已删除")
                                    time.sleep(0.5)
                                    st.rerun()
                    
                    st.divider()
        else:
            st.info("🔍 没有找到符合条件的食物")
        
        # 批量操作
        st.write("")
        st.write("#### 🛠️ 批量操作")
        col_batch1, col_batch2, col_batch3 = st.columns(3)
        with col_batch1:
            if st.button("✅ 启用所有", key="enable_all", use_container_width=True):
                cursor.execute("UPDATE foods SET active = 1")
                conn.commit()
                st.success("✅ 已启用所有食物")
                time.sleep(0.5)
                st.rerun()
        with col_batch2:
            if st.button("❌ 禁用所有", key="disable_all", use_container_width=True):
                cursor.execute("UPDATE foods SET active = 0")
                conn.commit()
                st.warning("⚠️ 已禁用所有食物")
                time.sleep(0.5)
                st.rerun()
        with col_batch3:
            if st.button("🗑️ 删除已禁用", key="delete_disabled", type="secondary", use_container_width=True):
                cursor.execute("DELETE FROM foods WHERE active = 0")
                conn.commit()
                st.warning("⚠️ 已删除所有禁用的食物")
                time.sleep(0.5)
                st.rerun()
        
        st.divider()
        
        # 添加新食物
        st.write("#### ➕ 添加新食物")
        col_a, col_b, col_c, col_d = st.columns(4)
        with col_a:
            new_food_name = st.text_input("🍴 食物名称", key="new_food_name")
        with col_b:
            new_food_cat = st.selectbox(
                "🏷️ 分类", 
                ["中餐", "西餐", "日料", "快餐", "家常菜", "甜品", "轻食", "烧烤", "零食饮料"],
                key="new_food_cat"
            )
        with col_c:
            new_food_cost = st.selectbox("💰 价格", ["$", "$$", "$$$"], key="new_food_cost")
        with col_d:
            new_food_tag = st.selectbox(
                "🏷️ 标签", 
                ["Normal", "Healthy", "Spicy", "CheatMeal"],
                key="new_food_tag"
            )
        
        if st.button("➕ 添加食物", key="add_new_food", use_container_width=True):
            if new_food_name:
                cursor.execute("""
                    INSERT INTO foods (name, category, cost_level, health_tag, active)
                    VALUES (?, ?, ?, ?, 1)
                """, (new_food_name, new_food_cat, new_food_cost, new_food_tag))
                conn.commit()
                st.success(f"✅ 已添加 **{new_food_name}**")
                time.sleep(0.5)
                st.rerun()
            else:
                st.warning("⚠️ 请输入食物名称")
        
    # ==== 黑名单 ====
    with tabs[3]:
        st.write("#### 我的黑名单")
        st.caption("添加到黑名单的食物将不会出现在推荐中")
        
        blacklist = prefs.get('blacklist', [])
        
        if blacklist:
            for item in blacklist:
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.write(f"🚫 {item}")
                with col2:
                    if st.button("移除", key=f"rm_black_{item}"):
                        blacklist.remove(item)
                        update_user_preferences(conn, user_id, {'blacklist': blacklist})
                        st.rerun()
        else:
            st.info("黑名单为空")
        
        st.divider()
        col_x, col_y = st.columns([3, 1])
        with col_x:
            new_blacklist_item = st.text_input("添加到黑名单")
        with col_y:
            if st.button("➕ 添加", key="add_blacklist"):
                if new_blacklist_item and new_blacklist_item not in blacklist:
                    blacklist.append(new_blacklist_item)
                    update_user_preferences(conn, user_id, {'blacklist': blacklist})
                    st.success("✅ 已添加")
                    st.rerun()
    
    # ==== 账户信息 ====
    with tabs[4]:
        st.write("#### 👤 账户信息")

        if user_id == 'guest':
            st.warning("访客模式不支持上传头像。")
        else:
            # 显示当前头像
            avatar = get_user_avatar(conn, user_id)
            if avatar:
                st.image(avatar, caption="当前头像", width=128)
            else:
                st.caption("你还没有设置头像")

            # 上传新头像
            uploaded_avatar = st.file_uploader(
                "上传新头像", 
                type=['png', 'jpg', 'jpeg'],
                accept_multiple_files=False,
                key="avatar_uploader"
            )
            if uploaded_avatar is not None:
                avatar_data = uploaded_avatar.getvalue()
                update_user_avatar(conn, user_id, avatar_data)
                st.success("✅ 头像更新成功！")
                time.sleep(0.5)
                st.rerun()

            st.divider()
            
            cursor.execute("SELECT * FROM users WHERE username = ?", (user_id,))
            user_row = cursor.fetchone()
            
            if user_row:
                user_info = dict(user_row)  # 转换为字典
                st.write(f"**用户名**: {user_info['username']}")
                st.write(f"**注册时间**: {user_info.get('created_at', '未知')}")
            else:
                st.error("用户信息不存在")
        
        st.divider()
        
        st.write("#### 修改密码")
        with st.form("change_password_form"):
            new_pwd = st.text_input("新密码", type="password")
            confirm_pwd = st.text_input("确认新密码", type="password")
            if st.form_submit_button("🔒 修改密码"):
                if not new_pwd:
                    st.warning("❗ 新密码不能为空！")
                elif new_pwd != confirm_pwd:
                    st.error("❗ 两次输入的新密码不一致！")
                else:
                    if update_password(conn, user_id, new_pwd):
                        st.success("✅ 密码修改成功！")
                    else:
                        st.error("❌ 密码修改失败，请稍后重试。")
        
        st.divider()
        
        if st.button("🚪 退出登录", key="logout_settings_btn", use_container_width=True):
            st.session_state.show_logout_confirmation = True
            st.rerun()

# ============ 结果展示 ============
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
        # 将 sqlite3.Row 转换为字典以支持 get 方法
        food_dict = dict(food)
        st.metric("标签", food_dict.get('health_tag') or "无")
    
    # 根据时间段自动推断哪一餐
    meal_time_map = {
        "早餐时间": "早餐",
        "午餐时间": "午餐",
        "下午茶": "午餐",  # 下午茶计入午餐
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
                VALUES (?, ?, ?, ?, ?, ?, 'smart')
            """, (
                datetime.now().date().isoformat(),
                auto_meal_time,  # 使用自动推断的餐次
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
            # 清空推荐结果，返回选择界面
            st.session_state.recommended_food = None
            st.rerun()
    
    # 显示菜谱链接
    # 将 sqlite3.Row 转换为字典以支持 get 方法
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
        # 将 sqlite3.Row 转换为字典以支持 get 方法
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
            VALUES (?, ?, ?, ?, ?, ?, 'random')
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
    
    # 显示菜谱链接
    if dict(food).get('recipe_link'):
        st.write(f"📖 [查看菜谱]({food['recipe_link']})")

# ============ 主入口 ============
if not st.session_state.logged_in:
    login_page()
else:
    main_app()
