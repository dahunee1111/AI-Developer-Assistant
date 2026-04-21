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

  function clearLoggedInUser() {
    localStorage.removeItem("loggedInUser");
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
      headers: {
        "Content-Type": "application/json",
        ...(options.headers || {})
      },
      ...options
    });
  }

  window.AppCommon = {
    getApiBase,
    escapeHtml,
    getLoggedInUser,
    saveLoggedInUser,
    clearLoggedInUser,
    requireLogin,
    redirectIfLoggedIn,
    logout,
    getUserId,
    updateUserChip,
    applyTheme,
    initTheme,
    toggleTheme,
    jsonFetch
  };
})();