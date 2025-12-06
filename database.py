import sqlite3
import hashlib
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path("honeyeat.db")

def get_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """初始化数据库表结构"""
    conn = get_connection()
    cursor = conn.cursor()
    
    # 用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            preferences TEXT DEFAULT '{}',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
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
            food_name TEXT NOT NULL,
            quantity INTEGER DEFAULT 0,
            status TEXT DEFAULT '充足',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
            quantity INTEGER DEFAULT 1,
            category TEXT,
            added_by TEXT,
            is_bought INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def hash_password(password):
    """密码哈希"""
    return hashlib.sha256(password.encode()).hexdigest()

def create_user(username, name, password, preferences=None):
    """创建用户"""
    conn = get_connection()
    cursor = conn.cursor()
    
    prefs = json.dumps(preferences or {})
    pwd_hash = hash_password(password)
    
    try:
        cursor.execute("""
            INSERT INTO users (username, name, password_hash, preferences)
            VALUES (?, ?, ?, ?)
        """, (username, name, pwd_hash, prefs))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    """验证用户登录"""
    conn = get_connection()
    cursor = conn.cursor()
    
    pwd_hash = hash_password(password)
    cursor.execute("""
        SELECT * FROM users WHERE username = ? AND password_hash = ?
    """, (username, pwd_hash))
    
    user = cursor.fetchone()
    conn.close()
    return dict(user) if user else None

def get_user_preferences(username):
    """获取用户偏好"""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT preferences FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return json.loads(result['preferences'])
    return {}

def update_user_preferences(username, preferences):
    """更新用户偏好"""
    conn = get_connection()
    cursor = conn.cursor()
    
    prefs_json = json.dumps(preferences)
    cursor.execute("""
        UPDATE users SET preferences = ? WHERE username = ?
    """, (prefs_json, username))
    
    conn.commit()
    conn.close()

# 初始化数据库和默认用户
def init_default_data():
    """初始化默认数据"""
    init_database()
    
    # 创建默认用户（如果不存在）
    create_user("admin", "管理员", "admin123", {"role": "admin"})
    create_user("bf", "男朋友", "bf123", {"spicy": True, "sweet": False})
    create_user("gf", "女朋友", "gf123", {"spicy": False, "sweet": True})
    
    # 插入默认食物数据
    conn = get_connection()
    cursor = conn.cursor()
    
    default_foods = [
        ("麻辣香锅", "中餐", "$$$", "Spicy", None),
        ("番茄炒蛋", "家常菜", "$", "Healthy", None),
        ("牛排", "西餐", "$$$", "CheatMeal", None),
        ("减脂沙拉", "轻食", "$$", "Healthy", None),
        ("重庆火锅", "大餐", "$$$", "CheatMeal", None),
        ("寿司", "日料", "$$", "Light", None),
        ("麦当劳", "快餐", "$", "CheatMeal", None),
        ("手抓饼", "速食", "$", None, None),
        ("水饺", "速食", "$", None, None),
        ("酸奶", "零食饮料", "$", "Healthy", None),
    ]
    
    try:
        cursor.executemany("""
            INSERT OR IGNORE INTO foods (name, category, cost_level, health_tag, recipe_link)
            VALUES (?, ?, ?, ?, ?)
        """, default_foods)
        conn.commit()
    except Exception as e:
        print(f"插入默认数据出错: {e}")
    finally:
        conn.close()
