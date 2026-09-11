(() => {
  'use strict';
  let data;
  const $ = id => document.getElementById(id);
  const team = id => data.teams.find(t => t.id === id);
  const name = t => t?.name || 'Nombre no disponible';
  const display = value => value === null || value === undefined ? '—' : String(value);
  const number = value => typeof value === 'number' && Number.isFinite(value) ? value.toFixed(2) : '—';
  // Los datos se insertan exclusivamente como texto, nunca como HTML.
  const el = (tag, className, text) => { const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = text; return node; };
  const append = (parent, ...children) => { parent.append(...children); return parent; };
  const avatar = t => { const node = el('span', 'avatar silver', t?.abbrev || t?.name?.split(/\s+/).map(word => word[0]).slice(0, 2).join('') || '—'); node.setAttribute('aria-hidden', 'true'); return node; };
  const action = (label, className, callback) => { const button = el('button', className, label); button.type = 'button'; button.addEventListener('click', callback); return button; };
  const navItems = [['inicio','Inicio','M3 10 12 3l9 7v11h-6v-7H9v7H3Z'],['jornada','Jornada','M4 5h16v16H4ZM8 2v6m8-6v6M4 11h16'],['clasificacion','Clasificación','M4 21V11h4v10m2 0V3h4v18m2 0V7h4v14'],['equipos','Equipos','M16 21v-3a4 4 0 0 0-8 0v3M12 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8ZM3 20v-3m18 3v-3'],['estadisticas','Estadísticas','M3 3v18h18M6 15l5-5 4 3 6-8'],['salon','Salón','M12 3l2.7 5.5 6.1.9-4.4 4.3 1 6.1-5.4-2.8-5.4 2.8 1-6.1L3.2 9.4l6.1-.9Z']];
  navItems.forEach(([id,label,path]) => {
    const button = action('', 'nav-button', () => { location.hash = id; });
    button.dataset.section = id; button.setAttribute('aria-controls', id);
    const svg = document.createElementNS('http://www.w3.org/2000/svg','svg'); svg.setAttribute('viewBox','0 0 24 24'); svg.setAttribute('aria-hidden','true');
    const p = document.createElementNS(svg.namespaceURI,'path'); p.setAttribute('d',path); svg.append(p);
    append(button, svg, el('span','',label)); $('navigation').append(button);
  });
  let currentSection;
  function navigate(focus = true) {
    const requested = location.hash.slice(1), id = navItems.some(n=>n[0]===requested) ? requested : 'inicio';
    navItems.forEach(([key]) => { $(key).hidden = key !== id; });
    document.querySelectorAll('.nav-button').forEach(button => { if(button.dataset.section === id) button.setAttribute('aria-current','page'); else button.removeAttribute('aria-current'); });
    document.title = `${navItems.find(n=>n[0]===id)[1]} · LFL — Logroño Fútbol League`;
    if (focus && currentSection !== id && $('intro').hidden) { $(`title-${id}`).focus({preventScroll:true}); window.scrollTo(0,0); }
    currentSection = id;
  }
  window.addEventListener('hashchange', () => navigate());
  document.querySelectorAll('[data-go]').forEach(button=>button.addEventListener('click',()=>{location.hash=button.dataset.go;}));

  const unavailable = 'Datos de ESPN no disponibles';
  const empty = (message = unavailable) => el('p', 'panel empty-state', message);
  function probability() {
    return el('p', 'legend', 'Probabilidad de victoria no disponible en los datos de ESPN.');
  }
  function matchCard(match) {
    const button = action('', 'match-card', () => openMatch(match));
    button.setAttribute('aria-label', `Ver jornada ${match.week}: ${name(team(match.homeId))} / ${name(team(match.awayId))}`);
    append(button, append(el('div','card-top'),el('span','',`JORNADA ${match.week}`),el('span','match-status',match.status)));
    [['home',match.homeId],['away',match.awayId]].forEach(([side,id]) => {
      const t = team(id);
      append(button, append(el('div','match-team'), avatar(t),
        append(el('span','team-label'),el('b','',id === null ? 'Sin rival asignado' : name(t)),el('small','',`Proy. ${number(match[side+'Projection'])}`)),
        el('strong','score',number(match[side+'Points']))));
    });
    append(button, probability(), el('span','card-link','Ver enfrentamiento ↗'));
    return button;
  }
  let champions=[];
  const paragraphs = lines => lines.map(line=>el('p','editorial-copy',line));
  function renderEditorial() {
    const current=data.weeks.find(w=>w.number===data.league.currentWeek);
    $('latest-news').replaceChildren(el('p','editorial-copy',current ? `La jornada ${current.number} es la referencia actual de la temporada 2026.` : 'ESPN aún no ha señalado una jornada actual.'));
    $('week-chronicle').replaceChildren(...paragraphs(window.editorial.weekChronicle(data,champions)));
    $('standings-chronicle').replaceChildren(...paragraphs(window.editorial.standingsChronicle(data)));
    const next=window.editorial.nextWeek(data,champions);
    const list=el('div','next-list');
    next.matches.forEach(match=>list.append(el('p','next-match',`${name(match.home)} — ${name(match.away)}`)));
    $('next-week').replaceChildren(...(next.text ? [el('p','editorial-copy',next.text)] : []),list);
  }
  function renderHallOfFame() {
    const table=el('table','hall-table');
    const head=el('thead'), row=el('tr');['AÑO','CAMPEÓN','RÉCORD'].forEach(label=>row.append(el('th','',label)));head.append(row);
    const body=el('tbody');champions.forEach(champion=>{const item=el('tr','hall-row');item.append(el('td','hall-year',String(champion.year)),el('th','',champion.champion),el('td','',champion.record));body.append(item);});
    append(table,head,body);$('hall-of-fame').replaceChildren(table);
  }
  function renderWeek() {
    const week = data.weeks.find(w => String(w.number) === $('week-selector').value);
    $('week-matches').replaceChildren(...(week?.matches.length ? week.matches.map(matchCard) : [empty()]));
  }
  $('week-selector').addEventListener('change',renderWeek);
  function renderStandings() {
    const table=el('table');
    const caption=el('caption','sr-only','Clasificación recibida de ESPN');
    const head=el('thead'), hr=el('tr');
    ['POS','EQUIPO','W','L','PF','PA'].forEach(label => { const cell=el('th','',label);cell.scope='col';hr.append(cell); });head.append(hr);
    const body=el('tbody');
    [...data.teams].sort((a,b)=>(a.standing ?? Infinity)-(b.standing ?? Infinity)).forEach(t => {
      const row=el('tr');row.append(el('td','rank',display(t.standing)));
      const cell=el('th');cell.scope='row';
      cell.append(append(action('','table-team',()=>openTeam(t)),avatar(t),el('span','',name(t))));
      append(row,cell,el('td','',display(t.wins)),el('td','',display(t.losses)),el('td','numeric',number(t.pf)),el('td','numeric',number(t.pa)));body.append(row);
    });
    append(table,caption,head,body);$('standings').replaceChildren(table);
  }
  const owners = t => t.owners?.length ? t.owners.join(' · ') : 'Propietario no disponible';
  function renderTeams() {
    $('teams').replaceChildren(...data.teams.map(t => {
      const card=action('','team-card',()=>openTeam(t));
      append(card,append(el('div','team-card-top'),avatar(t),el('span','card-link','VER EQUIPO ↗')),el('h2','',name(t)),el('p','owner',owners(t)),
        append(el('div','team-metrics'),append(el('div'),el('small','','RÉCORD W–L–T'),el('strong','',`${display(t.wins)} – ${display(t.losses)} – ${display(t.ties)}`)),
        append(el('div'),el('small','','PUNTOS TOTALES'),el('strong','',number(t.pf)))));
      return card;
    }));
  }
  function stat(label,value,description) {
    return append(el('article','panel stat'),el('p','eyebrow',label),el('h2','',value),el('p','muted',description));
  }
  function renderStats() {
    // No se calculan premios ni rankings a partir de datos parciales.
    const labels=['POWER RANKING','MVP DE LA SEMANA','MAYOR PALIZA','PARTIDO MÁS AJUSTADO','MÁS PUNTOS EN EL BANQUILLO','MÁXIMA PUNTUACIÓN'];
    const cards=labels.map(label=>stat(label,'—',unavailable));
    const streaks=data.teams.filter(t=>t.streakLength !== null && ['WIN','LOSS','TIE'].includes(t.streakType));
    const streak=append(el('article','panel stat'),el('p','eyebrow','RACHA ACTUAL'));
    if (!streaks.length) streak.append(el('p','muted',unavailable));
    streaks.forEach(t=>streak.append(el('p','profile-summary',`${name(t)} · ${t.streakLength} ${({WIN:'victorias',LOSS:'derrotas',TIE:'empates'})[t.streakType]}`)));
    $('stats').replaceChildren(...cards,streak);
  }
  const dialog=$('detail');let previousFocus;
  function showDetail(...nodes) {
    previousFocus=document.activeElement;$('detail-content').replaceChildren(...nodes);
    $('detail-content').querySelector('h2').id='detail-title';
    dialog.showModal();document.body.classList.add('modal-open');$('close-detail').focus();
  }
  function lineup(t,players,period) {
    const box=el('div','lineup');
    append(box,append(el('h3','lineup-title'),avatar(t),el('span','',name(t))));
    if (!players?.length) { box.append(empty('Alineación de ESPN no disponible para este periodo.')); return box; }
    append(box,el('p','legend',`Periodo de puntuación ESPN: ${display(period)}`),
      append(el('div','player-row player-head'),el('span','','POS'),el('span','','JUGADOR'),el('span','','PTS'),el('span','','PROY.')));
    players.forEach(p => append(box,append(el('div','player-row'),el('span','position',p.slot || display(p.slotId)),
      append(el('span','player-name'),el('b','',p.name || 'Nombre no disponible'),el('small','',p.position || 'Posición no disponible')),
      el('strong','',number(p.points)),el('span','muted',number(p.projection)))));
    return box;
  }
  function openMatch(m) {
    showDetail(el('h2','dialog-title',`${name(team(m.homeId))} / ${m.awayId === null ? 'Sin rival asignado' : name(team(m.awayId))}`),
      el('p','muted',`Jornada ${m.week} · ${m.status} · ${number(m.homePoints)} – ${number(m.awayPoints)}`),probability(),
      append(el('div','lineups'),lineup(team(m.homeId),m.homeRoster,m.rosterScoringPeriodId),lineup(team(m.awayId),m.awayRoster,m.rosterScoringPeriodId)));
  }
  function openTeam(t) {
    showDetail(append(el('div','profile-heading'),avatar(t),append(el('div'),el('h2','dialog-title',name(t)),el('p','muted',owners(t)))),
      el('p','profile-summary',`${display(t.wins)} W · ${display(t.losses)} L · ${display(t.ties)} T · ${number(t.pf)} PF · ${number(t.pa)} PA`),
      lineup(t,t.roster,t.rosterScoringPeriodId));
  }
  $('close-detail').addEventListener('click',()=>dialog.close());
  dialog.addEventListener('click',event=>{if(event.target===dialog){const r=dialog.getBoundingClientRect();if(event.clientX<r.left||event.clientX>r.right||event.clientY<r.top||event.clientY>r.bottom)dialog.close();}});
  dialog.addEventListener('close',()=>{document.body.classList.remove('modal-open');previousFocus?.focus();});
  function showUnavailable() {
    ['latest-news','week-chronicle','standings-chronicle','next-week','week-matches','standings','teams','stats'].forEach(id=>$(id).replaceChildren(empty()));
    $('week-selector').replaceChildren(el('option','','Sin jornadas disponibles'));$('week-selector').disabled=true;
    $('data-status').textContent=unavailable;
    $('data-notice').textContent=location.protocol === 'file:' ? 'Abre la web con el servidor local para cargar data/league.json.' : 'No se han podido actualizar los datos de ESPN.';
  }
  function updateDataNotice(updatedAt) {
    const date=new Date(updatedAt);
    if (Number.isNaN(date.getTime())) { $('data-notice').textContent='Datos ESPN actualizados: hora no disponible'; return; }
    const time=date.toLocaleTimeString('es-ES',{hour:'2-digit',minute:'2-digit'});
    const stale=Date.now()-date.getTime()>15*60*1000;
    $('data-notice').textContent=`Datos ESPN actualizados: ${time}${stale ? ' · Datos posiblemente desactualizados' : ''}`;
  }
  async function load(initial = false) {
    if (initial) $('data-status').textContent='Cargando ESPN…';
    try {
      const nextData=await window.loadLeague();
      if (!initial && data?.updatedAt === nextData.updatedAt) { updateDataNotice(data.updatedAt); return; }
      const selectedWeek=$('week-selector').value;
      data=nextData;
      const current=data.weeks.find(w=>w.number===data.league.currentWeek);
      $('week-selector').replaceChildren(...data.weeks.map(w=>{const o=el('option','',`Jornada ${w.number}`);o.value=w.number;return o;}));
      $('week-selector').disabled=!data.weeks.length;
      if (data.weeks.some(w=>String(w.number)===selectedWeek)) $('week-selector').value=selectedWeek;
      else if(current) $('week-selector').value=String(current.number);
      renderEditorial();renderWeek();renderStandings();renderTeams();renderStats();
      document.querySelectorAll('[data-current-week]').forEach(node=>{node.textContent=display(data.league.currentWeek);});
      $('team-count').textContent=`${data.teams.length} EQUIPOS · UNA LIGA`;
      $('data-status').textContent='DATOS DE ESPN';
      updateDataNotice(data.updatedAt);
    } catch {
      showUnavailable();
    }
  }
  navigate(false);
  window.loadHallOfFame().then(items=>{champions=items;renderHallOfFame();if(data)renderEditorial();}).catch(()=>{$('hall-of-fame').replaceChildren(empty('Salón de la Fama no disponible.'));});
  load(true);
  window.setInterval(()=>load(false),60000);
  const intro=$('intro');const reduced=window.matchMedia('(prefers-reduced-motion: reduce)');let finished=false;
  intro.hidden=false;$('app').inert=true;document.body.classList.add('intro-open');$('enter').focus({preventScroll:true});
  function endIntro(){if(finished)return;finished=true;clearTimeout(introTimer);intro.classList.add('leaving');$('app').inert=false;document.body.classList.remove('intro-open');$(`title-${currentSection}`).focus({preventScroll:true});setTimeout(()=>{intro.hidden=true;},reduced.matches?0:450);}
  const introTimer=setTimeout(endIntro,reduced.matches?1500:7000);$('enter').addEventListener('click',endIntro);intro.addEventListener('keydown',event=>{if(event.key==='Escape')endIntro();if(event.key==='Tab'){event.preventDefault();$('enter').focus();}});
  // Activación solo en HTTPS, sin caché de aplicación ni interceptación de red.
  if('serviceWorker' in navigator && location.protocol==='https:' && !['localhost','127.0.0.1','[::1]'].includes(location.hostname)) navigator.serviceWorker.register('./service-worker.js',{updateViaCache:'none'}).catch(()=>{ /* La web sigue funcionando sin instalación. */ });
})();
