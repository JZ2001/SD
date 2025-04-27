from __future__ import annotations

import os
import time

from modules import timer
from modules import initialize_util
from modules import initialize

startup_timer = timer.startup_timer
startup_timer.record("launcher")

initialize.imports()

initialize.check_versions()


def create_api(app):
    from modules.api.api import Api
    from modules.call_queue import queue_lock

    api = Api(app, queue_lock)
    return api


def api_only():
    from fastapi import FastAPI
    from modules.shared_cmd_options import cmd_opts

    initialize.initialize()

    app = FastAPI()
    initialize_util.setup_middleware(app)
    api = create_api(app)

    from modules import script_callbacks
    script_callbacks.before_ui_callback()
    script_callbacks.app_started_callback(None, app)

    print(f"Startup time: {startup_timer.summary()}.")
    api.launch(
        server_name=initialize_util.gradio_server_name(),
        port=cmd_opts.port if cmd_opts.port else 7861,
        root_path=f"/{cmd_opts.subpath}" if cmd_opts.subpath else ""
    )


def webui():
    from modules.shared_cmd_options import cmd_opts

    launch_api = cmd_opts.api
    initialize.initialize()

    from modules import shared, ui_tempdir, script_callbacks, ui, progress, ui_extra_networks

    while 1:
        if shared.opts.clean_temp_dir_at_start:
            ui_tempdir.cleanup_tmpdr()
            startup_timer.record("cleanup temp dir")

        script_callbacks.before_ui_callback()
        startup_timer.record("scripts before_ui_callback")

        shared.demo = ui.create_ui()
        startup_timer.record("create ui")

        if not cmd_opts.no_gradio_queue:
            shared.demo.queue(64)

        # 获取认证凭据，但不传递给Gradio，我们将使用自定义认证
        # 这样仍然保留了通过命令行参数/选项设置凭据的能力
        initialize_util.get_gradio_auth_creds()

        auto_launch_browser = False
        if os.getenv('SD_WEBUI_RESTARTING') != '1':
            if shared.opts.auto_launch_browser == "Remote" or cmd_opts.autolaunch:
                auto_launch_browser = True
            elif shared.opts.auto_launch_browser == "Local":
                auto_launch_browser = not cmd_opts.webui_is_non_local

        app, local_url, share_url = shared.demo.launch(
            share=cmd_opts.share,
            server_name=initialize_util.gradio_server_name(),
            server_port=cmd_opts.port,
            ssl_keyfile=cmd_opts.tls_keyfile,
            ssl_certfile=cmd_opts.tls_certfile,
            ssl_verify=cmd_opts.disable_tls_verify,
            debug=cmd_opts.gradio_debug,
            auth=None,  # 不使用Gradio的认证系统，使用我们的自定义认证
            inbrowser=auto_launch_browser,
            prevent_thread_lock=True,
            allowed_paths=cmd_opts.gradio_allowed_path,
            app_kwargs={
                "docs_url": "/docs",
                "redoc_url": "/redoc",
            },
            root_path=f"/{cmd_opts.subpath}" if cmd_opts.subpath else "",
        )

        startup_timer.record("gradio launch")

        # gradio uses a very open CORS policy via app.user_middleware, which makes it possible for
        # an attacker to trick the user into opening a malicious HTML page, which makes a request to the
        # running web ui and do whatever the attacker wants, including installing an extension and
        # running its code. We disable this here. Suggested by RyotaK.
        app.user_middleware = [x for x in app.user_middleware if x.cls.__name__ != 'CORSMiddleware']

        initialize_util.setup_middleware(app)

        # 设置自定义认证系统
        from modules import custom_auth
        custom_auth.setup_auth_routes(app)
        
        # 设置用户API路由
        from modules import user_api
        user_api.setup_user_api(app)
        
        # 添加用户导航栏静态文件路由
        from fastapi.staticfiles import StaticFiles
        from fastapi.responses import HTMLResponse
        from fastapi import Request
        
        # 设置静态文件路由
        if not hasattr(app, 'static_user_navbar'):
            app.mount("/static", StaticFiles(directory="html"), name="static")
        
        # 添加专门的导航栏路由
        @app.get("/navbar")
        async def navbar_handler():
            """返回单独的导航栏页面"""
            try:
                # 读取导航栏HTML
                with open("html/user_navbar.html", "r", encoding="utf-8") as f:
                    navbar_html = f.read()
                return HTMLResponse(content=navbar_html)
            except Exception as e:
                print(f"处理导航栏请求时出错: {str(e)}")
                return HTMLResponse(content=f"<p>加载导航栏出错: {str(e)}</p>", status_code=500)
        
        # 添加路由处理请求根路径，返回导航栏和Gradio UI
        @app.middleware("http")
        async def add_navbar_to_index(request: Request, call_next):
            response = await call_next(request)
            
            # 只处理HTML响应和根路径请求
            if request.url.path == "/" and isinstance(response, HTMLResponse):
                content = response.body.decode()
                
                # 读取导航栏HTML
                with open("html/user_navbar.html", "r", encoding="utf-8") as f:
                    navbar_html = f.read()
                
                # 将导航栏插入到Gradio UI前面
                # 找到<gradio-app>标签的位置，在其前面插入导航栏
                gradio_app_pos = content.find("<gradio-app")
                if gradio_app_pos != -1:
                    # 提取导航栏的关键部分，不包括<html>、<head>和<body>标签
                    start_pos = navbar_html.find('<div id="user-navbar">')
                    end_pos = navbar_html.find('</body>')
                    
                    # 提取样式和脚本
                    style_start = navbar_html.find('<style>')
                    style_end = navbar_html.find('</style>') + 8
                    style_content = navbar_html[style_start:style_end]
                    
                    script_start = navbar_html.find('<script>')
                    script_end = navbar_html.find('</script>') + 9
                    script_content = navbar_html[script_start:script_end]
                    
                    # 将Font Awesome链接添加到head部分
                    font_awesome_link = '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">'
                    head_end_pos = content.find('</head>')
                    if head_end_pos != -1:
                        content = content[:head_end_pos] + style_content + font_awesome_link + content[head_end_pos:]
                    
                    # 将用户导航栏添加到gradio-app前面
                    navbar_div = navbar_html[start_pos:navbar_html.find('</div>', start_pos) + 6]
                    content = content[:gradio_app_pos] + navbar_div + content[gradio_app_pos:]
                    
                    # 将模态框和脚本添加到body结束前
                    body_end_pos = content.find('</body>')
                    if body_end_pos != -1:
                        # 提取模态框HTML
                        modal_start = navbar_html.find('<div id="profile-modal">')
                        modal_end = navbar_html.find('</div>', navbar_html.find('</div>', navbar_html.find('</div>', modal_start) + 6) + 6) + 6
                        modal_html = navbar_html[modal_start:modal_end]
                        
                        content = content[:body_end_pos] + modal_html + script_content + content[body_end_pos:]
                
                return HTMLResponse(content=content, status_code=response.status_code, headers=dict(response.headers))
            
            return response

        progress.setup_progress_api(app)
        ui.setup_ui_api(app)

        if launch_api:
            create_api(app)

        ui_extra_networks.add_pages_to_demo(app)

        startup_timer.record("add APIs")

        with startup_timer.subcategory("app_started_callback"):
            script_callbacks.app_started_callback(shared.demo, app)

        timer.startup_record = startup_timer.dump()
        print(f"Startup time: {startup_timer.summary()}.")

        try:
            while True:
                server_command = shared.state.wait_for_server_command(timeout=5)
                if server_command:
                    if server_command in ("stop", "restart"):
                        break
                    else:
                        print(f"Unknown server command: {server_command}")
        except KeyboardInterrupt:
            print('Caught KeyboardInterrupt, stopping...')
            server_command = "stop"

        if server_command == "stop":
            print("Stopping server...")
            # If we catch a keyboard interrupt, we want to stop the server and exit.
            shared.demo.close()
            break

        # disable auto launch webui in browser for subsequent UI Reload
        os.environ.setdefault('SD_WEBUI_RESTARTING', '1')

        print('Restarting UI...')
        shared.demo.close()
        time.sleep(0.5)
        startup_timer.reset()
        script_callbacks.app_reload_callback()
        startup_timer.record("app reload callback")
        script_callbacks.script_unloaded_callback()
        startup_timer.record("scripts unloaded callback")
        initialize.initialize_rest(reload_script_modules=True)


if __name__ == "__main__":
    from modules.shared_cmd_options import cmd_opts

    if cmd_opts.nowebui:
        api_only()
    else:
        webui()
