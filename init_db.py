import os
from database import init_database, seed_default_data

DB_FILE = "honeyeat.db"

def main():
    """
    数据库初始化脚本。
    此脚本会先创建/更新表结构，然后填充默认数据。
    """
    if os.path.exists(DB_FILE):
        print(f"数据库文件 '{DB_FILE}' 已存在。")
        choice = input("您想重新初始化数据库吗？这将清空所有用户数据和食物！(y/n): ").lower()
        if choice == 'y':
            print("正在删除旧数据库并重新创建...")
            os.remove(DB_FILE)
        else:
            print("操作已取消。")
            return

    print("1/2: 正在初始化数据库表结构...")
    init_database()
    print("2/2: 正在载入默认用户和食物数据...")
    seed_default_data()
    print("✅ 数据库初始化完成！")

if __name__ == "__main__":
    main()