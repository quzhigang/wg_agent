document.addEventListener('DOMContentLoaded', function() {
    const resizer = document.getElementById('resizer-sidebar');
    const leftSidebar = document.querySelector('.left-sidebar');
    const iframeContainer = document.querySelector('.iframe-container');
    
    if (!resizer || !leftSidebar || !iframeContainer) return;

    let isResizing = false;
    let startX, startWidth;

    resizer.addEventListener('mousedown', function(e) {
        isResizing = true;
        startX = e.clientX;
        // 注意：这里的"左侧"栏现在在右边，所以我们要调整的是它的宽度
        startWidth = parseInt(document.defaultView.getComputedStyle(leftSidebar).width, 10);
        
        document.body.style.cursor = 'col-resize';
        // 防止选中文字
        e.preventDefault();
    });

    document.addEventListener('mousemove', function(e) {
        if (!isResizing) return;
        
        // 拖动时，往左拖动（x变小）意味着右侧栏变宽
        const width = startWidth + (startX - e.clientX);
        
        // 设置最小和最大宽度限制
        if (width > 200 && width < 800) {
            leftSidebar.style.width = width + 'px';
        }
    });

    document.addEventListener('mouseup', function() {
        if (isResizing) {
            isResizing = false;
            document.body.style.cursor = 'default';
        }
    });
});
