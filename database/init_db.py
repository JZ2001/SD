import os
import sqlite3
import hashlib
import sys

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user.db')

# 默认凭据
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "123456"

def hash_password(password):
    """使用SHA-256哈希密码"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def init_database():
    """初始化数据库和用户表"""
    # 确保目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    # 连接到数据库（如果不存在则创建）
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 创建用户表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL UNIQUE,  -- 用户名
        account TEXT NOT NULL UNIQUE,   -- 账号
        password TEXT NOT NULL,         -- 密码（哈希后）
        email TEXT,                     -- 邮箱
        points INTEGER DEFAULT 0,       -- 积分
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )
    ''')
    
    # 创建会话表
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS sessions (
        token TEXT PRIMARY KEY,
        user_id INTEGER NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        expires_at TIMESTAMP NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users (id)
    )
    ''')
    
    # 检查是否已存在默认用户
    cursor.execute('SELECT id FROM users WHERE account = ?', (DEFAULT_USERNAME,))
    default_user = cursor.fetchone()
    
    if not default_user:
        # 添加默认管理员用户
        hashed_password = hash_password(DEFAULT_PASSWORD)
        cursor.execute('''
        INSERT INTO users (username, account, password, email, points)
        VALUES (?, ?, ?, ?, ?)
        ''', ('管理员', DEFAULT_USERNAME, hashed_password, 'admin@example.com', 1000))
        print(f"已创建默认管理员账户: {DEFAULT_USERNAME}")
    
    # 提交更改并关闭连接
    conn.commit()
    conn.close()
    
    print(f"数据库初始化完成: {DB_PATH}")

if __name__ == "__main__":
    init_database() 