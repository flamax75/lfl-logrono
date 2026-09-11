/* Crónicas deterministas: solo interpretan league.json y el Salón estático. */
(() => {
  'use strict';
  const validNumber = value => typeof value === 'number' && Number.isFinite(value);
  const record = team => `${team.wins ?? 0}-${team.losses ?? 0}-${team.ties ?? 0}`;
  const historical = (team, champions) => champions.find(champion => champion.champion === team?.name);
  const mention = (team, champions) => {
    const champion = historical(team, champions);
    return champion ? `${team.name}, campeón de ${champion.year}` : team?.name || 'Equipo no disponible';
  };
  function weekChronicle(data, champions) {
    const week = data.weeks.find(item => item.number === data.league.currentWeek);
    const matches = week?.matches.filter(match => match.homeId !== null && match.awayId !== null) || [];
    if (!matches.length) return ['La jornada actual aún no dispone de enfrentamientos publicados por ESPN.'];
    const scored = matches.filter(match => validNumber(match.homePoints) && validNumber(match.awayPoints));
    const lines = [`La jornada ${week.number} reúne ${matches.length} enfrentamiento${matches.length === 1 ? '' : 's'} en Liga Papeo2.`];
    if (scored.length) {
      const closest = [...scored].sort((a, b) => Math.abs(a.homePoints - a.awayPoints) - Math.abs(b.homePoints - b.awayPoints))[0];
      const home = data.teams.find(team => team.id === closest.homeId), away = data.teams.find(team => team.id === closest.awayId);
      lines.push(`${mention(home, champions)} y ${mention(away, champions)} protagonizan por ahora el duelo más ajustado: ${closest.homePoints.toFixed(2)}-${closest.awayPoints.toFixed(2)}.`);
    } else {
      lines.push('Los marcadores todavía no están disponibles; la jornada queda a la espera de los datos reales de ESPN.');
    }
    return lines;
  }
  function standingsChronicle(data) {
    const teams = [...data.teams].sort((a, b) => (a.standing ?? Infinity) - (b.standing ?? Infinity));
    if (!teams.length) return ['La clasificación aún no está disponible.'];
    if (teams.every(team => (team.wins ?? 0) === 0 && (team.losses ?? 0) === 0 && (team.ties ?? 0) === 0)) return ['La clasificación parte con todos los equipos en 0-0-0. ESPN aún no refleja diferencias deportivas en la temporada.'];
    const leader = teams[0], second = teams[1], last = teams.at(-1);
    let text = `${leader.name} lidera Liga Papeo2 con un balance de ${record(leader)} y ${validNumber(leader.pf) ? leader.pf.toFixed(2) : '—'} puntos a favor.`;
    if (second) text += ` ${second.name} ocupa la segunda posición con ${record(second)}.`;
    if (last && last !== leader) text += ` En el otro extremo, ${last.name} figura último con ${record(last)}.`;
    return [text];
  }
  function nextWeek(data, champions) {
    const next = data.weeks.find(week => week.number > data.league.currentWeek);
    if (!next?.matches.length) return { text: 'ESPN aún no ha publicado enfrentamientos para la próxima jornada.', matches: [] };
    const matches = next.matches.filter(match => match.homeId !== null && match.awayId !== null).map(match => ({ home: data.teams.find(team => team.id === match.homeId), away: data.teams.find(team => team.id === match.awayId) }));
    const historicalMatch = matches.find(match => historical(match.home, champions) || historical(match.away, champions));
    return { text: historicalMatch ? `${mention(historicalMatch.home, champions)} se mide a ${mention(historicalMatch.away, champions)} en la próxima jornada.` : '', matches };
  }
  window.editorial = { weekChronicle, standingsChronicle, nextWeek };
})();
