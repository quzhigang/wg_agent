document.addEventListener('DOMContentLoaded', function() {
    // 顶部左右拖动
    const resizerTop = document.getElementById('resizer-top');
    const conclusionBox = document.querySelector('.conclusion-box');
    const topSection = document.querySelector('.top-section');

    if (resizerTop && conclusionBox && topSection) {
        let isResizing = false;
        let startX, startWidth;

        resizerTop.addEventListener('mousedown', function(e) {
            isResizing = true;
            startX = e.clientX;
            startWidth = parseInt(document.defaultView.getComputedStyle(conclusionBox).width, 10);
            document.body.style.cursor = 'col-resize';
            e.preventDefault();
        });

        document.addEventListener('mousemove', function(e) {
            if (!isResizing) return;
            const newWidth = startWidth + (e.clientX - startX);
            const parentWidth = topSection.clientWidth;
            
            // 限制宽度在 200px 到 父容器宽度的80% 之间
            if (newWidth > 200 && newWidth < (parentWidth * 0.8)) {
                conclusionBox.style.width = newWidth + 'px';
            }
        });

        document.addEventListener('mouseup', function() {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = 'default';
            }
        });
    }

    // 主区域上下拖动
    const resizerMainV = document.getElementById('resizer-main-v');
    const topSectionContainer = document.querySelector('.top-section');
    const rightMain = document.querySelector('.right-main');

    if (resizerMainV && topSectionContainer && rightMain) {
        let isResizingV = false;
        let startY, startHeight;

        resizerMainV.addEventListener('mousedown', function(e) {
            isResizingV = true;
            startY = e.clientY;
            startHeight = parseInt(document.defaultView.getComputedStyle(topSectionContainer).height, 10);
            document.body.style.cursor = 'row-resize';
            e.preventDefault();
        });

        document.addEventListener('mousemove', function(e) {
            if (!isResizingV) return;
            const newHeight = startHeight + (e.clientY - startY);
            const parentHeight = rightMain.clientHeight;
            
            // 限制高度在 200px 到 父容器高度的80% 之间
            if (newHeight > 200 && newHeight < (parentHeight * 0.8)) {
                topSectionContainer.style.height = newHeight + 'px';
            }
        });

        document.addEventListener('mouseup', function() {
            if (isResizingV) {
                isResizingV = false;
                document.body.style.cursor = 'default';
            }
        });
    }
});
