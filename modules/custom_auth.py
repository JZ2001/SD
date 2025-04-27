import os
import json
import time
import secrets
import base64
import hashlib
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any
from fastapi import Request, Response, HTTPException, Depends, status
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials

# 数据库导入
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import db_utils

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("custom_auth")

# 配置模板引擎
templates_dir = Path("html")
templates = Jinja2Templates(directory=templates_dir)

# 默认用户凭据（仅用于初始化时）
DEFAULT_USERNAME = "admin"
DEFAULT_PASSWORD = "admin"

# 会话有效期（秒）
SESSION_EXPIRY = 24 * 60 * 60  # 24小时

# 会话存储和配置
active_sessions: Dict[str, Dict] = {}  # 存储活跃会话
SESSION_COOKIE_NAME = "sd_session_id"
SESSION_EXPIRY_DAYS = 30  # 会话过期天数

# 数据库连接
try:
    from database.user_db import UserDatabase
    user_db = UserDatabase()
    logger.info("成功连接到用户数据库")
except Exception as e:
    logger.error(f"连接用户数据库失败: {str(e)}")
    user_db = None

# 安全工具函数
def hash_password(password: str) -> str:
    """使用SHA-256哈希密码"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_credentials(username: str, password: str) -> bool:
    """验证用户凭据"""
    if user_db:
        # 使用数据库验证
        return user_db.verify_user(username, hash_password(password))
    else:
        # 使用默认凭据验证
        return username == DEFAULT_USERNAME and password == DEFAULT_PASSWORD

def create_session(username: str) -> str:
    """为用户创建新会话"""
    session_id = secrets.token_urlsafe(32)
    expiry = datetime.now() + timedelta(days=SESSION_EXPIRY_DAYS)
    
    # 获取用户信息，包括积分
    user_info = None
    if user_db:
        user_info = user_db.get_user_info(username)
    
    # 创建会话数据
    session_data = {
        "username": username,
        "created_at": datetime.now().isoformat(),
        "expires_at": expiry.isoformat(),
        "user_id": str(uuid.uuid4()) if not user_info else user_info.get('id', str(uuid.uuid4())),
        "points": 0 if not user_info else user_info.get('points', 0)
    }
    
    # 存储会话
    active_sessions[session_id] = session_data
    
    # 如果有数据库，也更新数据库中的会话
    if user_db:
        user_db.add_session(session_id, session_data)
    
    return session_id

def get_current_session(request: Request) -> Optional[Dict]:
    """从请求中获取当前会话"""
    session_id = request.cookies.get(SESSION_COOKIE_NAME)
    if not session_id:
        return None
    
    # 首先尝试从内存中获取会话
    session = active_sessions.get(session_id)
    
    # 如果内存中没有但有数据库连接，尝试从数据库获取
    if not session and user_db:
        db_session = user_db.get_session(session_id)
        if db_session:
            # 将数据库中的会话加载到内存
            active_sessions[session_id] = db_session
            session = db_session
    
    if not session:
        return None
    
    # 检查会话是否过期
    try:
        expiry = datetime.fromisoformat(session["expires_at"])
        if datetime.now() > expiry:
            # 会话已过期，从内存中删除
            if session_id in active_sessions:
                del active_sessions[session_id]
            
            # 如果有数据库，也从数据库中删除
            if user_db:
                user_db.delete_session(session_id)
            
            return None
    except:
        # 如果解析日期时出错，视为无效会话
        return None
        
    return session

def update_user_info_in_session(username: str, new_info: Dict):
    """更新所有属于该用户的会话中的用户信息"""
    for session_id, session in active_sessions.items():
        if session.get("username") == username:
            # 更新会话中的用户信息
            for key, value in new_info.items():
                if key in session:
                    session[key] = value
            
            # 如果有数据库，也更新数据库中的会话
            if user_db:
                user_db.update_session(session_id, session)

# 获取登录页面HTML内容
def get_login_page() -> str:
    """读取登录页面HTML内容"""
    html_path = Path(os.path.dirname(os.path.dirname(__file__))) / "html" / "login.html"
    if not html_path.exists():
        return "登录页面不存在"
    
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()

def get_credentials() -> List[Tuple[str, str]]:
    """获取有效的用户凭据列表 (已废弃，仅为兼容性保留)"""
    from modules.initialize_util import get_gradio_auth_creds
    
    # 从initialize_util模块获取认证凭据
    credentials = list(get_gradio_auth_creds())
    
    # 如果没有凭据，使用默认值
    if not credentials:
        return [(DEFAULT_USERNAME, DEFAULT_PASSWORD)]
    
    return credentials

def verify_credentials(username: str, password: str) -> bool:
    """验证用户名和密码"""
    # 调用数据库验证函数
    user = db_utils.verify_user(username, password)
    return user is not None

def get_session_from_request(request: Request) -> Optional[Dict[str, Any]]:
    """从请求中获取会话数据"""
    session_token = request.cookies.get("session_token")
    if not session_token:
        return None
    
    # 从数据库验证会话
    return db_utils.validate_session(session_token)

def get_session_token_from_request(request: Request) -> Optional[str]:
    """从请求中获取会话令牌"""
    return request.cookies.get("session_token")

async def login_page_handler(request: Request) -> HTMLResponse:
    """处理登录页面请求"""
    html_content = get_login_page()
    return HTMLResponse(content=html_content)

async def auth_test_handler(request: Request) -> JSONResponse:
    """提供一个测试端点，验证认证系统是否工作正常"""
    return JSONResponse({
        "status": "success",
        "message": "认证系统正常工作",
        "timestamp": time.time()
    })

async def login_debug_handler(request: Request) -> HTMLResponse:
    """提供一个简单的登录调试页面"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>登录调试页面</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
            h1 { color: #333; }
            input, button { margin: 10px 0; padding: 8px; width: 100%; }
            button { background: #4CAF50; color: white; border: none; cursor: pointer; }
            pre { background: #f4f4f4; padding: 10px; overflow: auto; }
        </style>
    </head>
    <body>
        <h1>登录调试</h1>
        
        <h2>表单提交</h2>
        <form id="loginForm" method="post" action="/login_check">
            <input type="text" name="username" placeholder="用户名" value="admin">
            <input type="password" name="password" placeholder="密码" value="123456">
            <button type="submit">提交表单</button>
        </form>
        
        <h2>Ajax JSON提交</h2>
        <input type="text" id="jsonUsername" placeholder="用户名" value="admin">
        <input type="password" id="jsonPassword" placeholder="密码" value="123456">
        <button id="jsonSubmit">JSON提交</button>
        
        <h2>结果</h2>
        <pre id="result">等待操作...</pre>
        
        <script>
        document.getElementById('jsonSubmit').addEventListener('click', function() {
            const username = document.getElementById('jsonUsername').value;
            const password = document.getElementById('jsonPassword').value;
            const result = document.getElementById('result');
            
            result.textContent = '发送请求...';
            
            fetch('/login_check', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username, password })
            })
            .then(response => {
                result.textContent = '状态码: ' + response.status;
                return response.json();
            })
            .then(data => {
                result.textContent += '\\n数据: ' + JSON.stringify(data, null, 2);
            })
            .catch(error => {
                result.textContent += '\\n错误: ' + error;
            });
        });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

