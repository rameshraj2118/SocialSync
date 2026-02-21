(function () {
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

  function loadNotifications() {
    var body = document.getElementById("notificationDrawerBody");
    if (!body) return;
    body.innerHTML = '<p class="notification-empty">Loading notifications...</p>';

    fetch("/api/notifications")
      .then(function (res) {
        if (!res.ok) throw new Error("Notifications unavailable");
        return res.json();
      })
      .then(function (data) {
        renderNotifications(data);
      })
      .catch(function () {
        body.innerHTML = '<p class="notification-empty">Could not load notifications.</p>';
      });
  }

  function initNotifications() {
    createNotificationDrawer();

    var trigger = document.querySelector('[data-notification-trigger="true"]');
    if (!trigger) {
      var menuItems = Array.prototype.slice.call(document.querySelectorAll(".top-nav .menu li"));
      trigger = menuItems.find(function (li) {
        return li.textContent && li.textContent.trim() === "Notifications";
      });
    }
    if (!trigger) return;

    trigger.classList.add("notification-trigger");
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
