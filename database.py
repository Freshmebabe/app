import os
import json
from datetime import datetime
import psycopg2
import psycopg2.errors
import psycopg2.extensions
from psycopg2.extras import DictCursor
import streamlit as st


class _DictConnection(psycopg2.extensions.connection):
    """自动为所有 cursor 启用 DictCursor 的连接子类"""
    def cursor(self, *args, **kwargs):
        kwargs.setdefault('cursor_factory', DictCursor)
        return super().cursor(*args, **kwargs)


def get_connection():
    """获取PostgreSQL数据库连接（自动使用DictCursor）"""
    dbname = os.getenv('POSTGRES_DB', 'honeyeat')
    user = os.getenv('POSTGRES_USER', 'postgres')
    password = os.getenv('POSTGRES_PASSWORD', '')
    host = os.getenv('POSTGRES_HOST', 'localhost')
    port = os.getenv('POSTGRES_PORT', '5432')

    try:
        conn = psycopg2.connect(
            dbname=dbname,
            user=user,
            password=password,
            host=host,
            port=port,
            connect_timeout=10,
            connection_factory=_DictConnection
        )
    except Exception as e:
        # 判断 Secrets 是否生效（不泄露实际值）
        secrets_loaded = (host != 'localhost' and password != '')
        if not secrets_loaded:
            hint = (
                "⚠️ Secrets 未生效！请检查：\n"
                "1. Manage app → Secrets 中是否已保存配置\n"
                "2. 配置格式是否为 TOML（值要加双引号）\n"
                "3. 保存后是否点了 Reboot app"
            )
        elif 'could not translate host' in str(e).lower():
            hint = "⚠️ 无法解析主机名，请确认 POSTGRES_HOST 是否正确"
        elif 'password authentication' in str(e).lower():
            hint = "⚠️ 密码错误，请确认 POSTGRES_PASSWORD 是否正确"
        elif 'timeout' in str(e).lower() or 'could not connect' in str(e).lower():
            hint = (
                "⚠️ 连接超时/被拒绝。可能原因：\n"
                "1. 请使用 Supabase 的 Session Pooler 连接（以 pooler.supabase.com 结尾）\n"
                "2. 直连模式在某些云平台可能被防火墙拦截"
            )
        else:
            hint = f"原始错误: {e}"
        raise RuntimeError(f"❌ 数据库连接失败！\n{hint}")
    conn.autocommit = True
    return conn

@st.cache_resource
def get_db_connection():
    """
    获取并缓存数据库连接。
    幂等操作，可安全重复调用。
    """
    conn = get_connection()
    initialize_and_seed_database(conn)
    return conn

