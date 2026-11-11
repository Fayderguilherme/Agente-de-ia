const API_URL = "/api/tasks";
const MAX_TASK_LENGTH = 500;
const API_UNAVAILABLE_MESSAGE =
  "API indisponível. Inicie o projeto com SRC\\start.bat e acesse http://127.0.0.1:8000/.";

const form = document.querySelector("#task-form");
const input = document.querySelector("#task-input");
const submitButton = document.querySelector("#submit-button");
const formMessage = document.querySelector("#form-message");
const characterCount = document.querySelector("#character-count");
const listStatus = document.querySelector("#list-status");
const taskList = document.querySelector("#task-list");
const taskCount = document.querySelector("#task-count");

let tasks = [];
let isSubmitting = false;
let deletingTaskId = null;
let isLoading = false;

function isTask(value) {
  return (
    value !== null &&
    typeof value === "object" &&
    (typeof value.id === "string" || typeof value.id === "number") &&
    typeof value.text === "string" &&
    typeof value.created_at === "string"
  );
}

async function request(url, options = {}) {
  if (window.location.protocol === "file:") {
    throw new Error(API_UNAVAILABLE_MESSAGE);
  }

  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new Error(API_UNAVAILABLE_MESSAGE);
  }

  if (!response.ok) {
    if (response.status === 403 || response.status === 404) {
      throw new Error(
        "Esta página não está sendo servida pelo back-end. Inicie SRC\\start.bat e acesse http://127.0.0.1:8000/.",
      );
    }

    let message = "Não foi possível concluir a solicitação. Tente novamente.";
    try {
      const payload = await response.json();
      if (typeof payload.error === "string") {
        message = payload.error;
      }
    } catch {
      // Use the generic message when the server does not return a JSON error.
    }
    throw new Error(message);
  }
  return response;
}

async function readJson(response, errorMessage) {
  try {
    return await response.json();
  } catch {
    throw new Error(errorMessage);
  }
}

function setFormMessage(message = "", kind = "") {
  formMessage.textContent = message;
  if (kind) {
    formMessage.dataset.kind = kind;
  } else {
    delete formMessage.dataset.kind;
  }
}

function updateFormState() {
  const text = input.value.trim();
  const length = Array.from(input.value).length;
  characterCount.textContent = `${length} / ${MAX_TASK_LENGTH}`;
  submitButton.disabled =
    isLoading ||
    isSubmitting ||
    text.length === 0 ||
    Array.from(text).length > MAX_TASK_LENGTH;
}

function updateTaskCount() {
  const count = tasks.length;
  taskCount.textContent = `${count} ${count === 1 ? "tarefa" : "tarefas"}`;
}

function makeTaskElement(task) {
  const item = document.createElement("li");
  item.className = "task-item";

  const content = document.createElement("div");
  content.className = "task-content";

  const dot = document.createElement("span");
  dot.className = "task-dot";
  dot.setAttribute("aria-hidden", "true");

  const copy = document.createElement("div");
  copy.className = "task-copy";

  const text = document.createElement("p");
  text.className = "task-text";
  text.textContent = task.text;
  copy.append(text);

  const createdAt = new Date(task.created_at);
  if (!Number.isNaN(createdAt.getTime())) {
    const date = document.createElement("time");
    date.className = "task-date";
    date.dateTime = task.created_at;
    date.textContent = createdAt.toLocaleString("pt-BR", {
      dateStyle: "medium",
      timeStyle: "short",
    });
    copy.append(date);
  }

  content.append(dot, copy);

  const deleteButton = document.createElement("button");
  deleteButton.className = "delete-button";
  deleteButton.type = "button";
  deleteButton.textContent = "Excluir";
  deleteButton.setAttribute("aria-label", `Excluir tarefa: ${task.text}`);
  deleteButton.disabled = String(task.id) === deletingTaskId;
  deleteButton.addEventListener("click", () => deleteTask(task, deleteButton));

  item.append(content, deleteButton);
  return item;
}

function renderTasks() {
  taskList.replaceChildren(...tasks.map(makeTaskElement));
  updateTaskCount();
}

function showListError(message) {
  listStatus.replaceChildren();
  listStatus.dataset.kind = "error";
  listStatus.append(document.createTextNode(message));

  const retryButton = document.createElement("button");
  retryButton.className = "retry-button";
  retryButton.type = "button";
  retryButton.textContent = "Tentar novamente";
  retryButton.addEventListener("click", loadTasks);
  listStatus.append(document.createElement("br"), retryButton);
}

async function loadTasks() {
  if (isLoading) return;
  isLoading = true;
  updateFormState();
  listStatus.hidden = false;
  listStatus.textContent = "Carregando suas tarefas...";
  delete listStatus.dataset.kind;

  try {
    const response = await request(API_URL);
    const payload = await readJson(response, "A API retornou uma resposta inválida.");
    if (!Array.isArray(payload) || !payload.every(isTask)) {
      throw new Error("A resposta da API não contém uma lista de tarefas válida.");
    }
    tasks = payload;
    renderTasks();
    if (tasks.length === 0) {
      listStatus.textContent = "Sua lista está vazia. Que tal começar por uma tarefa pequena?";
      listStatus.hidden = false;
    } else {
      listStatus.hidden = true;
    }
  } catch (error) {
    showListError(error.message);
  } finally {
    isLoading = false;
    updateFormState();
  }
}

async function addTask(event) {
  event.preventDefault();
  const text = input.value.trim();
  if (!text || Array.from(text).length > MAX_TASK_LENGTH || isSubmitting) {
    updateFormState();
    return;
  }

  isSubmitting = true;
  submitButton.querySelector("span").textContent = "Adicionando...";
  setFormMessage("");
  updateFormState();

  try {
    const response = await request(API_URL, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    const createdTask = await readJson(response, "A API retornou uma resposta inválida.");
    if (!isTask(createdTask)) {
      throw new Error("A resposta da API não contém a tarefa criada.");
    }

    tasks = [...tasks, createdTask];
    renderTasks();
    listStatus.hidden = true;
    input.value = "";
    setFormMessage("Tarefa adicionada à sua lista.", "success");
  } catch (error) {
    setFormMessage(error.message, "error");
  } finally {
    isSubmitting = false;
    submitButton.querySelector("span").textContent = "Adicionar";
    updateFormState();
  }
}

async function deleteTask(task, button) {
  if (deletingTaskId !== null) return;
  if (!window.confirm(`Excluir esta tarefa?\n\n${task.text}`)) return;

  deletingTaskId = String(task.id);
  button.disabled = true;
  setFormMessage("");

  try {
    await request(`${API_URL}/${encodeURIComponent(String(task.id))}`, {
      method: "DELETE",
    });
    tasks = tasks.filter((item) => String(item.id) !== deletingTaskId);
    renderTasks();
    if (tasks.length === 0) {
      listStatus.textContent = "Sua lista está vazia. Que tal começar por uma tarefa pequena?";
      delete listStatus.dataset.kind;
      listStatus.hidden = false;
    }
    setFormMessage("Tarefa excluída.", "success");
  } catch (error) {
    setFormMessage(error.message, "error");
  } finally {
    deletingTaskId = null;
    renderTasks();
  }
}

input.addEventListener("input", () => {
  setFormMessage();
  updateFormState();
});
form.addEventListener("submit", addTask);

updateFormState();
loadTasks();
