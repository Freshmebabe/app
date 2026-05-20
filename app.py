import sys
import os
# 确保项目根目录在 Python 路径中（解决 Streamlit Cloud 子模块导入问题）
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
import time
import base64
from datetime import datetime, timedelta
from database import (
    get_connection, get_db_connection, initialize_and_seed_database, verify_user, create_user,
    get_user_avatar
)

# 页面模块
from modules.recommend import smart_recommendation_page
from modules.pantry import digital_pantry_page
from modules.calendar import calendar_page
from modules.settings import settings_page

# 工具模块
from utils.display import show_health_reminder

# 页面配置
st.set_page_config(
    page_title="HoneyEat - 亲爱的今天吃什么",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# 简约暖色系CSS
st.markdown("""
<style>
    /* 全局 */
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei";
        background: #fafafa;
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
    
    /* 卡片 */
    .card {
        background: white;
        border-radius: 14px;
        padding: 1.5rem;
        margin: 1rem 0;
        box-shadow: 0 1px 6px rgba(0,0,0,0.06);
    }
    
    /* 按钮 — 统一柔和渐变 */
    .stButton>button {
        background: linear-gradient(135deg, #f5f7fa 0%, #e8ecf1 100%);
        color: #333;
        border: none;
        border-radius: 12px;
        padding: 0.7rem 1.5rem;
        font-weight: 500;
        transition: all 0.25s;
        width: 100%;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .stButton>button:hover {
        background: linear-gradient(135deg, #e2e6f0 0%, #d5dbe8 100%);
        transform: translateY(-1px);
        box-shadow: 0 3px 8px rgba(0,0,0,0.08);
    }
    .stButton>button:active {
        transform: translateY(0);
    }
    
    /* 主操作按钮 */
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
        color: white !important;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(102,126,234,0.25);
    }
    .stButton>button[kind="primary"]:hover {
        background: linear-gradient(135deg, #5a6fd6 0%, #6a3f96 100%) !important;
        box-shadow: 0 6px 16px rgba(102,126,234,0.35);
    }
    
    /* 结果展示盒 */
    .result-box {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 2rem;
        border-radius: 18px;
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
        background: #fef9e7;
        border-left: 4px solid #f5b041;
        padding: 0.8rem 1rem;
        border-radius: 0 8px 8px 0;
        margin: 0.6rem 0;
        font-size: 0.95rem;
    }

    /* AI推荐结果卡片 */
    .ai-result-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8f9ff 100%);
        border: 1px solid #e8ecf1;
        border-radius: 18px;
        padding: 1.5rem 2rem;
        margin: 1rem 0;
        box-shadow: 0 4px 16px rgba(102, 126, 234, 0.08);
        animation: fadeIn 0.6s ease;
    }
    .ai-dish-name {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.5rem;
    }
    .ai-rating {
        font-size: 1.4rem;
        color: #f5a623;
        margin-bottom: 0.6rem;
        letter-spacing: 2px;
    }
    .ai-tag {
        display: inline-block;
        background: linear-gradient(135deg, #667eea, #764ba2);
        color: white;
        font-size: 0.75rem;
        font-weight: 600;
        padding: 0.2rem 0.7rem;
        border-radius: 20px;
        margin-right: 0.4rem;
        margin-bottom: 0.7rem;
    }
    .ai-meta {
        display: flex;
        gap: 1rem;
        font-size: 0.9rem;
        color: #555;
        margin-bottom: 0.8rem;
        flex-wrap: wrap;
    }
    .ai-meta span {
        background: #f0f2f5;
        padding: 0.25rem 0.7rem;
        border-radius: 6px;
    }
    .ai-desc {
        font-style: italic;
        color: #666;
        font-size: 1rem;
        line-height: 1.7;
        border-left: 3px solid #667eea;
        padding-left: 1rem;
        margin-top: 0.8rem;
    }

    /* 头像 */
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
        box-shadow: 0 2px 12px rgba(0,0,0,0.08);
    }
    .user-nav-name {
        font-weight: 600;
        text-align: center;
        color: #333;
    }
    
    /* 隐藏默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* 移动端适配 */
    @media (max-width: 768px) {
        .main-title { font-size: 1.7rem; }
        .result-box { font-size: 1.4rem; padding: 1.2rem; }
        .ai-dish-name { font-size: 1.4rem; }
        .ai-result-card { padding: 1rem 1.2rem; }
        .ai-meta { gap: 0.6rem; font-size: 0.8rem; }
        
        .stButton > button {
            min-height: 44px !important;
            font-size: 1rem !important;
            padding: 0.7rem 1rem !important;
        }
        input[type="text"], input[type="password"] {
            min-height: 44px !important;
            font-size: 16px !important;
        }
        .block-container {
            padding: 1rem 0.5rem !important;
        }
    }
</style>
""", unsafe_allow_html=True)

# Session state 初始化
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state:
    st.session_state.current_user = None
if 'show_switch_account' not in st.session_state:
    st.session_state.show_switch_account = False

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
        WHERE date = %s AND user_id = %s
    """, (today.isoformat(), user_id))
    
    checkin = cursor.fetchone()
    water_checked = checkin['water_checked'] if checkin else 0
    fruit_checked = checkin['fruit_checked'] if checkin else 0
    
    with col2:
        water = st.checkbox("💧 喝够水了", value=bool(water_checked), key="water_check")
    
    with col3:
        fruit = st.checkbox("🍎 吃水果了", value=bool(fruit_checked), key="fruit_check")
    
    if water != bool(water_checked) or fruit != bool(fruit_checked):
        if checkin:
            cursor.execute("""
                UPDATE health_checkin 
                SET water_checked = %s, fruit_checked = %s
                WHERE date = %s AND user_id = %s
            """, (int(water), int(fruit), today.isoformat(), user_id))
        else:
            cursor.execute("""
                INSERT INTO health_checkin (date, user_id, water_checked, fruit_checked)
                VALUES (%s, %s, %s, %s)
            """, (today.isoformat(), user_id, int(water), int(fruit)))
        conn.commit()
    
    show_health_reminder()

# ============ 默认用户初始化 ============
def init_default_user():
    """自动以 'gf' 身份登录，若用户不存在则自动创建"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT username, name FROM users WHERE username = 'gf'")
    user_row = cursor.fetchone()
    if user_row:
        st.session_state.logged_in = True
        st.session_state.current_user = {
            'username': user_row['username'],
            'name': user_row['name']
        }
    else:
        create_user(conn, 'gf', 'gf', 'gf123')
        st.session_state.logged_in = True
        st.session_state.current_user = {'username': 'gf', 'name': 'gf'}
    st.query_params["user"] = "gf"

