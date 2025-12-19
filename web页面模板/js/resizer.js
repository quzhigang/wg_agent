document.addEventListener('DOMContentLoaded', function () {
    // resizer-sidebar is now controlling the RIGHT sidebar, so dragging left (negative delta) should INCREASE width.
    // We set invertDelta = true.
    initResizer('resizer-sidebar', 'aside.left-sidebar', 'width', true, true);

    function initResizer(resizerId, targetSelector, dimension, isHorizontal, invertDelta = false) {
        const resizer = document.getElementById(resizerId);
        const target = document.querySelector(targetSelector);
        const iframe = document.getElementById('mainContentFrame');

        if (!resizer || !target) return;

        resizer.addEventListener('mousedown', function (e) {
            e.preventDefault();

            const startX = e.clientX;
            const startY = e.clientY;
            const startDim = isHorizontal ? target.offsetWidth : target.offsetHeight;

            resizer.classList.add('dragging');
            document.body.style.cursor = isHorizontal ? 'col-resize' : 'row-resize';

            // Disable iframe pointer events during drag to prevent event loss
            if (iframe) {
                iframe.style.pointerEvents = 'none';
            }

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

                if (iframe && iframe.contentWindow) {
                    iframe.contentWindow.dispatchEvent(new Event('resize'));
                }
            }

            function onMouseUp() {
                resizer.classList.remove('dragging');
                document.body.style.cursor = 'default';

                // Re-enable iframe pointer events
                if (iframe) {
                    iframe.style.pointerEvents = '';
                }

                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);

                window.dispatchEvent(new Event('resize'));

                if (iframe && iframe.contentWindow) {
                    iframe.contentWindow.dispatchEvent(new Event('resize'));
                }
            }

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    }
});
