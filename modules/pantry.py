import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
import json
import time
import pandas as pd
from database import get_db_connection
from utils.ai_chef import ai_generate_recipe


def recommend_from_pantry():
    """根据冰箱里的食材推荐菜谱 - v2.0 智能匹配版"""
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

    user_id = st.session_state.current_user['username']
    conn_user_recipe = get_db_connection()
    cursor_user_recipe = conn_user_recipe.cursor()
    cursor_user_recipe.execute("SELECT recipe_name, ingredients FROM user_recipes WHERE user_id = %s", (user_id,))
    user_recipes = cursor_user_recipe.fetchall()

    for rec in user_recipes:
        try:
            recipe_book[rec['recipe_name']] = json.loads(rec['ingredients'])
        except json.JSONDecodeError:
            continue

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT food_name FROM pantry WHERE quantity > 0 AND user_id = %s", (user_id,))
    available_ingredients = {item['food_name'] for item in cursor.fetchall()}

    if not available_ingredients:
        return []

    scored_dishes = []
    for dish, required in recipe_book.items():
        required_set = set(required)
        have_set = available_ingredients.intersection(required_set)
        missing_set = required_set - have_set
        
        match_score = len(have_set) / len(required_set)
        
        if match_score > 0:
            scored_dishes.append({
                'name': dish,
                'score': match_score,
                'have': list(have_set),
                'missing': list(missing_set)
            })
    
    scored_dishes.sort(key=lambda x: x['score'], reverse=True)
    return scored_dishes


