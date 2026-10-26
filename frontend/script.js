const API_BASE = "http://127.0.0.1:8000";

const loginSection = document.getElementById("loginSection");
const dashboardSection = document.getElementById("dashboardSection");
const loginForm = document.getElementById("loginForm");
const ticketForm = document.getElementById("ticketForm");
const loginMessage = document.getElementById("loginMessage");
const ticketMessage = document.getElementById("ticketMessage");
const userLabel = document.getElementById("userLabel");
const logoutBtn = document.getElementById("logoutBtn");

let accessToken = localStorage.getItem("helpdeskToken") || "";
let currentUser = null;

function showMessage(element, message, isError = false) {
    element.textContent = message;
    element.className = `message ${isError ? "error" : "success"}`;
}

async function apiRequest(path, options = {}) {
    const headers = {
        ...(options.headers || {})
    };

    if (accessToken) {
        headers.Authorization = `Bearer ${accessToken}`;
    }

    if (options.body && !(options.body instanceof FormData)) {
        headers["Content-Type"] = "application/json";
    }

    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers
    });

    const text = await response.text();
    let data = null;

    try {
        data = text ? JSON.parse(text) : null;
    } catch {
        data = text;
    }

    if (!response.ok) {
        const detail =
            data && typeof data === "object"
                ? data.detail || data.message
                : data;

        throw new Error(detail || `Request failed (${response.status})`);
    }

    return data;
}

function showDashboard() {
    loginSection.classList.add("hidden");
    dashboardSection.classList.remove("hidden");
    logoutBtn.classList.remove("hidden");
}

function showLogin() {
    loginSection.classList.remove("hidden");
    dashboardSection.classList.add("hidden");
    logoutBtn.classList.add("hidden");
    userLabel.textContent = "Guest";
}

async function loadCurrentUser() {
    currentUser = await apiRequest("/api/auth/me");
    userLabel.textContent =
        currentUser.full_name || currentUser.email || "Logged in";
}

loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    loginMessage.textContent = "";

    const email = document.getElementById("email").value.trim();
    const password = document.getElementById("password").value;

    const formData = new URLSearchParams();
    formData.append("username", email);
    formData.append("password", password);

    try {
        const response = await fetch(`${API_BASE}/api/auth/login`, {
            method: "POST",
            headers: {
                "Content-Type": "application/x-www-form-urlencoded"
            },
            body: formData
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || "Login failed.");
        }

        accessToken = data.access_token;
        localStorage.setItem("helpdeskToken", accessToken);

        await loadCurrentUser();
        showDashboard();
        showMessage(loginMessage, "");

        await loadDashboardData();
    } catch (error) {
        showMessage(loginMessage, error.message, true);
    }
});

async function loadTickets() {
    const tickets = await apiRequest("/api/tickets/");
    const ticketList = document.getElementById("ticketList");

    ticketList.replaceChildren();

    document.getElementById("totalTickets").textContent = tickets.length;
    document.getElementById("openTickets").textContent =
        tickets.filter(ticket => ticket.status === "Open").length;

    if (tickets.length === 0) {
        ticketList.innerHTML =
            '<p class="empty-state">No tickets found for this account.</p>';
        return;
    }

    tickets.forEach(ticket => {
        const item = document.createElement("article");
        item.className = "ticket-item";

        const title = document.createElement("h4");
        title.textContent = `#${ticket.id} — ${ticket.title}`;

        const description = document.createElement("p");
        description.textContent = ticket.description || "No description provided.";

        const meta = document.createElement("div");
        meta.className = "ticket-meta";

        [
            ["status", ticket.status],
            ["priority", ticket.priority],
            ["", ticket.category]
        ].forEach(([className, value]) => {
            const badge = document.createElement("span");
            badge.className = `badge ${className}`;
            badge.textContent = value || "Unknown";
            meta.appendChild(badge);
        });

        item.append(title, description, meta);
        ticketList.appendChild(item);
    });
}

ticketForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    ticketMessage.textContent = "";

    const payload = {
        title: document.getElementById("ticketTitle").value.trim(),
        description: document.getElementById("description").value.trim(),
        category: document.getElementById("category").value,
        priority: document.getElementById("priority").value
    };

    try {
        await apiRequest("/api/tickets/", {
            method: "POST",
            body: JSON.stringify(payload)
        });

        ticketForm.reset();
        showMessage(ticketMessage, "Ticket created successfully!");
        await loadDashboardData();
    } catch (error) {
        showMessage(ticketMessage, error.message, true);
    }
});

async function loadNotifications() {
    const notifications = await apiRequest("/api/notifications/");
    const notificationList = document.getElementById("notificationList");

    notificationList.replaceChildren();

    document.getElementById("notificationCount").textContent =
        notifications.filter(item => !item.is_read).length;

    if (notifications.length === 0) {
        notificationList.innerHTML =
            '<p class="empty-state">No notifications yet.</p>';
        return;
    }

    notifications.forEach(notification => {
        const item = document.createElement("article");
        item.className = "notification-item";

        const title = document.createElement("h4");
        title.textContent = notification.title;

        const message = document.createElement("p");
        message.textContent = notification.message;

        item.append(title, message);

        if (!notification.is_read) {
            const badge = document.createElement("span");
            badge.className = "badge unread";
            badge.textContent = "Unread";
            item.appendChild(badge);

            const button = document.createElement("button");
            button.className = "read-btn";
            button.textContent = "Mark as read";

            button.addEventListener("click", async () => {
                try {
                    await apiRequest(
                        `/api/notifications/${notification.id}/read`,
                        { method: "PATCH" }
                    );
                    await loadNotifications();
                } catch (error) {
                    alert(error.message);
                }
            });

            item.appendChild(button);
        }

        notificationList.appendChild(item);
    });
}

async function loadDashboardData() {
    try {
        await Promise.all([loadTickets(), loadNotifications()]);
    } catch (error) {
        alert(`Could not load dashboard data: ${error.message}`);
    }
}

document.getElementById("refreshBtn").addEventListener("click", loadDashboardData);

logoutBtn.addEventListener("click", () => {
    accessToken = "";
    currentUser = null;
    localStorage.removeItem("helpdeskToken");
    showLogin();
});

async function restoreSession() {
    if (!accessToken) {
        showLogin();
        return;
    }

    try {
        await loadCurrentUser();
        showDashboard();
        await loadDashboardData();
    } catch {
        accessToken = "";
        localStorage.removeItem("helpdeskToken");
        showLogin();
    }
}
// Load messages for a selected ticket
async function loadMessages() {
    const ticketId = document.getElementById("conversationTicketId").value;
    const messageList = document.getElementById("messageList");
    const feedback = document.getElementById("messageFeedback");

    feedback.textContent = "";
    messageList.replaceChildren();

    if (!ticketId || Number(ticketId) < 1) {
        messageList.textContent = "Please enter a valid ticket ID.";
        return;
    }

    try {
        const messages = await apiRequest(
            `/api/tickets/${ticketId}/messages/`
        );

        if (!Array.isArray(messages) || messages.length === 0) {
            messageList.textContent = "No messages yet. Send the first reply!";
            return;
        }

        messages.forEach(message => {
            const item = document.createElement("article");
            item.className = "message-item";

            const content = document.createElement("p");
            content.textContent = message.content;

            const meta = document.createElement("div");
            meta.className = "message-meta";

            const date = message.created_at
                ? new Date(message.created_at).toLocaleString()
                : "Date unavailable";

            meta.textContent =
                `Message #${message.id} · Sender ID: ${message.sender_id} · ${date}`;

            item.append(content, meta);
            messageList.appendChild(item);
        });
    } catch (error) {
        messageList.textContent = error.message;
    }
}

// Load conversation when the button is clicked
document.getElementById("loadMessagesBtn").addEventListener(
    "click",
    loadMessages
);

