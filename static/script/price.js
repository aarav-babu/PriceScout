document.addEventListener('DOMContentLoaded', function () {

    var countdownTime = 10;
    var timerElement = document.getElementById('timer');
    function updateTimer() {
        var minutes = Math.floor(countdownTime / 60);
        var seconds = countdownTime % 60;

        timerElement.textContent = minutes + 'm ' + seconds + 's';
        countdownTime--;
        if (countdownTime < 0) {
            timerElement.textContent = 'Time Expired';
        }
    }
    var timerInterval = setInterval(updateTimer, 1000);
});
