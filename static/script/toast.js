document.addEventListener('DOMContentLoaded', function () {
    var toasts = document.querySelectorAll('.toast');
    toasts.forEach(function (toast) {
        setTimeout(function () {
            toast.classList.add('fade-out');
            setTimeout(function () {
                toast.remove();
            }, 500);
        }, 3000);
    });
});
