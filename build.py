#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
B-BEAUTY 빌드 스크립트
======================
src/ 의 소스를 묶어 index.html 하나로 만든다.

    python3 build.py

두 개의 파일이 만들어진다.

  index.html           배포용. 사진 원본 화질
  index-미리보기.html    미리보기용. 사진을 줄여 용량을 절반으로 낮춘 것.
                       내용은 완전히 같고, Claude 미리보기처럼 큰 파일을
                       버거워하는 곳에서 쓴다. 배포에는 index.html 을 쓸 것.

  src/style.css        스타일
  src/app.js           화면 로직
  src/data/*.json      제품·브랜드·문구·영상 데이터
  src/images/*.jpg     제품·브랜드 이미지 (base64 로 파일에 내장)

이미지를 파일에 내장하므로 index.html 하나만 있으면 어디서든 열린다.
"""
import base64
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, 'src')
IMG_DIR = os.path.join(SRC, 'images')
FONT_DIR = os.path.join(SRC, 'fonts')
DATA_DIR = os.path.join(SRC, 'data')
OUT = os.path.join(HERE, 'index.html')
PREVIEW_OUT = os.path.join(HERE, 'index-미리보기.html')


def j(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))


def load(name):
    with open(os.path.join(DATA_DIR, name), encoding='utf-8') as f:
        return json.load(f)


# ── 데이터 ─────────────────────────────────────────────
dataset = load('dataset.json')
ui = load('ui.json')
posts = load('posts.json')
posts_tr = load('posts_tr.json')
notices = load('notices.json')
notices_tr = load('notices_tr.json')
tc = load('community_text.json')
badwords = load('badwords.json')      # 커뮤니티 금지 표현
legal = load('legal.json')            # 이용약관·개인정보처리방침
meta = load('meta.json')
videos = load('videos.json')

# ── 이미지 → base64 ────────────────────────────────────
IMG = {}
raw_total = 0
for name in sorted(os.listdir(IMG_DIR)):
    if not name.lower().endswith(('.jpg', '.jpeg', '.png')):
        continue
    path = os.path.join(IMG_DIR, name)
    with open(path, 'rb') as f:
        raw = f.read()
    raw_total += len(raw)
    mime = 'image/png' if name.lower().endswith('.png') else 'image/jpeg'
    IMG['/src/assets/images/' + name] = \
        'data:%s;base64,%s' % (mime, base64.b64encode(raw).decode())
print('이미지 %d장 내장 (%d KB)' % (len(IMG), raw_total // 1024))

css = open(os.path.join(SRC, 'style.css'), encoding='utf-8').read()

# 로고 글꼴(Midstar)을 base64 로 CSS 안에 심는다 — 파일 하나로 돌아가게
_font = os.path.join(FONT_DIR, 'quentin.woff2')
if os.path.exists(_font):
    with open(_font, 'rb') as f:
        _b64 = base64.b64encode(f.read()).decode()
    css = css.replace('__LOGO_WOFF2__', 'data:font/woff2;base64,' + _b64)
    print('로고 글꼴 내장 (%d KB)' % (os.path.getsize(_font) // 1024))
else:
    css = css.replace("src:url('__LOGO_WOFF2__') format('woff2');", '')
    print('  (src/fonts/quentin.woff2 없음 — 로고 글꼴은 건너뜁니다)')
app = open(os.path.join(SRC, 'app.js'), encoding='utf-8').read()

# ── 구글 애널리틱스 4 ──────────────────────────────────
# ⚠ 측정 ID(G-XXXXXXX)를 넣으면 방문 통계 수집이 켜진다.
#    비워 두면 아무 코드도 들어가지 않는다.
#    ID 는 구글 애널리틱스 → 관리 → 데이터 스트림에서 확인한다.
GA4_ID = 'G-YKQBXR25H8'

ga_tag = ''
if GA4_ID:
    ga_tag = f"""<script async src="https://www.googletagmanager.com/gtag/js?id={GA4_ID}"></script>
<script>
window.dataLayer = window.dataLayer || [];
function gtag(){{dataLayer.push(arguments);}}
gtag('js', new Date());
/* ⚠ `anonymize_ip` 는 넣지 않는다 — GA4 는 이 값을 무시한다.
      GA4 는 원래부터 IP 를 저장하지 않으므로 따로 설정할 것이 없다. */
