"""Disposable loopback Daphne smoke/load check. Never uses the application DB.

Run with the project's virtualenv Python. Results are local measurements, not
DigitalOcean/MySQL/Redis/SMS/CDN capacity claims. No live SMS is sent.
"""
import concurrent.futures
import json
import math
import os
from pathlib import Path
import socket
import statistics
import subprocess
import sys
import tempfile
import time


ROOT = Path(__file__).resolve().parents[1]


def percentile(values, fraction):
    return sorted(values)[max(0, math.ceil(len(values) * fraction) - 1)]


def main(output=None):
    if 'django' in sys.modules:
        raise RuntimeError('Run in a fresh process; never reuse deployment settings.')
    output = Path(output).resolve() if output is not None else ROOT / '.local-data' / 'pilot-readiness'
    output.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='pilot-load-', dir=output) as temporary:
        folder = Path(temporary).resolve()
        database = folder / 'test-only.sqlite3'
        config = folder / 'pilot_load_settings.py'
        config.write_text(
            'from jobportal.test_settings import *\n'
            f"DATABASES = {{'default': {{'ENGINE': 'django.db.backends.sqlite3', 'NAME': {str(database)!r}, "
            f"'TEST': {{'NAME': {str(database)!r}}}, 'OPTIONS': {{'timeout': 30}}}}}}\n"
            f"MEDIA_ROOT = {str(folder / 'media')!r}\n"
            f"STATIC_ROOT = {str(folder / 'static')!r}\n"
            f"NEWS_IDENTITY_ROOT = {str(folder / 'identities')!r}\n"
            f"NEWSDESK_MEDIA_ROOT = {str(folder / 'news')!r}\n"
            f"CHAT_PRIVATE_ROOT = {str(folder / 'chat')!r}\n"
            "ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']\n"
            "SESSION_COOKIE_SECURE = False\nCSRF_COOKIE_SECURE = False\n"
            "PASSWORD_HASHERS = ['django.contrib.auth.hashers.PBKDF2PasswordHasher']\n"
            "SECURE_SSL_REDIRECT = False\nDEBUG = False\n",
            encoding='utf-8',
        )
        sys.path[:0] = [str(folder), str(ROOT)]
        os.environ['DJANGO_SETTINGS_MODULE'] = 'pilot_load_settings'
        import django
        django.setup()
        from django.conf import settings
        from django.db import connection
        from django.test import Client
        from django.test.utils import CaptureQueriesContext, setup_databases
        if Path(connection.settings_dict['NAME']).resolve() != database or not database.is_relative_to(folder):
            raise RuntimeError('Refusing any database outside this disposable test directory.')
        setup_databases(verbosity=0, interactive=False)
        with connection.cursor() as cursor:
            cursor.execute('PRAGMA journal_mode=WAL')
        fixtures, sessions, conversations = seed()
        paths = ['/', '/products/', '/products/?q=Pilot', fixtures['product'],
                 fixtures['shop'], '/advertise/', '/news/', '/news/api/stories/',
                 '/flicks/', '/messages/', '/account/']
        query_counts = {}
        browser = Client()
        browser.force_login(fixtures['reader'])
        for path in paths:
            with CaptureQueriesContext(connection) as captured:
                response = browser.get(path)
            if response.status_code != 200:
                raise RuntimeError(f'Fixture smoke failed: {path}: {response.status_code}')
            query_counts[path] = len(captured)
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
        base = f'http://127.0.0.1:{port}'
        environment = {**os.environ, 'PYTHONPATH': os.pathsep.join([str(folder), str(ROOT), os.environ.get('PYTHONPATH', '')]),
                       'PYTHONDONTWRITEBYTECODE': '1'}
        log_path = output / 'daphne-load.log'
        with log_path.open('w', encoding='utf-8') as server_log:
            server = subprocess.Popen(
                [sys.executable, '-B', '-c', 'from daphne.cli import CommandLineInterface; CommandLineInterface.entrypoint()', '-b', '127.0.0.1', '-p', str(port),
                 'jobportal.asgi:application'], cwd=ROOT, env=environment,
                stdout=server_log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
            )
            try:
                import requests
                deadline = time.monotonic() + 25
                while True:
                    if server.poll() is not None:
                        raise RuntimeError('Disposable Daphne failed to start; see its log.')
                    try:
                        if requests.get(base + '/', timeout=1).status_code == 200:
                            break
                    except requests.RequestException:
                        pass
                    if time.monotonic() > deadline:
                        raise RuntimeError('Disposable Daphne readiness timed out.')
                    time.sleep(.2)
                stages = []
                for users in (1, 10, 25, 50):
                    started = time.perf_counter()
                    with concurrent.futures.ThreadPoolExecutor(max_workers=users) as pool:
                        batches = list(pool.map(lambda i: visit(base, paths, sessions[i], conversations[i]), range(users)))
                    elapsed = time.perf_counter() - started
                    entries = [entry for batch in batches for entry in batch]
                    latencies = [entry['ms'] for entry in entries]
                    stages.append({'concurrent_users': users, 'requests': len(entries),
                        'elapsed_seconds': round(elapsed, 2), 'requests_per_second': round(len(entries) / elapsed, 2),
                        'median_ms': round(statistics.median(latencies), 1),
                        'p95_ms': round(percentile(latencies, .95), 1),
                        'max_ms': round(max(latencies), 1),
                        'errors': [entry for entry in entries if not entry['ok']],
                        'by_path': {path: {'requests': sum(e['path'] == path for e in entries),
                            'p95_ms': round(percentile([e['ms'] for e in entries if e['path'] == path], .95), 1)}
                            for path in dict.fromkeys(e['path'] for e in entries)}})
                    print(json.dumps({k: v for k, v in stages[-1].items() if k != 'by_path'}), flush=True)
                import importlib.metadata
                result = {'scope': 'Local Windows Python/Daphne; disposable SQLite WAL; synthetic fixtures; loopback HTTP',
                    'versions': {'python': sys.version.split()[0], 'django': django.get_version(),
                                 'daphne': importlib.metadata.version('daphne')},
                    'limitations': ['Not DigitalOcean or the proposed 2GB CPU/RAM limit',
                        'No Nginx, TLS, MySQL, Redis, Spaces, real SMS, or browser rendering',
                        'No image/video/static transfers, WebSocket soak or internet latency',
                        'Closed concurrent bursts with minimal think time; not daily user traffic'],
                    'fixtures': {'shops': 10, 'products': 30, 'news': 10, 'readers': 50},
                    'query_counts': query_counts, 'stages': stages}
                (output / 'load-results.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
            finally:
                server.terminate()
                try:
                    server.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    server.kill()
                    server.wait(timeout=5)
        connection.close()


def seed():
    from django.contrib.auth.hashers import make_password
    from django.test import Client
    from jobs.models import CompanyProfile, Conversation, District, LocalOffer, PinCode, Product, State, User
    from newsdesk.models import NewsItem
    state = State.objects.create(name='Disposable pilot state', code='PLOAD')
    district = District.objects.create(name='Disposable pilot district', state=state)
    pin = PinCode.objects.create(code='604408', district=district, area_name='Vandavasi')
    first_shop = first_product = None
    password_hash = make_password('disposable-load-fixture-only')
    for index in range(10):
        owner = User.objects.create(username=f'pilot-owner-{index}', first_name='Pilot Owner',
            user_type='shop', pincode=pin.code, password=password_hash)
        shop = CompanyProfile.objects.create(user=owner, company_name=f'Pilot Shop {index}')
        for item in range(3):
            product = Product.objects.create(shop=shop, name=f'Pilot Product {index}-{item}',
                price='199.00', discount_percent=10, image='products/synthetic.png')
            first_product = first_product or product
        LocalOffer.objects.create(owner=owner, business_name=shop.company_name,
                                  title=f'Pilot offer {index}', discount_text='10%', is_active=True)
        NewsItem.objects.create(author=owner, pincode=pin, title=f'Pilot news {index}',
                                body='Disposable local news fixture.', status='published')
        first_shop = first_shop or shop
    sessions, conversations, first_reader = [], [], None
    for index in range(50):
        reader = User.objects.create(username=f'pilot-reader-{index}', first_name='Pilot Reader',
                                     user_type='individual', pincode=pin.code, password=password_hash)
        client = Client()
        client.force_login(reader)
        sessions.append(client.cookies['sessionid'].value)
        conversations.append(Conversation.objects.create(user_a=first_shop.user, user_b=reader).pk)
        first_reader = first_reader or reader
    return {'reader': first_reader, 'product': first_product.get_absolute_url(),
            'shop': first_shop.get_absolute_url()}, sessions, conversations


def visit(base, paths, session_id, conversation):
    import requests
    session = requests.Session()
    session.cookies.set('sessionid', session_id, domain='127.0.0.1', path='/')
    session.headers['User-Agent'] = 'LOCALFROM disposable pilot check'
    entries = []
    try:
        for path in paths + ['/messages/send/']:
            start = time.perf_counter()
            try:
                if path == '/messages/send/':
                    response = session.post(base + path, data={'conv_id': conversation, 'content': 'Disposable pilot message'},
                        headers={'X-CSRFToken': session.cookies.get('csrftoken', ''), 'Referer': base + '/messages/'},
                        allow_redirects=False, timeout=30)
                    ok = response.status_code == 200 and response.json().get('ok') is True
                else:
                    response = session.get(base + path, allow_redirects=False, timeout=30)
                    ok = response.status_code == 200
                entries.append({'path': path, 'status': response.status_code, 'ok': ok,
                                'ms': round((time.perf_counter() - start) * 1000, 2)})
            except (requests.RequestException, ValueError) as error:
                entries.append({'path': path, 'status': type(error).__name__, 'ok': False,
                                'ms': round((time.perf_counter() - start) * 1000, 2)})
            time.sleep(.05)
    finally:
        session.close()
    return entries


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', help='Directory for disposable fixtures and result logs')
    main(parser.parse_args().output)
