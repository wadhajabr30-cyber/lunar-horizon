"""Lunar Horizon — standalone website. Run this file in PyCharm. Python 3.10+.
All browser assets are local. Only new ephemerides require NASA/JPL internet access.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
import threading
import time
import webbrowser
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
FRONTEND = ROOT / 'frontend'
CACHE = ROOT / '.cache'
NASA_API = 'https://ssd.jpl.nasa.gov/api/horizons.api'
NASA_LOCK = threading.Lock()
MONTHS = {name: i for i, name in enumerate(('Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'), 1)}

class InputError(ValueError):
    pass

def utc(value: str) -> datetime:
    try:
        d = datetime.fromisoformat(value.replace('Z', '+00:00'))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(timezone.utc)
    except (ValueError, TypeError) as exc:
        raise InputError('Use ISO UTC dates, for example 2026-11-14T00:00Z.') from exc

def validate_query(query: str) -> dict:
    p = parse_qs(query)
    def field(name: str) -> str:
        if len(p.get(name, [])) != 1:
            raise InputError(f'Missing or repeated parameter: {name}.')
        return p[name][0]
    try:
        lat, lon, alt = (float(field(k)) for k in ('lat','lon','alt'))
        raw_step = float(field('step'))
        if not raw_step.is_integer():
            raise InputError('Sampling interval must be a whole number of minutes.')
        step = int(raw_step)
    except ValueError as exc:
        raise InputError(str(exc) if isinstance(exc, InputError) else 'Coordinates and interval must be numbers.') from exc
    if not all(math.isfinite(n) for n in (lat,lon,alt)) or not -90 <= lat <= 90 or not -360 <= lon <= 360 or not -20 <= alt <= 50:
        raise InputError('Coordinates or observer altitude are out of range.')
    start, end = utc(field('start')), utc(field('end'))
    seconds = (end-start).total_seconds()
    if not 2000 <= start.year <= 2050 or not 2000 <= end.year <= 2050 or seconds <= 0 or seconds > 31*86400:
        raise InputError('Choose a positive window of up to 31 days, between 2000 and 2050.')
    if not 10 <= step <= 1440 or seconds/(step*60) > 800:
        raise InputError('Choose a 10–1440 minute interval with at most 800 intervals.')
    return dict(lat=lat,lon=lon,alt=alt,start=start,end=end,step=step)

def parse_table(result: str) -> list[dict]:
    try:
        block = result.split('$$SOE', 1)[1].split('$$EOE', 1)[0]
    except IndexError as exc:
        raise RuntimeError('Horizons did not return a valid observer table.') from exc
    rows = []
    for line in block.strip().splitlines():
        c = [part.strip() for part in line.split(',')]
        try:
            datepart, clock = c[0].split()
            year, month, day = datepart.split('-')
            hour, minute = map(int, clock.split(':')[:2])
            dt = datetime(int(year), MONTHS[month], int(day), hour, minute, tzinfo=timezone.utc)
            values = dict(time=int(dt.timestamp()*1000), az=float(c[3]), el=float(c[4]), diameterArcsec=float(c[5]), distanceKm=float(c[6]))
        except (ValueError, IndexError, KeyError) as exc:
            raise RuntimeError('Horizons returned missing or malformed quantities.') from exc
        if not all(math.isfinite(v) for v in values.values()):
            raise RuntimeError('Horizons returned non-finite values.')
        rows.append(values)
    if not rows:
        raise RuntimeError('Horizons returned no time samples.')
    return rows

def query_url(target: str, p: dict) -> str:
    q = lambda value: "'" + str(value) + "'"
    args = dict(format='json', COMMAND=q(target), OBJ_DATA=q('NO'), MAKE_EPHEM=q('YES'), EPHEM_TYPE=q('OBSERVER'), CENTER=q('coord@301'), COORD_TYPE=q('GEODETIC'), SITE_COORD=q(f"{p['lon'] % 360},{p['lat']},{p['alt']}"), START_TIME=q(p['start'].strftime('%Y-%m-%d %H:%M')), STOP_TIME=q(p['end'].strftime('%Y-%m-%d %H:%M')), STEP_SIZE=q(f"{p['step']} m"), QUANTITIES=q('4,13,20'), CSV_FORMAT=q('YES'), TIME_DIGITS=q('MINUTES'), TIME_TYPE=q('UT'), RANGE_UNITS=q('KM'), APPARENT=q('AIRLESS'), EXTRA_PREC=q('YES'))
    return NASA_API+'?'+urlencode(args)

def ephemeris(p: dict) -> dict:
    key = hashlib.sha256(json.dumps(p, default=str, sort_keys=True).encode()).hexdigest()
    cached = CACHE / f'{key}.json'
    with NASA_LOCK:  # Respect JPL's request-at-a-time policy, including concurrent users.
        if cached.exists() and time.time()-cached.stat().st_mtime < 86400:
            try:
                return json.loads(cached.read_text(encoding='utf-8'))
            except (OSError, ValueError):
                pass
        value = dict(source='NASA/JPL Horizons', fetchedAt=datetime.now(timezone.utc).isoformat(), observer=dict(lat=p['lat'],lon=p['lon'],altitudeKm=p['alt'],body='Moon (301)',frame='Lunar Mean-Earth / DE421-compatible',timeScale='UTC'), stepMinutes=p['step'], queries={})
        for name, target in (('sun','10'),('earth','399')):
            url = query_url(target, p)
            request = Request(url, headers={'Accept':'application/json','User-Agent':'LunarHorizon/1.0'})
            try:
                with urlopen(request, timeout=40) as response:
                    raw = response.read(4_000_000)
                data = json.loads(raw)
            except (HTTPError, URLError, TimeoutError, ValueError, OSError) as exc:
                raise RuntimeError('NASA/JPL Horizons could not be reached. Check internet access, retry, or load the verified example.') from exc
            if data.get('error'):
                raise RuntimeError('Horizons: '+str(data['error'])[:250])
            value[name] = parse_table(data.get('result',''))
            value['queries'][name] = url
            value['signature'] = data.get('signature')
        if [r['time'] for r in value['sun']] != [r['time'] for r in value['earth']]:
            raise RuntimeError('Sun and Earth epochs do not match.')
        try:
            CACHE.mkdir(exist_ok=True)
            temporary = cached.with_suffix('.tmp')
            temporary.write_text(json.dumps(value, separators=(',',':')), encoding='utf-8')
            temporary.replace(cached)
        except OSError:
            pass  # A read-only deployment can still serve a fresh response.
        return value

class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND), **kwargs)
    def end_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('Referrer-Policy','strict-origin-when-cross-origin')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:; worker-src 'self'; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'self'")
        super().end_headers()
    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path == '/api/ephemeris':
            try:
                data, status = ephemeris(validate_query(parsed.query)), 200
            except InputError as exc:
                data, status = {'error':str(exc)}, 400
            except Exception as exc:
                data, status = {'error':str(exc)}, 502
            body = json.dumps(data, separators=(',',':')).encode()
            self.send_response(status)
            self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','private, max-age=300' if status==200 else 'no-store')
            self.end_headers(); self.wfile.write(body)
            return
        if parsed.path == '/api/health':
            body = b'{"status":"ok","application":"Lunar Horizon","auth_required":false}'
            self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
            return
        if parsed.path == '/':
            self.path = '/index.html'
        if parsed.path.endswith('.js'):
            self.extensions_map['.js']='text/javascript'
        if parsed.path.endswith('.json'):
            self.extensions_map['.json']='application/json'
        try:
            return super().do_GET()
        except (BrokenPipeError, ConnectionResetError):
            return None  # Browser canceled a download or navigated away.
    def list_directory(self,path):
        self.send_error(404,'Not found')
        return None

def main():
    parser=argparse.ArgumentParser(description='Run the independent Lunar Horizon website.')
    parser.add_argument('--host',default='127.0.0.1',help='Use 0.0.0.0 only when intentionally exposing the server.')
    parser.add_argument('--port',type=int,default=int(os.environ.get('PORT','8000')))
    parser.add_argument('--no-browser',action='store_true')
    args=parser.parse_args()
    if not FRONTEND.is_dir():
        parser.error('The frontend folder is missing. Extract the entire ZIP first.')
    try:
        server=ThreadingHTTPServer((args.host,args.port),Handler)
    except OSError as exc:
        parser.error(f'Cannot open port {args.port}: {exc}. Try --port 8001.')
    url=f"http://{'127.0.0.1' if args.host=='0.0.0.0' else args.host}:{server.server_port}"
    print(f'\nLUNAR HORIZON\nIndependent 3D lunar explorer\nOpen: {url}\nNo ChatGPT account, no API key, no pip installation.\nNew dates use NASA/JPL Horizons; bundled example works offline.\nPress Ctrl+C to stop.\n',flush=True)
    if not args.no_browser:
        threading.Timer(.7,lambda:webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('\nStopped.')
    finally:
        server.server_close()

if __name__=='__main__':
    main()
