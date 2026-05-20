import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import json
import time
from datetime import datetime
from openai import OpenAI
from database import get_db_connection, get_user_preferences
from utils.ai_chef import ai_generate_recipe


def _get_ai_client():
    """获取 AI 客户端"""
    api_key = st.secrets.get("DASHSCOPE_API_KEY", "")
    if not api_key:
        return None
    return OpenAI(
        api_key=api_key,
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1"
    )


def _ai_recommend_food(user_id: str) -> dict | None:
    """AI 根据用户偏好和历史推荐一道菜"""
    client = _get_ai_client()
    if not client:
        st.error("未配置 DASHSCOPE_API_KEY")
        return None

    conn = get_db_connection()
    cursor = conn.cursor()
    prefs = get_user_preferences(conn, user_id)

    # 当前时间段
    current_hour = datetime.now().hour
    if 5 <= current_hour < 10:
        time_label = "早餐时间"
    elif 10 <= current_hour < 14:
        time_label = "午餐时间"
    elif 14 <= current_hour < 17:
        time_label = "下午茶"
    elif 17 <= current_hour < 21:
        time_label = "晚餐时间"
    else:
        time_label = "夜宵时间"

    # 最近吃过的
    cursor.execute("SELECT food_name FROM eat_history WHERE user_id = %s ORDER BY date DESC LIMIT 5", (user_id,))
    recent_foods = [r['food_name'] for r in cursor.fetchall()]

    # 用户黑名单、偏好
    blacklist = prefs.get('blacklist', [])
    avoid_categories = prefs.get('avoid_category', [])
    favorite_categories = prefs.get('favorite_category', [])
    health_mode = prefs.get('health_mode', '普通模式')
    daily_calorie = prefs.get('daily_calorie_goal', 2000)
    vegetarian = prefs.get('vegetarian', False)
    spicy_lover = prefs.get('spicy', False)

    system_prompt = """你是一位懂用户口味的私人美食推荐师兼美食点评家。根据用户的口味偏好、近期饮食记录、当前时间段，推荐一道菜并给出详细的美食点评式介绍。

你必须以 JSON 格式回复，不要包含其他内容：
{
  "name": "有食欲的菜名（如「咕噜冒泡的番茄牛腩煲」）",
  "reason": "推荐理由（1-2句话，亲切口吻）",
  "description": "生动的风味口感描述（如「软烂的牛腩裹着酸甜番茄汁，一口下去满满的幸福感」）",
  "rating": 4.5,
  "tags": ["下饭神器", "本周热门"],
  "price_range": "$$",
  "flavor_profile": "酸甜浓郁",
  "difficulty": "简单"
}"""

    user_prompt = f"""现在是{time_label}，请推荐一道菜。

用户口味设置：
- 喜欢辣：{'是' if spicy_lover else '否'}
- 素食：{'是' if vegetarian else '否'}
- 健康模式：{health_mode}
- 喜欢的菜系：{', '.join(favorite_categories) if favorite_categories else '无特别偏好'}
- 避免的菜系：{', '.join(avoid_categories) if avoid_categories else '无'}
- 黑名单：{', '.join(blacklist) if blacklist else '无'}
- 每日热量目标：{daily_calorie}千卡

最近吃过的菜：{', '.join(recent_foods) if recent_foods else '暂无记录'}

请推荐一道适合现在吃的菜。"""

    try:
        response = client.chat.completions.create(
            model="qwen-plus",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.9,
            max_tokens=300
        )
        content = response.choices[0].message.content.strip()
        if content.startswith("```"):
            content = content.split("\n", 1)[-1]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
        return _ensure_recipe_fields(json.loads(content))
    except Exception as e:
        st.error(f"AI 推荐出错：{e}")
        return None


def _ensure_recipe_fields(recipe: dict) -> dict:
    """确保 AI 返回的菜谱包含所有必要字段，缺失的用默认值填充"""
    recipe.setdefault("name", "未知菜品")
    recipe.setdefault("reason", "这个应该不错！")
    recipe.setdefault("description", "")
    recipe.setdefault("rating", 4.0)
    recipe.setdefault("tags", [])
    recipe.setdefault("price_range", "$$")
    recipe.setdefault("flavor_profile", "")
    recipe.setdefault("difficulty", "简单")
    recipe.setdefault("needed", [])
    recipe.setdefault("steps", [])
    recipe.setdefault("missing", [])
    return recipe


