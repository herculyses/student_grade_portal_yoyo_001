// Automatically hide flash messages after 3 seconds
document.addEventListener("DOMContentLoaded", function() {
    const flashes = document.querySelectorAll(".flash");
    flashes.forEach(flash => {
        setTimeout(() => {
            flash.style.transition = "opacity 0.5s ease, transform 0.5s ease";
            flash.style.opacity = "0";
            flash.style.transform = "translateY(-10px)";
            setTimeout(() => flash.remove(), 500);
        }, 3000);
    });
});
