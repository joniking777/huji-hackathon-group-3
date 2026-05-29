/**
 * AISecutity Tracker v2 — High-fidelity bot detection.
 * 
 * Improvements over v1:
 * - Sends first batch quickly (after 3 events or 2s, whichever first)
 * - Collects scroll, mouse, hover, visibility, idle events
 * - Adaptive batching: 2s initial, then 5s
 * - Proper throttling that still captures human behavior patterns
 * - Records real timestamps so detection engine sees natural human timing
 */
(function() {
  'use strict';

  var script = document.currentScript;
  var API_KEY = script.getAttribute('data-api-key') || '';
  var ENDPOINT = script.getAttribute('data-endpoint') || 'http://localhost:5000/api/sdk/track';

  // Session — persists across page loads in same tab
  var SESSION_ID = sessionStorage.getItem('_aisec_sid') || generateId();
  sessionStorage.setItem('_aisec_sid', SESSION_ID);

  var events = [];
  var hasSentFirstBatch = false;
  var sessionStartTime = Date.now();

  // Mouse state
  var lastMouseX = -1, lastMouseY = -1, lastMouseTime = 0;
  var mousePoints = []; // for curve detection

  // Keyboard state
  var lastKeyTime = 0, keyBurst = 0, keyErrors = 0, keyTotal = 0;

  // Scroll state
  var scrollY = window.scrollY || 0;
  var lastScrollTime = 0;

  // Activity tracking
  var lastActivityTime = Date.now();

  function generateId() {
    return 'sess-' + Date.now() + '-' + Math.random().toString(36).substr(2, 9);
  }

  function record(eventType, data) {
    events.push({
      sessionId: SESSION_ID,
      userId: API_KEY,
      timestamp: new Date().toISOString(),
      eventType: eventType,
      endpoint: window.location.pathname,
      durationMs: data.duration || 0,
      mouse: data.mouse || null,
      keyboard: data.keyboard || null,
      scroll: data.scroll || null
    });

    // Send first batch as soon as we have 3+ events
    if (!hasSentFirstBatch && events.length >= 3) {
      hasSentFirstBatch = true;
      sendBatch();
    }
  }

  // ============================================================
  // NAVIGATION — immediate on page load
  // ============================================================
  record('navigation', {
    duration: 0,
    scroll: {
      scrollY: 0,
      deltaY: 0,
      viewportHeight: window.innerHeight,
      pageHeight: document.documentElement.scrollHeight
    }
  });

  // ============================================================
  // MOUSE MOVE — 150ms throttle, 15px minimum distance
  // This gives ~6-7 events/sec while moving, which is realistic
  // ============================================================
  var moveThrottle = 0;
  document.addEventListener('mousemove', function(e) {
    var now = Date.now();
    lastActivityTime = now;

    if (now - moveThrottle < 150) return;
    moveThrottle = now;

    var dx = e.clientX - lastMouseX;
    var dy = e.clientY - lastMouseY;
    var dist = Math.sqrt(dx * dx + dy * dy);
    var dt = now - lastMouseTime;

    // Keep last 5 points for curve detection
    mousePoints.push({ x: e.clientX, y: e.clientY, t: now });
    if (mousePoints.length > 5) mousePoints.shift();

    if (dist > 15 && dt > 100) {
      var speed = dt > 0 ? Math.min(dist / (dt / 1000), 2000) : 0;
      var hasCurve = detectCurve();

      record('mousemove', {
        duration: dt,
        mouse: { x: e.clientX, y: e.clientY, speed: Math.round(speed), hasCurve: hasCurve }
      });

      lastMouseX = e.clientX;
      lastMouseY = e.clientY;
      lastMouseTime = now;
    }
  });

  function detectCurve() {
    if (mousePoints.length < 3) return false;
    var p1 = mousePoints[mousePoints.length - 3];
    var p2 = mousePoints[mousePoints.length - 2];
    var p3 = mousePoints[mousePoints.length - 1];
    var cross = Math.abs(
      (p2.x - p1.x) * (p3.y - p1.y) - (p3.x - p1.x) * (p2.y - p1.y)
    );
    return cross > 40;
  }

  // ============================================================
  // CLICK
  // ============================================================
  document.addEventListener('click', function(e) {
    var now = Date.now();
    lastActivityTime = now;
    var hesitation = lastMouseTime > 0 ? now - lastMouseTime : 500;

    record('click', {
      duration: hesitation,
      mouse: { x: e.clientX, y: e.clientY, speed: 0, hasCurve: true }
    });
    lastMouseTime = now;
  });

  // ============================================================
  // SCROLL — 200ms throttle (captures smooth scrolling well)
  // ============================================================
  var scrollThrottle = 0;
  document.addEventListener('scroll', function() {
    var now = Date.now();
    lastActivityTime = now;

    if (now - scrollThrottle < 200) return;
    var dt = now - scrollThrottle;
    scrollThrottle = now;

    var newScrollY = window.scrollY || document.documentElement.scrollTop;
    var deltaY = newScrollY - scrollY;

    if (Math.abs(deltaY) > 5) {
      var velocity = dt > 0 ? Math.abs(deltaY) / (dt / 1000) : 0;
      record('scroll', {
        duration: dt,
        mouse: { x: lastMouseX, y: lastMouseY, speed: Math.round(velocity), hasCurve: true },
        scroll: {
          scrollY: Math.round(newScrollY),
          deltaY: Math.round(deltaY),
          viewportHeight: window.innerHeight,
          pageHeight: document.documentElement.scrollHeight
        }
      });
    }
    scrollY = newScrollY;
    lastScrollTime = now;
  });

  // Wheel events — captures individual scroll ticks
  var lastWheelTime = 0;
  document.addEventListener('wheel', function(e) {
    var now = Date.now();
    lastActivityTime = now;

    if (now - lastWheelTime < 250) return;
    lastWheelTime = now;

    record('scroll', {
      duration: now - lastScrollTime,
      mouse: { x: e.clientX, y: e.clientY, speed: Math.abs(Math.round(e.deltaY * 2)), hasCurve: true },
      scroll: {
        scrollY: Math.round(window.scrollY || 0),
        deltaY: Math.round(e.deltaY),
        viewportHeight: window.innerHeight,
        pageHeight: document.documentElement.scrollHeight
      }
    });
    lastScrollTime = now;
  }, { passive: true });

  // ============================================================
  // KEYBOARD — every 3 keystrokes
  // ============================================================
  document.addEventListener('keydown', function(e) {
    var now = Date.now();
    lastActivityTime = now;
    var dt = now - lastKeyTime;
    keyTotal++;

    if (dt < 500) keyBurst++;
    else keyBurst = 1;

    if (e.key === 'Backspace' || e.key === 'Delete') keyErrors++;

    if (keyTotal % 3 === 0 && lastKeyTime > 0) {
      record('keypress', {
        duration: dt,
        keyboard: {
          interKeyDelayMs: dt,
          burstLength: keyBurst,
          errorRate: keyTotal > 0 ? Math.round((keyErrors / keyTotal) * 100) / 100 : 0
        }
      });
    }
    lastKeyTime = now;
  });

  // ============================================================
  // PASTE
  // ============================================================
  document.addEventListener('paste', function(e) {
    lastActivityTime = Date.now();
    var pastedText = (e.clipboardData || window.clipboardData).getData('text');
    var len = pastedText ? pastedText.length : 0;
    if (len > 0) {
      record('paste', {
        duration: 0,
        keyboard: { interKeyDelayMs: 0, burstLength: len, errorRate: 0 }
      });
    }
  });

  // ============================================================
  // HOVER on interactive elements (humans hover before clicking)
  // ============================================================
  var lastHoverTarget = null, hoverStart = 0;
  document.addEventListener('mouseover', function(e) {
    var target = e.target.closest('a, button, [onclick], input, .product-card');
    if (target && target !== lastHoverTarget) {
      // Record previous hover duration
      if (lastHoverTarget && hoverStart) {
        var dur = Date.now() - hoverStart;
        if (dur > 150 && dur < 5000) {
          record('hover', {
            duration: dur,
            mouse: { x: e.clientX, y: e.clientY, speed: 0, hasCurve: true }
          });
        }
      }
      lastHoverTarget = target;
      hoverStart = Date.now();
    }
  });

  // ============================================================
  // VISIBILITY — tab switches (humans do this, bots don't)
  // ============================================================
  document.addEventListener('visibilitychange', function() {
    record('visibility', {
      duration: Date.now() - lastActivityTime,
      mouse: { x: lastMouseX, y: lastMouseY, speed: 0, hasCurve: !document.hidden }
    });
  });

  // ============================================================
  // IDLE — humans pause to read (record every 3s of inactivity)
  // ============================================================
  setInterval(function() {
    var idle = Date.now() - lastActivityTime;
    if (idle >= 3000 && idle < 15000) {
      record('idle', {
        duration: idle,
        mouse: { x: lastMouseX, y: lastMouseY, speed: 0, hasCurve: false }
      });
      lastActivityTime = Date.now();
    }
  }, 3500);

  // ============================================================
  // BATCH SENDING — 2s for first 3 batches, then 5s
  // ============================================================
  var batchCount = 0;

  function scheduleBatch() {
    var interval = batchCount < 3 ? 2000 : 5000;
    setTimeout(function() {
      sendBatch();
      batchCount++;
      scheduleBatch();
    }, interval);
  }

  function sendBatch() {
    if (events.length === 0) return;

    var payload = {
      apiKey: API_KEY,
      sessionId: SESSION_ID,
      userAgent: navigator.userAgent,
      url: window.location.href,
      events: events.splice(0, events.length)
    };

    fetch(ENDPOINT, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true
    }).then(function(resp) {
      return resp.json();
    }).then(function(data) {
      console.log('[AISecutity v2] Sent', data.received, 'events. Total:', data.totalEvents, '| Score:', data.score, '| Bot:', data.isBot);
    }).catch(function(err) {
      console.warn('[AISecutity v2] Send failed:', err.message);
    });
  }

  scheduleBatch();

  // ============================================================
  // FLUSH on page exit
  // ============================================================
  function flushEvents() {
    if (events.length === 0) return;
    var payload = {
      apiKey: API_KEY,
      sessionId: SESSION_ID,
      userAgent: navigator.userAgent,
      url: window.location.href,
      events: events.splice(0, events.length)
    };
    var blob = new Blob([JSON.stringify(payload)], { type: 'application/json' });
    if (navigator.sendBeacon) {
      navigator.sendBeacon(ENDPOINT, blob);
    } else {
      var xhr = new XMLHttpRequest();
      xhr.open('POST', ENDPOINT, false);
      xhr.setRequestHeader('Content-Type', 'application/json');
      xhr.send(JSON.stringify(payload));
    }
  }

  window.addEventListener('beforeunload', flushEvents);
  window.addEventListener('pagehide', flushEvents);
  document.addEventListener('click', function(e) {
    var link = e.target.closest ? e.target.closest('a[href]') : null;
    if (link && link.href && !link.href.startsWith('javascript:') && !link.href.startsWith('#')) {
      flushEvents();
    }
  }, true);

  console.log('[AISecutity v2] Tracker loaded. Session:', SESSION_ID, '| Endpoint:', ENDPOINT);
})();