def _get_meal_time() -> str:
    """根据当前时间自动判断用餐类型"""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 10:
        return "早餐"
    elif 10 <= current_hour < 14:
        return "午餐"
    elif 14 <= current_hour < 17:
        return "下午茶"
    elif 17 <= current_hour < 21:
        return "晚餐"
    else:
        return "夜宵"


def _save_food_and_record(food_name: str, category: str = "AI推荐", health_tag: str = "Normal", meal_time: str = None):
    """保存菜品到数据库并记录到饮食历史，同时清理旧的种子数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    user_id = st.session_state.current_user['username']

    # 确保 is_custom 列存在（兼容旧数据库）
    try:
        cursor.execute("""
            DELETE FROM foods WHERE is_custom = FALSE 
            AND id NOT IN (SELECT DISTINCT food_id FROM eat_history WHERE food_id IS NOT NULL)
        """)
    except Exception:
        conn.rollback()
        cursor.execute("ALTER TABLE foods ADD COLUMN IF NOT EXISTS is_custom BOOLEAN DEFAULT FALSE")
        conn.commit()
        cursor.execute("""
            DELETE FROM foods WHERE is_custom = FALSE
            AND id NOT IN (SELECT DISTINCT food_id FROM eat_history WHERE food_id IS NOT NULL)
        """)

    # 添加或更新当前菜品
    cursor.execute("SELECT id FROM foods WHERE name = %s", (food_name,))
    existing = cursor.fetchone()
    if existing:
        food_id = existing['id']
        cursor.execute("UPDATE foods SET is_custom = TRUE WHERE id = %s", (food_id,))
    else:
        cursor.execute("""
            INSERT INTO foods (name, category, cost_level, health_tag, is_custom, active)
            VALUES (%s, %s, '$$', %s, TRUE, 1)
            RETURNING id
        """, (food_name, category, health_tag))
        food_id = cursor.fetchone()['id']

    # 记录到饮食历史（使用传入的餐次或当前时间自动判断）
    if meal_time is None:
        meal_time = _get_meal_time()

    cursor.execute("""
        INSERT INTO eat_history (date, meal_time, food_id, food_name, user_id, rating, mode)
        VALUES (%s, %s, %s, %s, %s, %s, 'ai')
    """, (datetime.now().date().isoformat(), meal_time, food_id, food_name, user_id, 5))
    conn.commit()
    return meal_time


def smart_recommendation_page():
    st.write("### 今天吃什么")
    st.caption("让 AI 帮你决定！")

    # ---- 模式1: 随便推荐 ----
    if st.button("🎲 随便推荐", use_container_width=True, type="primary"):
        with st.spinner("AI 正在为你挑选..."):
            user_id = st.session_state.current_user['username']
            result = _ai_recommend_food(user_id)
            if result:
                st.session_state.ai_recommend = result
                st.session_state.ai_recommend_meal = _get_meal_time()  # 记录推荐时的用餐时间
                st.rerun()

    # ---- 模式2: 根据冰箱推荐 ----
    st.write("")
    if st.button("🧊 根据冰箱推荐", use_container_width=True):
        with st.spinner("正在查看冰箱..."):
            conn = get_db_connection()
            cursor = conn.cursor()
            user_id = st.session_state.current_user['username']
            cursor.execute("SELECT food_name FROM pantry WHERE quantity > 0 AND user_id = %s", (user_id,))
            ingredients = [r['food_name'] for r in cursor.fetchall()]
            if not ingredients:
                st.warning("冰箱空空如也，先去数字冰箱添加食材吧！")
            else:
                recipe = ai_generate_recipe(ingredients)
                if recipe:
                    st.session_state.fridge_recipe = recipe
                    st.session_state.fridge_recipe_meal = _get_meal_time()  # 记录推荐时的用餐时间
                    st.rerun()

    # ---- 展示随便推荐结果 ----
    if 'ai_recommend' in st.session_state and st.session_state.ai_recommend:
        result = st.session_state.ai_recommend
        
        # 星级评分
        rating = result.get('rating', 4.0)
        stars = "★" * int(rating) + ("☆" if rating % 1 >= 0.5 else "")
        
        # 标签
        tags = result.get('tags', [])
        tag_html = " ".join([f'<span class="ai-tag">{t}</span>' for t in tags])
        
        # 价格
        price = result.get('price_range', '$$')
        difficulty = result.get('difficulty', '简单')
        flavor = result.get('flavor_profile', '')
        
        st.divider()
        
        # 菜名卡片
        st.markdown(f"""
        <div class="ai-result-card">
            <div class="ai-dish-name">🍽️ {result['name']}</div>
            <div class="ai-rating">{stars} <span style="color:#888;">{rating}/5</span></div>
            {tag_html}
            <div class="ai-meta">
                <span>💰 {price}</span>
                <span>🔥 难度：{difficulty}</span>
                {f'<span>👅 {flavor}</span>' if flavor else ''}
            </div>
            <div class="ai-desc">"{result.get('description', result.get('reason', ''))}"</div>
        </div>
        """, unsafe_allow_html=True)
        
        # 推荐理由
        if result.get('reason'):
            st.success(f"💡 {result['reason']}")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ 就吃这个！", use_container_width=True, type="primary", key="confirm_ai"):
                meal_time = _save_food_and_record(result['name'], meal_time=st.session_state.get('ai_recommend_meal'))
                st.toast(f"已记录到{meal_time}！", icon="✅")
                del st.session_state.ai_recommend
                st.session_state.ai_recommend_meal = None
                time.sleep(1)
                st.rerun()
        with col_b:
            if st.button("🔄 再换一个", use_container_width=True, key="retry_ai"):
                with st.spinner("AI 正在重新挑選..."):
                    user_id = st.session_state.current_user['username']
                    new_result = _ai_recommend_food(user_id)
                    if new_result:
                        st.session_state.ai_recommend = new_result
                        st.session_state.ai_recommend_meal = _get_meal_time()
                st.rerun()

    # ---- 展示冰箱推荐结果 ----
    if 'fridge_recipe' in st.session_state and st.session_state.fridge_recipe:
        recipe = st.session_state.fridge_recipe
        recipe = _ensure_recipe_fields(recipe)
        
        rating = recipe.get('rating', 4.0)
        stars = "★" * int(rating) + ("☆" if rating % 1 >= 0.5 else "")
        tags = recipe.get('tags', [])
        tag_html = " ".join([f'<span class="ai-tag">{t}</span>' for t in tags])
        price = recipe.get('price_range', '$$')
        difficulty = recipe.get('difficulty', '简单')
        flavor = recipe.get('flavor_profile', '')
        
        st.divider()
        st.markdown(f"""
        <div class="ai-result-card">
            <div class="ai-dish-name">🧊 {recipe['name']}</div>
            <div class="ai-rating">{stars} <span style="color:#888;">{rating}/5</span></div>
            {tag_html}
            <div class="ai-meta">
                <span>💰 {price}</span>
                <span>🔥 难度：{difficulty}</span>
                {f'<span>👅 {flavor}</span>' if flavor else ''}
            </div>
            {f'<div class="ai-desc">"{recipe["description"]}"</div>' if recipe.get('description') else ''}
        </div>
        """, unsafe_allow_html=True)

        st.write("### 所需食材")
        needed_cols = st.columns(3)
        for i, item in enumerate(recipe.get('needed', [])):
            with needed_cols[i % 3]:
                st.write(f"- {item}")

        if recipe.get('missing'):
            st.warning(f"还缺少：{'、'.join(recipe['missing'])}")

        st.write("### 烹饪步骤")
        for i, step in enumerate(recipe.get('steps', []), 1):
            st.write(f"{i}. {step}")

        col_a, col_b = st.columns(2)
        with col_a:
            if st.button("✅ 就吃这个！", use_container_width=True, type="primary", key="confirm_fridge"):
                meal_time = _save_food_and_record(recipe['name'], category="家常菜", meal_time=st.session_state.get('fridge_recipe_meal'))
                st.toast(f"已记录到{meal_time}！", icon="✅")
                del st.session_state.fridge_recipe
                st.session_state.fridge_recipe_meal = None
                time.sleep(1)
                st.rerun()
        with col_b:
            if st.button("🔄 再换一个", use_container_width=True, key="retry_fridge"):
                with st.spinner("正在重新查看冰箱..."):
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    user_id = st.session_state.current_user['username']
                    cursor.execute("SELECT food_name FROM pantry WHERE quantity > 0 AND user_id = %s", (user_id,))
                    ingredients = [r['food_name'] for r in cursor.fetchall()]
                    recipe = ai_generate_recipe(ingredients)
                    if recipe:
                        st.session_state.fridge_recipe = recipe
                        st.session_state.fridge_recipe_meal = _get_meal_time()
                st.rerun()
