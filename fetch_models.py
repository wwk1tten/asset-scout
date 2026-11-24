"""find_bg.py --3d 로 찾은 후보의 원본 3D 를 받는다(Sketchfab 은 토큰, Poly Pizza 는 바로).
  python3 fetch_models.py <후보 폴더> [<후보 폴더> ...] [--public public]
각 후보 폴더 <dir>/m_XX/ 에 .glb 또는 압축 푼 glTF. 결과는 candidates.json 의 'model' 에 기록(--public 폴더 기준 경로, Remotion staticFile 용).
"""
import io, json, os, sys, zipfile
from find_assets import get, get_h, secret

args = sys.argv[1:]
PUBLIC = args[args.index('--public') + 1] if '--public' in args else ('public' if os.path.isdir('public') else '.')
dirs = [a for i, a in enumerate(args) if a != '--public' and (i == 0 or args[i - 1] != '--public')]
tok = secret('sketchfab_token')
for d in dirs:
    cj = os.path.join(d, 'candidates.json'); data = json.load(open(cj))
    for k, c in enumerate(data['candidates']):
        out = os.path.join(d, f'm_{k:02d}'); os.makedirs(out, exist_ok=True)
        try:
            if c['site'] == 'polypizza':
                open(os.path.join(out, 'model.glb'), 'wb').write(get(c['url'])); c['model'] = 'model.glb'
            else:
                info = json.loads(get_h(f"https://api.sketchfab.com/v3/models/{c['uid']}/download", {'Authorization': 'Token ' + tok}))
                if 'glb' in info:
                    open(os.path.join(out, 'model.glb'), 'wb').write(get(info['glb']['url'])); c['model'] = 'model.glb'
                else:
                    zipfile.ZipFile(io.BytesIO(get(info['gltf']['url']))).extractall(out)
                    c['model'] = next(os.path.relpath(os.path.join(r, f), out) for r, _, fs in os.walk(out) for f in fs if f.endswith('.gltf'))
            c['model'] = os.path.join(os.path.relpath(out, PUBLIC), c['model'])
            print('ok ', d[-6:], k, c['title'][:30], c['model'])
        except Exception as e:
            c['model_error'] = str(e); print('ERR', d[-6:], k, c['title'][:30], e)
    json.dump(data, open(cj, 'w'), ensure_ascii=False, indent=1)
