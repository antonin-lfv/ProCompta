// ProCompta Onboarding Tour
window.ProComptaTour = (function () {
  const STORAGE_KEY = 'procompta-tour-state';
  const DONE_KEY    = 'procompta-tour-done';
  const PAD         = 10;
  const POP_W       = 340;

  const STEPS = [
    {
      anchor: null,
      position: 'center',
      page: '/',
      exact: true,
      navigate: null,
      title: 'Bienvenue dans ProCompta',
      text: 'Votre espace comptable 100 % local et privé. Aucune donnée ne quitte votre machine. Laissez-nous vous guider en 2 minutes.',
    },
    {
      anchor: 'aside',
      position: 'right',
      page: '/',
      exact: true,
      navigate: null,
      title: 'La navigation',
      text: 'Le menu latéral donne accès à toutes les sections de l\'application. Il se replie automatiquement pour libérer de l\'espace.',
    },
    {
      anchor: '#tour-stats',
      position: 'bottom',
      page: '/',
      exact: true,
      navigate: null,
      title: 'Tableau de bord',
      text: 'Vos chiffres clés en un coup d\'œil : dépenses, recettes, solde net et TVA pour l\'exercice fiscal en cours.',
    },
    {
      anchor: '#tour-btn-add',
      position: 'bottom',
      page: '/',
      exact: true,
      navigate: null,
      title: 'Importer un document',
      text: 'Glissez-déposez un ou plusieurs fichiers PDF ou image n\'importe où - sur n\'importe quelle page - ou cliquez ici pour une sélection classique. L\'import multi-fichiers est pris en charge.',
    },
    {
      anchor: '#tour-year-header',
      position: 'bottom',
      page: '/year/',
      exact: false,
      navigate: 'YEAR',
      title: 'Vue annuelle',
      text: 'Vous êtes dans l\'exercice en cours - chaque année a son propre onglet dans le menu. Filtrez, triez et sélectionnez en masse. L\'export FEC se fait depuis l\'onglet Rapports ou via le bouton <strong>Bilan</strong> de cette vue.',
    },
    {
      anchor: '#tour-reports-header',
      position: 'bottom',
      page: '/reports',
      exact: true,
      navigate: '/reports',
      title: 'Rapports & TVA',
      text: 'Bilan mensuel, répartition par type et suivi TVA trimestriel. Exportez vos données en CSV ou générez le <strong>fichier FEC</strong> pour votre déclaration fiscale.',
    },
    {
      anchor: '#tour-config-header',
      position: 'bottom',
      page: '/config',
      exact: true,
      navigate: '/config',
      title: 'Configuration',
      text: 'Créez vos correspondants (clients, fournisseurs), types de documents et tags personnalisés avant de saisir vos premières factures.',
    },
    {
      anchor: '#tour-automations-header',
      position: 'bottom',
      page: '/automations',
      exact: true,
      navigate: '/automations',
      title: 'Automatisations Gmail',
      text: 'Connectez Gmail pour importer automatiquement vos factures reçues par email, et configurez des rappels intelligents.',
    },
    {
      anchor: '#tour-notif-bell',
      position: 'bottom',
      anyPage: true,
      navigate: null,
      title: 'Notifications & raccourcis',
      text: 'Vos alertes arrivent ici : documents incomplets, rappels, imports. Tapez <kbd style="padding:1px 5px;border-radius:4px;background:#f1f5f9;border:1px solid #e2e8f0;color:#475569;font-size:11px;font-family:monospace;">?</kbd> n\'importe quand pour voir les raccourcis clavier.',
      isLast: true,
    },
  ];

  let _idx    = 0;
  let _active = false;

  // ── Storage ─────────────────────────────────────────────────────────────

  function _getState() {
    try { return JSON.parse(localStorage.getItem(STORAGE_KEY)); } catch { return null; }
  }
  function _setState(s) { localStorage.setItem(STORAGE_KEY, JSON.stringify(s)); }
  function _clearState() { localStorage.removeItem(STORAGE_KEY); }
  function _isDone() { return !!localStorage.getItem(DONE_KEY); }
  function _markDone() { localStorage.setItem(DONE_KEY, '1'); _clearState(); }

  // ── Helpers ──────────────────────────────────────────────────────────────

  function _path() { return window.location.pathname; }

  function _pathMatches(step) {
    if (step.anyPage) return true;
    return step.exact ? _path() === step.page : _path().startsWith(step.page);
  }

  function _yearUrl() {
    const link = document.querySelector('aside a[href^="/year/"]');
    return link ? link.getAttribute('href') : '/year/' + new Date().getFullYear();
  }

  function _resolveUrl(step) {
    if (!step.navigate) return null;
    return step.navigate === 'YEAR' ? _yearUrl() : step.navigate;
  }

  function _el(id) { return document.getElementById(id); }

  // ── SVG Spotlight ────────────────────────────────────────────────────────

  function _updateSpotlight(el) {
    const hole = _el('tour-spotlight-hole');
    const ring = _el('tour-ring');
    if (!hole) return;

    if (!el) {
      hole.setAttribute('width', '0');
      hole.setAttribute('height', '0');
      if (ring) { ring.setAttribute('width', '0'); ring.setAttribute('height', '0'); }
      return;
    }

    const r = el.getBoundingClientRect();
    const x = Math.round(r.left - PAD);
    const y = Math.round(r.top  - PAD);
    const w = Math.round(r.width  + PAD * 2);
    const h = Math.round(r.height + PAD * 2);

    hole.setAttribute('x', x); hole.setAttribute('y', y);
    hole.setAttribute('width', w); hole.setAttribute('height', h);

    if (ring) {
      ring.setAttribute('x', x); ring.setAttribute('y', y);
      ring.setAttribute('width', w); ring.setAttribute('height', h);
    }
  }

  // ── Popover positioning ──────────────────────────────────────────────────

  function _positionPopover(el, position) {
    const pop   = _el('tour-popover');
    const arrow = _el('tour-arrow');
    if (!pop) return;

    const GAP = 16;
    const vw  = window.innerWidth;
    const vh  = window.innerHeight;

    pop.style.transform = '';
    if (arrow) {
      arrow.style.cssText = 'position:absolute;width:12px;height:12px;background:white;transform:rotate(45deg);';
    }

    if (!el || position === 'center') {
      pop.style.top  = '50%';
      pop.style.left = '50%';
      pop.style.transform = 'translate(-50%, -50%)';
      if (arrow) arrow.style.display = 'none';
      return;
    }

    if (arrow) arrow.style.display = '';

    const popH = pop.offsetHeight || 220;
    const r    = el.getBoundingClientRect();
    const ex   = r.left - PAD;
    const ey   = r.top  - PAD;
    const ew   = r.width  + PAD * 2;
    const eh   = r.height + PAD * 2;
    const ecx  = ex + ew / 2;
    const ecy  = ey + eh / 2;

    let top, left, side;

    if (position === 'bottom') {
      top  = ey + eh + GAP;
      left = Math.min(Math.max(ecx - POP_W / 2, 12), vw - POP_W - 12);
      side = 'top';
      if (top + popH > vh - 12) { top = ey - GAP - popH; side = 'bottom'; }
    } else if (position === 'top') {
      top  = ey - GAP - popH;
      left = Math.min(Math.max(ecx - POP_W / 2, 12), vw - POP_W - 12);
      side = 'bottom';
      if (top < 12) { top = ey + eh + GAP; side = 'top'; }
    } else if (position === 'right') {
      left = ex + ew + GAP;
      top  = Math.min(Math.max(ecy - popH / 2, 12), vh - popH - 12);
      side = 'left';
      if (left + POP_W > vw - 12) { left = ex - GAP - POP_W; side = 'right'; }
    } else {
      left = ex - GAP - POP_W;
      top  = Math.min(Math.max(ecy - popH / 2, 12), vh - popH - 12);
      side = 'right';
    }

    pop.style.top  = top  + 'px';
    pop.style.left = left + 'px';

    // Arrow placement
    if (arrow) {
      const half = 6;
      if (side === 'top') {
        const ax = Math.min(Math.max(ecx - left - half, 20), POP_W - 40);
        Object.assign(arrow.style, { top: (-half) + 'px', left: ax + 'px',
          borderTop: '1px solid #e2e8f0', borderLeft: '1px solid #e2e8f0' });
      } else if (side === 'bottom') {
        const ax = Math.min(Math.max(ecx - left - half, 20), POP_W - 40);
        Object.assign(arrow.style, { bottom: (-half) + 'px', left: ax + 'px',
          borderBottom: '1px solid #e2e8f0', borderRight: '1px solid #e2e8f0' });
      } else if (side === 'left') {
        const ay = Math.min(Math.max(ecy - top - half, 20), popH - 40);
        Object.assign(arrow.style, { left: (-half) + 'px', top: ay + 'px',
          borderBottom: '1px solid #e2e8f0', borderLeft: '1px solid #e2e8f0' });
      } else {
        const ay = Math.min(Math.max(ecy - top - half, 20), popH - 40);
        Object.assign(arrow.style, { right: (-half) + 'px', top: ay + 'px',
          borderTop: '1px solid #e2e8f0', borderRight: '1px solid #e2e8f0' });
      }
    }
  }

  // ── Render step ──────────────────────────────────────────────────────────

  function _renderStep(idx) {
    const step  = STEPS[idx];
    _idx = idx;
    _setState({ idx });

    const total = STEPS.length;

    // Progress bar
    const bar = _el('tour-progress');
    if (bar) {
      bar.style.width = ((idx + 1) / total * 100) + '%';
    }

    // Step count
    const cnt = _el('tour-step-count');
    if (cnt) cnt.textContent = (idx + 1) + ' / ' + total;

    // Title & text
    const titleEl = _el('tour-title');
    if (titleEl) titleEl.textContent = step.title;

    const textEl = _el('tour-text');
    if (textEl) textEl.innerHTML = step.text;

    // Dots
    const dotsEl = _el('tour-dots');
    if (dotsEl) {
      dotsEl.innerHTML = '';
      STEPS.forEach((_, i) => {
        const d = document.createElement('div');
        d.style.cssText = 'border-radius:9999px;transition:all 0.25s;flex-shrink:0;height:6px;background:' +
          (i === idx ? '#6366f1' : '#cbd5e1') + ';width:' + (i === idx ? '20px' : '6px');
        dotsEl.appendChild(d);
      });
    }

    // Next button + skip button visibility
    const nextBtn = _el('tour-next-btn');
    const skipBtn = _el('tour-skip-btn');
    if (nextBtn) {
      if (step.isLast) {
        nextBtn.innerHTML =
          'Terminer&nbsp;<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" style="width:12px;height:12px;display:inline-block;vertical-align:middle"><path stroke-linecap="round" stroke-linejoin="round" d="m4.5 12.75 6 6 9-13.5"/></svg>';
      } else {
        nextBtn.innerHTML =
          'Suivant&nbsp;<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="2.5" stroke="currentColor" style="width:12px;height:12px;display:inline-block;vertical-align:middle"><path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5"/></svg>';
      }
    }
    if (skipBtn) skipBtn.style.display = step.isLast ? 'none' : '';

    // Find & spotlight element
    const el = step.anchor ? document.querySelector(step.anchor) : null;
    _updateSpotlight(el);
    _positionPopover(el, step.position);

    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' });
      setTimeout(() => { _updateSpotlight(el); _positionPopover(el, step.position); }, 350);
    }
  }

  // ── Show / Hide ──────────────────────────────────────────────────────────

  function _show() {
    const root = _el('tour-root');
    if (!root) return;
    root.style.display = 'block';
    root.offsetHeight; // force reflow
    root.style.opacity = '1';
  }

  function _hide(cb) {
    const root = _el('tour-root');
    if (!root) { cb && cb(); return; }
    root.style.opacity = '0';
    setTimeout(() => { root.style.display = 'none'; cb && cb(); }, 220);
  }

  // ── Public API ───────────────────────────────────────────────────────────

  function end() {
    _active = false;
    _hide(() => _markDone());
  }

  function next() {
    const ni = _idx + 1;
    if (ni >= STEPS.length) { end(); return; }

    const ns = STEPS[ni];
    if (!_pathMatches(ns)) {
      _setState({ idx: ni });
      window.location.href = _resolveUrl(ns) || ns.page;
      return;
    }
    _renderStep(ni);
  }

  function start(fromIdx) {
    fromIdx = (fromIdx === undefined) ? 0 : fromIdx;
    if (fromIdx === 0 && _path() !== '/') {
      _setState({ idx: 0 });
      window.location.href = '/';
      return;
    }
    _active = true;
    _show();
    _renderStep(fromIdx);
  }

  // ── Init ─────────────────────────────────────────────────────────────────

  document.addEventListener('DOMContentLoaded', function () {
    // Wire buttons
    _el('tour-next-btn')  ?.addEventListener('click', next);
    _el('tour-skip-btn')  ?.addEventListener('click', end);
    _el('tour-close-btn') ?.addEventListener('click', end);

    // Resize handler
    window.addEventListener('resize', function () {
      if (!_active) return;
      const step = STEPS[_idx];
      const el   = step.anchor ? document.querySelector(step.anchor) : null;
      _updateSpotlight(el);
      _positionPopover(el, step.position);
    });

    // Resume in-progress tour or auto-start on first visit
    const state = _getState();
    if (state && typeof state.idx === 'number') {
      const step = STEPS[state.idx];
      if (!step) { _clearState(); return; }
      if (_pathMatches(step)) {
        _active = true;
        _show();
        _renderStep(state.idx);
      } else {
        window.location.href = _resolveUrl(step) || step.page;
      }
    } else if (!_isDone() && _path() === '/') {
      setTimeout(function () { start(0); }, 900);
    }
  });

  return { start: start, end: end, next: next };
})();
