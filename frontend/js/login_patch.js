/*
login.html 안의 login() 함수에서 로그인 성공 후 이 두 줄을 추가하세요.

기존:
AppCommon.saveLoggedInUser(data.user);

수정:
AppCommon.saveLoggedInUser(data.user);
AppCommon.saveAccessToken(data.access_token);
*/

async function login() {
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();

  if (!email || !password) {
    setMessage("이메일과 비밀번호를 입력하세요.", "error");
    return;
  }

  setMessage("로그인 중...", "warning");

  try {
    const res = await fetch(`${API_BASE}/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });

    const data = await res.json();

    if (!data.user) {
      setMessage(data.message || "로그인 실패", "error");
      return;
    }

    AppCommon.saveLoggedInUser(data.user);
    AppCommon.saveAccessToken(data.access_token);

    setMessage("로그인 성공! 이동 중...", "success");

    setTimeout(() => {
      location.href = "index.html";
    }, 700);
  } catch (e) {
    setMessage("로그인 중 오류가 발생했습니다.", "error");
  }
}