gtag('config', '{GA4_ID}');
</script>"""
    print('구글 애널리틱스 4 포함 (%s)' % GA4_ID)

html = f'''<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>B-BEAUTY | K-뷰티 연합 플랫폼</title>
{ga_tag}
<meta name="description" content="K-뷰티 브랜드 연합 플랫폼 B-Wave. 시에스킨·숲의 사랑·엘다라·슌유·힐마르의 제품을 한자리에서 비교하고 공식몰에서 바로 구매하세요.">
<style>
{css}
</style>
</head>
<body>
<script>
window.HERO_IMAGE   = {j(meta['HERO_IMAGE'])};
window.DATASET      = {j(dataset)};
window.UI           = {j(ui)};
window.SEED_POSTS   = {j(posts)};
window.POSTS_TR     = {j(posts_tr)};
window.NOTICES      = {j(notices)};
window.NOTICES_TR   = {j(notices_tr)};
window.TC           = {j(tc)};
window.BADWORDS     = {j(badwords)};
window.LEGAL        = {j(legal)};
window.VIDEOS       = {j(videos)};
window.IMG          = {j(IMG)};
</script>
<script>
{app}
</script>
</body>
</html>
'''

with open(OUT, 'w', encoding='utf-8') as f:
    f.write(html)
print('빌드 완료: %s (%.2f MB)' % (OUT, os.path.getsize(OUT) / 1024 / 1024))

# 빌드할 때마다 자동으로 점검한다.
#   · 다국어  — 영어·중국어에 한글이 남아 있는지 (한국어만 고치는 실수)
#   · 링크    — 외부 링크가 페이지를 두 개씩 여는지
_CHECKS = [('다국어-점검.py', '다국어 누락이 있습니다'),
           ('링크-점검.py', '링크에 문제가 있습니다')]
for _name, _msg in _CHECKS:
    try:
        import subprocess
        _chk = os.path.join(os.path.dirname(os.path.abspath(__file__)), _name)
        if os.path.exists(_chk):
            _r = subprocess.run([sys.executable, _chk], capture_output=True, text=True)
            if _r.returncode != 0:
                print('\n⚠ %s —' % _msg)
                print(_r.stdout.rstrip())
    except Exception as _e:
        print('  (%s 을 건너뜀: %s)' % (_name, _e))


# ── 미리보기용 경량본 ──────────────────────────────────
# 큰 파일을 못 여는 미리보기 환경을 위해, 사진만 줄인 판본을 함께 만든다.
# 내용·기능은 index.html 과 완전히 같다.
PREVIEW_MAX = 460      # 사진 긴 변 최대 픽셀
PREVIEW_Q = 54         # JPEG 품질
# 화면을 꽉 채우는 배경 사진은 460px 로 줄이면 심하게 뭉개진다 — 따로 더 크게 유지한다
# 히어로 배경은 미리보기에서도 화질을 유지한다 (제품 글자가 뭉개지지 않도록)
PREVIEW_BIG = {'ocean_cosmetics_hero_1784622126081.jpg': (1376, 88)}


def build_preview():
    try:
        from PIL import Image
    except ImportError:
        print('  (Pillow 가 없어 경량본은 건너뜁니다: pip install pillow)')
        return

    import io
    small = {}
    total = 0
    for name in sorted(os.listdir(IMG_DIR)):
        if not name.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue
        im = Image.open(os.path.join(IMG_DIR, name))
        # 투명 PNG(로고)는 배경이 비쳐야 하므로 PNG 그대로 둔다 — JPEG 로 바꾸면 흰 바탕이 생긴다
        if im.mode in ('RGBA', 'LA') or (im.mode == 'P' and 'transparency' in im.info):
            im = im.convert('RGBA')
            w, h = im.size
            if max(w, h) > PREVIEW_MAX:
                r = PREVIEW_MAX / float(max(w, h))
                im = im.resize((int(w * r), int(h * r)), Image.LANCZOS)
            buf = io.BytesIO()
            im.quantize(colors=64, method=Image.FASTOCTREE).save(buf, 'PNG', optimize=True)
            total += buf.tell()
            small['/src/assets/images/' + name] = \
                'data:image/png;base64,%s' % base64.b64encode(buf.getvalue()).decode()
            continue
        im = im.convert('RGB')
        w, h = im.size
        cap, q = PREVIEW_BIG.get(name, (PREVIEW_MAX, PREVIEW_Q))
        if max(w, h) > cap:
            r = cap / float(max(w, h))
            im = im.resize((int(w * r), int(h * r)), Image.LANCZOS)
        buf = io.BytesIO()
        im.save(buf, 'JPEG', quality=q, optimize=True, progressive=True)
        total += buf.tell()
        small['/src/assets/images/' + name] = \
            'data:image/jpeg;base64,%s' % base64.b64encode(buf.getvalue()).decode()

    out = html.replace(j(IMG), j(small))
    if out == html:
        print('  (경량본 생성 실패: 이미지 블록을 찾지 못했습니다)')
        return
    with open(PREVIEW_OUT, 'w', encoding='utf-8') as f:
        f.write(out)
    print('미리보기용: %s (%.2f MB · 사진 %d KB)'
          % (PREVIEW_OUT, os.path.getsize(PREVIEW_OUT) / 1024 / 1024, total // 1024))


build_preview()