def digital_pantry_page():
    st.write("### 🥗 数字冰箱")
    
    pantry_tabs = st.tabs(["库存管理", "智能配餐", "待买清单"])
    
    with pantry_tabs[0]:
        st.write("#### 当前库存")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        user_id = st.session_state.current_user['username']
        cursor.execute("SELECT * FROM pantry WHERE user_id = %s ORDER BY updated_at DESC", (user_id,))
        items = cursor.fetchall()
        
        if not items:
            st.info("冰箱空空如也")
        else:
            df = pd.DataFrame(items, columns=[desc[0] for desc in cursor.description])

            col_h1, col_h2, col_h3, col_h4 = st.columns([4, 2, 3, 1])
            with col_h1:
                st.caption("🥬 食材")
            with col_h2:
                st.caption("🔢 数量")
            with col_h3:
                st.caption("🕒 更新时间")
            with col_h4:
                st.caption("⚙️")
            st.divider()

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
                    with st.popover("操作", use_container_width=True):
                        if st.button("➕ 增加", key=f"incr_pantry_{item['id']}", use_container_width=True):
                            cursor.execute("UPDATE pantry SET quantity = quantity + 1, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (item['id'],))
                            conn.commit()
                            st.rerun()
                        if st.button("➖ 减少", key=f"decr_pantry_{item['id']}", use_container_width=True):
                            new_qty = item['quantity'] - 1
                            if new_qty > 0:
                                cursor.execute("UPDATE pantry SET quantity = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (new_qty, item['id']))
                            else:
                                cursor.execute("DELETE FROM pantry WHERE id = %s", (item['id'],))
                            conn.commit()
                            st.rerun()
                        if st.button("🗑️ 删除", key=f"del_pantry_{item['id']}", use_container_width=True, type="primary"):
                            cursor.execute("DELETE FROM pantry WHERE id = %s", (item['id'],))
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
                        VALUES (%s, %s, '充足', %s)
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
                    st.warning("冰箱里的食材好像还不够做一道完整的菜哦，去库存管理看看吧！")
        
        st.divider()
        st.caption("或者，让 AI 大厨为你量身定制一道菜")
        if st.button("🤖 AI 帮我配餐", use_container_width=True, type="primary"):
            with st.spinner("AI 大厨正在思考菜谱..."):
                # 获取冰箱当前食材
                conn2 = get_db_connection()
                cursor2 = conn2.cursor()
                user_id = st.session_state.current_user['username']
                cursor2.execute("SELECT food_name FROM pantry WHERE quantity > 0 AND user_id = %s", (user_id,))
                ingredients_in_fridge = [row['food_name'] for row in cursor2.fetchall()]
                        
                if not ingredients_in_fridge:
                    st.warning("冰箱空空如也，先去库存管理添加食材吧！")
                else:
                    st.session_state.ai_pantry_ingredients = ingredients_in_fridge
                    recipe = ai_generate_recipe(ingredients_in_fridge)
                    if recipe:
                        st.session_state.ai_recipe = recipe
                        st.rerun()
        
        # 显示 AI 生成的菜谱
        if 'ai_recipe' in st.session_state and st.session_state.ai_recipe:
            recipe = st.session_state.ai_recipe
            fridge_ingredients = st.session_state.get('ai_pantry_ingredients', [])
            st.write("---")
            st.success(f"## 🤖 AI 推荐：{recipe['name']}")
                    
            st.write("### 📋 所需食材")
            needed_cols = st.columns(3)
            for i, item in enumerate(recipe.get('needed', [])):
                with needed_cols[i % 3]:
                    icon = "✅" if item in fridge_ingredients else "🛒"
                    st.write(f"{icon} {item}")
                    
            if recipe.get('missing'):
                st.warning(f"⚠️ 还缺少：{'、'.join(recipe['missing'])}")
                col_m1, col_m2 = st.columns([1, 2])
                with col_m1:
                    if st.button("🛒 加入待买清单", key="ai_add_missing", use_container_width=True):
                        conn3 = get_db_connection()
                        cursor3 = conn3.cursor()
                        user_id = st.session_state.current_user['username']
                        for m in recipe['missing']:
                            cursor3.execute("INSERT INTO shopping_list (item_name, user_id) VALUES (%s, %s)", (m, user_id))
                        conn3.commit()
                        st.toast("已加入待买清单！")
                        time.sleep(0.5)
                    
            st.write("### 👨‍🍳 烹饪步骤")
            for i, step in enumerate(recipe.get('steps', []), 1):
                st.write(f"{i}. {step}")
                    
            st.divider()
            if st.button("🔄 让 AI 再推荐一个", key="ai_retry", use_container_width=True):
                del st.session_state.ai_recipe
                st.rerun()
        
        if 'pantry_recommendations' in st.session_state and st.session_state.pantry_recommendations:
            st.write("---")
            
            if 'score' not in st.session_state.pantry_recommendations[0]:
                st.session_state.pantry_recommendations = []
                st.rerun()

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
                                cursor.execute("INSERT INTO shopping_list (item_name, user_id) VALUES (%s, %s)", (item, user_id))
                            conn.commit()
                            st.toast(f"「{missing_str}」已加入待买清单！")
                            time.sleep(0.5)

                    st.link_button("📕 去小红书找灵感", f"https://www.xiaohongshu.com/search_result/?keyword={rec['name']} 做法", use_container_width=True)
    
    with pantry_tabs[2]:
        st.write("#### 待买清单")
        
        conn = get_db_connection()
        cursor = conn.cursor()
        user_id = st.session_state.current_user['username']
        cursor.execute("SELECT * FROM shopping_list WHERE is_bought = 0 AND user_id = %s", (user_id,))
        items = cursor.fetchall()
        
        if items:
            for item in items:
                col1, col2, col3 = st.columns([3, 1, 1])
                with col1:
                    st.write(f"✅ {item['item_name']}")
                with col2:
                    st.caption(f"x{item['quantity']}")
                with col3:
                    if st.button("删除", key=f"del_shop_{item['id']}"):
                        cursor.execute("DELETE FROM shopping_list WHERE id = %s", (item['id'],))
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
                        VALUES (%s, %s)
                    """, (new_item, st.session_state.current_user['username']))
                    conn.commit()
                    st.success("已添加")
                    st.rerun()
