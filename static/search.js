// Header search over Zola's elasticlunr index (search_index.en.json).
(function () {
  var input = document.getElementById('search');
  var list = document.getElementById('search-results');
  if (!input || !list) return;
  var index = null, loading = null, active = -1;

  function load() {
    if (index || loading) return loading;
    loading = fetch('/search_index.en.json')
      .then(function (r) { return r.json(); })
      .then(function (data) { index = elasticlunr.Index.load(data); })
      .catch(function () { loading = null; });
    return loading;
  }
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }
  function snippet(body, terms) {
    var text = (body || '').replace(/\s+/g, ' ');
    var lower = text.toLowerCase(), at = -1;
    for (var i = 0; i < terms.length && at < 0; i++) at = lower.indexOf(terms[i]);
    var start = Math.max(0, at - 60);
    var out = text.substr(start, 180);
    return (start > 0 ? '…' : '') + out + (start + 180 < text.length ? '…' : '');
  }
  function close() { list.hidden = true; input.setAttribute('aria-expanded', 'false'); active = -1; }
  function render(q) {
    if (!index) return;
    q = q.trim();
    if (q.length < 2) { close(); return; }
    var hits = index.search(q, { bool: 'AND', expand: true, fields: { title: { boost: 3 }, description: { boost: 2 }, body: { boost: 1 } } }).slice(0, 8);
    var terms = q.toLowerCase().split(/\s+/);
    if (!hits.length) {
      list.innerHTML = '<li class="r-empty">No page matches “' + esc(q) + '”.</li>';
    } else {
      list.innerHTML = hits.map(function (h) {
        var doc = h.doc;
        return '<li><a href="' + esc(h.ref) + '"><span class="r-title">' + esc(doc.title || h.ref) +
          '</span><span class="r-text">' + esc(snippet(doc.body || doc.description, terms)) + '</span></a></li>';
      }).join('');
    }
    list.hidden = false; input.setAttribute('aria-expanded', 'true'); active = -1;
  }
  function move(step) {
    var links = list.querySelectorAll('a');
    if (!links.length) return;
    if (active >= 0) links[active].classList.remove('active');
    active = (active + step + links.length) % links.length;
    links[active].classList.add('active');
    links[active].scrollIntoView({ block: 'nearest' });
  }
  input.addEventListener('focus', load);
  input.addEventListener('input', function () {
    var q = input.value;
    var p = load();
    if (index) render(q); else if (p) p.then(function () { render(input.value); });
  });
  input.addEventListener('keydown', function (e) {
    if (e.key === 'ArrowDown') { e.preventDefault(); move(1); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); move(-1); }
    else if (e.key === 'Enter') {
      var links = list.querySelectorAll('a');
      var target = links[active >= 0 ? active : 0];
      if (target) { e.preventDefault(); window.location.href = target.href; }
    } else if (e.key === 'Escape') { close(); input.blur(); }
  });
  document.addEventListener('click', function (e) {
    if (!list.contains(e.target) && e.target !== input) close();
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === '/' && document.activeElement !== input && !/^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement.tagName) && !document.activeElement.isContentEditable) {
      e.preventDefault(); input.focus();
    }
  });
})();
