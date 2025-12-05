import streamlit as st
import random
import time
from datetime import datetime
from collections import Counter

# 页面配置
st.set_page_config(
    page_title="亲爱的，今天吃什么？💕",
    page_icon="🍜",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自定义CSS样式
st.markdown("""
<style>
    body {font-family: -apple-system, BlinkMacSystemFont, \"Segoe UI\", Roboto, \"Helvetica Neue\", Arial;}
    .main-header {
        font-size: 3rem;
        color: #FF5C8D;
        text-align: center;
        font-weight: 800;
        margin: 1rem 0 2rem 0;
        letter-spacing: 1px;
    }
    .food-card {
        background: linear-gradient(135deg, #FFE9EF 0%, #FFF5FA 100%);
        padding: 1.25rem;
        border-radius: 18px;
        box-shadow: 0 10px 25px rgba(255,92,141,0.15);
        margin: 0.5rem 0 1rem;
        border: 1px solid rgba(255,92,141,0.2);
    }
    .result-text {
        font-size: 2.2rem;
        color: #E91E63;
        text-align: center;
        font-weight: 800;
        animation: bounce 0.9s ease;
    }
    @keyframes bounce {
        0%, 20%, 50%, 80%, 100% {transform: translateY(0);}
        40% {transform: translateY(-26px);}
        60% {transform: translateY(-12px);}
    }
    .stButton>button {
        background: linear-gradient(135deg, #FF5C8D 0%, #FF1493 100%);
        color: white;
        font-size: 1rem;
        padding: 0.75rem 1rem;
        border-radius: 14px;
        border: none;
        font-weight: 700;
        width: 100%;
    }
    .stButton>button:hover {
        filter: brightness(1.05);
        transform: translateY(-1px);
    }
    .badge {
        display:inline-block;
        padding: 0.25rem 0.6rem;
        border-radius: 999px;
        background:#FFD1DC;
        color:#8A004F;
        margin: 0.25rem 0.5rem 0.25rem 0;
        font-size: 0.9rem;
    }
    @media (max-width: 768px) {
        .main-header { font-size: 2rem; }
        .result-text { font-size: 1.8rem; }
        .food-card { padding: 1rem; border-radius: 14px; }
        .stButton>button { font-size: 1rem; padding: 0.6rem 0.8rem; }
    }
</style>
""", unsafe_allow_html=True)

# 初始化 session state
if 'history' not in st.session_state:
    st.session_state.history = []
if 'preferences' not in st.session_state:
    st.session_state.preferences = {
        'liked': [],
        'disliked': []
    }
if 'result' not in st.session_state:
    st.session_state.result = None
# 自定义临时菜库（本次会话有效）
if 'custom_foods' not in st.session_state:
    st.session_state.custom_foods = {}
# 手机风格界面状态
if 'orders' not in st.session_state:
    st.session_state.orders = []
if 'mobile_active_cat' not in st.session_state:
    st.session_state.mobile_active_cat = '菜品'
if 'shopping_checked' not in st.session_state:
    st.session_state.shopping_checked = {}

# 美食数据库
FOOD_DATABASE = {
    "中餐": {
        "川菜": ["麻辣香锅", "水煮鱼", "回锅肉", "宫保鸡丁", "毛血旺", "口水鸡"],
        "粤菜": ["白切鸡", "烧鹅", "虾饺", "肠粉", "煲仔饭", "烧腊"],
        "湘菜": ["剁椒鱼头", "小炒肉", "臭豆腐", "口味虾", "毛氏红烧肉"],
        "家常菜": ["番茄炒蛋", "青椒肉丝", "红烧排骨", "糖醋里脊", "鱼香肉丝", "麻婆豆腐"],
    },
    "西餐": {
        "意式": ["意大利面", "披萨", "千层面", "意式烩饭", "提拉米苏"],
        "美式": ["汉堡", "炸鸡", "牛排", "热狗", "薯条"],
        "法式": ["法式焗蜗牛", "鹅肝", "牛排", "可丽饼", "马卡龙"],
    },
    "日韩料理": {
        "日式": ["寿司", "拉面", "天妇罗", "乌冬面", "章鱼小丸子", "日式咖喱"],
        "韩式": ["石锅拌饭", "韩式烤肉", "部队锅", "炸鸡", "泡菜锅", "冷面"],
    },
    "快餐小吃": {
        "面食": ["牛肉面", "炸酱面", "刀削面", "凉皮", "热干面", "担担面"],
        "米饭类": ["盖浇饭", "炒饭", "煲仔饭", "卤肉饭", "盖码饭"],
        "其他": ["火锅", "烧烤", "麻辣烫", "冒菜", "煎饼果子", "肉夹馍", "饺子"],
    },
    "甜品饮品": {
        "甜品": ["冰淇淋", "奶茶", "蛋糕", "布丁", "双皮奶", "龟苓膏"],
    }
}

# 合并内置菜库与自定义菜库
def merge_food_db():
    import copy
    db = copy.deepcopy(FOOD_DATABASE)
    custom = st.session_state.get('custom_foods', {})
    for cat, subcats in custom.items():
        if cat not in db:
            db[cat] = {}
        for subcat, items in subcats.items():
            if subcat not in db[cat]:
                db[cat][subcat] = []
            db[cat][subcat].extend([i for i in items if i not in db[cat][subcat]])
    return db

# 获取所有美食列表（包含自定义）
def get_all_foods():
    foods = []
    db = merge_food_db()
    for category in db.values():
        for subcategory in category.values():
            foods.extend(subcategory)
    return foods

# 智能推荐算法
def smart_recommend(preferences):
    all_foods = get_all_foods()
    # 过滤掉不喜欢的食物
    available_foods = [f for f in all_foods if f not in preferences['disliked']]
    
    # 如果有喜欢的食物，增加权重
    if preferences['liked']:
        weighted_foods = preferences['liked'] * 3 + available_foods
        return random.choice(weighted_foods)
    
    return random.choice(available_foods)

# 转盘动画效果
def roulette_animation():
    placeholder = st.empty()
    all_foods = get_all_foods()
    
    for i in range(20):
        food = random.choice(all_foods)
        placeholder.markdown(f'<div class="result-text">🎰 {food} 🎰</div>', unsafe_allow_html=True)
        time.sleep(0.1)
    
    final_food = smart_recommend(st.session_state.preferences)
    placeholder.markdown(f'<div class="result-text">✨ {final_food} ✨</div>', unsafe_allow_html=True)
    return final_food

# 主标题
st.markdown('<h1 class="main-header">💕 亲爱的，今天吃什么？ 🍽️</h1>', unsafe_allow_html=True)

# 侧边栏 - 个性化设置
with st.sidebar:
    st.header("💖 个性化设置")
    
    st.subheader("😋 你喜欢的美食")
    liked_input = st.text_input("添加喜欢的食物", key="liked_input")
    if st.button("➕ 添加到喜欢", key="add_liked"):
        if liked_input and liked_input not in st.session_state.preferences['liked']:
            st.session_state.preferences['liked'].append(liked_input)
            st.success(f"已添加：{liked_input}")
    
    if st.session_state.preferences['liked']:
        st.write("已收藏：")
        for food in st.session_state.preferences['liked']:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"• {food}")
            with col2:
                if st.button("❌", key=f"remove_liked_{food}"):
                    st.session_state.preferences['liked'].remove(food)
                    st.rerun()
    
    st.divider()
    
    st.subheader("😭 不想吃的")
    disliked_input = st.text_input("添加不想吃的", key="disliked_input")
    if st.button("➕ 添加到黑名单", key="add_disliked"):
        if disliked_input and disliked_input not in st.session_state.preferences['disliked']:
            st.session_state.preferences['disliked'].append(disliked_input)
            st.warning(f"已拉黑：{disliked_input}")
    
    if st.session_state.preferences['disliked']:
        st.write("黑名单：")
        for food in st.session_state.preferences['disliked']:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"• {food}")
            with col2:
                if st.button("❌", key=f"remove_disliked_{food}"):
                    st.session_state.preferences['disliked'].remove(food)
                    st.rerun()
    
    st.divider()
    
    if st.session_state.history:
        st.subheader("📜 历史记录")
        for record in st.session_state.history[-5:]:
            st.caption(f"{record['time']}: {record['food']}")

