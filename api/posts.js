/* =========================================================
   커뮤니티 서버 (Vercel 서버리스 함수)
   ---------------------------------------------------------
   이 파일 하나가 글·댓글의 저장과 비밀번호 확인을 모두 맡는다.
   주소는 자동으로 https://내도메인/api/posts 가 된다.

   ⚠ 비밀번호는 **여기(서버)에서 확인한다.**
      브라우저에서 확인하면 개발자도구로 건너뛸 수 있지만,
      서버가 거절하면 방법이 없다.

   필요한 환경 변수 (Vercel 설정 화면에서 넣는다)
     SUPABASE_URL          : https://xxxx.supabase.co
     SUPABASE_SERVICE_KEY  : service_role 키 (절대 공개 금지)
     ADMIN_PW              : 관리자 마스터 비밀번호
     PW_SALT               : 아무 긴 문자열 (비밀번호를 뒤섞을 때 쓴다)
   ========================================================= */

const crypto = require('crypto');

const SB_URL = process.env.SUPABASE_URL || '';
const SB_KEY = process.env.SUPABASE_SERVICE_KEY || '';
const ADMIN_PW = process.env.ADMIN_PW || '';
const SALT = process.env.PW_SALT || 'b-beauty-default-salt';
const TABLE = 'community_posts';

/* 비밀번호를 되돌릴 수 없는 값으로 바꾼다 */
function hash(postId, pw) {
  return crypto.createHash('sha256').update(SALT + ':' + postId + ':' + pw).digest('hex');
}

/* Supabase 에 요청을 보낸다 */
async function sb(path, options = {}) {
  const res = await fetch(SB_URL + '/rest/v1/' + path, {
    ...options,
    headers: {
      apikey: SB_KEY,
      Authorization: 'Bearer ' + SB_KEY,
      'Content-Type': 'application/json',
      Prefer: 'return=representation',
      ...(options.headers || {})
    }
  });
  const text = await res.text();
  if (!res.ok) throw new Error('supabase ' + res.status + ': ' + text.slice(0, 200));
  return text ? JSON.parse(text) : null;
}

/* 글 하나를 화면에서 쓰는 모양으로 바꾼다 (비밀번호는 절대 내보내지 않는다) */
function toClient(row) {
  const p = row.data || {};
  p.id = row.id;
  p.date = row.date || p.date;
  delete p.pwHash;
  delete p.pw;
  return p;
}

