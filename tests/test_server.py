import os
os.environ['DEMO_MODE']='1'
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from server import app, lcd_pages

def test_lcd_pages():
    for content in ['Hello!', 'Where is the nearest railway station?', 'supercalifragilisticexpialidocious', '', 'Café déjà vu!']:
        pages = lcd_pages(content)
        assert pages and all(len(row)==2 and all(len(s)<=16 for s in row) for row in pages)

def test_routes():
    client = app.test_client()
    assert client.get('/').status_code == 200
    assert client.post('/api/lcd-test').status_code == 200
    data=client.post('/api/translate', json={'text':'안녕하세요','style':'standard'}).get_json()
    assert data['english']=='Hello!'
    assert data['hardware']['simulated'] is True
    assert client.post('/api/translate',json={'text':''}).status_code==400

def test_browser_mode_and_rate_limit(monkeypatch=None):
    import server
    saved = (server.DEMO, server.BROWSER_SERIAL, server.RATE_PER_MIN, server.DAILY_LIMIT, server.translate)
    try:
        server.DEMO, server.BROWSER_SERIAL = False, True
        server.RATE_PER_MIN, server.DAILY_LIMIT = 2, 3
        server.recent_hits.clear(); server.daily.update(day="", count=0)
        server.translate = lambda text, style: "Hello!"
        client = app.test_client()
        assert client.get('/api/status').get_json()['browser'] is True
        d = client.post('/api/translate', json={'text': '안녕'}).get_json()
        assert d['hardware']['browser'] is True and d['pages'] == [["Hello!", ""]]
        assert client.post('/api/translate', json={'text': '안녕'}).status_code == 200
        assert client.post('/api/translate', json={'text': '안녕'}).status_code == 429  # per-minute cap
        server.recent_hits.clear()
        assert client.post('/api/translate', json={'text': '안녕'}).status_code == 200  # 3rd of day
        server.recent_hits.clear()
        assert client.post('/api/translate', json={'text': '안녕'}).status_code == 429  # daily cap
    finally:
        server.DEMO, server.BROWSER_SERIAL, server.RATE_PER_MIN, server.DAILY_LIMIT, server.translate = saved

if __name__=='__main__':
    test_lcd_pages();test_routes();test_browser_mode_and_rate_limit();print('PASS: wrapping, Flask routes, browser mode')
