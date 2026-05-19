import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import json
import time
from database import get_db_connection, get_user_preferences, update_user_preferences, get_user_avatar, update_user_avatar, update_password


def settings_page():
    st.write("### ⚙️ 设置")
    
    user_id = st.session_state.current_user['username']
    conn = get_db_connection()
    cursor = conn.cursor()
    prefs = get_user_preferences(conn, user_id)
    
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

    # ==== 我的菜谱 ====
    with tabs[1]:
        st.write("#### 📖 我的菜谱")
        st.caption("在这里添加你的私房菜谱，让「智能配餐」更懂你！")

        cursor.execute("SELECT id, recipe_name, ingredients FROM user_recipes WHERE user_id = %s", (user_id,))
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
                        cursor.execute("DELETE FROM user_recipes WHERE id = %s", (recipe['id'],))
                        conn.commit()
                        st.rerun()
                st.divider()
        else:
            st.info("你还没有添加任何私房菜谱。")

        st.write("##### 添加新菜谱")
        new_recipe_name = st.text_input("菜谱名称", key="new_recipe_name")
        new_recipe_ingredients = st.text_input("所需食材（用逗号隔开）", key="new_recipe_ingredients", placeholder="例如: 猪肉, 青椒, 蒜")

        if st.button("💾 保存菜谱", key="add_my_recipe", use_container_width=True):
            if new_recipe_name and new_recipe_ingredients:
                ingredients_list = [item.strip() for item in new_recipe_ingredients.split(',')]
                ingredients_json = json.dumps(ingredients_list)
                try:
                    cursor.execute(
                        "INSERT INTO user_recipes (user_id, recipe_name, ingredients) VALUES (%s, %s, %s)",
                        (user_id, new_recipe_name, ingredients_json)
                    )
                    conn.commit()
                    st.success(f"菜谱「{new_recipe_name}」已保存！")
                    st.rerun()
                except Exception as e:
                    st.error("保存失败，菜谱名称可能已存在。")

    # ==== 食物管理 ====
    with tabs[2]:
        st.write("#### 🍽️ 食物管理")
        
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
        
        col_s4, col_s5 = st.columns([2, 1])
        with col_s4:
            sort_by = st.selectbox(
                "🔄 排序方式",
                ["最新添加", "名称A-Z", "名称Z-A", "价格从低到高", "价格从高到低"]
            )
        with col_s5:
            limit = st.selectbox("📊 显示数量", [10, 20, 50, 100], index=1)
        
        query = "SELECT * FROM foods WHERE 1=1"
        params = []
        
        if search_term:
            query += " AND name LIKE %s"
            params.append(f"%{search_term}%")
        
        if filter_category != "全部":
            query += " AND category = %s"
            params.append(filter_category)
        
        if filter_status == "已启用":
            query += " AND active = 1"
        elif filter_status == "已禁用":
            query += " AND active = 0"
        
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
                            cursor.execute("UPDATE foods SET active = %s WHERE id = %s", (new_status, food['id']))
                            conn.commit()
                            st.rerun()
                    
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
                                        SET name = %s, category = %s, cost_level = %s, health_tag = %s
                                        WHERE id = %s
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
                                    cursor.execute("DELETE FROM foods WHERE id = %s", (food['id'],))
                                    conn.commit()
                                    st.session_state[f"editing_{food['id']}"] = False
                                    st.warning("⚠️ 已删除")
                                    time.sleep(0.5)
                                    st.rerun()
                    
                    st.divider()
        else:
            st.info("🔍 没有找到符合条件的食物")
        
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
                    VALUES (%s, %s, %s, %s, 1)
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
            avatar = get_user_avatar(conn, user_id)
            if avatar:
                st.image(avatar, caption="当前头像", width=128)
            else:
                st.caption("你还没有设置头像")

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
            
            cursor.execute("SELECT * FROM users WHERE username = %s", (user_id,))
            user_row = cursor.fetchone()
            
            if user_row:
                user_info = dict(user_row)
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
