document.addEventListener("DOMContentLoaded", () => {
    const toggleBtn = document.getElementById("toggle-theme");
    const currentTheme = localStorage.getItem("theme");

    if (currentTheme === "dark") {
        document.documentElement.setAttribute("data-theme", "dark");
    }

    toggleBtn.addEventListener("click", () => {
        const isDark = document.documentElement.getAttribute("data-theme") === "dark";
        if (isDark) {
            document.documentElement.setAttribute("data-theme", "light");
            localStorage.setItem("theme", "light");
        } else {
            document.documentElement.setAttribute("data-theme", "dark");
            localStorage.setItem("theme", "dark");
        }
    });
});