def initialize_and_seed_database(conn):
    """
    统一的数据库初始化函数。
    幂等操作，可以安全地重复运行。
    """
    cursor = conn.cursor()

    # 用户表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username VARCHAR(255) PRIMARY KEY,
            name VARCHAR(255) NOT NULL,
            password VARCHAR(255) NOT NULL,
            preferences TEXT DEFAULT '{}',
            avatar BYTEA,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 检查并添加 avatar 列（用于兼容旧数据库）
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users' AND column_name='avatar'
    """)
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE users ADD COLUMN avatar BYTEA")
    
    # 兼容性修改：如果旧的 password_hash 列存在，则重命名为 password
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='users' AND column_name='password_hash'
    """)
    if cursor.fetchone():
        cursor.execute("ALTER TABLE users RENAME COLUMN password_hash TO password")
    
    # 食物全库
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS foods (
            id SERIAL PRIMARY KEY,
            name VARCHAR(255) NOT NULL UNIQUE,
            category VARCHAR(255) NOT NULL,
            cost_level VARCHAR(10) DEFAULT '$$',
            health_tag VARCHAR(255),
            recipe_link TEXT,
            active INTEGER DEFAULT 1,
            is_custom BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 迁移：为旧数据库添加 is_custom 列
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='foods' AND column_name='is_custom'
    """)
    if not cursor.fetchone():
        cursor.execute("ALTER TABLE foods ADD COLUMN is_custom BOOLEAN DEFAULT FALSE")
    
    # 冰箱/库存
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pantry (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            food_name VARCHAR(255) NOT NULL,
            quantity INTEGER DEFAULT 0,
            status VARCHAR(50) DEFAULT '充足',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(username)
        )
    """)
    
    # 饮食历史
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS eat_history (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            meal_time VARCHAR(50),
            food_id INTEGER,
            food_name VARCHAR(255),
            user_id VARCHAR(255),
            rating INTEGER,
            mode VARCHAR(50),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (food_id) REFERENCES foods(id),
            FOREIGN KEY (user_id) REFERENCES users(username)
        )
    """)
    
    # 健康打卡
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS health_checkin (
            id SERIAL PRIMARY KEY,
            date DATE NOT NULL,
            user_id VARCHAR(255),
            water_checked INTEGER DEFAULT 0,
            fruit_checked INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(username)
        )
    """)
    
    # 待买清单
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS shopping_list (
            id SERIAL PRIMARY KEY,
            item_name VARCHAR(255) NOT NULL,
            user_id VARCHAR(255) NOT NULL,
            quantity INTEGER DEFAULT 1,
            category VARCHAR(255),
            is_bought INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(username)
        )
    """)
    
    # 用户自定义菜谱表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_recipes (
            id SERIAL PRIMARY KEY,
            user_id VARCHAR(255) NOT NULL,
            recipe_name VARCHAR(255) NOT NULL,
            ingredients TEXT NOT NULL, -- JSON array of strings
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(username),
            UNIQUE(user_id, recipe_name)
        )
    """)

    # --- 数据库迁移脚本 (用于兼容旧数据库) ---
    # 检查并为 shopping_list 表添加 user_id 列
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='shopping_list' AND column_name='user_id'
    """)
    if not cursor.fetchone():
        cursor.execute("""
            ALTER TABLE shopping_list 
            ADD COLUMN user_id VARCHAR(255) NOT NULL DEFAULT 'admin'
        """)

    # 检查并为 pantry 表添加 user_id 列
    cursor.execute("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name='pantry' AND column_name='user_id'
    """)
    if not cursor.fetchone():
        cursor.execute("""
            ALTER TABLE pantry 
            ADD COLUMN user_id VARCHAR(255) NOT NULL DEFAULT 'admin'
        """)

    conn.commit()

def create_user(conn, username, name, password, preferences=None):
    """创建用户"""
    cursor = conn.cursor()
    
    prefs = json.dumps(preferences or {})
    
    try:
        cursor.execute(
            "INSERT INTO users (username, name, password, preferences) VALUES (%s, %s, %s, %s)",
            (username, name, password, prefs)
        )
        conn.commit()
        return True
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        return False

def verify_user(conn, username, password):
    """验证用户登录"""    
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
    
    user = cursor.fetchone()
    
    if user:
        return {"success": True, "user": dict(user)}
    else:
        # 检查用户名是否存在，以提供更明确的错误信息
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        if cursor.fetchone():
            return {"success": False, "message": "密码错误"}
        else:
            return {"success": False, "message": "用户名不存在"}

def get_user_preferences(conn, username):
    """获取用户偏好"""
    cursor = conn.cursor()
    
    cursor.execute("SELECT preferences FROM users WHERE username = %s", (username,))
    result = cursor.fetchone()
    
    if result:
        return json.loads(result['preferences'])
    return {}
 
def update_user_preferences(conn, username, preferences):
    """更新用户偏好"""
    cursor = conn.cursor()
    
    prefs_json = json.dumps(preferences)
    cursor.execute("""
        UPDATE users SET preferences = %s WHERE username = %s
    """, (prefs_json, username))
    conn.commit() # Add commit here
def update_user_avatar(conn, username, avatar_data):
    """更新用户头像"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            UPDATE users SET avatar = %s WHERE username = %s
        """, (avatar_data, username))
        conn.commit() # Add commit here
    except Exception as e:
        print(f"Error updating avatar: {e}") # Log the error

def get_user_avatar(conn, username):
    """获取用户头像"""
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT avatar FROM users WHERE username = %s", (username,))
        result = cursor.fetchone()
        if result and result['avatar']:
            # BYTEA 返回 memoryview，转为 bytes 给 st.image() 使用
            avatar_data = result['avatar']
            return bytes(avatar_data) if isinstance(avatar_data, memoryview) else avatar_data
    except Exception as e:
        print(f"Error getting avatar: {e}") # Log the error
    return None

def update_password(conn, username, new_password):
    """更新用户密码"""
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE users SET password = %s WHERE username = %s", (new_password, username))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error updating password for {username}: {e}")
        return False