async def login_check_handler(request: Request) -> JSONResponse:
    """处理登录验证请求"""
    try:
        # 尝试不同方式获取数据
        username = ""
        password = ""
        
        # 检查内容类型
        content_type = request.headers.get("content-type", "")
        print(f"请求Content-Type: {content_type}")
        
        # 处理表单数据 (multipart/form-data 或 application/x-www-form-urlencoded)
        if "multipart/form-data" in content_type or "application/x-www-form-urlencoded" in content_type:
            try:
                form_data = await request.form()
                username = form_data.get("username", "")
                password = form_data.get("password", "")
                print(f"从表单获取数据: username={username}, password={'*'*len(password)}")
            except Exception as e:
                print(f"解析表单数据失败: {str(e)}")
        # 处理JSON请求
        elif "application/json" in content_type:
            try:
                data = await request.json()
                username = data.get("username", "")
                password = data.get("password", "")
                print(f"从JSON获取数据: username={username}, password={'*'*len(password) if password else '无'}")
            except Exception as e:
                print(f"解析JSON失败: {str(e)}")
                return JSONResponse({"error": "无效的JSON格式"}, status_code=400)
        # 尝试从请求体直接获取数据
        else:
            try:
                body = await request.body()
                body_text = body.decode("utf-8")
                
                # 尝试将其作为JSON解析
                try:
                    import json
                    data = json.loads(body_text)
                    username = data.get("username", "")
                    password = data.get("password", "")
                    print(f"从原始JSON获取数据: username={username}")
                except json.JSONDecodeError:
                    # 尝试解析为表单格式 (key1=value1&key2=value2)
                    if "&" in body_text and "=" in body_text:
                        pairs = body_text.split("&")
                        data = {}
                        for pair in pairs:
                            if "=" in pair:
                                key, value = pair.split("=", 1)
                                # URL解码
                                import urllib.parse
                                key = urllib.parse.unquote_plus(key)
                                value = urllib.parse.unquote_plus(value)
                                data[key] = value
                        
                        username = data.get("username", "")
                        password = data.get("password", "")
                        print(f"从URL编码表单获取数据: username={username}")
            except Exception as e:
                print(f"处理请求体失败: {str(e)}")
        
        # 调试输出
        print(f"登录尝试: 用户名='{username}', 密码长度={len(password) if password else 0}")
        
        if not username or not password:
            return JSONResponse({"error": "请提供用户名和密码"}, status_code=400)
        
        # 调用数据库函数验证用户
        user_data = db_utils.verify_user(username, password)
        
        if user_data:
            # 登录成功，创建会话
            user_id = user_data['id']
            session_token = db_utils.create_session(user_id, SESSION_EXPIRY)
            print(f"用户 '{username}' (ID: {user_id}) 登录成功，创建会话令牌")
            
            # 创建带有会话令牌的响应
            response = JSONResponse({
                "success": True,
                "user": {
                    "username": user_data['username'],
                    "account": user_data['account'],
                    "points": user_data['points']
                }
            })
            
            # 同时设置两个cookie以确保兼容性
            cookie_settings = {
                "httponly": True,
                "max_age": SESSION_EXPIRY,
                "path": "/"
            }
            
            # 设置会话cookie (使用两个名称以确保兼容性)
            response.set_cookie(key="session_token", value=session_token, **cookie_settings)
            response.set_cookie(key="session_id", value=session_token, **cookie_settings)
            
            return response
        else:
            # 登录失败
            print(f"用户 '{username}' 登录失败：凭据无效")
            return JSONResponse({"error": "用户名或密码错误"}, status_code=401)
    except Exception as e:
        import traceback
        print(f"登录检查异常: {str(e)}")
        print(traceback.format_exc())
        return JSONResponse({"error": f"服务器错误: {str(e)}"}, status_code=500)

