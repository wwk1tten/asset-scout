"""무료(상업 이용 가능) 배경 이미지·3D 모델을 연관어 목록으로 검색해 받아 둔다.

  python3 find_assets.py <출력폴더> "red moon:1.0" "night sky:0.8" ... [--top 12] [--models 3] [--3d 12]

- 연관어 확장(sky → cloud, sunset …)과 가중치는 사람이나 AI 에이전트가 정해서 넘긴다(.claude/skills/find-assets).
- 2D: Openverse(여러 사이트 통합, 라이선스 commercial+modification 만). 세로·고해상도 우선.
- 3D: Poly Haven 모델(CC0, glTF). 태그·이름이 연관어와 맞는 것.
- 로그인이 필요한 곳(Unity Asset Store, CGTrader, TurboSquid, Free3D, Sketchfab)은 받지 않고 검색 링크만 적는다.
결과: <출력폴더>/img_XX.jpg, model_XX/…, candidates.json(출처·작가·라이선스·점수)
"""
import json
import time
import os
import sys
import urllib.parse
import urllib.request

UA = {'User-Agent': 'asset-scout/0.1'}
try:  # python.org 맥 파이썬은 기본 인증서가 없는 경우가 있다 → certifi 가 있으면 쓴다
    import certifi, ssl
    CTX = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    CTX = None
LINK_ONLY = {
    'Unity Asset Store': 'https://assetstore.unity.com/search#q={q}&free=true',
    'CGTrader': 'https://www.cgtrader.com/free-3d-models?keywords={q}',
    'TurboSquid': 'https://www.turbosquid.com/Search/3D-Models/free/{q}',
    'Free3D': 'https://free3d.com/3d-models/{q}',
    'Sketchfab': 'https://sketchfab.com/search?features=downloadable&q={q}&type=models',
}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30, context=CTX) as r:
        return r.read()


def score(text, terms):
    t = text.lower()
    return sum(w for term, w in terms if term.lower() in t)


def images(terms, top):
    seen, out = set(), []
    for term, w in terms:
        q = urllib.parse.urlencode({'q': term, 'license_type': 'commercial,modification', 'size': 'large', 'page_size': 20,
                                   'excluded_source': 'wikimedia'})  # 위키미디어는 대량 다운로드를 429/424 로 막는다
        try:
            res = json.loads(get('https://api.openverse.org/v1/images/?' + q))['results']
        except Exception as e:  # 한 사이트가 막혀도 나머지는 계속
            print('openverse 실패', term, e)
            continue
        for r in res:
            if r['id'] in seen or not r.get('width') or not r.get('height'):
                continue
            seen.add(r['id'])
            text = ' '.join([r.get('title') or ''] + [t['name'] for t in r.get('tags') or []])
            tall = r['height'] / r['width']
            s = score(text, terms) + w + (0.5 if tall >= 1 else 0) + (0.3 if r['height'] >= 1600 else 0)
            out.append({'kind': 'image', 'score': round(s, 2), 'title': r.get('title'), 'url': r['url'], 'thumb': r.get('thumbnail'), 'creator': r.get('creator'),
                        'license': f"{r['license']} {r.get('license_version') or ''}".strip(), 'source': r.get('source'), 'page': r.get('foreign_landing_url')})
    return sorted(out, key=lambda c: -c['score'])[:top]


def models(terms, top):
    try:
        allm = json.loads(get('https://api.polyhaven.com/assets?t=models'))
    except Exception as e:
        print('polyhaven 실패', e)
        return []
    out = []
    for mid, m in allm.items():
        s = score(' '.join([m.get('name', '')] + m.get('tags', []) + m.get('categories', [])), terms)
        if s > 0:
            out.append({'kind': 'model', 'score': round(s, 2), 'title': m.get('name'), 'id': mid, 'creator': ', '.join(m.get('authors', {}).keys()),
                        'license': 'CC0', 'source': 'polyhaven', 'page': f'https://polyhaven.com/a/{mid}'})
    return sorted(out, key=lambda c: -c['score'])[:top]


def secret(name):
    """키: 환경변수(POLYPIZZA_KEY / SKETCHFAB_TOKEN) 또는 .secrets/<name> 파일(한 줄)"""
    env = os.environ.get(name.upper())
    if env:
        return env.strip()
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.secrets', name)
    return open(p).read().strip() if os.path.exists(p) else None