// Send a reply to the selected ticket
document.getElementById("messageForm").addEventListener(
    "submit",
    async (event) => {
        event.preventDefault();

        const ticketId =
            document.getElementById("conversationTicketId").value;
        const messageText = document.getElementById("messageText");
        const feedback = document.getElementById("messageFeedback");
        const content = messageText.value.trim();

        feedback.textContent = "";

        if (!ticketId || Number(ticketId) < 1) {
            feedback.textContent = "Please enter a valid ticket ID.";
            return;
        }

        if (!content) {
            feedback.textContent = "Please write a message first.";
            return;
        }

        try {
            await apiRequest(`/api/tickets/${ticketId}/messages/`, {
                method: "POST",
                body: JSON.stringify({ content })
            });

            messageText.value = "";
            showMessage(feedback, "Reply sent successfully!");

            await loadMessages();
            await loadNotifications();
        } catch (error) {
            feedback.textContent = `Could not send reply: ${error.message}`;
        }
    }
);
// Upload an attachment to a ticket
document.getElementById("attachmentForm").addEventListener(
    "submit",
    async (event) => {
        event.preventDefault();

        const ticketId =
            document.getElementById("attachmentTicketId").value;
        const fileInput = document.getElementById("attachmentFile");
        const feedback = document.getElementById("attachmentFeedback");
        const file = fileInput.files[0];

        feedback.textContent = "";

        if (!ticketId || Number(ticketId) < 1) {
            feedback.textContent = "Please enter a valid ticket ID.";
            return;
        }

        if (!file) {
            feedback.textContent = "Please choose a file.";
            return;
        }

        const allowedExtensions = ["pdf", "png", "jpg", "jpeg", "txt"];
        const extension = file.name.split(".").pop().toLowerCase();

        if (!allowedExtensions.includes(extension)) {
            feedback.textContent =
                "Allowed file types: PDF, PNG, JPG, JPEG, and TXT.";
            return;
        }

        if (file.size > 5 * 1024 * 1024) {
            feedback.textContent = "File must be 5 MB or smaller.";
            return;
        }

        const formData = new FormData();
        formData.append("file", file);

        try {
            await apiRequest(
                `/api/tickets/${ticketId}/attachments/`,
                {
                    method: "POST",
                    body: formData
                }
            );

            feedback.textContent = "Attachment uploaded successfully!";
            fileInput.value = "";
        } catch (error) {
            feedback.textContent =
                `Upload failed: ${error.message}`;
        }
    }
);
document.getElementById("loadAttachmentsBtn").addEventListener(
    "click",
    async () => {
        const ticketId =
            document.getElementById("attachmentTicketId").value;
        const attachmentList =
            document.getElementById("attachmentList");

        attachmentList.replaceChildren();

        if (!ticketId || Number(ticketId) < 1) {
            attachmentList.textContent = "Please enter a valid ticket ID.";
            return;
        }

        try {
            const attachments = await apiRequest(
                `/api/tickets/${ticketId}/attachments/`
            );

            if (!Array.isArray(attachments) || attachments.length === 0) {
                attachmentList.textContent =
                    "No attachments found for this ticket.";
                return;
            }

            attachments.forEach(attachment => {
                const item = document.createElement("div");
                item.className = "message-item";

                const filename = document.createElement("button");

filename.type = "button";
filename.textContent = `Download: ${attachment.filename || "file"}`;

filename.addEventListener("click", async () => {
    try {
        const response = await fetch(
            `${API_BASE}/api/tickets/${ticketId}/attachments/${attachment.id}/download`,
            {
                headers: {
                    Authorization: `Bearer ${accessToken}`
                }
            }
        );

        if (!response.ok) {
            throw new Error(`Download failed (${response.status})`);
        }

        const blob = await response.blob();
        const downloadUrl = URL.createObjectURL(blob);
        const link = document.createElement("a");

        link.href = downloadUrl;
        link.download = attachment.filename || "download";
        document.body.appendChild(link);
        link.click();
        link.remove();

        URL.revokeObjectURL(downloadUrl);
    } catch (error) {
        alert(error.message);
    }
});

                const details = document.createElement("p");
                details.className = "message-meta";
                details.textContent =
                    `Attachment #${attachment.id} · Uploaded by user #${attachment.uploaded_by}`;

                item.append(filename, details);
                attachmentList.appendChild(item);
            });
        } catch (error) {
            attachmentList.textContent =
                `Could not load attachments: ${error.message}`;
        }
    }
);
restoreSession();