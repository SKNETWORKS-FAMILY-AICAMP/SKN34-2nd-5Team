const page = document.body.dataset.page;

function getCookie(name) {
  const match = document.cookie
    .split("; ")
    .find((entry) => entry.startsWith(`${encodeURIComponent(name)}=`));
  return match ? decodeURIComponent(match.split("=").slice(1).join("=")) : "";
}

function errorMessage(body, fallback = "요청을 처리하지 못했습니다.") {
  if (typeof body?.detail?.message === "string") return body.detail.message;
  if (typeof body?.detail === "string") return body.detail;
  if (Array.isArray(body?.detail)) return "입력 내용을 다시 확인해 주세요.";
  return fallback;
}

function showMessage(message, kind = "error") {
  const target = document.querySelector("#form-message");
  if (!target) return;
  target.textContent = message;
  target.className = `message ${kind}`;
  target.hidden = false;
}

async function apiFetch(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  const csrf = getCookie("rr_auth_csrf");
  if (csrf && options.method && options.method !== "GET") headers.set("X-CSRF-Token", csrf);
  const response = await fetch(path, { ...options, headers, credentials: "include" });
  const body = response.status === 204 ? null : await response.json().catch(() => null);
  if (!response.ok) {
    const error = new Error(errorMessage(body));
    error.status = response.status;
    error.code = body?.detail?.code;
    throw error;
  }
  return body;
}

function setNavigationState(isAuthenticated, user = null) {
  const guestNavigation = document.querySelector('[data-nav-state="guest"]');
  const memberNavigation = document.querySelector('[data-nav-state="member"]');
  const homeLink = document.querySelector("#auth-home-link");
  if (!guestNavigation || !memberNavigation) return;
  guestNavigation.hidden = isAuthenticated;
  memberNavigation.hidden = !isAuthenticated;
  if (homeLink) {
    homeLink.href = isAuthenticated ? "/" : "/auth/login";
  }
}

async function syncNavigationState() {
  try {
    const user = await apiFetch("/auth/api/me");
    setNavigationState(true, user);
    if (page === "login" || page === "signup") {
      window.location.replace("/");
    }
  } catch {
    setNavigationState(false);
  }
}

syncNavigationState();

function setSubmitting(form, submitting) {
  const button = form.querySelector('button[type="submit"]');
  if (!button) return;
  button.disabled = submitting;
  button.dataset.originalText ||= button.textContent;
  button.textContent = submitting ? "처리 중..." : button.dataset.originalText;
}

if (page === "signup") {
  const form = document.querySelector("#signup-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    if (data.password !== data.password_confirm) {
      showMessage("비밀번호 확인이 일치하지 않습니다.");
      return;
    }
    delete data.password_confirm;
    setSubmitting(form, true);
    try {
      const result = await apiFetch("/auth/api/register", {
        method: "POST",
        body: JSON.stringify(data),
      });
      sessionStorage.setItem("pendingEmail", result.user.email);
      window.location.assign("/auth/pending");
    } catch (error) {
      showMessage(error.message);
    } finally {
      setSubmitting(form, false);
    }
  });
}

if (page === "login") {
  const form = document.querySelector("#login-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const data = Object.fromEntries(new FormData(form));
    setSubmitting(form, true);
    try {
      const result = await apiFetch("/auth/api/login", {
        method: "POST",
        body: JSON.stringify(data),
      });
      window.location.assign(result.redirect_to);
    } catch (error) {
      showMessage(error.message, error.code === "approval_pending" ? "info" : "error");
    } finally {
      setSubmitting(form, false);
    }
  });
}

if (page === "pending") {
  const email = sessionStorage.getItem("pendingEmail");
  if (email) document.querySelector("#pending-email").textContent = email;
}

async function logout() {
  try {
    await apiFetch("/auth/api/logout", { method: "POST" });
  } finally {
    window.location.assign("/auth/login");
  }
}

document.querySelectorAll('[data-action="logout"]').forEach((button) => {
  button.addEventListener("click", logout);
});

