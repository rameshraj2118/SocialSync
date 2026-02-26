(function () {
  var notificationTriggerEl = null;
  var aiMessages = [];

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#39;");
  }

  function formatTimeLabel(value) {
    if (!value) return "";
    var raw = String(value).replace(" ", "T");
    var date = new Date(raw);
    if (isNaN(date.getTime())) return "";
    return date.toLocaleString([], {
      month: "short",
      day: "numeric",
      hour: "numeric",
      minute: "2-digit"
    });
  }

  function createNotificationDrawer() {
    if (document.getElementById("notificationDrawer")) return;

    var drawer = document.createElement("aside");
    drawer.id = "notificationDrawer";
    drawer.className = "notification-drawer";
    drawer.setAttribute("aria-hidden", "true");

    drawer.innerHTML =
      '<div class="notification-drawer-header">' +
      '<h3>Notifications</h3>' +
      '<button type="button" class="notification-close-btn" aria-label="Close notifications">&times;</button>' +
      "</div>" +
      '<div class="notification-drawer-body" id="notificationDrawerBody">' +
      '<p class="notification-empty">Loading notifications...</p>' +
      "</div>";

    var backdrop = document.createElement("div");
    backdrop.id = "notificationBackdrop";
    backdrop.className = "notification-backdrop";

    document.body.appendChild(backdrop);
    document.body.appendChild(drawer);
  }

  function openNotificationDrawer() {
    var drawer = document.getElementById("notificationDrawer");
    var backdrop = document.getElementById("notificationBackdrop");
    if (!drawer || !backdrop) return;

    drawer.classList.add("open");
    drawer.setAttribute("aria-hidden", "false");
    backdrop.classList.add("open");
    document.body.classList.add("notification-open");
  }

  function closeNotificationDrawer() {
    var drawer = document.getElementById("notificationDrawer");
    var backdrop = document.getElementById("notificationBackdrop");
    if (!drawer || !backdrop) return;

    drawer.classList.remove("open");
    drawer.setAttribute("aria-hidden", "true");
    backdrop.classList.remove("open");
    document.body.classList.remove("notification-open");
  }

  function renderNotifications(payload) {
    var body = document.getElementById("notificationDrawerBody");
    if (!body) return;

    if (payload && payload.disabled) {
      body.innerHTML = '<p class="notification-empty">In-app notifications are turned off in Settings.</p>';
      return;
    }

    var items = (payload && payload.items) || [];
    if (!items.length) {
      body.innerHTML = '<p class="notification-empty">No new notifications right now.</p>';
      return;
    }

    body.innerHTML = items
      .map(function (item) {
        var kind = item.kind === "message" ? "message" : "post";
        var iconClass = kind === "message" ? "fa-regular fa-comment-dots" : "fa-regular fa-image";
        return (
          '<article class="notification-item notification-' + kind + '">' +
          '<div class="notification-icon"><i class="' + iconClass + '"></i></div>' +
          '<div class="notification-copy">' +
          '<p class="notification-title">' + escapeHtml(item.title) + "</p>" +
          '<p class="notification-desc">' + escapeHtml(item.description) + "</p>" +
          '<p class="notification-time">' + escapeHtml(formatTimeLabel(item.created_at)) + "</p>" +
          "</div>" +
          "</article>"
        );
      })
      .join("");
  }

  function setNotificationBadgeCount(count) {
    if (!notificationTriggerEl) return;
    var badge = notificationTriggerEl.querySelector(".notification-count-badge");
    if (!badge) return;

    var safeCount = Math.max(0, Number(count) || 0);
    if (!safeCount) {
      badge.classList.add("hidden");
      badge.textContent = "0";
      notificationTriggerEl.setAttribute("aria-label", "Notifications");
      return;
    }

    var label = safeCount > 99 ? "99+" : String(safeCount);
    badge.textContent = label;
    badge.classList.remove("hidden");
    notificationTriggerEl.setAttribute("aria-label", "Notifications, " + safeCount + " new");
  }

  function fetchNotifications() {
    return fetch("/api/notifications")
      .then(function (res) {
        if (!res.ok) throw new Error("Notifications unavailable");
        return res.json();
      });
  }

  function loadNotifications() {
    var body = document.getElementById("notificationDrawerBody");
    if (!body) return;
    body.innerHTML = '<p class="notification-empty">Loading notifications...</p>';

    fetchNotifications()
      .then(function (data) {
        var count = data && !data.disabled && Array.isArray(data.items) ? data.items.length : 0;
        setNotificationBadgeCount(count);
        renderNotifications(data);
      })
      .catch(function () {
        setNotificationBadgeCount(0);
        body.innerHTML = '<p class="notification-empty">Could not load notifications.</p>';
      });
  }

  function refreshNotificationBadge() {
    fetchNotifications()
      .then(function (data) {
        var count = data && !data.disabled && Array.isArray(data.items) ? data.items.length : 0;
        setNotificationBadgeCount(count);
      })
      .catch(function () {
        setNotificationBadgeCount(0);
      });
  }

  function initNotifications() {
    createNotificationDrawer();
    initAiAssistant();

    var trigger = document.querySelector('[data-notification-trigger="true"]');
    if (!trigger) {
      var menuItems = document.querySelectorAll(".top-nav .menu li");
      Array.prototype.forEach.call(menuItems, function (li) {
        var label = (li.textContent || "").trim().toLowerCase();
        if (!trigger && label === "notifications") {
          trigger = li;
        }
      });
    }
    if (!trigger) return;

    trigger.classList.add("notification-trigger");
    notificationTriggerEl = trigger;
    var triggerLabel = trigger.textContent ? trigger.textContent.trim() : "Notifications";
    trigger.innerHTML =
      '<span class="notification-trigger-label">' +
      escapeHtml(triggerLabel || "Notifications") +
      "</span>" +
      '<span class="notification-count-badge hidden" aria-hidden="true">0</span>';
    trigger.setAttribute("role", "button");
    trigger.setAttribute("tabindex", "0");

    trigger.addEventListener("click", function (event) {
      event.preventDefault();
      openNotificationDrawer();
      loadNotifications();
    });

    trigger.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openNotificationDrawer();
        loadNotifications();
      }
    });

    var closeBtn = document.querySelector(".notification-close-btn");
    var backdrop = document.getElementById("notificationBackdrop");

    if (closeBtn) {
      closeBtn.addEventListener("click", closeNotificationDrawer);
    }

    if (backdrop) {
      backdrop.addEventListener("click", closeNotificationDrawer);
    }

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeNotificationDrawer();
      }
    });

    refreshNotificationBadge();
    window.setInterval(refreshNotificationBadge, 30000);
  }

  function createAiAssistantModal() {
    if (document.getElementById("aiAssistantModal")) return;

    var modal = document.createElement("aside");
    modal.id = "aiAssistantModal";
    modal.className = "ai-assistant-modal";
    modal.setAttribute("aria-hidden", "true");
    modal.innerHTML =
      '<div class="ai-assistant-header">' +
      "<h3>AI Assistant</h3>" +
      '<button type="button" class="ai-assistant-close" aria-label="Close AI assistant">&times;</button>' +
      "</div>" +
      '<div class="ai-assistant-body" id="aiAssistantBody"></div>' +
      '<div class="ai-assistant-compose">' +
      '<input id="aiAssistantInput" type="text" maxlength="1000" placeholder="Ask anything..." />' +
      '<button id="aiAssistantSendBtn" type="button">Send</button>' +
      "</div>";

    var backdrop = document.createElement("div");
    backdrop.id = "aiAssistantBackdrop";
    backdrop.className = "ai-assistant-backdrop";

    document.body.appendChild(backdrop);
    document.body.appendChild(modal);

    var closeBtn = modal.querySelector(".ai-assistant-close");
    var input = document.getElementById("aiAssistantInput");
    var sendBtn = document.getElementById("aiAssistantSendBtn");

    if (closeBtn) closeBtn.addEventListener("click", closeAiAssistantModal);
    if (backdrop) backdrop.addEventListener("click", closeAiAssistantModal);
    if (sendBtn) sendBtn.addEventListener("click", sendAiAssistantMessage);
    if (input) {
      input.addEventListener("keydown", function (event) {
        if (event.key === "Enter" && !event.shiftKey) {
          event.preventDefault();
          sendAiAssistantMessage();
        }
      });
    }
  }

  function openAiAssistantModal() {
    createAiAssistantModal();
    var modal = document.getElementById("aiAssistantModal");
    var backdrop = document.getElementById("aiAssistantBackdrop");
    if (!modal || !backdrop) return;

    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    backdrop.classList.add("open");
    document.body.classList.add("ai-assistant-open");
    renderAiAssistantMessages();

    var input = document.getElementById("aiAssistantInput");
    if (input) input.focus();
  }

  function closeAiAssistantModal() {
    var modal = document.getElementById("aiAssistantModal");
    var backdrop = document.getElementById("aiAssistantBackdrop");
    if (!modal || !backdrop) return;

    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    backdrop.classList.remove("open");
    document.body.classList.remove("ai-assistant-open");
  }

  function renderAiAssistantMessages() {
    var body = document.getElementById("aiAssistantBody");
    if (!body) return;

    if (!aiMessages.length) {
      body.innerHTML = '<p class="ai-assistant-empty">Hi, ask me anything.</p>';
      return;
    }

    body.innerHTML = aiMessages
      .map(function (item) {
        var role = item.role === "assistant" ? "assistant" : "user";
        return (
          '<div class="ai-msg-row ' + role + '">' +
          '<p class="ai-msg-bubble ' + role + '">' + escapeHtml(item.content) + "</p>" +
          "</div>"
        );
      })
      .join("");

    body.scrollTop = body.scrollHeight;
  }

  function sendAiAssistantMessage() {
    var input = document.getElementById("aiAssistantInput");
    var sendBtn = document.getElementById("aiAssistantSendBtn");
    if (!input || !sendBtn || sendBtn.disabled) return;

    var text = String(input.value || "").trim();
    if (!text) return;

    var history = aiMessages.slice(-10);
    aiMessages.push({ role: "user", content: text });
    input.value = "";
    renderAiAssistantMessages();

    sendBtn.disabled = true;
    fetch("/api/ai/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: history
      })
    })
      .then(function (res) {
        return res.json().then(function (payload) {
          return { ok: res.ok, payload: payload };
        });
      })
      .then(function (result) {
        if (!result.ok) {
          var msg = result.payload && result.payload.error ? result.payload.error : "AI request failed";
          if (result.payload && result.payload.details) {
            msg += " - " + result.payload.details;
          }
          throw new Error(msg);
        }
        aiMessages.push({
          role: "assistant",
          content: (result.payload && result.payload.reply) || "No response"
        });
        renderAiAssistantMessages();
      })
      .catch(function (err) {
        aiMessages.push({
          role: "assistant",
          content: "Error: " + (err.message || "Could not reach AI")
        });
        renderAiAssistantMessages();
      })
      .finally(function () {
        sendBtn.disabled = false;
      });
  }

  function initAiAssistant() {
    if (document.querySelector('[data-ai-assistant-trigger="true"]')) return;

    var aiTriggerLink = document.createElement("a");
    aiTriggerLink.href = "#";
    aiTriggerLink.setAttribute("data-ai-assistant-trigger", "true");
    aiTriggerLink.setAttribute("aria-label", "Open AI assistant");

    var aiTrigger = document.createElement("li");
    aiTrigger.className = "ai-chat-tab-trigger";
    aiTrigger.setAttribute("data-ai-assistant-trigger", "true");
    aiTrigger.innerHTML = '<i class="fa-solid fa-robot" aria-hidden="true"></i> AI Chat';
    aiTriggerLink.appendChild(aiTrigger);

    var sidebarItems = document.querySelectorAll(".sidebar nav ul li");
    var settingsListItem = null;
    Array.prototype.forEach.call(sidebarItems, function (li) {
      var label = (li.textContent || "").trim().toLowerCase();
      if (!settingsListItem && label.indexOf("settings") !== -1) {
        settingsListItem = li;
      }
    });

    if (settingsListItem && settingsListItem.parentElement && settingsListItem.parentElement.tagName === "A") {
      settingsListItem.parentElement.insertAdjacentElement("afterend", aiTriggerLink);
    } else {
      var sidebarList = document.querySelector(".sidebar nav ul");
      if (!sidebarList) return;
      sidebarList.appendChild(aiTriggerLink);
    }

    aiTriggerLink.addEventListener("click", function (event) {
      event.preventDefault();
      openAiAssistantModal();
    });
    aiTriggerLink.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openAiAssistantModal();
      }
    });

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        closeAiAssistantModal();
      }
    });
  }

  function applyPreferences(prefs) {
    if (!prefs || typeof prefs !== "object") return;

    var appearance = String(prefs.appearance || "Dark").toLowerCase();
    var fontSize = String(prefs.font_size || "Medium").toLowerCase();
    var language = String(prefs.language || "English");

    document.body.setAttribute("data-theme", appearance === "light" ? "light" : "dark");

    if (fontSize !== "small" && fontSize !== "medium" && fontSize !== "large") {
      fontSize = "medium";
    }
    document.body.setAttribute("data-font-size", fontSize);
    document.body.setAttribute("data-language", language);

    window.dispatchEvent(new CustomEvent("userPreferencesApplied", { detail: prefs }));
  }

  function loadCached() {
    try {
      var raw = localStorage.getItem("socialsync_user_preferences");
      if (!raw) return null;
      return JSON.parse(raw);
    } catch (err) {
      return null;
    }
  }

  function saveCached(prefs) {
    try {
      localStorage.setItem("socialsync_user_preferences", JSON.stringify(prefs));
    } catch (err) {
      return;
    }
  }

  function normalizeAvatarUrl(path) {
    var value = String(path || "").trim();
    if (!value) return "";
    if (value.indexOf("http://") === 0 || value.indexOf("https://") === 0) return value;
    if (value.charAt(0) === "/") return value;
    return "/" + value;
  }

  function applyAvatarToNav(profileImage) {
    var avatarUrl = normalizeAvatarUrl(profileImage);
    var avatars = document.querySelectorAll(".top-nav .avatar");

    Array.prototype.forEach.call(avatars, function (avatar) {
      avatar.style.width = "32px";
      avatar.style.height = "32px";
      avatar.style.minWidth = "32px";
      avatar.style.minHeight = "32px";
      avatar.style.borderRadius = "50%";
      avatar.style.cursor = "pointer";
      avatar.addEventListener("click", function () {
        window.location.href = "/settings";
      });

      if (!avatarUrl) return;

      if (avatar.tagName === "IMG") {
        avatar.src = avatarUrl;
        avatar.style.objectFit = "cover";
        avatar.style.display = "block";
      } else {
        avatar.style.backgroundImage = "url('" + avatarUrl + "')";
        avatar.style.backgroundSize = "cover";
        avatar.style.backgroundPosition = "center";
      }
    });
  }

  function loadAvatarProfile() {
    fetch("/api/account/info")
      .then(function (res) {
        if (!res.ok) throw new Error("No profile");
        return res.json();
      })
      .then(function (data) {
        applyAvatarToNav(data.profile_image || "");
      })
      .catch(function () {
        applyAvatarToNav("");
      });
  }

  function boot() {
    initNotifications();
    loadAvatarProfile();

    var cached = loadCached();
    if (cached) applyPreferences(cached);

    fetch("/api/settings")
      .then(function (res) {
        if (!res.ok) throw new Error("No session settings");
        return res.json();
      })
      .then(function (data) {
        applyPreferences(data);
        saveCached(data);
      })
      .catch(function () {
        return;
      });
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
