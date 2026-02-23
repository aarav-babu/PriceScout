function popCar(box) {
    createPopup(box, "Using our Cars data tool, you can conveniently enter the details of the vehicle you intend to sell. Simply input your data into the provided HTML form on our platform. As part of our project, we employ a web scraper that gathers user-submitted data from this form. This data is then distributed across multiple websites for scraping relevant information. The collected data is subsequently utilized to train a machine learning model.\nThe primary goal of this model is to provide an accurate estimation of the cost of the vehicle. Through a combination of user-provided details and data scraped from various sources, we aim to enhance the precision of our cost predictions, offering valuable insights to users in the selling process.");
}

function popLaptop(box) {
    createPopup(box, "Get a precise estimate for your laptop's value using our Laptops data tool. Input your laptop's details, and our system, equipped with web scraping and machine learning capabilities, will analyze the data to offer an accurate valuation.");
}

function popMobiles(box) {
    createPopup(box, "Explore accurate pricing for your mobile device by entering its details into our Mobiles data tool. Our advanced system uses web scraping and machine learning to provide precise valuations based on user-provided data and insights gathered from various sources.");
}

function popOther(box) {
    createPopup(box, "Discover the value of your second-hand items by utilizing our Other Items data tool. Input relevant details into the form, and our system, powered by web scraping and machine learning, will provide you with an accurate estimation based on a comprehensive dataset.");
}

function createPopup(box, text) {
    // Remove any existing popup first
    var existingPopup = document.querySelector('.popup');
    var existingOverlay = document.querySelector('.overlay');
    if (existingPopup) existingPopup.remove();
    if (existingOverlay) existingOverlay.remove();

    var overlay = document.createElement("div");
    overlay.className = "overlay";
    document.body.appendChild(overlay);

    var popup = document.createElement("div");
    popup.className = "popup";

    text = text.replace(/\n/g, '<br>');
    popup.style.fontFamily = "Times New Roman, Times, serif";
    popup.style.fontSize = "18px";
    popup.innerHTML = text;

    document.body.appendChild(popup);

    var centerX = window.innerWidth / 2;
    var centerY = window.innerHeight / 2;
    popup.style.top = centerY - popup.offsetHeight / 2 + "px";
    popup.style.left = centerX - popup.offsetWidth / 2 + "px";
    popup.style.zIndex = 2;

    setTimeout(function () {
        popup.classList.add("active");
    }, 10);

    // Close when clicking the overlay (not the popup itself)
    overlay.addEventListener("click", function () {
        popup.classList.remove("active");
        setTimeout(function () {
            popup.remove();
            overlay.remove();
        }, 500);
    });
}