document.querySelectorAll('[data-action="toggle-password"]').forEach((button) => {
  button.addEventListener("click", () => {
    const input = button.closest("label").querySelector("input");
    const revealing = input.type === "password";
    input.type = revealing ? "text" : "password";
    button.textContent = revealing ? "숨기기" : "보기";
    button.setAttribute("aria-pressed", String(revealing));
  });
});

if (page === "profile") {
  apiFetch("/auth/api/me")
    .then((user) => {
      ["full_name", "email", "organization", "requested_role", "access_role"].forEach((field) => {
        const target = document.querySelector(`[data-field="${field}"]`);
        if (target) target.textContent = user[field] || "-";
      });
    })
    .catch(() => window.location.replace("/auth/login"));
}

function appendTextCell(row, value, className = "") {
  const cell = document.createElement("td");
  if (className) cell.className = className;
  cell.textContent = value || "-";
  row.appendChild(cell);
  return cell;
}

const assignableRoles = [
  { value: "VIEWER", label: "VIEWER · 조회 전용" },
  { value: "OPERATOR", label: "OPERATOR · 운영 담당" },
];

function createRoleSelect(user, selectedRole = "VIEWER") {
  const select = document.createElement("select");
  select.className = "role-select";
  select.setAttribute("aria-label", `${user.full_name} 권한`);
  assignableRoles.forEach(({ value, label }) => {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = label;
    option.selected = value === selectedRole;
    select.appendChild(option);
  });
  return select;
}

function formatDateTime(value) {
  if (!value) return "-";
  const normalized = value.endsWith("Z") ? value : `${value}Z`;
  return new Date(normalized).toLocaleString("ko-KR");
}

function renderPendingUsers(users) {
  const tbody = document.querySelector("#pending-users");
  tbody.replaceChildren();
  if (!users.length) {
    const row = document.createElement("tr");
    const cell = appendTextCell(row, "현재 승인 대기 중인 가입 신청이 없습니다.", "empty-cell");
    cell.colSpan = 6;
    tbody.appendChild(row);
    return;
  }

  users.forEach((user) => {
    const row = document.createElement("tr");
    const applicantCell = document.createElement("td");
    const name = document.createElement("strong");
    const email = document.createElement("small");
    name.textContent = user.full_name;
    email.textContent = user.email;
    applicantCell.append(name, email);
    row.appendChild(applicantCell);
    appendTextCell(row, `${user.organization || "소속 미입력"} · ${user.requested_role}`);
    appendTextCell(row, user.signup_reason || "가입 사유 미입력");
    appendTextCell(row, formatDateTime(user.created_at));

    const roleCell = document.createElement("td");
    const roleSelect = createRoleSelect(user, "VIEWER");
    roleCell.appendChild(roleSelect);
    row.appendChild(roleCell);

    const actions = document.createElement("td");
    actions.className = "row-actions";
    const approve = document.createElement("button");
    approve.type = "button";
    approve.className = "approve-button";
    approve.textContent = "승인";
    approve.addEventListener("click", () => decide(user, "approve", approve, roleSelect));
    const reject = document.createElement("button");
    reject.type = "button";
    reject.className = "reject-button";
    reject.textContent = "거절";
    reject.addEventListener("click", () => decide(user, "reject", reject, roleSelect));
    actions.append(approve, reject);
    row.appendChild(actions);
    tbody.appendChild(row);
  });
}

