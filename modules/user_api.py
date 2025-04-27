from fastapi import APIRouter, Depends, HTTPException, Request, Body
import sqlite3
import json
import logging
from typing import Optional
from modules import custom_auth

# 创建API路由
router = APIRouter()

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("user_api")

# 获取数据库连接
def get_db_connection():
    conn = sqlite3.connect('database/users.db')
    conn.row_factory = sqlite3.Row
    return conn

# 获取当前用户信息
@router.get("/user/info")
async def get_user_info(request: Request):
    """获取当前登录用户的信息"""
    # 验证用户是否已登录
    session_id = request.cookies.get("session_token")
    logger.info(f"获取用户信息 - 会话ID: {session_id}")
    
    if not session_id:
        logger.warning("未找到会话令牌")
        # 尝试从其他可能的cookie名称中获取会话ID
        for cookie_name in ["session_id", "auth_token"]:
            temp_session_id = request.cookies.get(cookie_name)
            if temp_session_id:
                logger.info(f"从备用cookie {cookie_name} 中找到会话: {temp_session_id}")
                session_id = temp_session_id
                break
                
        if not session_id:
            raise HTTPException(status_code=401, detail="未登录")
    
    # 获取用户账号
    account = None
    
    # 尝试使用自定义认证模块验证会话
    try:
        from database import db_utils
        # 首先尝试验证session_token
        session_data = db_utils.validate_session(session_id)
        if session_data:
            logger.info(f"通过数据库验证会话成功: {session_data.get('username')}")
            
            # 直接返回会话中的用户信息
            return {
                "username": session_data.get("username", "未知用户"),
                "account": session_data.get("account", ""),
                "email": session_data.get("email", ""),
                "points": session_data.get("points", 0)
            }
        else:
            logger.warning("数据库会话验证失败，尝试备用验证方法")
    except Exception as e:
        logger.error(f"验证会话时出错: {str(e)}")
    
    # 如果上面的方法失败，尝试使用自定义认证模块
    try:
        account = custom_auth.verify_session(session_id)
        logger.info(f"通过custom_auth验证会话: {account}")
    except Exception as e:
        logger.error(f"通过custom_auth验证会话时出错: {str(e)}")
    
    if not account:
        logger.warning("所有会话验证方法失败")
        raise HTTPException(status_code=401, detail="会话已过期")
    
    # 从数据库获取用户详细信息
    conn = get_db_connection()
    try:
        user = conn.execute(
            "SELECT username, account, email, points FROM users WHERE account = ?", 
            (account,)
        ).fetchone()
        
        if not user:
            logger.warning(f"数据库中未找到用户: {account}")
            raise HTTPException(status_code=404, detail="用户不存在")
        
        logger.info(f"成功获取用户信息: {user['username']}")
        
        # 返回用户信息
        return {
            "username": user["username"],
            "account": user["account"],
            "email": user["email"],
            "points": user["points"]
        }
    except Exception as e:
        logger.error(f"查询数据库时出错: {str(e)}")
        raise HTTPException(status_code=500, detail=f"获取用户信息失败: {str(e)}")
    finally:
        conn.close()

# 更新用户信息
@router.post("/user/update")
async def update_user_info(
    request: Request,
    user_data: dict = Body(...)
):
    """更新当前登录用户的信息"""
    # 验证用户是否已登录
    session_id = request.cookies.get("session_token")
    if not session_id:
        # 尝试从其他可能的cookie名称中获取会话ID
        for cookie_name in ["session_id", "auth_token"]:
            temp_session_id = request.cookies.get(cookie_name)
            if temp_session_id:
                session_id = temp_session_id
                break
                
        if not session_id:
            raise HTTPException(status_code=401, detail="未登录")
    
    # 获取用户账号
    account = None
    
    # 尝试使用数据库方法验证会话
    try:
        from database import db_utils
        session_data = db_utils.validate_session(session_id)
        if session_data:
            account = session_data.get("account")
    except Exception:
        pass
    
    # 如果上面的方法失败，尝试使用自定义认证模块
    if not account:
        try:
            account = custom_auth.verify_session(session_id)
        except Exception as e:
            logger.error(f"验证会话时出错: {str(e)}")
    
    if not account:
        raise HTTPException(status_code=401, detail="会话已过期")
    
    # 提取要更新的字段
    username = user_data.get("username")
    email = user_data.get("email")
    
    # 参数验证
    if not username:
        raise HTTPException(status_code=400, detail="用户名不能为空")
    
    # 更新数据库中的用户信息
    conn = get_db_connection()
    try:
        # 开始事务
        conn.execute("BEGIN TRANSACTION")
        
        # 更新用户信息
        if email:
            conn.execute(
                "UPDATE users SET username = ?, email = ? WHERE account = ?",
                (username, email, account)
            )
        else:
            conn.execute(
                "UPDATE users SET username = ? WHERE account = ?",
                (username, account)
            )
        
        # 提交事务
        conn.commit()
        
        # 返回更新后的用户信息
        user = conn.execute(
            "SELECT username, account, email, points FROM users WHERE account = ?", 
            (account,)
        ).fetchone()
        
        return {
            "success": True,
            "message": "用户信息更新成功",
            "data": {
                "username": user["username"],
                "account": user["account"],
                "email": user["email"],
                "points": user["points"]
            }
        }
    except Exception as e:
        # 回滚事务
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"更新用户信息失败: {str(e)}")
    finally:
        conn.close()

# 设置API路由
def setup_user_api(app):
    """将用户API路由添加到FastAPI应用"""
    app.include_router(router, prefix="/api") 