document.addEventListener('DOMContentLoaded', function () {
    const resizer = document.getElementById('resizer-sidebar');
    const leftSidebar = document.querySelector('.left-sidebar');
    const iframeContainer = document.querySelector('.iframe-container');
    const layoutGrid = document.querySelector('.layout-grid');

    if (!resizer || !leftSidebar || !iframeContainer) return;

    // 创建折叠/展开按钮（挂载到对话框左边缘以保持位置固定）
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'toggle-sidebar-btn';
    toggleBtn.id = 'toggle-collapse-btn';
    toggleBtn.title = '折叠/展开左侧区域';
    leftSidebar.appendChild(toggleBtn);

    // 默认折叠状态
    let isCollapsed = true;

    // 初始化：默认折叠左侧iframe
    iframeContainer.classList.add('collapsed');
    // 初始图标：指向左 (表示点击后向左侧展开)
    toggleBtn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg>';

    // 折叠/展开功能
    toggleBtn.addEventListener('click', function (e) {
        e.stopPropagation();

        if (!isCollapsed) {
            // 折叠：左侧 iframe 区域向右收缩 (通过 width 动画由 CSS 控制)
            iframeContainer.classList.add('collapsed');

            // 图标改变：指向左 (表示点击后向左侧展开)
            toggleBtn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg>';
            isCollapsed = true;
        } else {
            // 展开
            iframeContainer.classList.remove('collapsed');

            // 图标改变：指向右 (表示点击后发起向右折叠)
            toggleBtn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M8.59 16.59L10 18l6-6-6-6-1.41 1.41L13.17 12z"/></svg>';
            isCollapsed = false;
        }
    });

    // 暴露全局方法供外部调用（如 handleEvent 中页面生成完成时触发展开）
    window.expandIframePanel = function() {
        if (isCollapsed) {
            toggleBtn.click();  // 触发展开动画
        }
    };

    window.collapseIframePanel = function() {
        if (!isCollapsed) {
            toggleBtn.click();  // 触发折叠动画
        }
    };

    // 获取当前折叠状态
    window.isIframePanelCollapsed = function() {
        return isCollapsed;
    };

    // 禁用拖动逻辑防止冲突
    resizer.style.display = 'none';
});