async def logout_handler(request: Request) -> RedirectResponse:
    """处理注销请求"""
    print("处理登出请求...")
    
    # 获取所有可能的会话token
    session_token = request.cookies.get("session_token")
    session_id = request.cookies.get("session_id")
    sd_session_id = request.cookies.get("sd_session_id")
    
    # 删除所有可能的会话
    if session_token:
        print(f"正在删除会话: {session_token[:10]}...")
        try:
            # 从数据库删除会话
            db_utils.delete_session(session_token)
            print("会话已从数据库删除")
        except Exception as e:
            print(f"删除会话时出错: {str(e)}")
    
    # 创建响应（重定向到登录页面）
    response = RedirectResponse(url="/login")
    
    # 清除所有可能的会话cookie
    response.delete_cookie(key="session_token", path="/")
    response.delete_cookie(key="session_id", path="/")
    response.delete_cookie(key="sd_session_id", path="/")
    
    print("已删除所有会话cookie，重定向到登录页面")
    
    # 如果是POST请求，返回JSON响应而不是重定向
    if request.method == "POST":
        return JSONResponse({"success": True, "message": "已成功登出"})
    
    return response

async def user_info_handler(request: Request) -> JSONResponse:
    """返回当前登录用户信息"""
    session = get_session_from_request(request)
    
    if not session:
        return JSONResponse({"error": "未登录"}, status_code=401)
    
    return JSONResponse({
        "user": {
            "id": session["user_id"],
            "username": session["username"],
            "account": session["account"],
            "email": session["email"],
            "points": session["points"]
        }
    })

