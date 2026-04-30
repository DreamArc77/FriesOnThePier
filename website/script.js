/* ═══════════════════════════════
   去码头整点薯条 · 官网交互脚本
   ═══════════════════════════════ */

/* ─── 1. 气泡打字机效果 ─── */
const bubbleText = document.getElementById('bubble-text');
const lines = [
  '别人只关心你飞的高不高，',
  '我关心你飞的累不累',
  '（和饿不饿）。'
];
const fullText = lines.join('\n');

let charIdx = 0;
let started = false;

function startTyping() {
  if (started) return;
  started = true;
  const interval = setInterval(() => {
    if (charIdx >= fullText.length) {
      clearInterval(interval);
      return;
    }
    const ch = fullText[charIdx];
    if (ch === '\n') {
      bubbleText.appendChild(document.createElement('br'));
    } else {
      bubbleText.appendChild(document.createTextNode(ch));
    }
    charIdx++;
  }, 45);
}

// 等海鸥落地后开始打字
setTimeout(startTyping, 950);

/* ─── 2. Intersection Observer：步骤卡片 & FAQ 气泡入场 ─── */
const observeEls = (selector, cls = 'visible', threshold = 0.2) => {
  const els = document.querySelectorAll(selector);
  if (!els.length) return;
  const obs = new IntersectionObserver((entries) => {
    entries.forEach((entry, i) => {
      if (entry.isIntersecting) {
        // stagger
        setTimeout(() => entry.target.classList.add(cls), i * 120);
        obs.unobserve(entry.target);
      }
    });
  }, { threshold });
  els.forEach(el => obs.observe(el));
};

observeEls('.step-card');
observeEls('.chat-bubble');
observeEls('#comic-img', 'visible', 0.15);

/* ─── 3. Tab 切换 ─── */
const tabBtns = document.querySelectorAll('.tab-btn');
const tabPanels = document.querySelectorAll('.tab-content');

tabBtns.forEach(btn => {
  btn.addEventListener('click', () => {
    const target = btn.dataset.tab;

    tabBtns.forEach(b => b.classList.remove('active'));
    tabPanels.forEach(p => p.classList.remove('active'));

    btn.classList.add('active');
    const panel = document.getElementById('panel-' + target);
    if (panel) panel.classList.add('active');
  });
});

/* ─── 4. 复制按钮 ─── */
const toast = document.getElementById('toast');
let toastTimer;

function showToast() {
  toast.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('show'), 2000);
}

document.querySelectorAll('.copy-btn').forEach(btn => {
  btn.addEventListener('click', async () => {
    const code = btn.dataset.code;
    try {
      await navigator.clipboard.writeText(code);
      showToast();
    } catch {
      // fallback
      const ta = document.createElement('textarea');
      ta.value = code;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.focus(); ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      showToast();
    }
  });
});

/* ─── 5. CTA 按钮晃动彩蛋 ─── */
const ctaBtn = document.getElementById('cta-btn');
if (ctaBtn) {
  let wobble = false;
  ctaBtn.addEventListener('mouseenter', () => {
    if (wobble) return;
    wobble = true;
    ctaBtn.style.transition = 'transform 0.1s ease-in-out';
    const times = [0, 100, 200, 300];
    const angles = [-3, 3, -2, 0];
    times.forEach((t, i) => {
      setTimeout(() => {
        ctaBtn.style.transform = `rotate(${angles[i]}deg)`;
        if (i === times.length - 1) {
          setTimeout(() => { wobble = false; }, 200);
        }
      }, t);
    });
  });
}

/* ─── 6. Waitlist 表单（Supabase） ─── */
const SUPABASE_URL = 'https://nlmqzteddyrkfgajsqdg.supabase.co';
const SUPABASE_KEY = 'sb_publishable_GLBc3NaHpf8IZMXqG3czuw_I9cB1b9u';

const waitlistForm   = document.getElementById('waitlist-form');
const waitlistEmail  = document.getElementById('waitlist-email');
const waitlistError  = document.getElementById('waitlist-error');
const waitlistSucc   = document.getElementById('waitlist-success');
const waitlistSubmit = document.getElementById('waitlist-submit');

function isValidEmail(email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
}
function setError(msg) {
  waitlistError.textContent = msg;
  waitlistEmail.classList.add('input-error');
}
function clearError() {
  waitlistError.textContent = '';
  waitlistEmail.classList.remove('input-error');
}

async function submitToSupabase(email) {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/waitlist`, {
    method: 'POST',
    headers: {
      'apikey': SUPABASE_KEY,
      'Authorization': `Bearer ${SUPABASE_KEY}`,
      'Content-Type': 'application/json',
      'Prefer': 'return=minimal',
    },
    body: JSON.stringify({ email }),
  });
  return res;
}

if (waitlistForm) {
  // 点击"抢先体验"按钮平滑滚动到表单并聚焦
  const waitlistBtn = document.getElementById('waitlist-btn');
  if (waitlistBtn) {
    waitlistBtn.addEventListener('click', (e) => {
      e.preventDefault();
      const card = document.getElementById('waitlist');
      if (card) {
        card.scrollIntoView({ behavior: 'smooth', block: 'center' });
        setTimeout(() => waitlistEmail.focus(), 600);
      }
    });
  }

  waitlistEmail.addEventListener('input', clearError);

  waitlistForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const email = waitlistEmail.value.trim();

    if (!email) {
      setError('🐦 先填个邮箱嘛，海鸥总要找到你的。');
      return;
    }
    if (!isValidEmail(email)) {
      setError('🍟 这个邮箱格式不太对，薯条送不过去。');
      return;
    }

    clearError();
    waitlistSubmit.disabled = true;
    waitlistSubmit.textContent = '提交中…';

    try {
      const res = await submitToSupabase(email);

      if (res.ok) {
        // 同时写入 localStorage 作本地备份
        try {
          const list = JSON.parse(localStorage.getItem('fries-waitlist') || '[]');
          if (!list.includes(email)) {
            list.push(email);
            localStorage.setItem('fries-waitlist', JSON.stringify(list));
          }
        } catch (_) {}

        waitlistForm.hidden = true;
        waitlistSucc.hidden = false;

      } else if (res.status === 409) {
        // 唯一约束冲突：邮箱已存在
        setError('🐦 这个邮箱已经在队列里了，海鸥记得你！');
        waitlistSubmit.disabled = false;
        waitlistSubmit.textContent = 'JOIN THE WAITLIST';

      } else {
        throw new Error(`HTTP ${res.status}`);
      }

    } catch (err) {
      console.error('Supabase error:', err);
      setError('😵 网络出了点问题，稍后再试？（薯条还在炸）');
      waitlistSubmit.disabled = false;
      waitlistSubmit.textContent = 'JOIN THE WAITLIST';
    }
  });
}

