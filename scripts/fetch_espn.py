"""Exportacion local ESPN. Python 3.10+, exclusivamente biblioteca estandar."""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'data' / 'league.json'
LEAGUE_ID, SEASON = 1294118495, 2026
ENDPOINT = f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{SEASON}/segments/0/leagues/{LEAGUE_ID}'
VIEWS = ('mTeam', 'mRoster', 'mMatchup', 'mMatchupScore', 'mScoreboard', 'mStandings', 'mSettings', 'mStatus')
POSITIONS = {1: 'QB', 2: 'RB', 3: 'WR', 4: 'TE', 5: 'K', 16: 'D/ST'}
SLOTS = {0: 'QB', 1: 'TQB', 2: 'RB', 3: 'RB/WR', 4: 'WR', 5: 'WR/TE', 6: 'TE', 7: 'OP', 8: 'DT', 9: 'DE', 10: 'LB', 11: 'DL', 12: 'CB', 13: 'S', 14: 'DB', 15: 'DP', 16: 'D/ST', 17: 'K', 18: 'P', 19: 'HC', 20: 'BN', 21: 'IR', 23: 'FLEX', 24: 'EDR', 25: 'Rookie'}


class ExportError(Exception):
    """Mensajes controlados, nunca respuestas, cookies o cabeceras."""


def load_env(path=ROOT / '.env'):
    credentials = {}
    if not path.exists():
        return credentials
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        key, sep, value = line.partition('=')
        key, value = key.strip(), value.strip()
        if sep and key in ('ESPN_S2', 'ESPN_SWID'):
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
                value = value[1:-1]
            credentials[key] = value
    return credentials


class EspnRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if target.scheme != 'https' or target.hostname not in ('fantasy.espn.com', 'lm-api-reads.fantasy.espn.com') or target.port not in (None, 443) or not target.path.startswith('/apis/v3/games/ffl/'):
            raise ExportError('Redireccion fuera de la API ESPN autorizada. No se han reenviado las cookies.')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def download(s2, swid):
    url = ENDPOINT + '?' + urlencode([('view', view) for view in VIEWS])
    # Los nombres HTTP de las cookies son espn_s2 y SWID.
    request = Request(url, headers={'Accept': 'application/json', 'User-Agent': 'LFL-local-export/1.0', 'Cookie': f'espn_s2={s2}; SWID={swid}'})
    try:
        with build_opener(EspnRedirect()).open(request, timeout=30) as response:
            if response.status != 200:
                raise ExportError(f'ESPN ha devuelto HTTP {response.status}.')
            try:
                return json.load(response)
            except (ValueError, UnicodeError):
                raise ExportError('ESPN no ha devuelto JSON valido. Comprueba la sesion y el acceso a la liga.') from None
    except HTTPError as error:
        if error.code == 401:
            raise ExportError('HTTP 401: ESPN no autoriza el acceso. Renueva ESPN_S2 y ESPN_SWID de una cuenta con acceso a esta liga privada.') from None
        if error.code == 403:
            raise ExportError('HTTP 403: ESPN ha denegado el acceso. Comprueba las cookies y la pertenencia a la liga.') from None
        raise ExportError(f'ESPN ha devuelto HTTP {error.code}. No se han descargado datos.') from None
    except (URLError, TimeoutError, OSError):
        raise ExportError('No se ha podido conectar con ESPN. Comprueba la red e intentalo de nuevo.') from None


def numeric(value):
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) else None


def positive_integer(value):
    return value if isinstance(value, int) and not isinstance(value, bool) and value > 0 else None


def text(value):
    return value if isinstance(value, str) and value.strip() else None


