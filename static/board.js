const state = {
  user: null,
  tasks: [],
  draggingTaskId: null,
  movingTaskIds: new Set()
};

const managerCreatePanel = document.getElementById("manager-create-panel");
const userChip = document.getElementById("user-chip");
const roleNote = document.getElementById("role-note");
const toast = document.getElementById("toast");

const todoColumn = document.getElementById("todo-column");
const inprogressColumn = document.getElementById("inprogress-column");
const doneColumn = document.getElementById("done-column");

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
  const payload = await response.json();
  if (!response.ok || payload.ok === false) {
    throw new Error(payload.error || "Request failed");
  }
  return payload;
}

function renderTaskCard(task) {
  const card = document.createElement("div");
  card.className = "task-card rounded-xl border border-zinc-200 bg-zinc-50 p-3 transition duration-150";
  card.dataset.id = task.id;
  card.draggable = true;
  if (state.movingTaskIds.has(task.id)) {
    card.classList.add("pointer-events-none", "opacity-60");
  }

  const dueDateHtml = task.due_date
    ? `<p class=\"mt-2 text-xs text-zinc-500\">Due: ${task.due_date}</p>`
    : "<p class=\"mt-2 text-xs text-zinc-400\">Due: Not set</p>";

  const controls = [];
  if (task.status !== "To Do") {
    controls.push(`<button data-next=\"To Do\" class=\"rounded-lg bg-zinc-200 px-2 py-1 text-xs font-medium\">Move To Do</button>`);
  }
  if (task.status !== "In Progress") {
    controls.push(`<button data-next=\"In Progress\" class=\"rounded-lg bg-amber-200 px-2 py-1 text-xs font-medium\">Move In Progress</button>`);
  }
  if (task.status !== "Done") {
    controls.push(`<button data-next=\"Done\" class=\"rounded-lg bg-emerald-200 px-2 py-1 text-xs font-medium\">Move Done</button>`);
  }

  card.innerHTML = `
    <h3 class="font-semibold text-zinc-900">${task.title}</h3>
    <p class="mt-1 text-xs text-zinc-600">Assigned: ${task.assigned_to}</p>
    ${dueDateHtml}
    <div class="mt-3 flex flex-wrap gap-2">${controls.join("")}</div>
  `;

  card.querySelectorAll("button[data-next]").forEach((button) => {
    if (state.movingTaskIds.has(task.id)) {
      button.disabled = true;
      button.classList.add("opacity-50", "cursor-not-allowed");
    }

    button.addEventListener("click", async () => {
      const nextStatus = button.dataset.next;
      try {
        await updateTaskStatus(card.dataset.id, nextStatus);
      } catch (error) {
        showToast(error.message, true);
      }
    });
  });

  card.addEventListener("dragstart", (event) => {
    if (state.movingTaskIds.has(card.dataset.id)) {
      event.preventDefault();
      return;
    }
    state.draggingTaskId = card.dataset.id;
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", card.dataset.id);
    card.classList.add("opacity-50", "scale-[0.98]", "shadow-xl");
  });

  card.addEventListener("dragend", () => {
    state.draggingTaskId = null;
    card.classList.remove("opacity-50", "scale-[0.98]", "shadow-xl");
  });

  return card;
}

function updateEmptyColumnState(columnElement) {
  const cards = Array.from(columnElement.children).filter((child) => child.classList.contains("task-card"));
  if (!cards.length) {
    columnElement.innerHTML = "<p class='text-sm text-zinc-400'>No tasks</p>";
  }
}

