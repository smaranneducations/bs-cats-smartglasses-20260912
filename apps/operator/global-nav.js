(() => {
  if (document.querySelector('#global-nav')) return;
  const local = ['127.0.0.1', 'localhost'].includes(location.hostname);
  const publicView = location.pathname.startsWith('/discover');
  const adminLinks = [
    ['/operator', 'Workflow'],
    ['/operator#agents', 'Agents'],
    ['/intelligence#knowledge', 'Data'],
    ['/operator#ontology', 'Ontology'],
    ['/#content', 'Create'],
    ['/#review', 'Decisions'],
    ['/#learning', 'Learning'],
    ['/discover?preview=1', 'Audience']
  ];
  const publicLinks = [
    ['/discover?preview=1', 'Discover'],
    ['/intelligence#comparison', 'Compare'],
    ['#visual-sources', 'Image sources']
  ];
  const links = publicView ? [...publicLinks, ...(local ? [['/operator', 'Local admin']] : [])] : adminLinks;
  const current = href => {
    const [path, hash = ''] = href.split('#');
    if (path && path !== location.pathname) return false;
    return !hash || location.hash === `#${hash}`;
  };
  const style = document.createElement('style');
  style.textContent = `
    #global-nav{position:fixed;z-index:1000;top:12px;right:14px;font-family:"Avenir Next","Gill Sans",sans-serif}
    #global-nav *{box-sizing:border-box}
    .global-nav-trigger{height:40px;padding:0 15px;border:1px solid #fff5;border-radius:99px;background:#111116;color:#fff;box-shadow:0 8px 26px #0004;font-size:11px;font-weight:900;letter-spacing:.12em;cursor:pointer}
    .global-nav-panel{position:absolute;top:48px;right:0;width:min(310px,calc(100vw - 28px));padding:12px;border:1px solid #ffffff38;border-radius:20px;background:#111116f5;color:#fff;box-shadow:0 24px 70px #0008;backdrop-filter:blur(20px)}
    .global-nav-panel[hidden]{display:none}
    .global-nav-head{display:flex;align-items:center;justify-content:space-between;padding:7px 8px 12px;border-bottom:1px solid #fff2}
    .global-nav-head b{font-size:11px;letter-spacing:.14em;text-transform:uppercase}
    .global-nav-head span{font-size:9px;color:#aaa;text-transform:uppercase}
    .global-nav-links{display:grid;grid-template-columns:1fr 1fr;gap:6px;padding-top:10px}
    .global-nav-links a{display:flex;align-items:center;min-height:45px;padding:10px 12px;border-radius:12px;color:#d7d6d1;text-decoration:none;font-size:12px;font-weight:800}
    .global-nav-links a:hover,.global-nav-links a.current{background:#c9ff38;color:#111116}
    .global-nav-foot{margin:9px 5px 2px;color:#92918d;font-size:9px;line-height:1.35}
    @media(max-width:680px){#global-nav{top:10px;right:10px}.global-nav-trigger{height:38px;padding:0 12px}.global-nav-panel{position:fixed;top:58px;right:10px}.global-nav-links{grid-template-columns:1fr}}
  `;
  document.head.append(style);
  const nav = document.createElement('div');
  nav.id = 'global-nav';
  nav.innerHTML = `<button class="global-nav-trigger" aria-expanded="false" aria-controls="global-nav-panel">MENU</button><nav class="global-nav-panel" id="global-nav-panel" hidden><div class="global-nav-head"><b>${publicView ? 'Audience experience' : 'Operator workspace'}</b><span>${local ? 'Local preview' : 'Public'}</span></div><div class="global-nav-links">${links.map(([href,label]) => `<a href="${href}" class="${current(href) ? 'current' : ''}">${label}</a>`).join('')}</div><p class="global-nav-foot">Routine work is automatic. Decisions appear only for consequential exceptions and exact publication.</p></nav>`;
  document.body.append(nav);
  const trigger = nav.querySelector('.global-nav-trigger');
  const panel = nav.querySelector('.global-nav-panel');
  trigger.addEventListener('click', () => {
    panel.hidden = !panel.hidden;
    trigger.setAttribute('aria-expanded', String(!panel.hidden));
  });
  nav.addEventListener('click', event => {
    const link = event.target.closest('a[href="#visual-sources"]');
    if (!link) return;
    event.preventDefault();
    panel.hidden = true;
    trigger.setAttribute('aria-expanded', 'false');
    document.querySelector('#openSources')?.click();
  });
  document.addEventListener('click', event => {
    if (!nav.contains(event.target)) {
      panel.hidden = true;
      trigger.setAttribute('aria-expanded', 'false');
    }
  });
})();