async def deduct_points_handler(request: Request) -> JSONResponse:
    """处理扣除用户积分的请求"""
    print("收到扣除积分请求")
    
    # 获取用户会话
    session_token = request.cookies.get("session_token")
    if not session_token:
        print("扣除积分失败：未找到会话令牌")
        return JSONResponse({"success": False, "error": "未找到会话令牌"}, status_code=401)
    
    try:
        session = db_utils.validate_session(session_token)
        if not session:
            print("扣除积分失败：会话无效")
            return JSONResponse({"success": False, "error": "会话无效"}, status_code=401)
    except Exception as e:
        print(f"验证会话时出错: {str(e)}")
        return JSONResponse({"success": False, "error": f"验证会话失败: {str(e)}"}, status_code=500)
    
    # 获取要扣除的积分数量
    try:
        data = await request.json()
        points = data.get("points", 1)  # 默认扣除1点
        print(f"请求扣除积分: {points}点")
    except Exception as e:
        print(f"解析请求数据失败: {str(e)}")
        points = 1  # 如果没有指定，默认扣除1点
        
    # 获取用户当前积分
    user_id = session.get("user_id")
    current_points = session.get("points", 0)
    print(f"用户ID: {user_id}, 当前积分: {current_points}")
    
    # 如果积分不足，返回错误
    if current_points < points:
        print(f"积分不足: 当前{current_points}, 需要{points}")
        return JSONResponse({
            "success": False,
            "error": "积分不足",
            "points": current_points
        }, status_code=400)
    
    # 更新用户积分
    new_points = current_points - points
    try:
        # 更新数据库中的用户积分
        print(f"尝试更新积分: 从{current_points}减少到{new_points}")
        
        # 检查update_user_points函数是否存在
        if not hasattr(db_utils, 'update_user_points'):
            print("警告: db_utils模块中没有update_user_points函数，尝试直接使用SQL更新")
            # 使用SQL直接更新用户积分
            conn = None
            try:
                import sqlite3
                conn = sqlite3.connect('database/users.db')
                cursor = conn.cursor()
                cursor.execute("UPDATE users SET points = ? WHERE id = ?", (new_points, user_id))
                conn.commit()
                print(f"直接SQL更新成功，影响行数: {cursor.rowcount}")
                if cursor.rowcount == 0:
                    raise Exception("未找到要更新的用户记录")
            except Exception as sql_error:
                print(f"SQL更新出错: {str(sql_error)}")
                raise sql_error
            finally:
                if conn:
                    conn.close()
        else:
            # 使用db_utils模块函数更新
            db_utils.update_user_points(user_id, new_points)
        
        # 更新会话中的积分
        print("更新会话中的积分")
        session["points"] = new_points
        
        # 更新会话数据
        try:
            db_utils.update_session(session_token, session)
            print("会话数据已更新")
        except Exception as session_error:
            print(f"更新会话数据时出错: {str(session_error)}")
            # 继续执行，不中断流程
        
        print(f"积分更新成功: 新积分={new_points}")
        return JSONResponse({
            "success": True,
            "message": f"已扣除{points}积分",
            "points": new_points
        })
    except Exception as e:
        import traceback
        print(f"扣除积分时出错: {str(e)}")
        print(traceback.format_exc())
        return JSONResponse({
            "success": False,
            "error": f"扣除积分失败: {str(e)}",
            "points": current_points
        }, status_code=500)