function setupDropzones() {
  const columns = [todoColumn, inprogressColumn, doneColumn];
  columns.forEach((column) => {
    column.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "move";
      column.classList.add("border-accent", "bg-accentSoft");
    });

    column.addEventListener("dragleave", () => {
      column.classList.remove("border-accent", "bg-accentSoft");
    });

    column.addEventListener("drop", async (event) => {
      event.preventDefault();
      column.classList.remove("border-accent", "bg-accentSoft");

      const taskId = event.dataTransfer.getData("text/plain") || state.draggingTaskId;
      const targetStatus = column.dataset.status;
      if (!taskId || !targetStatus) {
        return;
      }

      const task = state.tasks.find((item) => item.id === taskId);
      if (!task || task.status === targetStatus) {
        return;
      }

      try {
        await updateTaskStatus(taskId, targetStatus);
      } catch (error) {
        showToast(error.message, true);
      }
    });
  });
}

function renderBoard() {
  todoColumn.innerHTML = "";
  inprogressColumn.innerHTML = "";
  doneColumn.innerHTML = "";

  const columns = {
    "To Do": todoColumn,
    "In Progress": inprogressColumn,
    Done: doneColumn
  };

  state.tasks.forEach((task) => {
    const target = columns[task.status] || todoColumn;
    target.appendChild(renderTaskCard(task));
  });

  [todoColumn, inprogressColumn, doneColumn].forEach(updateEmptyColumnState);
}

function setUiForUser() {
  if (!state.user) {
    window.location.href = "/login";
    return;
  }

  userChip.textContent = `${state.user.email} (${state.user.role})`;

  if (state.user.role === "Manager") {
    managerCreatePanel.classList.remove("hidden");
    roleNote.textContent = "Manager view: you can see all tasks and create new assignments.";
  } else {
    managerCreatePanel.classList.add("hidden");
    roleNote.textContent = "Member view: you can only see tasks assigned to you.";
  }
}

async function loadTasks() {
  const payload = await api("/api/tasks", { method: "GET" });
  state.tasks = payload.tasks || [];
  renderBoard();
}

async function updateTaskStatus(taskId, status) {
  const previousTasks = state.tasks.map((task) => ({ ...task }));
  const target = state.tasks.find((task) => task.id === taskId);
  if (!target || target.status === status || state.movingTaskIds.has(taskId)) {
    return;
  }

  state.movingTaskIds.add(taskId);
  state.tasks = state.tasks.map((task) =>
    task.id === taskId
      ? {
          ...task,
          status,
          updated_at: new Date().toISOString()
        }
      : task
  );
  renderBoard();

  try {
    const payload = await api(`/api/tasks/${taskId}/status`, {
      method: "PUT",
      body: JSON.stringify({ status })
    });

    state.tasks = state.tasks.map((task) =>
      task.id === taskId ? payload.task : task
    );
    showToast(`Task moved to ${status}`);
  } catch (error) {
    state.tasks = previousTasks;
    showToast(`Move failed: ${error.message}`, true);
    throw error;
  } finally {
    state.movingTaskIds.delete(taskId);
    renderBoard();
  }
}

async function createTask(event) {
  event.preventDefault();
  const title = document.getElementById("task-title").value.trim();
  const assigned_to = document.getElementById("task-assigned-to").value.trim().toLowerCase();
  const due_date = document.getElementById("task-due-date").value || null;

  const payload = await api("/api/tasks", {
    method: "POST",
    body: JSON.stringify({ title, assigned_to, due_date, status: "To Do" })
  });

  state.tasks.unshift(payload.task);
  renderBoard();
  event.target.reset();
  showToast("Task created");
}

async function logout() {
  await api("/auth/logout", { method: "POST" });
  window.location.href = "/login";
}

async function initialize() {
  setupDropzones();

  document.getElementById("create-task-form").addEventListener("submit", async (event) => {
    try {
      await createTask(event);
    } catch (error) {
      showToast(error.message, true);
    }
  });

  document.getElementById("logout-btn").addEventListener("click", async () => {
    try {
      await logout();
    } catch (error) {
      showToast(error.message, true);
    }
  });

  try {
    const payload = await api("/auth/me", { method: "GET" });
    state.user = payload.user || null;
    setUiForUser();
    await loadTasks();
  } catch (error) {
    window.location.href = "/login";
  }
}

initialize();
