/* TIC Industry Dashboard. Small, dependency-free script, inlined into every page.
   Every screen reads fine without it: filters show everything and all sections stay visible. */
(function () {
  'use strict';

  function all(sel, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(sel));
  }

  /* ----- News screens: filter by company and by type -----
     Each screen keeps its own choice, so the two news screens do not affect each other
     when the one-file build puts them on the same page. */
  all('.screen').forEach(function (screen) {
    var state = { company: 'all', type: 'all' };

    function press(attr, value) {
      all('[' + attr + ']', screen).forEach(function (b) {
        b.setAttribute('aria-pressed', String(b.getAttribute(attr) === value));
      });
    }

    function matches(el) {
      return state.company === 'all' || el.getAttribute('data-company') === state.company;
    }

    function applyFilters() {
      all('[data-filterable]', screen).forEach(function (box) {
        var shown = 0;
        all('[data-company]', box).forEach(function (el) {
          el.hidden = !matches(el);
          if (!el.hidden) { shown += 1; }
        });
        var wrap = box.closest('.table-wrap') || box;
        var msg = wrap.nextElementSibling;
        if (!msg || !msg.hasAttribute('data-none')) {
          msg = document.createElement('p');
          msg.className = 'empty';
          msg.setAttribute('data-none', '');
          msg.textContent = 'Nothing here for this selection.';
          wrap.parentNode.insertBefore(msg, wrap.nextSibling);
        }
        msg.hidden = shown !== 0;
        wrap.hidden = shown === 0;
      });
      var count = 0;
      all('[data-feed] .news-item', screen).forEach(function (el) {
        var ok = matches(el) && (state.type === 'all' || el.getAttribute('data-type') === state.type);
        el.hidden = !ok;
        if (ok) { count += 1; }
      });
      all('[data-month]', screen).forEach(function (m) {
        m.hidden = !m.querySelector('.news-item:not([hidden])');
      });
      all('[data-empty]', screen).forEach(function (e) { e.hidden = count !== 0; });
      all('[data-count]', screen).forEach(function (c) { c.textContent = count + (count === 1 ? ' item' : ' items'); });
    }

    all('[data-filter-company]', screen).forEach(function (b) {
      b.addEventListener('click', function () {
        state.company = b.getAttribute('data-filter-company');
        press('data-filter-company', state.company);
        applyFilters();
      });
    });
    all('[data-filter-type]', screen).forEach(function (b) {
      b.addEventListener('click', function () {
        state.type = b.getAttribute('data-filter-type');
        press('data-filter-type', state.type);
        applyFilters();
      });
    });
  });

  /* ----- Company financials: mark the company in view on the jump bar and in the sidebar ----- */
  var jumps = all('[data-jump]');
  if (jumps.length && 'IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (en) {
        if (!en.isIntersecting) { return; }
        jumps.forEach(function (j) { j.classList.toggle('on', j.getAttribute('data-jump') === en.target.id); });
      });
    }, { rootMargin: '-15% 0px -75% 0px' });
    all('.co').forEach(function (s) { io.observe(s); });
  }

  /* ----- Monthly line chart: read a month off the chart -----
     Moves the cursor group to the month under the pointer and prints its levels.
     The native tooltip is removed once this works, so the two do not show together. */
  all('.chart-svg').forEach(function (svg) {
    var cursor = svg.querySelector('.c-cursor');
    if (!cursor) { return; }
    var rule = cursor.querySelector('line');
    var dots = all('circle', cursor);
    var out = cursor.querySelector('text');
    all('.c-hit', svg).forEach(function (hit) {
      var title = hit.querySelector('title');
      var tip = title ? title.textContent : '';
      if (title) { hit.removeChild(title); }
      var showAt = function () {
        var x = hit.getAttribute('data-x');
        var ys = hit.getAttribute('data-y').split(' ');
        rule.setAttribute('x1', x);
        rule.setAttribute('x2', x);
        dots.forEach(function (dot, i) {
          dot.setAttribute('visibility', ys[i] ? 'inherit' : 'hidden');
          if (ys[i]) { dot.setAttribute('cx', x); dot.setAttribute('cy', ys[i]); }
        });
        out.textContent = tip;
        cursor.setAttribute('visibility', 'visible');
      };
      hit.addEventListener('pointerenter', showAt);
      hit.addEventListener('pointerdown', showAt);
    });
    svg.addEventListener('pointerleave', function () { cursor.setAttribute('visibility', 'hidden'); });
  });

  /* ----- One-file build: show one screen at a time ----- */
  var screens = all('.screen');
  if (document.body.getAttribute('data-mode') === 'single' && screens.length > 1) {
    var base = document.title;

    var show = function (id) {
      var el = id ? document.getElementById(id) : null;
      var screen = el ? el.closest('.screen') : null;
      if (!screen) { screen = screens[0]; el = screen; }
      screens.forEach(function (s) { s.hidden = s !== screen; });
      all('.nav-item').forEach(function (a) {
        if (a.getAttribute('data-screen') === screen.id) {
          a.setAttribute('aria-current', 'page');
          document.title = a.textContent.replace(/^\d+/, '').trim() + ' | ' + base;
        } else {
          a.removeAttribute('aria-current');
        }
      });
      jumps.forEach(function (j) {  // a company stays marked only while its screen is the one shown
        var target = document.getElementById(j.getAttribute('data-jump'));
        if (!target || target.closest('.screen') !== screen) { j.classList.remove('on'); }
      });
      all('.is-target').forEach(function (t) { t.classList.remove('is-target'); });
      if (el === screen) {
        window.scrollTo(0, 0);
      } else {
        el.classList.add('is-target');
        el.scrollIntoView();
      }
    };

    document.addEventListener('click', function (ev) {
      var a = ev.target.closest ? ev.target.closest('a[href^="#"]') : null;
      if (!a) { return; }
      var id = a.getAttribute('href').slice(1);
      var target = id ? document.getElementById(id) : null;
      if (!target || !target.closest('.screen')) { return; }
      ev.preventDefault();
      show(id);
      try { history.pushState(null, '', '#' + id); } catch (e) { /* history can be unavailable in a sandboxed frame */ }
    });
    window.addEventListener('popstate', function () { show(location.hash.slice(1)); });
    show(location.hash.slice(1));
  }
})();