module.exports = async function handler(req, res) {
  res.setHeader('Cache-Control', 'no-store');

  if (!SB_URL || !SB_KEY) {
    res.status(500).json({ error: '서버 설정이 끝나지 않았습니다 (SUPABASE_URL / SUPABASE_SERVICE_KEY).' });
    return;
  }

  try {
    /* ── 관리자 게시판(이벤트·공지) 목록 ── */
    if (req.method === 'GET' && req.query && req.query.kind === 'board') {
      const rows = await sb('admin_board?select=*');
      const out = { notices: [], events: [] };
      (rows || []).forEach(r => { (out[r.kind === 'event' ? 'events' : 'notices']).push(r.data); });
      res.status(200).json(out);
      return;
    }

    /* ── 글 목록 ── */
    if (req.method === 'GET') {
      const rows = await sb(TABLE + '?select=*&order=created_at.desc&limit=300');
      res.status(200).json(rows.map(toClient));
      return;
    }

    if (req.method !== 'POST') {
      res.status(405).json({ error: 'method not allowed' });
      return;
    }

    const body = typeof req.body === 'string' ? JSON.parse(req.body || '{}') : (req.body || {});
    const action = body.action || 'create';

    /* 관리자인지 확인 */
    const isAdmin = !!(ADMIN_PW && body.adminPw && body.adminPw === ADMIN_PW);

    /* ── 글 등록 ── */
    if (action === 'create') {
      const post = body.post || {};
      const pw = String(body.pw || '');
      if (!/^[0-9]{4}$/.test(pw)) {
        res.status(400).json({ error: '비밀번호는 숫자 4자리여야 합니다.' });
        return;
      }
      if (!post.title || !post.content || String(post.content).length < 10) {
        res.status(400).json({ error: '제목과 본문(10자 이상)을 입력해 주세요.' });
        return;
      }
      const id = post.id || ('post-' + Date.now());
      delete post.pwHash;
      const row = {
        id: id,
        date: post.date || new Date().toISOString().slice(0, 10),
        pw_hash: hash(id, pw),
        data: { ...post, id: id }
      };
      const saved = await sb(TABLE, { method: 'POST', body: JSON.stringify(row) });
      res.status(200).json(toClient(saved[0]));
      return;
    }

    /* ── 관리자 게시판 올리기·지우기 (관리자만) ── */
    if (action === 'board-save' || action === 'board-delete') {
      if (!isAdmin) { res.status(403).json({ error: '관리자만 할 수 있습니다.' }); return; }
      const kind = body.kind === 'event' ? 'event' : 'notice';
      if (action === 'board-delete') {
        await sb('admin_board?id=eq.' + encodeURIComponent(body.id), { method: 'DELETE' });
      } else {
        const it = body.item || {};
        await sb('admin_board', {
          method: 'POST',
          headers: { Prefer: 'resolution=merge-duplicates,return=representation' },
          body: JSON.stringify({ id: it.id, kind: kind, data: it })
        });
      }
      res.status(200).json({ ok: true });
      return;
    }

    /* ── 아래 작업은 모두 비밀번호(또는 관리자)가 필요하다 ── */
    const postId = body.postId;
    if (!postId) { res.status(400).json({ error: 'postId 가 없습니다.' }); return; }

    const found = await sb(TABLE + '?id=eq.' + encodeURIComponent(postId) + '&select=*');
    if (!found || !found.length) { res.status(404).json({ error: '글을 찾지 못했습니다.' }); return; }
    const row = found[0];

    /* 댓글 달기 — 누구나 할 수 있지만 비밀번호를 함께 저장한다 */
    if (action === 'comment') {
      const data = row.data || {};
      const cm = body.comment || {};
      const cpw = String(body.pw || '');
      if (!/^[0-9]{4}$/.test(cpw)) {
        res.status(400).json({ error: '댓글 비밀번호는 숫자 4자리여야 합니다.' });
        return;
      }
      cm.pwHash = hash(postId + '|' + cm.id, cpw);
      data.comments = (data.comments || []).concat([cm]);
      await sb(TABLE + '?id=eq.' + encodeURIComponent(postId), {
        method: 'PATCH', body: JSON.stringify({ data: data })
      });
      res.status(200).json({ ok: true });
      return;
    }

    /* 댓글 수정·삭제 — 그 댓글의 비밀번호를 맞혀야 한다 */
    if (action.indexOf('comment-') === 0) {
      const data = row.data || {};
      const cid = body.commentId;
      const cm = (data.comments || []).filter(c => c.id === cid)[0];
      if (!cm) { res.status(404).json({ error: '댓글을 찾지 못했습니다.' }); return; }
      const okCm = isAdmin || (body.pw && cm.pwHash === hash(postId + '|' + cid, String(body.pw)));
      if (!okCm) { res.status(403).json({ error: '비밀번호가 맞지 않습니다.' }); return; }

      if (action === 'comment-verify') { res.status(200).json({ ok: true }); return; }
      if (action === 'comment-delete') {
        data.comments = data.comments.filter(c => c.id !== cid);
      } else if (action === 'comment-update') {
        cm.content = String(body.content || '').slice(0, 2000);
        cm.edited = true;
      }
      await sb(TABLE + '?id=eq.' + encodeURIComponent(postId), {
        method: 'PATCH', body: JSON.stringify({ data: data })
      });
      res.status(200).json({ ok: true });
      return;
    }

    /* 수정·삭제는 비밀번호를 맞혀야 한다 */
    const ok = isAdmin || (body.pw && hash(postId, String(body.pw)) === row.pw_hash);
    if (!ok) { res.status(403).json({ error: '비밀번호가 맞지 않습니다.' }); return; }

    if (action === 'delete') {
      await sb(TABLE + '?id=eq.' + encodeURIComponent(postId), { method: 'DELETE' });
      res.status(200).json({ ok: true });
      return;
    }

    /* 비밀번호만 확인한다 (수정 화면을 열기 전에 쓴다) */
    if (action === 'verify') {
      res.status(200).json({ ok: true });
      return;
    }

    if (action === 'update') {
      const post = body.post || {};
      delete post.pwHash;
      post.id = postId;
      await sb(TABLE + '?id=eq.' + encodeURIComponent(postId), {
        method: 'PATCH', body: JSON.stringify({ data: post })
      });
      res.status(200).json({ ok: true });
      return;
    }

    /* 관리자 로그인 확인만 하는 요청 */
    if (action === 'admin-check') {
      res.status(isAdmin ? 200 : 403).json({ ok: isAdmin });
      return;
    }

    res.status(400).json({ error: '알 수 없는 요청입니다.' });
  } catch (e) {
    res.status(500).json({ error: String(e.message || e) });
  }
};