function renderApprovedUsers(users) {
  const tbody = document.querySelector("#approved-users");
  tbody.replaceChildren();
  if (!users.length) {
    const row = document.createElement("tr");
    const cell = appendTextCell(row, "현재 승인 완료된 일반 계정이 없습니다.", "empty-cell");
    cell.colSpan = 5;
    tbody.appendChild(row);
    return;
  }

  users.forEach((user) => {
    const row = document.createElement("tr");
    const memberCell = document.createElement("td");
    const name = document.createElement("strong");
    const email = document.createElement("small");
    name.textContent = user.full_name;
    email.textContent = user.email;
    memberCell.append(name, email);
    row.appendChild(memberCell);
    appendTextCell(row, `${user.organization || "소속 미입력"} · ${user.requested_role}`);
    appendTextCell(row, formatDateTime(user.approved_at));

    const roleCell = document.createElement("td");
    const roleSelect = createRoleSelect(user, user.access_role || "VIEWER");
    roleCell.appendChild(roleSelect);
    row.appendChild(roleCell);

    const actionCell = document.createElement("td");
    const saveButton = document.createElement("button");
    saveButton.type = "button";
    saveButton.className = "role-button";
    saveButton.textContent = "권한 변경";
    saveButton.addEventListener("click", () => updateRole(user, roleSelect, saveButton));
    actionCell.appendChild(saveButton);
    row.appendChild(actionCell);
    tbody.appendChild(row);
  });
}

async function loadAdminUsers() {
  const refresh = document.querySelector("#refresh-users");
  refresh.disabled = true;
  refresh.textContent = "전체 조회 중...";
  try {
    const [pending, approved] = await Promise.all([
      apiFetch("/auth/api/admin/users?status=PENDING"),
      apiFetch("/auth/api/admin/users?status=APPROVED"),
    ]);
    renderPendingUsers(pending.items);
    renderApprovedUsers(approved.items);
    document.querySelector("#pending-count").textContent = pending.total.toLocaleString("ko-KR");
    document.querySelector("#approved-count").textContent = approved.total.toLocaleString("ko-KR");
    document.querySelector("#last-refreshed").textContent = new Date().toLocaleTimeString("ko-KR");
  } catch (error) {
    if (error.status === 401 || error.status === 403) {
      window.location.replace("/auth/login");
      return;
    }
    showMessage(error.message);
  } finally {
    refresh.disabled = false;
    refresh.textContent = "전체 새로고침";
  }
}

async function decide(user, action, button, roleSelect) {
  const label = action === "approve" ? "승인" : "거절";
  const roleLabel = assignableRoles.find(({ value }) => value === roleSelect.value)?.label;
  const question = action === "approve"
    ? `${user.full_name} 계정을 ${roleLabel} 권한으로 승인하시겠습니까?`
    : `${user.full_name} 계정의 가입 신청을 거절하시겠습니까?`;
  if (!window.confirm(question)) return;
  button.disabled = true;
  try {
    const payload = { note: `관리자 화면에서 ${label}` };
    if (action === "approve") payload.access_role = roleSelect.value;
    await apiFetch(`/auth/api/admin/users/${user.id}/${action}`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    showMessage(`가입 신청을 ${label}했습니다.`, "success");
    await loadAdminUsers();
  } catch (error) {
    showMessage(error.message);
    button.disabled = false;
  }
}

async function updateRole(user, roleSelect, button) {
  const roleLabel = assignableRoles.find(({ value }) => value === roleSelect.value)?.label;
  if (user.access_role === roleSelect.value) {
    showMessage("현재 권한과 동일합니다.", "info");
    return;
  }
  if (!window.confirm(`${user.full_name} 계정의 권한을 ${roleLabel}(으)로 변경하시겠습니까?`)) return;
  button.disabled = true;
  try {
    await apiFetch(`/auth/api/admin/users/${user.id}/role`, {
      method: "PATCH",
      body: JSON.stringify({
        access_role: roleSelect.value,
        note: "관리자 화면에서 권한 변경",
      }),
    });
    showMessage(`${user.full_name} 계정의 권한을 변경했습니다.`, "success");
    await loadAdminUsers();
  } catch (error) {
    showMessage(error.message);
    button.disabled = false;
  }
}

if (page === "admin") {
  document.querySelector("#refresh-users").addEventListener("click", loadAdminUsers);
  apiFetch("/auth/api/me")
    .then((user) => {
      if (!user.is_admin) throw Object.assign(new Error("관리자 권한이 필요합니다."), { status: 403 });
      return loadAdminUsers();
    })
    .catch(() => window.location.replace("/auth/login"));
}
