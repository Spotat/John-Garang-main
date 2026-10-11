const menuToggle = document.querySelector(".menu-toggle");
const navigation = document.querySelector(".primary-navigation");
const themeToggle = document.querySelector(".theme-toggle");
const themeLabel = themeToggle?.querySelector(".theme-label");
const themeMeta = document.querySelector('meta[name="theme-color"]');

function applyTheme(theme, persist = false) {
    const isDark = theme === "dark";
    document.documentElement.dataset.theme = theme;
    themeToggle?.setAttribute("aria-pressed", String(isDark));
    themeToggle?.setAttribute("aria-label", `Switch to ${isDark ? "light" : "dark"} theme`);
    if (themeLabel) {
        themeLabel.textContent = isDark ? "Light mode" : "Dark mode";
    }
    themeMeta?.setAttribute("content", isDark ? "#141b16" : "#f6f7f2");

    if (persist) {
        try {
            localStorage.setItem("portfolio-theme", theme);
        } catch (error) {
            const storageUnavailable = error instanceof DOMException
                && ["SecurityError", "QuotaExceededError"].includes(error.name);
            if (!storageUnavailable) {
                throw error;
            }
            console.warn("Theme preference could not be saved to local storage; using a cookie.");
        }
        const secure = window.location.protocol === "https:" ? "; Secure" : "";
        document.cookie = `portfolio-theme=${theme}; Path=/; Max-Age=31536000; SameSite=Lax${secure}`;
    }
}

if (themeToggle) {
    applyTheme(document.documentElement.dataset.theme || "light");
    themeToggle.addEventListener("click", () => {
        const nextTheme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
        applyTheme(nextTheme, true);
    });
}

if (menuToggle && navigation) {
    menuToggle.addEventListener("click", () => {
        const isExpanded = menuToggle.getAttribute("aria-expanded") === "true";
        menuToggle.setAttribute("aria-expanded", String(!isExpanded));
        navigation.classList.toggle("is-open", !isExpanded);
    });

    navigation.addEventListener("click", (event) => {
        if (event.target instanceof Element && event.target.closest("a")) {
            menuToggle.setAttribute("aria-expanded", "false");
            navigation.classList.remove("is-open");
        }
    });
}

document.querySelectorAll("[data-confirm-delete]").forEach((form) => {
    form.addEventListener("submit", (event) => {
        if (!window.confirm("Delete this project and all of its stored media?")) {
            event.preventDefault();
        }
    });
});

document.querySelectorAll("[data-gallery]").forEach((gallery) => {
    const slides = Array.from(gallery.querySelectorAll("[data-slide]"));
    const previous = gallery.parentElement?.querySelector("[data-gallery-prev]");
    const next = gallery.parentElement?.querySelector("[data-gallery-next]");
    const current = gallery.parentElement?.querySelector("[data-gallery-current]");
    const caption = gallery.parentElement?.querySelector(".gallery-caption-subtitle");
    const thumbnails = Array.from(gallery.parentElement?.querySelectorAll("[data-gallery-to]") || []);
    let activeIndex = 0;
    let pointerStartX = null;

    const activateSlide = (index) => {
        if (index < 0 || index >= slides.length) {
            return;
        }
        slides.forEach((slide, slideIndex) => {
            const isActive = slideIndex === index;
            slide.classList.toggle("is-active", isActive);
            slide.setAttribute("aria-hidden", String(!isActive));
            if (!isActive) {
                slide.querySelectorAll("video").forEach((video) => video.pause());
            }
        });
        thumbnails.forEach((thumbnail, thumbnailIndex) => {
            const isActive = thumbnailIndex === index;
            thumbnail.classList.toggle("is-active", isActive);
            thumbnail.setAttribute("aria-pressed", String(isActive));
        });
        activeIndex = index;
        if (current) {
            current.textContent = String(index + 1).padStart(2, "0");
        }
        if (caption) {
            caption.textContent = index === 0
                ? "Motion graphics opener"
                : slides[index].getAttribute("aria-label") || `Project media ${index}`;
        }
        if (previous instanceof HTMLButtonElement) {
            previous.disabled = index === 0;
        }
        if (next instanceof HTMLButtonElement) {
            next.disabled = index === slides.length - 1;
        }
    };

    previous?.addEventListener("click", () => activateSlide(activeIndex - 1));
    next?.addEventListener("click", () => activateSlide(activeIndex + 1));
    thumbnails.forEach((thumbnail, index) => {
        thumbnail.addEventListener("click", () => activateSlide(index));
    });

    gallery.addEventListener("keydown", (event) => {
        if (event.target instanceof Element && event.target.closest("video")) {
            return;
        }
        if (event.key === "ArrowLeft") {
            event.preventDefault();
            activateSlide(activeIndex - 1);
        } else if (event.key === "ArrowRight") {
            event.preventDefault();
            activateSlide(activeIndex + 1);
        }
    });
    gallery.addEventListener("pointerdown", (event) => {
        pointerStartX = event.clientX;
    });
    gallery.addEventListener("pointerup", (event) => {
        if (pointerStartX === null) {
            return;
        }
        const distance = event.clientX - pointerStartX;
        pointerStartX = null;
        if (Math.abs(distance) > 55 && !(event.target instanceof Element && event.target.closest("video"))) {
            activateSlide(activeIndex + (distance < 0 ? 1 : -1));
        }
    });
    gallery.addEventListener("pointercancel", () => {
        pointerStartX = null;
    });
    activateSlide(0);
});

const motionQuery = window.matchMedia("(prefers-reduced-motion: reduce)");
if (!motionQuery.matches && "IntersectionObserver" in window) {
    document.documentElement.classList.add("motion-ready");
    const revealObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach((entry) => {
            if (entry.isIntersecting) {
                entry.target.classList.add("is-visible");
                observer.unobserve(entry.target);
            }
        });
    }, { threshold: 0.14, rootMargin: "0px 0px -35px 0px" });

    document.querySelectorAll(
        ".hero-copy > *, .hero-visual, .project-card, .skill-card, .timeline-item, "
        + ".journey-step, .about-copy > *, .contact-detail, .section-heading, .contact-cta > *"
    ).forEach((element, index) => {
        element.classList.add("reveal");
        element.dataset.revealOrder = String(index % 4);
        revealObserver.observe(element);
    });
}
