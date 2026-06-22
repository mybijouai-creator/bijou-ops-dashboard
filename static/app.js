async function fetchJSON(url) {
    try {
        const res = await fetch(url);
        return await res.json();
    } catch (e) {
        return { error: e.message };
    }
}

function formatDate(iso) {
    if (!iso) return "N/A";
    const d = new Date(iso);
    return d.toLocaleString();
}

async function loadPublora() {
    const el = document.getElementById("publora-posts");
    const data = await fetchJSON("/api/publora/posts");
    if (data.error) {
        el.innerHTML = `<div class="error">Error: ${data.error}</div>`;
        return;
    }
    if (!data.posts || data.posts.length === 0) {
        el.innerHTML = "<p class=\"text-gray-500\">No scheduled posts.</p>";
        return;
    }
    el.innerHTML = data.posts.map(p => `
        <div class="border-b last:border-0 py-3">
            <p class="text-sm text-gray-800">${p.content}...</p>
            <div class="mt-1 text-xs text-gray-500 flex justify-between">
                <span>${p.status} • ${p.platforms.join(", ")}</span>
                <span>${formatDate(p.scheduledTime)}</span>
            </div>
        </div>
    `).join("");
}

async function loadGitHub() {
    const el = document.getElementById("github-commits");
    const data = await fetchJSON("/api/github/commits");
    if (data.error) {
        el.innerHTML = `<div class="error">Error: ${data.error}</div>`;
        return;
    }
    el.innerHTML = data.commits.map(c => `
        <div class="border-b last:border-0 py-2">
            <p class="text-sm font-medium text-gray-900">${c.message}</p>
            <p class="text-xs text-gray-500">${c.author} • ${c.sha} • ${formatDate(c.date)}</p>
        </div>
    `).join("");
}

async function loadMonday() {
    const el = document.getElementById("monday-tasks");
    const data = await fetchJSON("/api/monday/tasks");
    if (data.error) {
        el.innerHTML = `<div class="error">Error: ${data.error}</div>`;
        return;
    }
    if (!data.tasks || data.tasks.length === 0) {
        el.innerHTML = "<p class=\"text-gray-500\">No tasks found.</p>";
        return;
    }
    el.innerHTML = data.tasks.map(t => `
        <div class="border-b last:border-0 py-2">
            <p class="text-sm font-medium text-gray-900">${t.name}</p>
            <p class="text-xs text-gray-500">${t.status || "No status"} • ${formatDate(t.updated_at)}</p>
        </div>
    `).join("");
}

async function loadAgentMail() {
    const el = document.getElementById("agentmail");
    const data = await fetchJSON("/api/agentmail/unread");
    if (data.error) {
        el.innerHTML = `<div class="error">Error: ${data.error}</div>`;
        return;
    }
    let html = `<div class="text-2xl font-bold text-blue-600">${data.unread_count} unread</div>`;
    html += `<p class="text-xs text-gray-500 mb-3">${data.total} total messages</p>`;
    if (data.latest && data.latest.length > 0) {
        html += `<div class="text-sm">${data.latest.map(m => `
            <div class="border-b last:border-0 py-1">
                <span class="font-medium">${m.from}</span>
                <span class="text-gray-600">${m.subject}</span>
            </div>
        `).join("")}</div>`;
    }
    el.innerHTML = html;
}

async function loadAll() {
    await Promise.all([loadPublora(), loadGitHub(), loadMonday(), loadAgentMail()]);
    document.getElementById("last-refresh").textContent = "Last refreshed: " + new Date().toLocaleString();
}

loadAll();
setInterval(loadAll, 30000);
