const API_URL = "http://localhost:5000/tasks";
let currentPage = 1;
let totalPages = 1;

function renderTasks(tasks) {
    const taskList = document.getElementById("taskList");
    taskList.innerHTML = "";

    if (!tasks || tasks.length === 0) {
        taskList.innerHTML = "<li class='empty'>Niciun task găsit.</li>";
        return;
    }

    tasks.forEach(task => {
        const li = document.createElement("li");
        li.className = task.completed ? "completed" : "";

        const info = document.createElement("div");
        info.className = "task-info";
        info.innerHTML = `<strong>#${task.id} ${task.title}</strong>` +
            (task.description ? `<p>${task.description}</p>` : "");

        const actions = document.createElement("div");
        actions.className = "actions";

        const completeBtn = document.createElement("button");
        completeBtn.textContent = task.completed ? "Undo" : "✓ Complete";
        completeBtn.className = task.completed ? "secondary" : "success";
        completeBtn.onclick = () => toggleTask(task.id, !task.completed);

        const editBtn = document.createElement("button");
        editBtn.textContent = "Edit";
        editBtn.onclick = () => editTask(task.id, task.title, task.description);

        const deleteBtn = document.createElement("button");
        deleteBtn.textContent = "Delete";
        deleteBtn.className = "danger";
        deleteBtn.onclick = () => deleteTask(task.id);

        actions.appendChild(completeBtn);
        actions.appendChild(editBtn);
        actions.appendChild(deleteBtn);

        li.appendChild(info);
        li.appendChild(actions);
        taskList.appendChild(li);
    });
}

// TODO 2: GET /tasks
async function fetchAllTasks() {
    const response = await fetch(API_URL);
    const result = await response.json();
    if (result.status) {
        renderTasks(result.data);
        document.getElementById("pageInfo").textContent = `Toate (${result.data.length})`;
    }
}

// TODO 9: GET /tasks/paginate
async function changePage(page) {
    if (page < 1) return;
    const limit = document.getElementById("limitSelect").value;
    const response = await fetch(`${API_URL}/paginate?page=${page}&limit=${limit}`);
    const result = await response.json();

    if (result.status) {
        currentPage = result.page || page;
        totalPages = result.pages || 1;
        renderTasks(result.data);
        document.getElementById("pageInfo").textContent =
            `Pagina ${currentPage} din ${totalPages || 1} (Total: ${result.total ?? result.data.length})`;
        document.getElementById("prevBtn").disabled = currentPage <= 1;
        document.getElementById("nextBtn").disabled = currentPage >= totalPages;
    }
}

// TODO 1: POST /tasks
async function addTask() {
    const titleInput = document.getElementById("taskInput");
    const descInput = document.getElementById("descInput");
    const title = titleInput.value.trim();
    const description = descInput.value.trim();

    const response = await fetch(API_URL, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title, description })
    });
    const result = await response.json();

    if (!response.ok) {
        alert(result.error || "Eroare la adăugare");
        return;
    }

    titleInput.value = "";
    descInput.value = "";
    fetchAllTasks();
}

// TODO 4: PUT /tasks/<id>
async function toggleTask(id, completed) {
    await fetch(`${API_URL}/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ completed })
    });
    fetchAllTasks();
}

async function editTask(id, currentTitle, currentDesc) {
    const newTitle = prompt("Modifică titlul:", currentTitle);
    if (newTitle === null) return;
    const newDesc = prompt("Modifică descrierea:", currentDesc || "");

    const response = await fetch(`${API_URL}/${id}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ title: newTitle, description: newDesc })
    });
    const result = await response.json();
    if (!response.ok) {
        alert(result.error || "Eroare la actualizare");
    }
    fetchAllTasks();
}

// TODO 5: DELETE /tasks/<id>
async function deleteTask(id) {
    await fetch(`${API_URL}/${id}`, { method: "DELETE" });
    fetchAllTasks();
}

// TODO 8: GET /tasks/filter
async function filterTasks() {
    const val = document.getElementById("filterSelect").value;
    if (val === "all") {
        fetchAllTasks();
        return;
    }
    const response = await fetch(`${API_URL}/filter?completed=${val}`);
    const result = await response.json();
    if (result.status) {
        renderTasks(result.data);
        document.getElementById("pageInfo").textContent = `Filtrate (${result.data.length})`;
    }
}

// TODO 10: GET /tasks/search
async function searchTasks() {
    const q = document.getElementById("searchInput").value.trim();
    if (!q) {
        fetchAllTasks();
        return;
    }
    const response = await fetch(`${API_URL}/search?q=${encodeURIComponent(q)}`);
    const result = await response.json();
    if (result.status) {
        renderTasks(result.data);
        document.getElementById("pageInfo").textContent = `Rezultate căutare (${result.data.length})`;
    }
}

function resetView() {
    document.getElementById("searchInput").value = "";
    document.getElementById("filterSelect").value = "all";
    fetchAllTasks();
}

document.addEventListener("DOMContentLoaded", fetchAllTasks);