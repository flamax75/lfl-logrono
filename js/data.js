/* Solo lee la exportación local. Las credenciales nunca llegan al navegador. */
(() => {
  'use strict';
  window.loadLeague = async () => {
    const response = await fetch(`./data/league.json?ts=${Date.now()}`, { cache: 'no-store', credentials: 'omit' });
    if (!response.ok) throw new Error('Datos de ESPN no disponibles');
    const data = await response.json();
    if (data.schemaVersion !== 1 || data.source !== 'ESPN' || data.available !== true ||
        typeof data.updatedAt !== 'string' || Number.isNaN(new Date(data.updatedAt).getTime()) ||
        !data.league || !Array.isArray(data.teams) || !data.teams.length || !Array.isArray(data.weeks)) {
      throw new Error('Datos de ESPN no disponibles');
    }
    const ids = new Set(data.teams.map(t => t.id));
    if (ids.size !== data.teams.length || data.teams.some(t => !Number.isInteger(t.id) || !Array.isArray(t.roster)) ||
        data.weeks.some(w => !Number.isInteger(w.number) || !Array.isArray(w.matches) || w.matches.some(m =>
          (m.homeId !== null && !ids.has(m.homeId)) || (m.awayId !== null && !ids.has(m.awayId))))) {
      throw new Error('Datos de ESPN no disponibles');
    }
    return data;
  };
})();
