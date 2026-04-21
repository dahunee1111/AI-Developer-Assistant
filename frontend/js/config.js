(function () {
  const LOCAL_API = "http://127.0.0.1:8000";
  const PROD_API = "https://ai-developer-assistant-0wz0.onrender.com";

  const forceLocal = localStorage.getItem("useLocalApi") === "true";

  const protocol = window.location.protocol;
  const hostname = window.location.hostname;

  const isLocalLike =
    protocol === "file:" ||
    hostname === "127.0.0.1" ||
    hostname === "localhost" ||
    hostname === "";

  window.APP_CONFIG = {
    API_BASE: (forceLocal || isLocalLike) ? LOCAL_API : PROD_API
  };

  console.log("API_BASE:", window.APP_CONFIG.API_BASE);
})();