async def index_handler(request: Request):
    """处理主页请求，确保正确重定向到Gradio接口"""
    # 检查用户是否已登录
    session = get_session_from_request(request)
    if not session:
        # 未登录，重定向到登录页面
        return RedirectResponse(url="/login")
    
    # 已登录，直接返回一个简单的HTML页面，通过JavaScript重定向到Gradio界面
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>重定向到应用程序...</title>
        <meta charset="UTF-8">
        <script>
            // 使用JavaScript重定向到Gradio接口，指定使用黑色主题
            window.location.href = "./?__theme=dark";
        </script>
    </head>
    <body>
        <p>正在加载应用程序，请稍候...</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

class AuthMiddleware(BaseHTTPMiddleware):
    """认证中间件，验证用户是否已登录"""
    
    async def dispatch(self, request: Request, call_next):
        """处理请求并验证认证状态"""
        # 获取请求路径
        path = request.url.path
        
        # 不需要验证的路径
        exempt_paths = [
            "/login", 
            "/login_check", 
            "/logout",      # 添加登出路径到豁免列表，确保登出请求可以正常处理
            "/favicon.ico", 
            "/docs", 
            "/redoc", 
            "/openapi.json",
            "/auth_test",
            "/login_debug",
            "/navbar"  # 添加导航栏路径到豁免列表
        ]
        
        # 不需要验证的路径前缀
        exempt_prefixes = [
            "/static/", 
            "/file=", 
            "/js/", 
            "/css/", 
            "/images/", 
            "/fonts/",
            "/assets/",
            "/theme=",
            "/api/",          # API请求
            "/internal/",     # Gradio内部请求
            "/run/",          # Gradio运行请求
            "/queue/",        # Gradio队列请求
            "/upload",        # 上传请求
            "/file/",         # 文件请求
            "/stream",        # 流媒体请求
            "/ws",            # WebSocket请求
            "/tmp/"           # 临时文件请求
        ]
        
        # 检查是否是忽略的路径
        is_exempt = path in exempt_paths or any(path.startswith(prefix) for prefix in exempt_prefixes)
        
        # 如果路径是 /logout，允许直接通过，确保登出功能正常工作
        if path == "/logout":
            return await call_next(request)
            
        # 特殊处理 - 检查URL查询参数，处理Gradio特定请求
        query_string = request.url.query.decode() if hasattr(request.url.query, 'decode') else request.url.query
        
        # 检查主题参数，如果存在light主题，修改为dark主题
        if '__theme=light' in query_string:
            # 创建新的URL，并将light替换为dark
            new_url = str(request.url).replace('__theme=light', '__theme=dark')
            return RedirectResponse(url=new_url)
            
        has_gradio_param = any(param in query_string for param in ['__theme=', 'view=', 'component='])
        
        # 对于根路径，即使有Gradio参数，也要检查认证状态
        if path == "/" and has_gradio_param:
            # 检查是否已认证
            session = None
            session_token = request.cookies.get("session_token")
            if session_token:
                try:
                    session = db_utils.validate_session(session_token)
                except Exception as e:
                    print(f"验证session_token时发生错误: {str(e)}")
                    
            # 如果未认证，重定向到登录页面
            if not session:
                print(f"未授权访问根路径: {request.url}, 重定向到登录页面")
                return RedirectResponse(url="/login")
                
            # 已认证，继续处理
            return await call_next(request)
            
        if is_exempt or (has_gradio_param and path != "/"):
            # 对于免验证路径，直接处理请求
            return await call_next(request)
        
        # 尝试从不同的cookie名称获取会话ID
        session = None
        
        # 首先尝试session_token
        session_token = request.cookies.get("session_token")
        if session_token:
            try:
                # 尝试使用数据库验证
                session = db_utils.validate_session(session_token)
            except Exception as e:
                print(f"验证session_token时发生错误: {str(e)}")
        
        # 如果上述方法失败，尝试session_id
        if not session:
            session_id = request.cookies.get("session_id")
            if session_id:
                account = verify_session(session_id)
                if account:
                    # 构造最小会话数据
                    session = {"account": account, "username": account}
        
        if session:
            # 用户已登录，继续处理请求
            try:
                # 输出调试信息
                if path == "/":
                    username = session.get('username', session.get('account', '未知用户'))
                    print(f"用户 {username} 访问主页")
                
                # 调用下一个处理程序
                return await call_next(request)
            except Exception as e:
                import traceback
                print(f"处理已认证请求时出错: {str(e)}")
                print(traceback.format_exc())
                # 出错时仍继续处理
                return await call_next(request)
        else:
            # 用户未登录，重定向到登录页面
            print(f"未授权访问: {path}, 重定向到登录页面")
            return RedirectResponse(url="/login")

