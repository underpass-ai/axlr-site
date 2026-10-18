// Catalog index: search, category and runtime filters, sort, and infinite
// scroll. Every card is in the HTML (all visible without JavaScript); this
// script filters them and reveals the matches PAGE at a time as the reader
// reaches the end of the grid. The query and category live in the URL.
(function () {
  var grid = document.getElementById('cat-grid');
  if (!grid) return;
  var PAGE = 24;
  var cards = Array.prototype.slice.call(grid.querySelectorAll('.tcard'));
  var q = document.getElementById('cat-q');
  var sort = document.getElementById('cat-sort');
  var offline = document.getElementById('cat-offline');
  var progs = Array.prototype.slice.call(document.querySelectorAll('.cat-prog'));
  var filters = Array.prototype.slice.call(document.querySelectorAll('.cat-filter'));
  var count = document.getElementById('cat-count');
  var empty = document.getElementById('cat-empty');
  var category = '';
  var matches = [];
  var shown = 0;

  var sentinel = document.createElement('div');
  sentinel.className = 'cat-sentinel';
  sentinel.setAttribute('aria-hidden', 'true');
  grid.parentNode.insertBefore(sentinel, empty);

  function norm(s) {
    return (s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
  }
  var texts = cards.map(function (c) { return norm(c.getAttribute('data-text')); });

  function sorted(list) {
    var key = sort ? sort.value : 'name';
    return list.slice().sort(function (a, b) {
      var an = a.getAttribute('data-name'), bn = b.getAttribute('data-name');
      if (key === 'category') {
        var ac = a.getAttribute('data-category'), bc = b.getAttribute('data-category');
        if (ac !== bc) return ac < bc ? -1 : 1;
      } else if (key === 'reviewed') {
        var ar = a.getAttribute('data-reviewed'), br = b.getAttribute('data-reviewed');
        if (ar !== br) return ar < br ? 1 : -1;
      }
      return an < bn ? -1 : an > bn ? 1 : 0;
    });
  }

  function reveal() {
    var next = Math.min(matches.length, shown + PAGE);
    for (var i = shown; i < next; i++) matches[i].hidden = false;
    shown = next;
    sentinel.hidden = shown >= matches.length;
  }

  function apply(keepScroll) {
    var terms = norm(q ? q.value : '').split(/\s+/).filter(Boolean);
    var allowed = progs.filter(function (p) { return p.checked; }).map(function (p) { return p.value; });
    matches = [];
    cards.forEach(function (c, i) {
      var ok = (!category || c.getAttribute('data-category') === category) &&
        (!offline || !offline.checked || c.getAttribute('data-network') === '0') &&
        (!progs.length || allowed.indexOf(c.getAttribute('data-program')) !== -1) &&
        terms.every(function (t) { return texts[i].indexOf(t) !== -1; });
      c.hidden = true;
      if (ok) matches.push(c);
    });
    matches = sorted(matches);
    matches.forEach(function (c) { grid.appendChild(c); });
    shown = 0;
    reveal();
    count.textContent = matches.length + (matches.length === 1 ? ' tool' : ' tools') +
      (category ? ' in ' + labelOf(category) : '') + (terms.length ? ' matching “' + q.value.trim() + '”' : '');
    empty.hidden = matches.length !== 0;
    filters.forEach(function (f) {
      f.setAttribute('aria-pressed', f.getAttribute('data-category') === category ? 'true' : 'false');
    });
    var params = new URLSearchParams();
    if (q && q.value.trim()) params.set('q', q.value.trim());
    if (category) params.set('category', category);
    var url = location.pathname + (params.toString() ? '?' + params : '') + location.hash;
    try { history.replaceState(null, '', url); } catch (e) {}
    if (!keepScroll && (terms.length || category)) {
      var top = document.getElementById('all');
      if (top && top.getBoundingClientRect().top < 0) top.scrollIntoView();
    }
  }

  function labelOf(slug) {
    for (var i = 0; i < filters.length; i++) {
      if (filters[i].getAttribute('data-category') === slug) return filters[i].textContent.replace(/\d+\s*$/, '').trim();
    }
    return slug;
  }

  if ('IntersectionObserver' in window) {
    new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting && shown < matches.length) reveal();
    }, { rootMargin: '600px 0px' }).observe(sentinel);
  } else {
    PAGE = 1e6; // no observer: show everything that matches
  }

  var timer;
  if (q) q.addEventListener('input', function () {
    clearTimeout(timer);
    timer = setTimeout(function () { apply(false); }, 120);
  });
  if (q) q.addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { e.preventDefault(); document.getElementById('all').scrollIntoView({ behavior: 'smooth' }); }
  });
  filters.forEach(function (f) {
    f.addEventListener('click', function () { category = f.getAttribute('data-category'); apply(false); });
  });
  [sort, offline].concat(progs).forEach(function (el) {
    if (el) el.addEventListener('change', function () { apply(true); });
  });

  var params = new URLSearchParams(location.search);
  if (q && params.get('q')) q.value = params.get('q');
  if (params.get('category')) category = params.get('category');
  apply(true);
  if (params.get('q') || params.get('category')) document.getElementById('all').scrollIntoView();
})();