# ============ 主应用 ============
def main_app():
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
                    st.markdown('<div style="font-size: 72px; text-align: center;">👤</div>', unsafe_allow_html=True)
                st.markdown(f"<div class='user-nav-name'>{st.session_state.current_user['name']}</div>", unsafe_allow_html=True)
            else:
                st.markdown('<div style="font-size: 72px; text-align: center;">👤</div>', unsafe_allow_html=True)
                st.markdown(f"<div class='user-nav-name'>{st.session_state.current_user['name']}</div>", unsafe_allow_html=True)
            
            if st.button("切换账号", key="switch_account_btn", use_container_width=True):
                st.session_state.show_switch_account = True
                st.rerun()
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    # 处理切换账号
    if st.session_state.get('show_switch_account'):
        _ , center_col, _ = st.columns([1, 1.8, 1])
        with center_col:
            with st.container(border=True):
                st.write("#### 切换账号")
                switch_username = st.text_input("用户名", key="switch_username")
                switch_password = st.text_input("密码", type="password", key="switch_password")
                col_sw1, col_sw2, col_sw3 = st.columns(3)
                with col_sw1:
                    if st.button("登录", key="switch_login_btn", use_container_width=True):
                        if switch_username and switch_password:
                            conn = get_db_connection()
                            result = verify_user(conn, switch_username, switch_password)
                            if result["success"]:
                                user = result["user"]
                                st.session_state.logged_in = True
                                st.session_state.current_user = user
                                st.session_state.show_switch_account = False
                                st.query_params["user"] = user['username']
                                st.rerun()
                            else:
                                st.error(result["message"])
                        else:
                            st.warning("请输入用户名和密码")
                with col_sw2:
                    if st.button("游客", key="switch_guest_btn", use_container_width=True):
                        st.session_state.logged_in = True
                        st.session_state.current_user = {'username': 'guest', 'name': '游客'}
                        st.session_state.show_switch_account = False
                        st.query_params["user"] = "guest"
                        st.rerun()
                with col_sw3:
                    if st.button("取消", key="switch_cancel_btn", use_container_width=True):
                        st.session_state.show_switch_account = False
                        st.rerun()
        return

    # 健康打卡栏
    show_health_checkin()
    
    # 主功能标签页
    tabs = st.tabs([
        "😋 今天吃什么",
        "🥗 数字冰箱",
        "📊 饮食日历",
        "⚙️ 设置"
    ])
    
    with tabs[0]:
        smart_recommendation_page()
    
    with tabs[1]:
        digital_pantry_page()
    
    with tabs[2]:
        calendar_page()
    
    with tabs[3]:
        settings_page()

# ============ 主入口 ============
if not st.session_state.logged_in:
    init_default_user()
    st.rerun()
else:
    main_app()