def setup_auth_routes(app):
    """设置认证相关的路由"""
    # 登录页面
    app.add_route("/login", login_page_handler, methods=["GET"])
    
    # 登录验证 - 添加/login的POST路由处理
    app.add_route("/login", login_check_handler, methods=["POST"])
    
    # 保留原有的登录验证路由以保持兼容性
    app.add_route("/login_check", login_check_handler, methods=["POST"])
    
    # 测试认证系统路由
    app.add_route("/auth_test", auth_test_handler, methods=["GET"])
    
    # 登录调试页面
    app.add_route("/login_debug", login_debug_handler, methods=["GET"])
    
    # 用户信息API
    app.add_route("/user_info", user_info_handler, methods=["GET"])
    
    # 扣除积分API
    app.add_route("/api/deduct_points", deduct_points_handler, methods=["POST"])
    
    # 注销 - 同时支持GET和POST请求
    app.add_route("/logout", logout_handler, methods=["GET", "POST"])
    
    # 添加认证中间件
    app.add_middleware(AuthMiddleware)

    # 清理过期会话
    db_utils.clean_expired_sessions()
    
    print("已设置数据库认证系统，用户数据已迁移至database/user.db")

# 确保verify_session函数可用于用户API
def verify_session(session_id):
    """
    验证会话ID并返回关联的账号
    
    Args:
        session_id: 会话ID
        
    Returns:
        如果会话有效，返回关联的账号；否则返回None
    """
    if not session_id:
        return None
    
    # 首先尝试使用数据库工具验证会话
    try:
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from database import db_utils
        
        session_data = db_utils.validate_session(session_id)
        if session_data:
            return session_data.get("account")
    except Exception as e:
        print(f"使用db_utils验证会话时出错: {str(e)}")
        
    # 如果上面的方法失败，尝试使用sqlite直接查询
    try:
        conn = get_db_connection()
        try:
            # 获取会话信息
            session = conn.execute(
                "SELECT account, expiry FROM sessions WHERE id = ?", 
                (session_id,)
            ).fetchone()
            
            # 检查会话是否存在且未过期
            if session and session['expiry'] > time.time():
                return session['account']
        finally:
            conn.close()
    except Exception as e:
        print(f"直接查询数据库验证会话时出错: {str(e)}")
    
    # 如果会话不存在或已过期，则返回None
    return None

# 获取数据库连接
def get_db_connection():
    """获取数据库连接"""
    import sqlite3
    conn = sqlite3.connect('database/users.db')
    conn.row_factory = sqlite3.Row
    return conn 