def models3d(terms, top):
    """Poly Pizza(키 필요)·Sketchfab(검색은 키 없이, 다운로드는 토큰) — 썸네일로 비교표, 원본은 고른 것만"""
    out, key = [], secret('polypizza_key')
    for term, w in terms:
        if key:
            try:
                for r in json.loads(get_h(f'https://api.poly.pizza/v1/search/{urllib.parse.quote(term)}?Limit=12', {'x-auth-token': key}))['results']:
                    lic = 'CC0' if 'publicdomain' in r.get('Attribution', '').lower() or 'cc0' in r.get('Attribution', '').lower() else 'CC-BY'
                    out.append({'kind': 'model3d', 'site': 'polypizza', 'score': round(score(r['Title'] + ' ' + (r.get('Description') or ''), terms) + w + (0.3 if lic == 'CC0' else 0), 2),
                                'title': r['Title'], 'thumb': r['Thumbnail'], 'url': r['Download'], 'creator': r['Creator']['Username'], 'license': lic,
                                'credit': r.get('Attribution'), 'page': f"https://poly.pizza/m/{r['ID']}"})
            except Exception as e:
                print('polypizza 실패', term, e)
        try:
            q = urllib.parse.urlencode({'type': 'models', 'q': term, 'downloadable': 'true', 'count': 12})
            for r in json.loads(get('https://api.sketchfab.com/v3/search?' + q))['results']:
                lic = r['license']['label'] if r.get('license') else '?'
                if 'NonCommercial' in lic or 'NoDerivs' in lic:
                    continue
                th = max(r['thumbnails']['images'], key=lambda i: min(i['width'], 640) - abs(i['width'] - 640) / 1000)['url']
                out.append({'kind': 'model3d', 'site': 'sketchfab', 'uid': r['uid'], 'score': round(score(r['name'] + ' ' + ' '.join(t['name'] for t in r.get('tags', [])), terms) + w + (0.3 if 'CC0' in lic else 0), 2),
                            'title': r['name'], 'thumb': th, 'creator': r['user']['displayName'], 'license': lic, 'page': r['viewerUrl']})
        except Exception as e:
            print('sketchfab 실패', term, e)
    seen, uniq = set(), []
    for c in sorted(out, key=lambda c: -c['score']):
        if c['page'] not in seen:
            seen.add(c['page']); uniq.append(c)
    return uniq[:top]


def get_h(url, headers):
    with urllib.request.urlopen(urllib.request.Request(url, headers={**UA, **headers}), timeout=30, context=CTX) as r:
        return r.read()


def download(c, path):
    if c['kind'] == 'model3d':  # 비교표용 썸네일만
        ext = '.webp' if c['thumb'].endswith('.webp') else '.jpg'
        open(path + ext, 'wb').write(get(c['thumb']))
        return path + ext
    if c['kind'] == 'image':
        # 테스트는 Openverse 썸네일(원본 사이트 rate limit 회피). 원본은 고른 것만 --full 로
        open(path + '.jpg', 'wb').write(get(c['thumb'] or c['url']))
        return path + '.jpg'
    files = json.loads(get(f"https://api.polyhaven.com/files/{c['id']}"))['gltf']['1k']['gltf']
    os.makedirs(path, exist_ok=True)
    open(os.path.join(path, os.path.basename(files['url'])), 'wb').write(get(files['url']))
    for rel, f in files.get('include', {}).items():  # .bin·텍스처(경로 유지)
        dst = os.path.join(path, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        open(dst, 'wb').write(get(f['url']))
    return os.path.join(path, os.path.basename(files['url']))


def main():
    args = sys.argv[1:]
    top = int(args[args.index('--top') + 1]) if '--top' in args else 12
    nm = int(args[args.index('--models') + 1]) if '--models' in args else 3
    n3 = int(args[args.index('--3d') + 1]) if '--3d' in args else 0
    pos = [a for i, a in enumerate(args) if not a.startswith('--') and (i == 0 or args[i - 1] not in ('--top', '--models', '--3d'))]
    out_dir, terms = pos[0], [(t.rsplit(':', 1)[0], float(t.rsplit(':', 1)[1]) if ':' in t else 1.0) for t in pos[1:]]
    os.makedirs(out_dir, exist_ok=True)
    cands = (images(terms, top) if top else []) + (models(terms, nm) if nm else []) + (models3d(terms, n3) if n3 else [])
    for k, c in enumerate(cands):
        time.sleep(0.5)
        try:
            c['file'] = os.path.relpath(download(c, os.path.join(out_dir, f"{c['kind'][:3]}_{k:02d}")), out_dir)
        except Exception as e:
            c['error'] = str(e)
    q = urllib.parse.quote(terms[0][0])
    json.dump({'terms': terms, 'candidates': cands, 'links': {k: v.format(q=q) for k, v in LINK_ONLY.items()}},
              open(os.path.join(out_dir, 'candidates.json'), 'w'), ensure_ascii=False, indent=1)
    for k, c in enumerate(cands):
        print(k, c['kind'], c['score'], c.get('file', 'ERR ' + c.get('error', '')), '|', c['title'], '|', c['license'], '|', c['creator'])


if __name__ == '__main__':
    main()
