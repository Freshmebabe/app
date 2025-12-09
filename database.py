import sqlite3
import json
from datetime import datetime
import os

DB_PATH = "honeyeat.db"

def get_connection():
    """获取数据库连接"""
    # check_same_thread=False 对于 Streamlit 的多线程环境是必要的
    conn = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    conn.row_factory = sqlite3.Row
    return conn

def initialize_and_seed_database(conn):
    """
    统一的数据库初始化函数。
    如果数据库文件不存在，则创建所有表并填充所有默认数据。
    这个函数会处理所有初始化逻辑，确保操作的原子性。
    """
    cursor = conn.cursor()
    
    # 用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            preferences TEXT DEFAULT '{}',
            avatar BLOB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 检查并添加 avatar 列（用于兼容旧数据库）
    cursor.execute("PRAGMA table_info(users)")
    columns = [info[1] for info in cursor.fetchall()]
    if 'avatar' not in columns:
        cursor.execute("ALTER TABLE users ADD COLUMN avatar BLOB")
    # 兼容性修改：如果旧的 password_hash 列存在，则重命名为 password
    if 'password_hash' in columns and 'password' not in columns:
        # 在重命名之前，需要禁用外键约束
        cursor.execute("PRAGMA foreign_keys=off")
        cursor.execute("ALTER TABLE users RENAME COLUMN password_hash TO password")
    
    # 食物全库
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            category TEXT NOT NULL,
            cost_level TEXT DEFAULT '$$',
            health_tag TEXT,
            recipe_link TEXT,
            active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 冰箱/库存
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pantry (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            food_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            status TEXT DEFAULT '充足',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(username)
        )
    """)
    
    # 饮食历史
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eat_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            meal_time TEXT,
            food_id INTEGER,
            food_name TEXT,
            user_id TEXT,
            rating INTEGER,
            mode TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (food_id) REFERENCES foods(id),
            FOREIGN KEY (user_id) REFERENCES users(username)
        )
    """)
    
    # 健康打卡
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_checkin (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date DATE NOT NULL,
            user_id TEXT,
            water_checked INTEGER DEFAULT 0,
            fruit_checked INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(username)
        )
    """)
    
    # 待买清单
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shopping_list (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            user_id TEXT NOT NULL,
            quantity INTEGER DEFAULT 1,
            category TEXT,
            is_bought INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(username)
        )
    """)
    
    # 用户自定义菜谱表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_recipes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            recipe_name TEXT NOT NULL,
            ingredients TEXT NOT NULL, -- JSON array of strings
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(username),
            UNIQUE(user_id, recipe_name)
        )
    """)

    # --- 数据库迁移脚本 (用于兼容旧数据库) ---
    # 检查并为 shopping_list 表添加 user_id 列
    cursor.execute("PRAGMA table_info(shopping_list)")
    shopping_list_columns = [info[1] for info in cursor.fetchall()]
    if 'user_id' not in shopping_list_columns:
        # 添加列，并为现有数据设置一个默认值（例如 'admin'），避免 NOT NULL 约束失败
        cursor.execute("ALTER TABLE shopping_list ADD COLUMN user_id TEXT NOT NULL DEFAULT 'admin'")

    # 检查并为 pantry 表添加 user_id 列
    cursor.execute("PRAGMA table_info(pantry)")
    pantry_columns = [info[1] for info in cursor.fetchall()]
    if 'user_id' not in pantry_columns and pantry_columns: # 增加 pantry_columns 是否为空的判断
        # 添加列，并为现有数据设置一个默认值
        cursor.execute("ALTER TABLE pantry ADD COLUMN user_id TEXT NOT NULL DEFAULT 'admin'")

    # --- 步骤 2: 填充默认数据 (在同一个连接下) ---
    
    # 默认用户
    default_users = [
        ("admin", "管理员", "admin123", json.dumps({"role": "admin"})),
        ("bf", "男朋友", "bf123", json.dumps({"spicy": True, "sweet": False})),
        ("gf", "女朋友", "gf123", json.dumps({"spicy": False, "sweet": True})),
    ]
    try:
        cursor.executemany("""
            INSERT OR IGNORE INTO users (username, name, password, preferences)
            VALUES (?, ?, ?, ?) ON CONFLICT(username) DO NOTHING
        """, default_users)
    except Exception as e:
        print(f"插入默认用户数据出错: {e}")

    # 默认食物
    default_foods = [
        # 原有数据
        ("麻辣香锅", "中餐", "$$$", "Spicy", None),
        ("番茄炒蛋", "家常菜", "$", "Healthy", None),
        ("牛排", "西餐", "$$$", "CheatMeal", None),
        ("减脂沙拉", "轻食", "$$", "Healthy", None),
        ("重庆火锅", "大餐", "$$$", "CheatMeal", None),
        ("寿司", "日料", "$$", "Light", None),
        ("麦当劳", "快餐", "$", "CheatMeal", None),
        ("手抓饼", "速食", "$", "Normal", None),
        ("水饺", "速食", "$", "Normal", None),
        ("酸奶", "零食饮料", "$", "Healthy", None),

        # 中餐
        ("宫保鸡丁", "中餐", "$$", "Normal", None),
        ("鱼香肉丝", "中餐", "$$", "Normal", None),
        ("回锅肉", "中餐", "$$", "CheatMeal", None),
        ("北京烤鸭", "大餐", "$$$", "CheatMeal", None),
        ("咕咾肉", "中餐", "$$", "Sweet", None),
        ("锅包肉", "中餐", "$$", "Sweet", None),
        ("蒜泥白肉", "中餐", "$$", "Spicy", None),
        ("东坡肉", "大餐", "$$$", "CheatMeal", None),
        ("梅菜扣肉", "家常菜", "$$", "CheatMeal", None),
        ("葱爆羊肉", "中餐", "$$", "Normal", None),

        # 家常菜
        ("青椒肉丝", "家常菜", "$", "Normal", None),
        ("可乐鸡翅", "家常菜", "$", "Sweet", None),
        ("红烧排骨", "家常菜", "$$", "CheatMeal", None),
        ("蒜蓉西兰花", "家常菜", "$", "Healthy", None),
        ("蚂蚁上树", "家常菜", "$$", "Spicy", None),
        ("麻婆豆腐", "家常菜", "$", "Spicy", None),
        ("农家小炒肉", "家常菜", "$$", "Spicy", None),
        ("拍黄瓜", "家常菜", "$", "Healthy", None),
        ("地三鲜", "家常菜", "$$", "CheatMeal", None),
        ("清蒸鱼", "家常菜", "$$", "Healthy", None),

        # 西餐
        ("黑椒牛排", "西餐", "$$$", "CheatMeal", None),
        ("奶油蘑菇汤", "西餐", "$$", "Normal", None),
        ("凯撒沙拉", "西餐", "$$", "Healthy", None),
        ("意大利肉酱面", "西餐", "$$", "Normal", None),
        ("夏威夷披萨", "西餐", "$$", "CheatMeal", None),
        ("烤三文鱼", "西餐", "$$$", "Healthy", None),
        ("惠灵顿牛排", "大餐", "$$$", "CheatMeal", None),
        ("西班牙海鲜饭", "西餐", "$$$", "Light", None),
        ("炸鱼薯条", "快餐", "$$", "CheatMeal", None),
        ("法式鹅肝", "大餐", "$$$", "CheatMeal", None),

        # 日料
        ("三文鱼刺身", "日料", "$$$", "Light", None),
        ("鳗鱼饭", "日料", "$$$", "CheatMeal", None),
        ("豚骨拉面", "日料", "$$", "Normal", None),
        ("天妇罗", "日料", "$$", "CheatMeal", None),
        ("章鱼烧", "小吃", "$", "Normal", None),
        ("寿喜烧", "大餐", "$$$", "Sweet", None),
        ("味噌汤", "日料", "$", "Healthy", None),
        ("日式猪排饭", "日料", "$$", "CheatMeal", None),
        ("关东煮", "小吃", "$", "Healthy", None),
        ("亲子丼", "日料", "$$", "Normal", None),

        # 快餐
        ("牛肉汉堡", "快餐", "$$", "CheatMeal", None),
        ("炸鸡桶", "快餐", "$$", "CheatMeal", None),
        ("原味薯条", "快餐", "$", "CheatMeal", None),
        ("热狗", "快餐", "$", "CheatMeal", None),
        ("墨西哥鸡肉卷", "快餐", "$$", "Normal", None),
        ("鸡米花", "快餐", "$", "CheatMeal", None),
        ("洋葱圈", "快餐", "$", "CheatMeal", None),
        ("香草奶昔", "零食饮料", "$", "Sweet", None),
        ("方便面", "速食", "$", "Normal", None),
        ("螺蛳粉", "速食", "$$", "Spicy", None),

        # 甜品
        ("提拉米苏", "甜品", "$$", "Sweet", None),
        ("芝士蛋糕", "甜品", "$$", "Sweet", None),
        ("芒果班戟", "甜品", "$$", "Sweet", None),
        ("杨枝甘露", "甜品", "$$", "Healthy", None),
        ("双皮奶", "甜品", "$", "Sweet", None),
        ("香草冰淇淋", "甜品", "$", "Sweet", None),
        ("巧克力熔岩蛋糕", "甜品", "$$", "CheatMeal", None),
        ("葡式蛋挞", "甜品", "$", "Sweet", None),
        ("草莓华夫饼", "甜品", "$$", "Sweet", None),
        ("马卡龙", "甜品", "$$$", "Sweet", None),

        # 轻食
        ("鸡胸肉沙ラ", "轻食", "$$", "Healthy", None),
        ("水果酸奶碗", "轻食", "$$", "Healthy", None),
        ("能量棒", "轻食", "$", "Healthy", None),
        ("全麦火腿三明治", "轻食", "$$", "Normal", None),
        ("越南春卷", "轻食", "$$", "Light", None),
        ("藜麦沙拉", "轻食", "$$", "Healthy", None),
        ("鹰嘴豆泥", "轻食", "$$", "Healthy", None),
        ("烤时蔬", "轻食", "$$", "Healthy", None),
        ("燕麦粥", "早餐", "$", "Healthy", None),

        # 烧烤
        ("烤羊肉串", "烧烤", "$$", "Spicy", None),
        ("烤五花肉", "烧烤", "$$", "CheatMeal", None),
        ("烤鸡翅", "烧烤", "$$", "Normal", None),
        ("烤茄子", "烧烤", "$", "Spicy", None),
        ("烤韭菜", "烧烤", "$", "Normal", None),
        ("烤生蚝", "烧烤", "$$$", "CheatMeal", None),
        ("烤面筋", "烧烤", "$", "Spicy", None),
        ("烤鱿鱼", "烧烤", "$$", "Spicy", None),
        ("烤玉米", "烧烤", "$", "Healthy", None),
        ("烤土豆片", "烧烤", "$", "Normal", None),

        # 零食饮料
        ("珍珠奶茶", "零食饮料", "$", "Sweet", None),
        ("柠檬茶", "零食饮料", "$", "Healthy", None),
        ("薯片", "零食饮料", "$", "CheatMeal", None),
        ("辣条", "零食饮料", "$", "Spicy", None),
        ("混合坚果", "零食饮料", "$$", "Healthy", None),
        ("美式咖啡", "零食饮料", "$$", "Normal", None),
        ("鲜榨橙汁", "零食饮料", "$$", "Healthy", None),
        ("可口可乐", "零食饮料", "$", "CheatMeal", None),
        ("电影院爆米花", "零食饮料", "$$", "Sweet", None),
        ("海苔", "零食饮料", "$", "Healthy", None),

        # 大餐
        ("海底捞火锅", "大餐", "$$$", "CheatMeal", None),
        ("羊蝎子火锅", "大餐", "$$$", "CheatMeal", None),
        ("潮汕牛肉火锅", "大餐", "$$$", "Healthy", None),
        ("烤全羊", "大餐", "$$$", "CheatMeal", None),
        ("佛跳墙", "大餐", "$$$", "CheatMeal", None),
        ("广式早茶", "大餐", "$$", "Normal", None),
        ("小龙虾", "大餐", "$$$", "Spicy", None),
        ("帝王蟹", "大餐", "$$$", "CheatMeal", None),
        ("波士顿龙虾", "大餐", "$$$", "CheatMeal", None),
        ("自助餐", "大餐", "$$$", "CheatMeal", None),
    ]
    try:
        cursor.executemany("""
            INSERT OR IGNORE INTO foods (name, category, cost_level, health_tag, recipe_link)
            VALUES (?, ?, ?, ?, ?)
        """, default_foods)
    except Exception as e:
        print(f"插入默认食物数据出错: {e}")

    # --- 步骤 3: 提交并关闭 ---
    conn.commit()

def create_user(conn, username, name, password, preferences=None):
    """创建用户"""
    cursor = conn.cursor()
    
    prefs = json.dumps(preferences or {})
    
    try:
        cursor.execute(
            "INSERT INTO users (username, name, password, preferences) VALUES (?, ?, ?, ?)",
            (username, name, password, prefs)
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False

def verify_user(conn, username, password):
    """验证用户登录"""    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
    
    user = cursor.fetchone()
    
    if user:
        return {"success": True, "user": dict(user)}
    else:
        # 检查用户名是否存在，以提供更明确的错误信息
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        if cursor.fetchone():
            return {"success": False, "message": "密码错误"}
        else:
            return {"success": False, "message": "用户名不存在"}

def get_user_preferences(conn, username):
    """获取用户偏好"""
    cursor = conn.cursor()
    
    cursor.execute("SELECT preferences FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    
    if result:
        return json.loads(result['preferences'])
    return {}
 
def update_user_preferences(conn, username, preferences):
    """更新用户偏好"""
    cursor = conn.cursor()
    
    prefs_json = json.dumps(preferences)
    cursor.execute("""
        UPDATE users SET preferences = ? WHERE username = ?
    """, (prefs_json, username))
    conn.commit() # Add commit here
def update_user_avatar(conn, username, avatar_data):
    """更新用户头像"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE users SET avatar = ? WHERE username = ?
        """, (avatar_data, username))
        conn.commit() # Add commit here
    except Exception as e:
        print(f"Error updating avatar: {e}") # Log the error

def get_user_avatar(conn, username):
    """获取用户头像"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT avatar FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        if result and result['avatar']:
            return result['avatar']
    except Exception as e:
        print(f"Error getting avatar: {e}") # Log the error
    return None

def update_password(conn, username, new_password):
    """更新用户密码"""
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET password = ? WHERE username = ?", (new_password, username))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating password for {username}: {e}")
        return False
