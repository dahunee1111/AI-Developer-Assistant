/*
signup.html 안의 signup() 함수에서 회원가입 성공 후 이 두 줄을 추가하세요.

기존:
AppCommon.saveLoggedInUser(data.user);

수정:
AppCommon.saveLoggedInUser(data.user);
AppCommon.saveAccessToken(data.access_token);
*/

async function signup() {
  const username = document.getElementById("username").value.trim();
  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value.trim();
  const passwordConfirm = document.getElementById("passwordConfirm").value.trim();

  if (!username || !email || !password || !passwordConfirm) {
    setMessage("아이디, 이메일, 비밀번호를 모두 입력하세요.", "error");
    return;
  }

  if (password !== passwordConfirm) {
    setMessage("비밀번호가 일치하지 않습니다.", "error");
    return;
  }

  setMessage("회원가입 중...", "warning");

  try {
    const res = await fetch(`${API_BASE}/signup`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, email, password })
    });

    const data = await res.json();

    if (!data.user) {
      setMessage(data.message || "회원가입 실패", "error");
      return;
    }

    AppCommon.saveLoggedInUser(data.user);
    AppCommon.saveAccessToken(data.access_token);

    setMessage("회원가입 성공! 이동 중...", "success");

    setTimeout(() => {
      location.href = "index.html";
    }, 700);
  } catch (e) {
    setMessage("회원가입 중 오류가 발생했습니다.", "error");
  }
}
