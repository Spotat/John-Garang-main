(() => {
    const cookieTheme = document.cookie.match(
        /(?:^|;\s*)portfolio-theme=(dark|light)(?:;|$)/
    )?.[1];
    let storedTheme = null;
    try {
        storedTheme = localStorage.getItem("portfolio-theme");
    } catch (error) {
        if (!(error instanceof DOMException && error.name === "SecurityError")) {
            throw error;
        }
    }

    const hasStoredTheme = storedTheme === "light" || storedTheme === "dark";
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    const savedTheme = hasStoredTheme ? storedTheme : cookieTheme;
    const theme = savedTheme === "light" || savedTheme === "dark"
        ? savedTheme
        : prefersDark ? "dark" : "light";
    document.documentElement.dataset.theme = theme;
})();
