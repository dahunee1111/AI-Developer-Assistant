(function () {
  const LOCAL_API = "http://127.0.0.1:8000";
  API_BASE: http://52.63.38.2:8000;

  const hostname = window.location.hostname;

  const isLocalLike =
    hostname === "127.0.0.1" ||
    hostname === "localhost";

  window.APP_CONFIG = {
    API_BASE: isLocalLike ? LOCAL_API : PROD_API
  };

  console.log("API_BASE:", window.APP_CONFIG.API_BASE);
})();
