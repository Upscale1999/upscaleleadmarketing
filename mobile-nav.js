/* Mobile nav toggle — hamburger opens/closes the slide-out drawer. */
(function () {
    'use strict';

    function init() {
        var toggle = document.querySelector('.mobile-nav-toggle');
        var drawer = document.getElementById('mobile-drawer');
        var backdrop = document.getElementById('mobile-drawer-backdrop');
        var close = document.querySelector('.mobile-nav-close');

        if (!toggle || !drawer || !backdrop) return;

        function openDrawer() {
            drawer.classList.add('open');
            backdrop.classList.add('open');
            document.body.classList.add('mobile-nav-open');
            toggle.setAttribute('aria-expanded', 'true');
        }

        function closeDrawer() {
            drawer.classList.remove('open');
            backdrop.classList.remove('open');
            document.body.classList.remove('mobile-nav-open');
            toggle.setAttribute('aria-expanded', 'false');
        }

        toggle.addEventListener('click', openDrawer);
        backdrop.addEventListener('click', closeDrawer);
        if (close) close.addEventListener('click', closeDrawer);

        // Close when any drawer link is tapped
        drawer.querySelectorAll('a').forEach(function (a) {
            a.addEventListener('click', closeDrawer);
        });

        // Close on Escape
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && drawer.classList.contains('open')) {
                closeDrawer();
            }
        });

        // Close on resize past breakpoint (avoids drawer being open on desktop after rotating tablet)
        var mq = window.matchMedia('(min-width: 721px)');
        if (mq.addEventListener) {
            mq.addEventListener('change', function (e) {
                if (e.matches) closeDrawer();
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();
