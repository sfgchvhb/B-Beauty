# B-BEAUTY — 부산 코스메틱 연합 플랫폼

부산 화장품 브랜드 5개사(아마란스·크레이지앤트·엘다라·더블리·유엔비)의 연합 플랫폼 사이트입니다.
제품을 소개하고 구매는 각 브랜드 공식몰로 연결합니다. 자체 결제는 없습니다.
한국어·영어·중국어 3개 언어를 지원합니다.

의존성 없는 **순수 HTML/CSS/JS**로 만들어져 있습니다. React·Tailwind·빌드 도구를 쓰지 않습니다.

## 파일 구성

| 파일 | 설명 |
|---|---|
| `index.html` | 사이트 본체. 이미지·데이터가 모두 들어 있는 단일 파일. **배포는 이 파일** |
| `index-미리보기.html` | 사진만 줄인 경량본(약 0.7MB). 내용은 동일. 미리보기 전용 |
| `build.py` | `src/` 를 묶어 위 두 파일을 만드는 스크립트 |
| `src/` | 실제 소스. 여기를 고치고 `build.py` 를 돌립니다 |

제품·가격 정보는 각 브랜드 공식몰/스토어 캡처를 기준으로 사이트에 직접 넣어 둡니다.
외부 사이트를 실시간으로 읽어오지 않으므로 서버·API·네트워크 설정이 필요 없습니다.

---

## 1. 수정하고 다시 빌드하기

```bash
python3 build.py        # index.html 재생성
```

이미지를 base64 로 파일에 내장하므로 `index.html` 하나만 있으면 인터넷 없이도 열립니다.

---

## 2. 배포

### Cloudflare Pages (권장 · 무료)

1. GitHub 에 이 폴더를 올립니다.
2. Cloudflare 대시보드 → Workers & Pages → Create → Pages → Connect to Git
3. 빌드 설정은 비워 둡니다 (정적 파일이라 빌드가 필요 없습니다).
   - Build command: *(비움)*
   - Build output directory: `/`
4. 배포 후 Custom domains 에서 보유하신 도메인을 연결합니다. SSL 은 자동 발급됩니다.

### 그 외

- **Netlify / Vercel** — 폴더를 화면에 끌어다 놓으면 배포됩니다.
- **GitHub Pages** — Settings → Pages → Branch 지정.
- **직접 열기** — `index.html` 을 더블클릭하면 그대로 열립니다.
  로컬에서 서버로 확인하려면:

  ```bash
  python3 -m http.server 8000
  # http://localhost:8000 접속
  ```

---

## 3. 제품 정보 갱신 방법

공식몰에 새 제품이 올라오거나 가격이 바뀌면 다음 순서로 반영합니다.

1. 공식몰/스마트스토어에서 제품 정보와 사진을 확인합니다.
2. 사진은 `src/images/` 에 넣습니다.
3. `src/data/dataset.json` 의 해당 브랜드 항목을 고칩니다.
   `KR` · `EN` · `CN` 세 곳을 모두 맞춰야 언어 전환 시 어긋나지 않습니다.
4. `python3 build.py` 로 다시 빌드합니다.

공지·이벤트는 `src/data/notices.json`(+ `notices_tr.json`),
커뮤니티 글은 `src/data/posts.json` 에서 고칩니다.
