/* UpScale cookie consent — Google Consent Mode v2.
 *
 * GA4 (gtag.js) loads on every page view in a "denied" state by default, which
 * sends anonymous cookieless pings to Google. Google uses these to model the
 * unconsented portion of traffic, so GA4 reports stay realistic even when most
 * visitors never touch the banner. On Accept we upgrade consent to "granted"
 * and also fire up Vercel Web Analytics + Speed Insights.
 *
 * On Reject (or no choice) NO cookies are stored — only cookieless modelling
 * pings — which keeps the setup UK-GDPR / PECR compliant.
 */
(function () {
    'use strict';

    var STORAGE_KEY = 'upscale-cookie-consent';
    var GA4_ID = 'G-JEHSHTGVQW';

    // -- gtag bootstrap (runs IMMEDIATELY, before consent UI / before any user choice) --
    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () { window.dataLayer.push(arguments); };

    // 1. Set Consent Mode v2 defaults BEFORE loading gtag.js
    //    All denied by default = no cookies stored, only anonymous cookieless pings.
    //    wait_for_update gives the banner ~500ms to update consent before the first hit fires.
    window.gtag('consent', 'default', {
        ad_storage: 'denied',
        ad_user_data: 'denied',
        ad_personalization: 'denied',
        analytics_storage: 'denied',
        functionality_storage: 'granted',  // strictly necessary, no consent needed
        security_storage: 'granted',       // strictly necessary, no consent needed
        wait_for_update: 500
    });

    // 2. If the visitor previously accepted, upgrade consent BEFORE the first ping
    //    so they get fully attributed pageviews on this load too.
    try {
        if (localStorage.getItem(STORAGE_KEY) === 'accept') {
            window.gtag('consent', 'update', {
                ad_storage: 'granted',
                ad_user_data: 'granted',
                ad_personalization: 'granted',
                analytics_storage: 'granted'
            });
        }
    } catch (e) { /* localStorage blocked — stay denied */ }

    // 3. Load gtag.js + fire the page_view (cookieless if denied, full if granted)
    (function loadGtag() {
        if (window.__ga4Loaded) return;
        var s = document.createElement('script');
        s.async = true;
        s.src = 'https://www.googletagmanager.com/gtag/js?id=' + GA4_ID;
        document.head.appendChild(s);
        window.gtag('js', new Date());
        window.gtag('config', GA4_ID, {
            // url_passthrough lets ad-click ids survive even when ad_storage is denied
            url_passthrough: true,
            // anonymized IP, lighter ping in denied state
            ads_data_redaction: true
        });
        window.__ga4Loaded = true;
    })();

    // -- Storage helpers --
    function safeGet() {
        try { return localStorage.getItem(STORAGE_KEY); } catch (e) { return null; }
    }
    function safeSet(value) {
        try { localStorage.setItem(STORAGE_KEY, value); } catch (e) {}
    }
    function safeRemove() {
        try { localStorage.removeItem(STORAGE_KEY); } catch (e) {}
    }

    // -- Consent transitions --
    function grantConsent() {
        window.gtag('consent', 'update', {
            ad_storage: 'granted',
            ad_user_data: 'granted',
            ad_personalization: 'granted',
            analytics_storage: 'granted'
        });

        // Load Vercel Web Analytics (cookieless but still gated to keep the banner promise)
        if (!window.__vercelInsightsLoaded) {
            window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
            var s2 = document.createElement('script');
            s2.defer = true;
            s2.src = '/_vercel/insights/script.js';
            document.head.appendChild(s2);
            window.__vercelInsightsLoaded = true;
        }

        // Load Vercel Speed Insights
        if (!window.__vercelSpeedLoaded) {
            window.si = window.si || function () { (window.siq = window.siq || []).push(arguments); };
            var s3 = document.createElement('script');
            s3.defer = true;
            s3.src = '/_vercel/speed-insights/script.js';
            document.head.appendChild(s3);
            window.__vercelSpeedLoaded = true;
        }
    }

    function denyConsent() {
        window.gtag('consent', 'update', {
            ad_storage: 'denied',
            ad_user_data: 'denied',
            ad_personalization: 'denied',
            analytics_storage: 'denied'
        });
    }

    // -- Banner UI --
    function hideBanner(banner) {
        if (banner) banner.classList.add('hidden');
    }

    function init() {
        var banner = document.getElementById('cookie-banner');
        var consent = safeGet();

        // Already accepted: load Vercel analytics, hide banner.
        // (GA4 consent was already upgraded in the bootstrap above.)
        if (consent === 'accept') {
            grantConsent();
            hideBanner(banner);
            return;
        }

        // Already rejected: hide banner, GA4 stays in denied/cookieless mode.
        if (consent === 'reject') {
            hideBanner(banner);
            return;
        }

        // First visit: show banner.
        if (banner) banner.classList.remove('hidden');

        var acceptBtn = document.getElementById('cookie-accept');
        var rejectBtn = document.getElementById('cookie-reject');

        if (acceptBtn) {
            acceptBtn.addEventListener('click', function () {
                safeSet('accept');
                hideBanner(banner);
                grantConsent();
            });
        }

        if (rejectBtn) {
            rejectBtn.addEventListener('click', function () {
                safeSet('reject');
                hideBanner(banner);
                denyConsent();
            });
        }
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // Public API so /legal#cookies can let users change their mind.
    window.UpscaleCookies = {
        currentConsent: function () { return safeGet(); },
        accept: function () { safeSet('accept'); grantConsent(); },
        reject: function () { safeSet('reject'); denyConsent(); },
        reset: function () { safeRemove(); window.location.reload(); }
    };
})();
