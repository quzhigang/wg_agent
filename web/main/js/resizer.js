document.addEventListener('DOMContentLoaded', function() {
    const resizer = document.getElementById('resizer-sidebar');
    const leftSidebar = document.querySelector('.left-sidebar');
    const iframeContainer = document.querySelector('.iframe-container');
    const layoutGrid = document.querySelector('.layout-grid');
    
    if (!resizer || !leftSidebar || !iframeContainer) return;

    let isResizing = false;
    let startX, startWidth;

    // 拖动调整大小功能
    resizer.addEventListener('mousedown', function(e) {
        // 如果点击的是按钮，不触发拖动
        if (e.target.closest('.toggle-sidebar-btn')) return;
        
        isResizing = true;
        startX = e.clientX;
        startWidth = parseInt(document.defaultView.getComputedStyle(leftSidebar).width, 10);
        
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
        e.preventDefault();
    });

    document.addEventListener('mousemove', function(e) {
        if (!isResizing) return;
        
        // 计算新宽度：向左拖动（x变小）右侧栏变宽，向右拖动（x变大）右侧栏变窄
        const deltaX = startX - e.clientX;
        const newWidth = startWidth + deltaX;
        
        // 设置最小和最大宽度限制
        if (newWidth >= 200 && newWidth <= 800) {
            leftSidebar.style.width = newWidth + 'px';
        }
    });

    document.addEventListener('mouseup', function() {
        if (isResizing) {
            isResizing = false;
            document.body.style.cursor = 'default';
            document.body.style.userSelect = '';
        }
    });

    // 创建折叠/展开按钮（独立于resizer，固定在对话框左侧）
    const toggleBtn = document.createElement('button');
    toggleBtn.className = 'toggle-sidebar-btn';
    toggleBtn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg>';
    toggleBtn.title = '折叠/展开左侧区域';
    // 将按钮添加到body而不是resizer
    document.body.appendChild(toggleBtn);

    let isCollapsed = false;
    let savedSidebarWidth = null;

    // 更新按钮位置的函数
    function updateToggleBtnPosition() {
        const sidebarRect = leftSidebar.getBoundingClientRect();
        toggleBtn.style.position = 'fixed';
        toggleBtn.style.left = (sidebarRect.left - 12) + 'px';
        toggleBtn.style.top = '50%';
        toggleBtn.style.transform = 'translateY(-50%)';
        toggleBtn.style.zIndex = '100';
    }

    // 初始化按钮位置
    updateToggleBtnPosition();

    // 窗口大小改变时更新按钮位置
    window.addEventListener('resize', updateToggleBtnPosition);

    toggleBtn.addEventListener('click', function(e) {
        e.stopPropagation();
        
        if (!isCollapsed) {
            // 保存当前对话框宽度
            savedSidebarWidth = parseInt(document.defaultView.getComputedStyle(leftSidebar).width, 10);
            
            // 折叠：右侧对话框使用固定定位保持在右边
            const sidebarRect = leftSidebar.getBoundingClientRect();
            leftSidebar.style.position = 'fixed';
            leftSidebar.style.right = '0';
            leftSidebar.style.top = '0';
            leftSidebar.style.height = '100vh';
            leftSidebar.style.width = savedSidebarWidth + 'px';
            
            // iframe区域向右折叠（使用transform从右向左收缩）
            iframeContainer.style.transformOrigin = 'right center';
            iframeContainer.style.transition = 'transform 1s ease, opacity 1s ease';
            iframeContainer.style.transform = 'scaleX(0)';
            iframeContainer.style.opacity = '0';
            
            // 隐藏分隔条
            resizer.style.transition = 'opacity 1s ease';
            resizer.style.opacity = '0';
            resizer.style.pointerEvents = 'none';
            
            // 箭头方向改变（指向右，表示点击可展开）
            toggleBtn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M8.59 16.59L10 18l6-6-6-6-1.41 1.41L13.17 12z"/></svg>';
            
            isCollapsed = true;
            
            // 更新按钮位置
            setTimeout(updateToggleBtnPosition, 50);
            
        } else {
            // 展开：恢复iframe区域
            iframeContainer.style.transition = 'transform 1s ease, opacity 1s ease';
            iframeContainer.style.transform = 'scaleX(1)';
            iframeContainer.style.opacity = '1';
            
            // 显示分隔条
            resizer.style.transition = 'opacity 1s ease';
            resizer.style.opacity = '1';
            resizer.style.pointerEvents = '';
            
            // 箭头方向改变（指向左，表示点击可折叠）
            toggleBtn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor"><path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/></svg>';
            
            isCollapsed = false;
            
            // 动画结束后恢复对话框的正常布局
            setTimeout(() => {
                leftSidebar.style.position = '';
                leftSidebar.style.right = '';
                leftSidebar.style.top = '';
                leftSidebar.style.height = '';
                iframeContainer.style.transition = '';
                iframeContainer.style.transform = '';
                iframeContainer.style.transformOrigin = '';
                resizer.style.transition = '';
                updateToggleBtnPosition();
            }, 1010);
        }
    });

    // 拖动时也更新按钮位置
    document.addEventListener('mouseup', function() {
        if (isResizing) {
            setTimeout(updateToggleBtnPosition, 10);
        }
    });
});
