import os
import sqlite3
import time
import hashlib
from typing import Dict, Optional, Tuple, List, Any

# 数据库文件路径
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'user.db')

def get_db_connection():
    """获取数据库连接"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 使查询结果可以通过列名访问
    return conn

def hash_password(password: str) -> str:
    """使用SHA-256哈希密码"""
    return hashlib.sha256(password.encode('utf-8')).hexdigest()

def verify_user(account: str, password: str) -> Optional[Dict[str, Any]]:
    """验证用户凭据并返回用户数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 哈希输入的密码进行比较
    hashed_password = hash_password(password)
    
    cursor.execute(
        'SELECT id, username, account, email, points FROM users WHERE account = ? AND password = ?', 
        (account, hashed_password)
    )
    user = cursor.fetchone()
    
    if user:
        # 更新最后登录时间
        cursor.execute(
            'UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?', 
            (user['id'],)
        )
        conn.commit()
        
        # 转换为字典
        user_dict = dict(user)
    else:
        user_dict = None
    
    conn.close()
    return user_dict

def create_session(user_id: int, expiry_seconds: int = 86400) -> str:
    """创建用户会话并返回会话令牌"""
    import secrets
    
    # 生成随机令牌
    token = secrets.token_hex(32)
    expires_at = time.time() + expiry_seconds
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 存储会话信息
    cursor.execute(
        'INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)',
        (token, user_id, expires_at)
    )
    conn.commit()
    conn.close()
    
    return token

def validate_session(token: str) -> Optional[Dict[str, Any]]:
    """验证会话并返回用户数据"""
    if not token:
        return None
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 获取会话信息和关联的用户数据
    cursor.execute('''
        SELECT 
            s.token, s.user_id, s.expires_at,
            u.username, u.account, u.email, u.points
        FROM sessions s
        JOIN users u ON s.user_id = u.id
        WHERE s.token = ?
    ''', (token,))
    
    result = cursor.fetchone()
    
    if not result:
        conn.close()
        return None
    
    # 检查会话是否过期
    if result['expires_at'] < time.time():
        # 清理过期会话
        cursor.execute('DELETE FROM sessions WHERE token = ?', (token,))
        conn.commit()
        conn.close()
        return None
    
    # 会话有效，返回用户数据
    user_data = {
        'user_id': result['user_id'],
        'username': result['username'],
        'account': result['account'],
        'email': result['email'],
        'points': result['points'],
        'session_token': result['token'],
        'expires_at': result['expires_at']
    }
    
    conn.close()
    return user_data

def delete_session(token: str) -> bool:
    """删除会话"""
    if not token:
        return False
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM sessions WHERE token = ?', (token,))
    deleted = cursor.rowcount > 0
    
    conn.commit()
    conn.close()
    
    return deleted

def get_all_users() -> List[Dict[str, Any]]:
    """获取所有用户数据"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT id, username, account, email, points, created_at, last_login FROM users')
    users = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    return users

def add_user(username: str, account: str, password: str, email: str = "", points: int = 0) -> Optional[int]:
    """添加新用户并返回用户ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        hashed_password = hash_password(password)
        cursor.execute('''
            INSERT INTO users (username, account, password, email, points)
            VALUES (?, ?, ?, ?, ?)
        ''', (username, account, hashed_password, email, points))
        
        user_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return user_id
    except sqlite3.IntegrityError:
        # 用户名或账号已存在
        conn.close()
        return None

def update_user_points(user_id: int, points_delta: int) -> bool:
    """更新用户积分"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            'UPDATE users SET points = points + ? WHERE id = ?',
            (points_delta, user_id)
        )
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        return success
    except:
        conn.close()
        return False

def clean_expired_sessions():
    """清理所有过期会话"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('DELETE FROM sessions WHERE expires_at < ?', (time.time(),))
    deleted_count = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    return deleted_count 