def roster(raw, period):
    result = []
    for entry in (raw or {}).get('entries', []):
        pool = entry.get('playerPoolEntry') or {}
        player = pool.get('player') or {}
        player_id = entry.get('playerId', player.get('id'))
        if not isinstance(player_id, int):
            continue
        points = projection = None
        for stat in player.get('stats', []):
            if stat.get('seasonId') == SEASON and stat.get('scoringPeriodId') == period and stat.get('statSplitTypeId') == 1:
                if stat.get('statSourceId') == 0:
                    points = numeric(stat.get('appliedTotal'))
                elif stat.get('statSourceId') == 1:
                    projection = numeric(stat.get('appliedTotal'))
        slot = entry.get('lineupSlotId')
        result.append({'id': player_id, 'name': text(player.get('fullName')), 'proTeamId': player.get('proTeamId'), 'positionId': player.get('defaultPositionId'), 'position': POSITIONS.get(player.get('defaultPositionId')), 'slotId': slot, 'slot': SLOTS.get(slot), 'points': points, 'projection': projection, 'scoringPeriodId': period})
    return result


def normalize(raw):
    if not isinstance(raw, dict) or raw.get('id') != LEAGUE_ID or raw.get('seasonId') != SEASON or not isinstance(raw.get('teams'), list) or not raw['teams']:
        raise ExportError('Respuesta ESPN inesperada: faltan equipos o no corresponde a la liga y temporada solicitadas.')
    status, settings = raw.get('status') or {}, raw.get('settings') or {}
    period = numeric(raw.get('scoringPeriodId'))
    current = numeric(status.get('currentMatchupPeriod'))
    members = {m.get('id'): m for m in raw.get('members', [])}
    teams = []
    for item in raw['teams']:
        if not isinstance(item.get('id'), int):
            raise ExportError('Respuesta ESPN inesperada: equipo sin ID valido.')
        # mStandings entrega aquí el récord oficial de temporada. No se mezcla
        # con los puntos live de los enfrentamientos aún sin cerrar.
        record = (item.get('record') or {}).get('overall') or {}
        rank_calculated = positive_integer(item.get('rankCalculatedFinal'))
        rank_final = positive_integer(item.get('rankFinal'))
        playoff_seed = positive_integer(item.get('playoffSeed'))
        standing = rank_calculated or rank_final or playoff_seed
        standing_source = ('rankCalculatedFinal' if rank_calculated else
                           'rankFinal' if rank_final else
                           'playoffSeed' if playoff_seed else None)
        owners = []
        for owner_id in item.get('owners', []):
            member = members.get(owner_id, {})
            name = ' '.join(filter(None, (text(member.get('firstName')), text(member.get('lastName'))))) or text(member.get('displayName'))
            # No publicar GUID de miembros: puede coincidir con la cookie SWID.
            if name:
                owners.append(name)
        name = text(item.get('name')) or ' '.join(filter(None, (text(item.get('location')), text(item.get('nickname'))))) or None
        teams.append({'id': item['id'], 'name': name, 'abbrev': text(item.get('abbrev')), 'owners': owners, 'wins': numeric(record.get('wins')), 'losses': numeric(record.get('losses')), 'ties': numeric(record.get('ties')), 'pf': numeric(record.get('pointsFor')), 'pa': numeric(record.get('pointsAgainst')), 'percentage': numeric(record.get('percentage')), 'gamesBack': numeric(record.get('gamesBack')), 'standing': standing, 'standingSource': standing_source, 'streakLength': numeric(record.get('streakLength')), 'streakType': text(record.get('streakType')), 'rosterScoringPeriodId': period, 'roster': roster(item.get('roster'), period)})
    known_ids = {t['id'] for t in teams}
    if len(known_ids) != len(teams):
        raise ExportError('Respuesta ESPN inesperada: IDs de equipo duplicados.')
    weeks = {}
    for match in raw.get('schedule', []):
        week = match.get('matchupPeriodId')
        if not isinstance(week, int):
            continue
        sides = [match.get('home') or {}, match.get('away') or {}]
        ids = [side.get('teamId') for side in sides]
        if any(id_ is not None and id_ not in known_ids for id_ in ids):
            raise ExportError('Respuesta ESPN incompleta: un enfrentamiento referencia equipos no recibidos.')
        winner = text(match.get('winner'))
        is_current = week == current
        state = 'Final' if winner in ('HOME', 'AWAY', 'TIE') else 'Programado' if current is not None and week > current else 'En directo' if is_current else 'Sin finalizar'
        result = {'id': match.get('id'), 'week': week, 'homeId': ids[0], 'awayId': ids[1], 'winner': winner, 'status': state, 'playoffTierType': text(match.get('playoffTierType')), 'homeChance': None, 'rosterScoringPeriodId': period if week == current else None}
        for prefix, side in zip(('home', 'away'), sides):
            live_points = numeric(side.get('totalPointsLive'))
            live_projection = numeric(side.get('totalProjectedPointsLive'))
            # En la jornada activa ESPN mantiene totalPoints como récord oficial
            # del matchup hasta el cierre; la pantalla Jornada debe mostrar live.
            result[prefix + 'Points'] = live_points if is_current and live_points is not None else numeric(side.get('totalPoints'))
            result[prefix + 'Projection'] = live_projection if is_current and live_projection is not None else numeric(side.get('totalProjectedPoints'))
            result[prefix + 'Roster'] = roster(side.get('rosterForCurrentScoringPeriod'), period) if is_current else []
            result[prefix + 'LivePoints'] = live_points
            result[prefix + 'LiveProjection'] = live_projection
        weeks.setdefault(week, []).append(result)
    return {'schemaVersion': 1, 'source': 'ESPN', 'available': True, 'updatedAt': datetime.now(timezone.utc).isoformat(), 'league': {'id': raw['id'], 'name': text(settings.get('name')), 'season': raw['seasonId'], 'sport': 'ffl', 'size': len(teams), 'currentWeek': current, 'scoringPeriodId': period, 'scoringType': text((settings.get('scoringSettings') or {}).get('scoringType'))}, 'teams': teams, 'weeks': [{'number': week, 'matches': matches} for week, matches in sorted(weeks.items())]}


