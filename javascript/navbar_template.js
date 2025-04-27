// 导航栏服务器加载脚本
(function() {
    console.log('导航栏加载脚本已初始化');

    function injectNavbarFrame() {
        // 如果已经存在导航栏，则不重复注入
        if (document.getElementById('navbarFrame')) {
            console.log('导航栏框架已存在');
            return;
        }

        // 创建iframe元素用于加载导航栏
        const navbarFrame = document.createElement('iframe');
        navbarFrame.id = 'navbarFrame';
        navbarFrame.src = '/navbar';
        navbarFrame.style.position = 'fixed';
        navbarFrame.style.top = '0';
        navbarFrame.style.left = '0';
        navbarFrame.style.width = '100%';
        navbarFrame.style.height = '60px';
        navbarFrame.style.border = 'none';
        navbarFrame.style.zIndex = '9999';
        navbarFrame.style.backgroundColor = 'transparent';
        navbarFrame.style.overflow = 'hidden';
        navbarFrame.setAttribute('scrolling', 'no');
        navbarFrame.setAttribute('frameborder', '0');

        // 创建一个占位元素，为导航栏留出空间
        const spacer = document.createElement('div');
        spacer.id = 'navbarSpacer';
        spacer.style.height = '60px';
        spacer.style.width = '100%';
        spacer.style.display = 'block';

        // 插入导航栏框架
        document.body.insertBefore(spacer, document.body.firstChild);
        document.body.insertBefore(navbarFrame, document.body.firstChild);

        console.log('导航栏框架已注入');
    }

    // 检查DOM是否已经加载完成
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(injectNavbarFrame, 100);
        });
    } else {
        setTimeout(injectNavbarFrame, 100);
    }

    // 确保Gradio加载后仍然保持导航栏可见
    function monitorGradioLoading() {
        const checkInterval = setInterval(function() {
            const gradioApp = document.querySelector('gradio-app');
            if (gradioApp && gradioApp.shadowRoot) {
                console.log('Gradio应用已检测到，确保导航栏可见');
                
                // Gradio加载后重新注入导航栏
                setTimeout(injectNavbarFrame, 500);
                
                // 停止监控
                clearInterval(checkInterval);
            }
        }, 1000);

        // 最多监控30秒
        setTimeout(function() {
            clearInterval(checkInterval);
        }, 30000);
    }

    // 启动Gradio监控
    monitorGradioLoading();
})(); 