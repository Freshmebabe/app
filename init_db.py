import os
from database import init_default_data

DB_FILE = "honeyeat.db"

def main():
    """
    数据库初始化脚本。
    """
    if os.path.exists(DB_FILE):
        print(f"数据库文件 '{DB_FILE}' 已存在。")
        choice = input("您想重新初始化数据库吗？这将清空所有现有数据！(y/n): ").lower()
        if choice == 'y':
            print("正在删除旧数据库并重新创建...")
            os.remove(DB_FILE)
        else:
            print("操作已取消。")
            return

    print("正在初始化数据库并载入默认数据...")
    init_default_data()
    print("✅ 数据库初始化完成！")

if __name__ == "__main__":
    main()