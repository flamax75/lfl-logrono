"""Pruebas aisladas, sin credenciales reales ni peticiones a ESPN."""
import contextlib
import io
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

import fetch_espn as exporter
from serve_local import PublicHandler, ThreadingHTTPServer


def response_data():
    return {'id': exporter.LEAGUE_ID, 'seasonId': exporter.SEASON, 'scoringPeriodId': 2,
            'status': {'currentMatchupPeriod': 2}, 'settings': {},
            'teams': [{'id': 1, 'owners': ['private-member-guid'], 'record': {'overall': {'wins': 0, 'pointsFor': 0}}}, {'id': 2}],
            'members': [{'id': 'private-member-guid', 'displayName': 'Nombre recibido', 'email': 'excluded'}],
            'schedule': [{'id': 99, 'matchupPeriodId': 2, 'home': {'teamId': 1, 'totalPoints': 0}, 'away': {'teamId': 2}}]}


class ExportTests(unittest.TestCase):
    def test_normalize_missing_and_zero(self):
        raw = response_data()
        raw['teams'][0].update({'playoffSeed': 4, 'rankFinal': 2, 'rankCalculatedFinal': 1})
        raw['teams'][0]['record']['overall'].update({'ties': 2, 'pointsAgainst': 3.5, 'percentage': .625, 'gamesBack': 1.0})
        data = exporter.normalize(raw)
        self.assertIsNone(data['teams'][0]['name'])
        self.assertEqual(data['teams'][0]['wins'], 0)
        self.assertEqual(data['teams'][0]['ties'], 2)
        self.assertEqual(data['teams'][0]['pa'], 3.5)
        self.assertEqual(data['teams'][0]['percentage'], .625)
        self.assertEqual(data['teams'][0]['gamesBack'], 1.0)
        self.assertEqual(data['teams'][0]['standing'], 1)
        self.assertEqual(data['teams'][0]['standingSource'], 'rankCalculatedFinal')
        self.assertIsNone(data['teams'][0]['losses'])
        self.assertEqual(data['teams'][0]['owners'], ['Nombre recibido'])
        self.assertNotIn('private-member-guid', json.dumps(data))
        self.assertNotIn('excluded', json.dumps(data))
        match = data['weeks'][0]['matches'][0]
        self.assertEqual(match['id'], 99)
        self.assertEqual(match['homePoints'], 0)
        self.assertIsNone(match['awayPoints'])
        self.assertIsNone(match['homeChance'])

    def test_current_week_uses_live_scores_without_changing_official_record(self):
        raw = response_data()
        raw['schedule'][0]['home'].update({'totalPoints': 99, 'totalPointsLive': 12.34, 'totalProjectedPoints': 110, 'totalProjectedPointsLive': 100})
        data = exporter.normalize(raw)
        team = data['teams'][0]
        match = data['weeks'][0]['matches'][0]
        self.assertEqual(team['wins'], 0)
        self.assertEqual(team['pf'], 0)
        self.assertEqual(match['status'], 'En directo')
        self.assertEqual(match['homePoints'], 12.34)
        self.assertEqual(match['homeProjection'], 100)

    def test_roster_period(self):
        entry = {'playerId': 123, 'lineupSlotId': 20, 'playerPoolEntry': {'player': {'id': 123, 'stats': [
            {'seasonId': 2026, 'scoringPeriodId': 1, 'statSplitTypeId': 1, 'statSourceId': 0, 'appliedTotal': 50},
            {'seasonId': 2026, 'scoringPeriodId': 2, 'statSplitTypeId': 1, 'statSourceId': 0, 'appliedTotal': 0},
            {'seasonId': 2026, 'scoringPeriodId': 2, 'statSplitTypeId': 1, 'statSourceId': 1, 'appliedTotal': 12}]}}}
        player = exporter.roster({'entries': [entry]}, 2)[0]
        self.assertEqual(player['points'], 0)
        self.assertEqual(player['projection'], 12)
        self.assertEqual(player['slot'], 'BN')
        self.assertIsNone(exporter.roster({'entries': [entry]}, 3)[0]['points'])

    def test_views_and_cookie_names(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.read.return_value = '{}'
        opener = MagicMock()
        opener.open.return_value = response
        with patch.object(exporter, 'build_opener', return_value=opener):
            exporter.download('test-only-s2', 'test-only-swid')
        request = opener.open.call_args.args[0]
        self.assertEqual(request.full_url.split('?')[0], 'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/2026/segments/0/leagues/1294118495')
        self.assertEqual(parse_qs(urlsplit(request.full_url).query)['view'], list(exporter.VIEWS))
        self.assertEqual(request.get_header('Cookie'), 'espn_s2=test-only-s2; SWID=test-only-swid')

    def test_401_does_not_echo_response(self):
        opener = MagicMock()
        opener.open.side_effect = HTTPError(exporter.ENDPOINT, 401, 'private response', {}, None)
        with patch.object(exporter, 'build_opener', return_value=opener):
            with self.assertRaisesRegex(exporter.ExportError, 'HTTP 401') as error:
                exporter.download('test-only-s2', 'test-only-swid')
        self.assertNotIn('private response', str(error.exception))

    def test_redirect_blocks_external_cookie_destination(self):
        with self.assertRaises(exporter.ExportError):
            exporter.EspnRedirect().redirect_request(Request(exporter.ENDPOINT), None, 302, '', {}, 'https://example.com/')

    def test_wrong_league(self):
        raw = response_data()
        raw['id'] = -1
        with self.assertRaises(exporter.ExportError):
            exporter.normalize(raw)

    def test_missing_credentials_clears_export(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'league.json'
            with patch.dict(os.environ, {}, clear=True), patch.object(exporter, 'load_env', return_value={}), patch.object(exporter, 'OUTPUT', output), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(exporter.main(), 1)
                self.assertFalse(json.loads(output.read_text(encoding='utf-8'))['available'])

    def test_env_preserves_equals_and_prefers_action_secrets(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / '.env'
            path.write_text('ESPN_S2="test=value=="\nESPN_SWID={test-only}\n', encoding='utf-8-sig')
            with patch.dict(os.environ, {}, clear=True):
                credentials = exporter.load_env(path)
                self.assertEqual(credentials['ESPN_S2'], 'test=value==')
                self.assertEqual(credentials['ESPN_SWID'], '{test-only}')
            with patch.dict(os.environ, {'ESPN_S2': 'action-s2', 'ESPN_SWID': 'action-swid'}, clear=True):
                self.assertEqual(exporter.load_env(path), {'ESPN_S2': 'action-s2', 'ESPN_SWID': 'action-swid'})

    def test_secret_guard_before_write(self):
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / 'league.json'
            with patch.object(exporter, 'OUTPUT', output):
                with self.assertRaises(exporter.ExportError):
                    exporter.save({'unsafe': 'test-only-secret'}, ('test-only-secret',))
                self.assertFalse(output.exists())

    def test_local_server_public_allowlist(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), PublicHandler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f'http://127.0.0.1:{server.server_port}'
        try:
            for path in ('/', '/data/league.json', '/js/app.js', '/assets/images/logo-lfl.png', '/assets/images/logo-papeo2.png'):
                with urlopen(base + path) as response:
                    self.assertEqual(response.status, 200)
                    self.assertEqual(response.headers['Cache-Control'], 'no-store')
                    response.read()
            for path in ('/.env', '/%2eenv', '/.git/config', '/scripts/fetch_espn.py', '/data/../.env'):
                with self.assertRaises(HTTPError) as error:
                    urlopen(base + path)
                self.assertEqual(error.exception.code, 404)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == '__main__':
    unittest.main()
