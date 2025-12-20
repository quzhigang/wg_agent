document.addEventListener('DOMContentLoaded', function () {
    // Initialize resizers for the main content area
    initResizer('resizer-top', '.conclusion-box', 'width', true, false);
    initResizer('resizer-main-v', '.top-section', 'height', false, false);

    function initResizer(resizerId, targetSelector, dimension, isHorizontal, invertDelta = false) {
        const resizer = document.getElementById(resizerId);
        const target = document.querySelector(targetSelector);

        if (!resizer || !target) return;

        // Create overlay for capturing mouse events during drag
        let overlay = null;

        resizer.addEventListener('mousedown', function (e) {
            e.preventDefault();

            const startX = e.clientX;
            const startY = e.clientY;
            const startDim = isHorizontal ? target.offsetWidth : target.offsetHeight;

            resizer.classList.add('dragging');
            document.body.style.cursor = isHorizontal ? 'col-resize' : 'row-resize';

            // Create overlay to capture mouse events over map/chart elements
            overlay = document.createElement('div');
            overlay.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;z-index:9999;cursor:' + (isHorizontal ? 'col-resize' : 'row-resize');
            document.body.appendChild(overlay);

            function onMouseMove(e) {
                let delta;
                if (isHorizontal) {
                    delta = e.clientX - startX;
                } else {
                    delta = e.clientY - startY;
                }

                if (invertDelta) {
                    delta = -delta;
                }

                let newDim = startDim + delta;

                target.style[dimension] = newDim + 'px';

                window.dispatchEvent(new Event('resize'));
            }

            function onMouseUp() {
                resizer.classList.remove('dragging');
                document.body.style.cursor = 'default';

                // Remove overlay
                if (overlay && overlay.parentNode) {
                    overlay.parentNode.removeChild(overlay);
                    overlay = null;
                }

                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);

                window.dispatchEvent(new Event('resize'));
            }

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    }
});