# 主要内容区域
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🎲 随机推荐", "🎯 分类选择", "🎮 互动游戏", "📊 数据统计", "📖 使用教程"])

# Tab 1: 随机推荐
with tab1:
    st.markdown('<div class="food-card">', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.write("### 🤔 还在纠结吗？让我帮你决定！")
        
        if st.button("🎰 开始转盘抽选", use_container_width=True, key="roulette"):
            result = roulette_animation()
            st.session_state.result = result
            st.session_state.history.append({
                'time': datetime.now().strftime("%H:%M"),
                'food': result,
                'method': '转盘'
            })
            st.balloons()
        
        if st.button("✨ 智能推荐", use_container_width=True, key="smart"):
            result = smart_recommend(st.session_state.preferences)
            st.session_state.result = result
            st.session_state.history.append({
                'time': datetime.now().strftime("%H:%M"),
                'food': result,
                'method': '智能推荐'
            })
            st.markdown(f'<div class="result-text">🌟 {result} 🌟</div>', unsafe_allow_html=True)
            st.success("为你精心挑选！")
        
        if st.button("🎲 完全随机", use_container_width=True, key="random"):
            all_foods = get_all_foods()
            result = random.choice(all_foods)
            st.session_state.result = result
            st.session_state.history.append({
                'time': datetime.now().strftime("%H:%M"),
                'food': result,
                'method': '随机'
            })
            st.markdown(f'<div class="result-text">🎲 {result} 🎲</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if st.session_state.result:
        st.write("---")
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("❤️ 喜欢", use_container_width=True):
                if st.session_state.result not in st.session_state.preferences['liked']:
                    st.session_state.preferences['liked'].append(st.session_state.result)
                st.success("已添加到喜欢！")
        
        with col2:
            if st.button("👍 还行", use_container_width=True):
                st.info("好的，记住了！")
        
        with col3:
            if st.button("💔 不想吃", use_container_width=True):
                if st.session_state.result not in st.session_state.preferences['disliked']:
                    st.session_state.preferences['disliked'].append(st.session_state.result)
                st.warning("已加入黑名单！")
                st.session_state.result = None
                st.rerun()

# Tab 2: 分类选择
with tab2:
    st.write("### 🎯 按心情选择美食类型")
    
    db = merge_food_db()
    category = st.selectbox("选择大类", list(db.keys()))
    
    if category:
        subcategory = st.selectbox("选择小类", list(db[category].keys()))
        
        if subcategory:
            st.write(f"#### {subcategory} 可选美食：")
            foods = db[category][subcategory]
            
            # 过滤黑名单
            available_foods = [f for f in foods if f not in st.session_state.preferences['disliked']]
            
            cols = st.columns(2)
            for idx, food in enumerate(available_foods):
                with cols[idx % 2]:
                    if st.button(f"🍴 {food}", key=f"select_{food}", use_container_width=True):
                        st.session_state.result = food
                        st.session_state.history.append({
                            'time': datetime.now().strftime("%H:%M"),
                            'food': food,
                            'method': '分类选择'
                        })
                        st.success(f"就决定吃 {food} 了！")
                        st.balloons()

# Tab 3: 互动游戏
with tab3:
    st.write("### 🎮 趣味互动环节")
    
    game_mode = st.radio("选择游戏模式", ["🎰 抽签", "🎲 掷骰子", "💝 爱心猜猜猜"])
    
    if game_mode == "🎰 抽签":
        st.write("#### 抽个签看看今天的美食运势！")
        if st.button("🎰 抽签", key="lottery"):
            with st.spinner("正在抽签..."):
                time.sleep(1)
                fortunes = [
                    ("大吉", "今天适合吃大餐！", "high"),
                    ("中吉", "简单美味就好", "medium"),
                    ("小吉", "清淡饮食更健康", "low")
                ]
                fortune, msg, level = random.choice(fortunes)
                
                st.success(f"🎊 {fortune}！{msg}")
                
                if level == "high":
                    expensive_foods = ["牛排", "海鲜大餐", "日式料理", "法式大餐"]
                    result = random.choice(expensive_foods)
                elif level == "medium":
                    result = smart_recommend(st.session_state.preferences)
                else:
                    light_foods = ["沙拉", "粥", "素食", "轻食"]
                    result = random.choice(light_foods)
                
                st.markdown(f'<div class="result-text">推荐：{result}</div>', unsafe_allow_html=True)
                st.session_state.result = result
    
    elif game_mode == "🎲 掷骰子":
        st.write("#### 掷骰子决定美食类型！")
        if st.button("🎲 掷骰子", key="dice"):
            dice_result = random.randint(1, 6)
            
            # 动画效果
            placeholder = st.empty()
            for _ in range(10):
                placeholder.write(f"🎲 {random.randint(1, 6)}")
                time.sleep(0.1)
            
            placeholder.write(f"### 🎲 点数：{dice_result}")
            
            db = merge_food_db()
            categories = list(db.keys())
            selected_category = categories[dice_result % len(categories)]
            
            all_in_category = []
            for foods in db[selected_category].values():
                all_in_category.extend(foods)
            
            result = random.choice(all_in_category)
            st.success(f"今天吃 {selected_category}！")
            st.markdown(f'<div class="result-text">推荐：{result}</div>', unsafe_allow_html=True)
            st.session_state.result = result
    
    else:  # 爱心猜猜猜
        st.write("#### 💝 猜猜我想让你吃什么？")
        st.write("提示：我会想一道美食，你来猜！")
        
        if 'mystery_food' not in st.session_state:
            st.session_state.mystery_food = random.choice(get_all_foods())
            st.session_state.guesses = 0
        
        guess = st.text_input("输入你的猜测：")
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("确认猜测"):
                st.session_state.guesses += 1
                if guess == st.session_state.mystery_food:
                    st.success(f"🎉 猜对了！就是 {st.session_state.mystery_food}！")
                    st.balloons()
                    st.session_state.result = st.session_state.mystery_food
                    del st.session_state.mystery_food
                else:
                    hints = [
                        f"不对哦~ 提示：它属于某种料理",
                        f"再想想~ 已经猜了 {st.session_state.guesses} 次了",
                        "加油！你一定能猜到的！"
                    ]
                    st.warning(random.choice(hints))
        
        with col2:
            if st.button("我放弃了，告诉我吧"):
                st.info(f"答案是：{st.session_state.mystery_food}")
                st.session_state.result = st.session_state.mystery_food
                del st.session_state.mystery_food

# Tab 4: 数据统计
with tab4:
    st.write("### 📊 你的美食偏好分析")
    
    if st.session_state.history:
        records = st.session_state.history
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("总决策次数", len(records))
            st.metric("收藏美食数", len(st.session_state.preferences['liked']))
        
        with col2:
            st.metric("黑名单数量", len(st.session_state.preferences['disliked']))
            foods = [h['food'] for h in records]
            if foods:
                counts = Counter(foods)
                most_common_food = max(counts, key=counts.get)
                st.metric("最常选择", most_common_food)
        
        st.write("#### 最近的选择记录")
        st.dataframe([{k: r.get(k) for k in ['time','food','method']} for r in records], use_container_width=True)
        
        # 方法统计
        methods = [h.get('method') for h in records if h.get('method')]
        if methods:
            st.write("#### 决策方式分布")
            method_counts = Counter(methods)
            chart_data = [{'method': m, 'count': c} for m, c in method_counts.items()]
            st.vega_lite_chart(chart_data, {
                'mark': 'bar',
                'encoding': {
                    'x': {'field': 'method', 'type': 'nominal'},
                    'y': {'field': 'count', 'type': 'quantitative'}
                }
            })
    else:
        st.info("还没有历史记录哦，快去选择美食吧！")

# 📖 使用教程
with tab5:
    st.write("### 📖 添加菜品教程与临时菜库")
    st.info("说明：通过下方表单添加的菜品仅在本次会话有效，适合手机端快速添加。若需永久添加，请按教程修改 app.py 中的 FOOD_DATABASE。")

    # 初始化自定义菜库
    if 'custom_foods' not in st.session_state:
        st.session_state.custom_foods = {}

    cols = st.columns(2)
    with cols[0]:
        db = merge_food_db()
        existing_categories = list(db.keys())
        new_category_mode = st.checkbox("创建新的大类", value=False)
        category_input = st.text_input("大类名称（如：中餐/西餐）") if new_category_mode else st.selectbox("选择现有大类", existing_categories)

        if category_input:
            existing_subcategories = list(db.get(category_input, {}).keys())
            new_subcategory_mode = st.checkbox("创建新的小类", value=False)
            subcategory_input = st.text_input("小类名称（如：川菜/家常菜）") if new_subcategory_mode else st.selectbox("选择现有小类", existing_subcategories if existing_subcategories else ["（创建新小类）"]) 

            dish_name = st.text_input("菜品名称（如：宫保鸡丁）")
            if st.button("➕ 添加到临时菜库", use_container_width=True):
                if dish_name:
                    st.session_state.custom_foods.setdefault(category_input, {}).setdefault(subcategory_input, [])
                    if dish_name not in st.session_state.custom_foods[category_input][subcategory_input]:
                        st.session_state.custom_foods[category_input][subcategory_input].append(dish_name)
                        st.success(f"已添加：{category_input} - {subcategory_input} - {dish_name}")
                    else:
                        st.warning("该菜品已存在于临时菜库")
                else:
                    st.error("请输入菜品名称")

    with cols[1]:
        st.write("#### 当前临时菜库")
        if st.session_state.get('custom_foods'):
            st.json(st.session_state.custom_foods)
            if st.button("🗑️ 清空临时菜库", use_container_width=True):
                st.session_state.custom_foods = {}
                st.success("已清空临时菜库")
        else:
            st.caption("暂无临时菜品，快添加几道吧～")

    st.write("#### 永久添加教程")
    st.markdown("""在 `app.py` 中找到并编辑 `FOOD_DATABASE`，按如下结构添加：
```python
FOOD_DATABASE = {
    "中餐": {
        "川菜": ["麻辣香锅", "宫保鸡丁"],
        "家常菜": ["番茄炒蛋"]
    },
    "西餐": {
        "意式": ["披萨", "意大利面"]
    }
}
```
- 在对应大类下新增小类键（如 `"川菜"`），并把菜名加入列表即可。
- 保存后重新部署到 Streamlit Cloud。
""")

# 📱 手机风格界面（Beta）
st.markdown("""
<style>
.mobile-header {position: relative; border-radius: 18px; overflow: hidden; margin-bottom: 0.75rem;}
.mobile-header .cover {height: 140px; background-size: cover; background-position: center; filter: brightness(0.85);} 
.mobile-header .overlay {position:absolute; left:0; right:0; bottom:10px; padding:0 12px;}
.mobile-title {font-size: 1.4rem; font-weight: 800; color: #222;}
.mobile-sub {color:#FF5C8D; font-size: 0.95rem;}
.side-menu {background:#F7F8FA; border-radius: 14px; padding: 8px;}
.side-item {padding:10px; border-radius:10px; display:flex; align-items:center; gap:8px;}
.side-item.active {background:white; box-shadow: 0 6px 16px rgba(0,0,0,0.06);} 
.item-card {background:white; border-radius: 14px; padding: 10px; margin-bottom: 10px; box-shadow: 0 8px 18px rgba(0,0,0,0.06);} 
.item-name {font-size:1.05rem; font-weight:700;}
.plus-btn {background:#35C16F; color:white; border:none; padding:8px 12px; border-radius:999px; font-weight:700;}
.badge-tiny {display:inline-block; padding:2px 6px; border-radius:999px; background:#EAF9F0; color:#35C16F; font-size:0.75rem;}
.progress-wrap {position: sticky; bottom: 0; background: rgba(255,255,255,0.9); backdrop-filter: blur(6px); padding: 8px; border-radius: 12px;}
@media (max-width: 768px){ .mobile-header .cover {height: 120px;} }
</style>
""", unsafe_allow_html=True)

st.write("## 📱 手机风格界面（Beta）")

mobile_tabs = st.tabs(["🍳 厨房", "🧾 订单", "🛒 去买菜", "👤 我的"])

MOBILE_ITEMS = {
    "菜品": [
        {"name": "红烧肉", "img": "https://images.unsplash.com/photo-1551218808-94e220e084d2?w=640"},
        {"name": "西红柿炒蛋", "img": "https://images.unsplash.com/photo-1604908177073-91b830d9b09f?w=640"},
        {"name": "宫保鸡丁", "img": "https://images.unsplash.com/photo-1544025162-d76694265947?w=640"},
    ],
    "水果": [
        {"name": "苹果", "img": "https://images.unsplash.com/photo-1567306226416-28f0efdc88ce?w=640"},
        {"name": "草莓", "img": "https://images.unsplash.com/photo-1517260911015-4a6f2d2d2c6c?w=640"},
        {"name": "香蕉", "img": "https://images.unsplash.com/photo-1571772805064-2074a1f5ee45?w=640"},
    ],
    "零食": [
        {"name": "曲奇", "img": "https://images.unsplash.com/photo-1499636136210-6f4ee915583e?w=640"},
        {"name": "薯片", "img": "https://images.unsplash.com/photo-1550246140-29d56f2b1a56?w=640"},
        {"name": "坚果", "img": "https://images.unsplash.com/photo-1505577058444-a3dab90d4253?w=640"},
    ],
    "饮品": [
        {"name": "奶茶", "img": "https://images.unsplash.com/photo-1551024709-8f23befc6cf7?w=640"},
        {"name": "咖啡", "img": "https://images.unsplash.com/photo-1498804103079-a6351b050096?w=640"},
        {"name": "果汁", "img": "https://images.unsplash.com/photo-1510626176961-4b57d4fbad03?w=640"},
    ],
    "按摩": [
        {"name": "按按头", "img": "https://images.unsplash.com/photo-1544161515-4ab6ce6db874?w=640", "tag": "5 分钟"},
        {"name": "捏捏肩", "img": "https://images.unsplash.com/photo-1519826310069-d2b1b12e018b?w=640"},
        {"name": "洗洗脚", "img": "https://images.unsplash.com/photo-1544829099-20bf4f7b553e?w=640"},
        {"name": "按后背", "img": "https://images.unsplash.com/photo-1511471108750-1f9f2f9f59c3?w=640", "tag": "5 分钟"},
    ],
    "鲜花": [
        {"name": "玫瑰", "img": "https://images.unsplash.com/photo-1505577058444-a3dab90d4253?w=640"}
    ],
}

MOBILE_RECIPES = {
    "家常菜-荷塘小炒": ["荷兰豆", "胡萝卜", "木耳", "莲藕", "水淀粉", "葱末", "葱花"],
    "红烧肉的家常做法": ["五花肉", "生姜", "大葱", "八角", "香叶", "桂皮", "老抽", "生抽", "冰糖"],
}

# 厨房
with mobile_tabs[0]:
    st.markdown(
        f"""
        <div class='mobile-header'>
            <div class='cover' style='background-image:url(https://images.unsplash.com/photo-1514516884750-9c66f3c2f5b0?w=1200);'></div>
            <div class='overlay'>
                <div class='mobile-title'>厨神与吃货 🌍</div>
                <div class='mobile-sub'>全是我喜欢吃的 💗</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    colL, colR = st.columns([1, 3])
    with colL:
        st.write("### 私房菜")
        for cat in ["默认分类", "菜品", "水果", "零食", "饮品", "按摩", "鲜花", "分类管理"]:
            active = (st.session_state.mobile_active_cat == cat)
            if st.button(f"{cat}", key=f"m_cat_{cat}"):
                st.session_state.mobile_active_cat = cat
            st.markdown(f"<div class='side-item {'active' if active else ''}'>{cat}</div>", unsafe_allow_html=True)

    with colR:
        active_cat = st.session_state.mobile_active_cat
        # 顶部操作区：标题/管理/添加菜谱/搜索
        t1, t2, t3, t4 = st.columns([1, 1, 1.5, 2])
        with t1:
            st.write(f"### {active_cat}")
        with t2:
            st.button("管理", key="wx_manage")
        with t3:
            st.button("＋ 添加菜谱", key="wx_add_recipe")
        with t4:
            st.text_input("搜索", key="wx_search", placeholder="搜索")
        # 搜索过滤
        q = st.session_state.get("wx_search", "").strip()
        items = MOBILE_ITEMS.get(active_cat, [])
        if q:
            items = [it for it in items if q in it['name']]
        # 列表
        for item in items:
            r1, r2, r3 = st.columns([1, 2, 1])
            with r1:
                st.image(item["img"], use_column_width=True)
            with r2:
                st.markdown(f"<div class='item-name'>{item['name']}</div>", unsafe_allow_html=True)
                if item.get('tag'):
                    st.markdown(f"<span class='badge-tiny'>{item['tag']}</span>", unsafe_allow_html=True)
                st.caption("月销 1")
            with r3:
                if st.button("＋", key=f"add_{item['name']}"):
                    st.session_state.orders.append({
                        'time': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'items': [item['name']],
                        'images': [item['img']],
                        'status': '待下单'
                    })
                    st.success("已加入订单")
        # 底部操作条
        st.markdown("<div class='progress-wrap'></div>", unsafe_allow_html=True)
        b1, b2, b3 = st.columns([1, 2, 1])
        with b2:
            st.button("邀请好友下单", key="wx_invite")
        with b3:
            st.button("下单", key="wx_order")

# 订单
with mobile_tabs[1]:
    st.write("### 厨房订单")
    if st.session_state.orders:
        for i, od in enumerate(reversed(st.session_state.orders)):
            st.write(od['time'])
            img_cols = st.columns(min(len(od['images']), 3) or 1)
            for idx, img in enumerate(od['images'][:3]):
                with img_cols[idx % len(img_cols)]:
                    st.image(img, use_column_width=True)
            c1, c2, c3 = st.columns(3)
            with c1:
                st.button("已取消", key=f"cancel_{i}")
            with c2:
                st.button("更多", key=f"more_{i}")
            with c3:
                st.caption(f"{len(od['items'])} 个美味")
            st.divider()
    else:
        st.info("暂无订单，去厨房添加吧～")

# 去买菜
with mobile_tabs[2]:
    mode = st.radio("查看方式", ["按菜谱查看", "合并用料"], horizontal=True)
    total, done = 0, 0
    if mode == "按菜谱查看":
        for rp_name, ings in MOBILE_RECIPES.items():
            st.write(f"#### {rp_name}")
            for ing in ings:
                key = f"ing_{rp_name}_{ing}"
                total += 1
                checked = st.session_state.shopping_checked.get(key, False)
                new_val = st.checkbox(ing, key=key, value=checked)
                st.session_state.shopping_checked[key] = new_val
                if new_val:
                    done += 1
            st.write("---")
    else:
        all_ings = []
        for ings in MOBILE_RECIPES.values():
            all_ings.extend(ings)
        unique_ings = sorted(set(all_ings))
        for ing in unique_ings:
            key = f"ing_all_{ing}"
            total += 1
            checked = st.session_state.shopping_checked.get(key, False)
            new_val = st.checkbox(ing, key=key, value=checked)
            st.session_state.shopping_checked[key] = new_val
            if new_val:
                done += 1
    progress = int((done / total) * 100) if total else 0
    st.write(f"采购进度 {progress}%")
    st.progress(progress / 100.0)

# 我的
with mobile_tabs[3]:
    st.write("### 我的")
    st.metric("收藏美食数", len(st.session_state.preferences['liked']))
    st.metric("黑名单数量", len(st.session_state.preferences['disliked']))

# 底部
st.write("---")
st.markdown("""
<div style='text-align: center; color: #999; padding: 2rem;'>
    <p>💕 亲爱的，不管吃什么，和你在一起最重要 💕</p>
    <p style='font-size: 0.9rem;'>Made with ❤️ using Streamlit</p>
</div>
""", unsafe_allow_html=True)