def save(data, secrets=()):
    payload = json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + '\n'
    for secret in secrets:
        if secret and (secret in payload or json.dumps(secret, ensure_ascii=False)[1:-1] in payload):
            raise ExportError('Exportacion cancelada: se ha detectado una credencial en los datos procesados.')
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    temporary = OUTPUT.with_suffix('.json.tmp')
    temporary.write_text(payload, encoding='utf-8')
    temporary.replace(OUTPUT)


def unavailable():
    return {'schemaVersion': 1, 'source': 'ESPN', 'available': False, 'updatedAt': None, 'message': 'Datos de ESPN no disponibles', 'league': None, 'teams': [], 'weeks': []}


def main():
    try:
        credentials = load_env()
        s2, swid = (credentials.get(key, '').strip() for key in ('ESPN_S2', 'ESPN_SWID'))
        if not s2 or not swid:
            raise ExportError('Faltan ESPN_S2 y/o ESPN_SWID. Completa el archivo .env local.')
        if any(char in s2 + swid for char in ('\r', '\n', ';')):
            raise ExportError('Formato de cookies no valido. Copia solo sus valores, sin cabeceras ni punto y coma.')
        data = normalize(download(s2, swid))
        save(data, (s2, swid, swid.strip('{}')))
        print('HTTP 200. Guardado data/league.json.')
        print(f"Liga: {data['league']['name']}")
        print(f"Equipos encontrados: {len(data['teams'])}")
        for team in data['teams']:
            print(team['name'] or '(nombre no disponible)')
        return 0
    except (ExportError, OSError, ValueError, TypeError, KeyError, AttributeError) as error:
        try:
            save(unavailable())
        except OSError:
            print('No se ha podido actualizar data/league.json. Comprueba los permisos.', file=sys.stderr)
        print(str(error) if isinstance(error, ExportError) else 'No se ha podido procesar o guardar la respuesta de ESPN.', file=sys.stderr)
        print('Datos de ESPN no disponibles', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
