const state = {
  registerEmail: "",
  loginEmail: ""
};

const toast = document.getElementById("toast");

function showToast(message, isError = false) {
  toast.textContent = message;
  toast.classList.remove("hidden");
  toast.classList.toggle("bg-red-600", isError);
  toast.classList.toggle("bg-zinc-900", !isError);
  window.setTimeout(() => toast.classList.add("hidden"), 2500);
}

async function api(url, options = {}) {
  const config = {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    },
    credentials: "same-origin",
    ...options
  };

  const response = await fetch(url, config);
  const contentType = response.headers.get("content-type") || "";
  let payload = null;

  if (contentType.includes("application/json")) {
    payload = await response.json();
  } else {
    const text = await response.text();
    const compact = (text || "").replace(/\s+/g, " ").trim();
    throw new Error(compact ? `Server returned non-JSON response: ${compact.slice(0, 120)}` : "Server returned non-JSON response");
  }

  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || payload.message || "Request failed");
  }
  return payload;
}

function wireRegisterForms() {
  const requestForm = document.getElementById("register-request-form");
  const verifyForm = document.getElementById("register-verify-form");
  if (!requestForm || !verifyForm) {
    return;
  }

  requestForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("register-email").value.trim().toLowerCase();
    const role = document.getElementById("register-role").value;

    try {
      const payload = await api("/auth/register/request-otp", {
        method: "POST",
        body: JSON.stringify({ email, role })
      });

      state.registerEmail = email;
      document.getElementById("register-otp").focus();
      showToast(payload.message || "Registration OTP sent");
    } catch (error) {
      showToast(error.message, true);
    }
  });

  verifyForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const otp = document.getElementById("register-otp").value.trim();
    const email = state.registerEmail || document.getElementById("register-email").value.trim().toLowerCase();

    try {
      await api("/auth/register/verify", {
        method: "POST",
        body: JSON.stringify({ email, otp })
      });
      window.location.href = "/dashboard";
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

function wireLoginForms() {
  const requestForm = document.getElementById("login-request-form");
  const verifyForm = document.getElementById("login-verify-form");
  if (!requestForm || !verifyForm) {
    return;
  }

  requestForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const email = document.getElementById("login-email").value.trim().toLowerCase();

    try {
      const payload = await api("/auth/login/request-otp", {
        method: "POST",
        body: JSON.stringify({ email })
      });

      state.loginEmail = email;
      document.getElementById("login-otp").focus();
      showToast(payload.message || "Login OTP sent");
    } catch (error) {
      showToast(error.message, true);
    }
  });

  verifyForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const otp = document.getElementById("login-otp").value.trim();
    const email = state.loginEmail || document.getElementById("login-email").value.trim().toLowerCase();

    try {
      await api("/auth/login/verify", {
        method: "POST",
        body: JSON.stringify({ email, otp })
      });
      window.location.href = "/dashboard";
    } catch (error) {
      showToast(error.message, true);
    }
  });
}

async function initialize() {
  try {
    const payload = await api("/auth/me", { method: "GET" });
    if (payload.user) {
      window.location.href = "/dashboard";
      return;
    }
  } catch (error) {
    // No active session; stay on auth pages.
  }

  wireRegisterForms();
  wireLoginForms();
}

initialize();
