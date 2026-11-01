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

def test_assistant_and_song_demo():
    client = app.test_client()
    d = client.post('/api/assistant', json={'text': '안녕'}).get_json()
    assert d['answer_ko'] and d['answer_en'] == 'Hi! I am your AI helper. Ask me!'
    assert d['pages'] and d['hardware']['simulated'] is True
    d = client.post('/api/song', json={'text': '반짝반짝 작은 별'}).get_json()
    assert d['found'] is True and d['pages'] == [['Butter - BTS', '']]
    assert client.post('/api/song', json={'text': ''}).status_code == 400

def test_song_not_found_and_errors():
    import server
    saved = (server.guess_song, server.assistant_answer)
    try:
        server.guess_song = lambda t: {"found": False, "title_ko": "", "artist_ko": "", "title_en": "", "artist_en": ""}
        d = app.test_client().post('/api/song', json={'text': 'la la'}).get_json()
        assert d['found'] is False and d['pages'][0][0].startswith('I am not sure')
        def boom(t): raise RuntimeError('AI down')
        server.assistant_answer = boom
        r = app.test_client().post('/api/assistant', json={'text': 'hi'})
        assert r.status_code == 502 and r.get_json()['error'] == 'AI down'
    finally:
        server.guess_song, server.assistant_answer = saved

def test_llm_json_parsing():
    import server
    saved = (server.DEMO, server.llm)
    try:
        server.DEMO = False
        server.llm = lambda *a, **k: {"found": True, "title_en": "Butter", "artist_en": "BTS", "title_ko": "버터"}
        song = server.guess_song("x")
        assert song["found"] is True and song["artist_ko"] == ""
        server.llm = lambda *a, **k: {"found": True, "title_en": ""}
        assert server.guess_song("x")["found"] is False  # no title -> not found
        server.llm = lambda *a, **k: {"ko": "하늘", "en": "A" * 200}
        ko, en = server.assistant_answer("x")
        assert ko == "하늘" and len(en) == 120
        server.llm = lambda *a, **k: {"ko": "", "en": "x"}
        try:
            server.assistant_answer("x"); assert False
        except RuntimeError:
            pass
    finally:
        server.DEMO, server.llm = saved


if __name__=='__main__':
    test_lcd_pages();test_routes();test_browser_mode_and_rate_limit();test_assistant_and_song_demo();test_song_not_found_and_errors();test_llm_json_parsing();print('PASS: wrapping, Flask routes, browser mode, assistant, song, llm parsing')
