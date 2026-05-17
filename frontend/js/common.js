// common.js
(function () {
  function getApiBase() {
    return window.APP_CONFIG?.API_BASE || "http://127.0.0.1:8000";
  }

  function escapeHtml(text) {
    return String(text ?? "")
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;");
  }

  function getLoggedInUser() {
    const raw = localStorage.getItem("loggedInUser");
    if (!raw) return null;

    try {
      return JSON.parse(raw);
    } catch (e) {
      localStorage.removeItem("loggedInUser");
      return null;
    }
  }

  function saveLoggedInUser(user) {
    localStorage.setItem("loggedInUser", JSON.stringify(user));
  }

  function saveAccessToken(token) {
    if (!token) return;
    localStorage.setItem("accessToken", token);
  }

  function getAccessToken() {
    return localStorage.getItem("accessToken");
  }

  function getAuthHeaders() {
    const token = getAccessToken();

    if (!token) {
      return {};
    }

    return {
      Authorization: `Bearer ${token}`
    };
  }

  function clearLoggedInUser() {
    localStorage.removeItem("loggedInUser");
    localStorage.removeItem("accessToken");
  }

  function requireLogin(redirectUrl = "login.html") {
    const user = getLoggedInUser();

    if (!user || !user.id) {
      clearLoggedInUser();
      location.href = redirectUrl;
      return null;
    }

    return user;
  }

  function redirectIfLoggedIn(targetUrl = "index.html") {
    const user = getLoggedInUser();
    if (user && user.id) {
      location.href = targetUrl;
      return true;
    }
    return false;
  }

  function logout(redirectUrl = "login.html") {
    clearLoggedInUser();
    location.href = redirectUrl;
  }

  function getUserId() {
    return getLoggedInUser()?.id ?? null;
  }

  function updateUserChip(user, elementId = "userChip") {
    const chip = document.getElementById(elementId);
    if (!chip) return;

    if (!user) {
      chip.innerText = "로그인 정보 없음";
      return;
    }

    chip.innerText = `👤 ${user.username} (${user.email})`;
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("theme", theme);
  }

  function getSavedTheme() {
    return localStorage.getItem("theme") || "dark";
  }

  function initTheme() {
    applyTheme(getSavedTheme());
  }

  function toggleTheme(afterToggle) {
    const current = document.documentElement.getAttribute("data-theme") || "dark";
    const next = current === "dark" ? "light" : "dark";
    applyTheme(next);

    if (typeof afterToggle === "function") {
      afterToggle(next);
    }
  }

  function jsonFetch(url, options = {}) {
    return fetch(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
        ...(options.headers || {})
      }
    });
  }

  function injectFloatingChatStyles() {
    if (document.getElementById("adaFloatingChatStyles")) return;

    const style = document.createElement("style");
    style.id = "adaFloatingChatStyles";
    style.textContent = `
      .ada-chatbot-widget, .ada-chatbot-widget * {
        box-sizing: border-box;
      }

      .ada-chatbot-widget {
        position: fixed;
        right: 24px;
        bottom: 24px;
        z-index: 99999;
        font-family: inherit;
      }

      .ada-chatbot-fab {
        position: relative;
        width: 72px;
        height: 72px;
        border: 0;
        border-radius: 999px;
        cursor: pointer;
        display: grid;
        place-items: center;
        background:
          radial-gradient(circle at 30% 22%, rgba(255,255,255,.42), transparent 26%),
          linear-gradient(135deg, #59f3ff 0%, #6c5cff 48%, #d65cff 100%);
        box-shadow:
          0 18px 42px rgba(55, 95, 255, .42),
          0 0 0 1px rgba(255,255,255,.22) inset;
        transition: transform .2s ease, box-shadow .2s ease, filter .2s ease;
      }

      .ada-chatbot-fab:hover {
        transform: translateY(-4px) scale(1.03);
        box-shadow:
          0 24px 54px rgba(55, 95, 255, .55),
          0 0 0 1px rgba(255,255,255,.3) inset;
        filter: saturate(1.08);
      }

      .ada-chatbot-fab:active {
        transform: translateY(-1px) scale(.98);
      }

      .ada-chatbot-fab img {
        width: 48px;
        height: 48px;
        display: block;
        filter: drop-shadow(0 8px 12px rgba(0,0,0,.28));
        pointer-events: none;
      }

      .ada-chatbot-fallback-icon {
        display: none;
        width: 48px;
        height: 48px;
        place-items: center;
        font-size: 36px;
        line-height: 1;
        pointer-events: none;
      }

      .ada-chatbot-pulse {
        position: absolute;
        right: 8px;
        top: 8px;
        width: 14px;
        height: 14px;
        border-radius: 999px;
        background: #41ff9f;
        border: 2px solid rgba(8, 14, 32, .9);
        box-shadow: 0 0 0 0 rgba(65, 255, 159, .68);
        animation: adaChatPulse 1.7s infinite;
      }

      @keyframes adaChatPulse {
        0% { box-shadow: 0 0 0 0 rgba(65, 255, 159, .68); }
        70% { box-shadow: 0 0 0 12px rgba(65, 255, 159, 0); }
        100% { box-shadow: 0 0 0 0 rgba(65, 255, 159, 0); }
      }

      .ada-chatbot-panel {
        position: absolute;
        right: 0;
        bottom: 88px;
        width: min(390px, calc(100vw - 32px));
        height: min(620px, calc(100vh - 128px));
        border-radius: 28px;
        overflow: hidden;
        display: grid;
        grid-template-rows: auto auto 1fr auto;
        background: rgba(9, 15, 35, .96);
        color: #eef5ff;
        border: 1px solid rgba(160, 180, 255, .24);
        box-shadow: 0 24px 80px rgba(0,0,0,.46);
        backdrop-filter: blur(18px);
        opacity: 0;
        transform: translateY(16px) scale(.96);
        transform-origin: bottom right;
        pointer-events: none;
        transition: opacity .2s ease, transform .2s ease;
      }

      .ada-chatbot-panel.is-open {
        opacity: 1;
        transform: translateY(0) scale(1);
        pointer-events: auto;
      }

      .ada-chatbot-header {
        padding: 18px 18px 16px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        background:
          radial-gradient(circle at 12% 0%, rgba(89, 243, 255, .24), transparent 34%),
          linear-gradient(135deg, rgba(94, 111, 255, .25), rgba(214, 92, 255, .16));
        border-bottom: 1px solid rgba(255,255,255,.08);
      }

      .ada-chatbot-title-area {
        display: flex;
        align-items: center;
        gap: 12px;
        min-width: 0;
      }

      .ada-chatbot-mini-avatar {
        width: 44px;
        height: 44px;
        border-radius: 16px;
        display: grid;
        place-items: center;
        background: linear-gradient(135deg, rgba(89, 243, 255, .24), rgba(214, 92, 255, .24));
        border: 1px solid rgba(255,255,255,.16);
        flex: 0 0 auto;
      }

      .ada-chatbot-mini-avatar img {
        width: 32px;
        height: 32px;
      }

      .ada-chatbot-title {
        margin: 0;
        font-size: 15px;
        font-weight: 900;
        letter-spacing: -.01em;
      }

      .ada-chatbot-subtitle {
        margin-top: 4px;
        font-size: 12px;
        color: rgba(238,245,255,.7);
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .ada-chatbot-header-actions {
        display: flex;
        gap: 8px;
      }

      .ada-chatbot-icon-btn {
        width: 34px;
        height: 34px;
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 12px;
        cursor: pointer;
        color: #eef5ff;
        background: rgba(255,255,255,.08);
        transition: background .18s ease, transform .18s ease;
      }

      .ada-chatbot-icon-btn:hover {
        background: rgba(255,255,255,.15);
        transform: translateY(-1px);
      }

      .ada-chatbot-quick {
        display: flex;
        gap: 8px;
        overflow-x: auto;
        padding: 12px 14px;
        background: rgba(255,255,255,.035);
        border-bottom: 1px solid rgba(255,255,255,.06);
      }

      .ada-chatbot-quick::-webkit-scrollbar,
      .ada-chatbot-messages::-webkit-scrollbar {
        height: 7px;
        width: 7px;
      }

      .ada-chatbot-quick::-webkit-scrollbar-thumb,
      .ada-chatbot-messages::-webkit-scrollbar-thumb {
        background: rgba(255,255,255,.16);
        border-radius: 999px;
      }

      .ada-chatbot-chip {
        border: 1px solid rgba(129, 179, 255, .22);
        background: rgba(91, 120, 255, .12);
        color: #dfe9ff;
        border-radius: 999px;
        padding: 8px 10px;
        font-size: 12px;
        white-space: nowrap;
        cursor: pointer;
      }

      .ada-chatbot-chip:hover {
        background: rgba(91, 120, 255, .2);
      }

      .ada-chatbot-messages {
        padding: 16px;
        overflow-y: auto;
        display: flex;
        flex-direction: column;
        gap: 12px;
        min-height: 0;
      }

      .ada-chatbot-message {
        max-width: 86%;
        display: flex;
        flex-direction: column;
        gap: 6px;
      }

      .ada-chatbot-message.user {
        align-self: flex-end;
        align-items: flex-end;
      }

      .ada-chatbot-message.assistant {
        align-self: flex-start;
        align-items: flex-start;
      }

      .ada-chatbot-meta {
        font-size: 11px;
        color: rgba(238,245,255,.52);
        padding: 0 4px;
      }

      .ada-chatbot-bubble {
        padding: 12px 14px;
        border-radius: 18px;
        line-height: 1.55;
        font-size: 13px;
        white-space: normal;
        word-break: break-word;
        box-shadow: 0 10px 24px rgba(0,0,0,.18);
      }

      .ada-chatbot-message.user .ada-chatbot-bubble {
        border-bottom-right-radius: 6px;
        color: #061225;
        background: linear-gradient(135deg, #8df4ff, #b9a7ff);
      }

      .ada-chatbot-message.assistant .ada-chatbot-bubble {
        border-bottom-left-radius: 6px;
        color: #eef5ff;
        background: rgba(255,255,255,.08);
        border: 1px solid rgba(255,255,255,.08);
      }

      .ada-chatbot-typing {
        display: inline-flex;
        gap: 4px;
        align-items: center;
        min-width: 42px;
      }

      .ada-chatbot-typing span {
        width: 6px;
        height: 6px;
        border-radius: 999px;
        background: rgba(238,245,255,.8);
        animation: adaChatTyping 1s infinite ease-in-out;
      }

      .ada-chatbot-typing span:nth-child(2) { animation-delay: .15s; }
      .ada-chatbot-typing span:nth-child(3) { animation-delay: .3s; }

      @keyframes adaChatTyping {
        0%, 80%, 100% { transform: translateY(0); opacity: .45; }
        40% { transform: translateY(-5px); opacity: 1; }
      }

      .ada-chatbot-form {
        display: grid;
        grid-template-columns: 1fr auto;
        gap: 10px;
        padding: 14px;
        border-top: 1px solid rgba(255,255,255,.08);
        background: rgba(3, 8, 20, .72);
      }

      .ada-chatbot-input {
        width: 100%;
        min-height: 44px;
        max-height: 112px;
        resize: none;
        outline: none;
        border: 1px solid rgba(255,255,255,.1);
        border-radius: 16px;
        color: #eef5ff;
        background: rgba(255,255,255,.07);
        padding: 12px 13px;
        font: inherit;
        font-size: 13px;
      }

      .ada-chatbot-input::placeholder {
        color: rgba(238,245,255,.45);
      }

      .ada-chatbot-send {
        width: 46px;
        height: 44px;
        border: 0;
        border-radius: 16px;
        cursor: pointer;
        color: #061225;
        font-size: 18px;
        font-weight: 900;
        background: linear-gradient(135deg, #8df4ff, #b9a7ff);
        box-shadow: 0 12px 24px rgba(104, 135, 255, .24);
      }

      .ada-chatbot-send:disabled {
        cursor: not-allowed;
        opacity: .55;
      }

      html[data-theme="light"] .ada-chatbot-panel {
        background: rgba(250, 252, 255, .97);
        color: #142033;
        border-color: rgba(70, 96, 160, .18);
      }

      html[data-theme="light"] .ada-chatbot-subtitle,
      html[data-theme="light"] .ada-chatbot-meta {
        color: rgba(20, 32, 51, .58);
      }

      html[data-theme="light"] .ada-chatbot-icon-btn {
        color: #142033;
        background: rgba(20,32,51,.06);
        border-color: rgba(20,32,51,.1);
      }

      html[data-theme="light"] .ada-chatbot-chip {
        color: #24324a;
        background: rgba(76, 113, 255, .08);
        border-color: rgba(76, 113, 255, .18);
      }

      html[data-theme="light"] .ada-chatbot-message.assistant .ada-chatbot-bubble {
        color: #142033;
        background: rgba(20,32,51,.055);
        border-color: rgba(20,32,51,.08);
      }

      html[data-theme="light"] .ada-chatbot-form {
        background: rgba(246, 249, 255, .86);
        border-color: rgba(20,32,51,.08);
      }

      html[data-theme="light"] .ada-chatbot-input {
        color: #142033;
        background: rgba(20,32,51,.055);
        border-color: rgba(20,32,51,.1);
      }

      html[data-theme="light"] .ada-chatbot-input::placeholder {
        color: rgba(20,32,51,.45);
      }

      @media (max-width: 520px) {
        .ada-chatbot-widget {
          right: 16px;
          bottom: 16px;
        }

        .ada-chatbot-fab {
          width: 64px;
          height: 64px;
        }

        .ada-chatbot-fab img {
          width: 43px;
          height: 43px;
        }

        .ada-chatbot-panel {
          position: fixed;
          right: 12px;
          left: 12px;
          bottom: 92px;
          width: auto;
          height: min(620px, calc(100vh - 112px));
          border-radius: 24px;
        }
      }
    `;

    document.head.appendChild(style);
  }

  function initFloatingChatWidget() {
    if (window.__ADA_FLOATING_CHAT_WIDGET__) return;
    window.__ADA_FLOATING_CHAT_WIDGET__ = true;

    const currentPath = window.location.pathname.toLowerCase();
    if (currentPath.endsWith("/chatbot.html") || currentPath.endsWith("chatbot.html")) {
      return;
    }

    if (document.body?.dataset?.disableFloatingChat === "true") {
      return;
    }

    const user = getLoggedInUser();
    if (!user || !user.id) {
      return;
    }

    injectFloatingChatStyles();

    const root = document.createElement("div");
    root.id = "adaFloatingChat";
    root.className = "ada-chatbot-widget";
    root.innerHTML = `
      <button class="ada-chatbot-fab" type="button" aria-label="AI 챗봇 열기" aria-expanded="false">
        <img src="images/chatbot-avatar.svg" alt="" onerror="this.style.display='none'; this.nextElementSibling.style.display='grid';">
        <span class="ada-chatbot-fallback-icon">🤖</span>
        <span class="ada-chatbot-pulse" aria-hidden="true"></span>
      </button>

      <section class="ada-chatbot-panel" aria-label="AI 챗봇 창">
        <header class="ada-chatbot-header">
          <div class="ada-chatbot-title-area">
            <div class="ada-chatbot-mini-avatar">
              <img src="images/chatbot-avatar.svg" alt="AI 챗봇">
            </div>
            <div>
              <h2 class="ada-chatbot-title">AI 챗봇 도우미</h2>
              <div class="ada-chatbot-subtitle">프로젝트 · Python · FastAPI 질문 가능</div>
            </div>
          </div>
          <div class="ada-chatbot-header-actions">
            <button class="ada-chatbot-icon-btn ada-chatbot-clear" type="button" title="대화 기록 삭제">🗑</button>
            <button class="ada-chatbot-icon-btn ada-chatbot-close" type="button" title="닫기">×</button>
          </div>
        </header>

        <div class="ada-chatbot-quick" aria-label="빠른 질문">
          <button class="ada-chatbot-chip" type="button" data-question="이 프로젝트가 뭔지 쉽게 설명해줘">프로젝트 설명</button>
          <button class="ada-chatbot-chip" type="button" data-question="현재 사용한 기술 스택을 정리해줘">기술 스택</button>
          <button class="ada-chatbot-chip" type="button" data-question="EC2 배포에서 확인해야 할 것을 알려줘">EC2 배포 체크</button>
          <button class="ada-chatbot-chip" type="button" data-question="FastAPI 오류를 해결할 때 보는 순서를 알려줘">오류 해결 순서</button>
        </div>

        <div class="ada-chatbot-messages" aria-live="polite"></div>

        <form class="ada-chatbot-form">
          <textarea class="ada-chatbot-input" rows="1" placeholder="궁금한 걸 입력해줘. Shift+Enter는 줄바꿈"></textarea>
          <button class="ada-chatbot-send" type="submit" aria-label="보내기">➤</button>
        </form>
      </section>
    `;

    document.body.appendChild(root);

    const fab = root.querySelector(".ada-chatbot-fab");
    const panel = root.querySelector(".ada-chatbot-panel");
    const closeBtn = root.querySelector(".ada-chatbot-close");
    const clearBtn = root.querySelector(".ada-chatbot-clear");
    const form = root.querySelector(".ada-chatbot-form");
    const input = root.querySelector(".ada-chatbot-input");
    const sendBtn = root.querySelector(".ada-chatbot-send");
    const messagesEl = root.querySelector(".ada-chatbot-messages");
    const quickButtons = root.querySelectorAll(".ada-chatbot-chip");

    let isOpen = false;
    let historyLoaded = false;
    let isSending = false;

    function scrollToBottom() {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function formatMessage(message) {
      return escapeHtml(message).replaceAll("\n", "<br>");
    }

    function renderMessage(role, message, createdAt = "") {
      const label = role === "user" ? "나" : "AI 챗봇";
      const messageEl = document.createElement("div");
      messageEl.className = `ada-chatbot-message ${role}`;
      messageEl.innerHTML = `
        <div class="ada-chatbot-meta">${label}${createdAt ? ` · ${escapeHtml(createdAt)}` : ""}</div>
        <div class="ada-chatbot-bubble">${formatMessage(message)}</div>
      `;
      messagesEl.appendChild(messageEl);
      scrollToBottom();
    }

    function renderWelcome() {
      renderMessage(
        "assistant",
        "안녕! 나는 AI Developer Assistant 안에 붙은 챗봇이야.\n프로젝트 설명, Python/FastAPI 오류, EC2 배포 점검, 기능 구조를 물어보면 도와줄게."
      );
    }

    function setTyping(isTyping) {
      const oldTyping = messagesEl.querySelector(".ada-chatbot-message.typing");
      if (oldTyping) oldTyping.remove();

      if (!isTyping) return;

      const typingEl = document.createElement("div");
      typingEl.className = "ada-chatbot-message assistant typing";
      typingEl.innerHTML = `
        <div class="ada-chatbot-meta">AI 챗봇</div>
        <div class="ada-chatbot-bubble">
          <span class="ada-chatbot-typing" aria-label="답변 생성 중">
            <span></span><span></span><span></span>
          </span>
        </div>
      `;
      messagesEl.appendChild(typingEl);
      scrollToBottom();
    }

    function setSending(nextState) {
      isSending = nextState;
      sendBtn.disabled = nextState;
      input.disabled = nextState;
    }

    async function loadHistory() {
      if (historyLoaded) return;
      historyLoaded = true;
      messagesEl.innerHTML = "";

      try {
        const res = await jsonFetch(`${getApiBase()}/chat/history?user_id=${user.id}`);
        const data = await res.json().catch(() => ({}));

        if (!res.ok) {
          renderWelcome();
          return;
        }

        const history = Array.isArray(data.history) ? data.history : [];
        if (history.length === 0) {
          renderWelcome();
          return;
        }

        history.forEach((item) => {
          renderMessage(item.role, item.message, item.created_at || "");
        });
      } catch (e) {
        renderWelcome();
      }
    }

    function openPanel() {
      isOpen = true;
      panel.classList.add("is-open");
      fab.setAttribute("aria-expanded", "true");
      loadHistory();
      setTimeout(() => input.focus(), 80);
    }

    function closePanel() {
      isOpen = false;
      panel.classList.remove("is-open");
      fab.setAttribute("aria-expanded", "false");
    }

    async function sendMessage(message) {
      const trimmed = String(message || "").trim();
      if (!trimmed || isSending) return;

      renderMessage("user", trimmed);
      input.value = "";
      setSending(true);
      setTyping(true);

      try {
        const res = await jsonFetch(`${getApiBase()}/chat`, {
          method: "POST",
          body: JSON.stringify({
            user_id: user.id,
            message: trimmed
          })
        });

        const data = await res.json().catch(() => ({}));
        setTyping(false);

        if (!res.ok) {
          renderMessage("assistant", data.detail || data.message || "챗봇 응답 중 서버 오류가 발생했습니다.");
          return;
        }

        renderMessage("assistant", data.reply || "응답 내용이 비어 있습니다.");
      } catch (e) {
        setTyping(false);
        renderMessage("assistant", "챗봇 요청 중 오류가 발생했습니다. API 주소와 EC2 백엔드 서버 상태를 확인해주세요.");
      } finally {
        setSending(false);
        input.focus();
      }
    }

    async function clearHistory() {
      if (!confirm("챗봇 대화 기록을 삭제하시겠습니까?")) return;

      try {
        const res = await jsonFetch(`${getApiBase()}/chat/history?user_id=${user.id}`, {
          method: "DELETE"
        });

        if (!res.ok) {
          renderMessage("assistant", "대화 기록 삭제 중 오류가 발생했습니다.");
          return;
        }

        messagesEl.innerHTML = "";
        renderMessage("assistant", "대화 기록을 삭제했어. 새로 궁금한 걸 물어봐줘.");
      } catch (e) {
        renderMessage("assistant", "대화 기록 삭제 요청 중 오류가 발생했습니다.");
      }
    }

    fab.addEventListener("click", () => {
      if (isOpen) {
        closePanel();
      } else {
        openPanel();
      }
    });

    closeBtn.addEventListener("click", closePanel);
    clearBtn.addEventListener("click", clearHistory);

    form.addEventListener("submit", (event) => {
      event.preventDefault();
      sendMessage(input.value);
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage(input.value);
      }
    });

    quickButtons.forEach((button) => {
      button.addEventListener("click", () => {
        const question = button.dataset.question || "";
        openPanel();
        sendMessage(question);
      });
    });
  }

  function runWhenReady(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  window.AppCommon = {
    getApiBase,
    escapeHtml,
    getLoggedInUser,
    saveLoggedInUser,
    saveAccessToken,
    getAccessToken,
    getAuthHeaders,
    clearLoggedInUser,
    requireLogin,
    redirectIfLoggedIn,
    logout,
    getUserId,
    updateUserChip,
    applyTheme,
    initTheme,
    toggleTheme,
    jsonFetch,
    initFloatingChatWidget
  };

  runWhenReady(initFloatingChatWidget);
})();
