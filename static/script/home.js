// Function to create a popup for Cars
function popCar(box) {
    createPopup(box, "Using our Cars data tool, you can conveniently enter the details of the vehicle you intend to sell. Simply input your data into the provided HTML form on our platform. As part of our project, we employ a web scraper that gathers user-submitted data from this form. This data is then distributed across multiple websites for scraping relevant information. The collected data is subsequently utilized to train a machine learning model.\nThe primary goal of this model is to provide an accurate estimation of the cost of the vehicle. Through a combination of user-provided details and data scraped from various sources, we aim to enhance the precision of our cost predictions, offering valuable insights to users in the selling process.");
}

// Function to create a popup for Vehicles
function popLaptop(box) {
    createPopup(box, "Get a precise estimate for your laptop's value using our Laptops data tool. Input your laptop's details, and our system, equipped with web scraping and machine learning capabilities, will analyze the data to offer an accurate valuation.")
}

// Function to create a popup for Mobiles
function popMobiles(box) {
    createPopup(box, "Explore accurate pricing for your mobile device by entering its details into our Mobiles data tool. Our advanced system uses web scraping and machine learning to provide precise valuations based on user-provided data and insights gathered from various sources.");
}

// Function to create a popup for Other
function popOther(box) {
    createPopup(box,"Discover the value of your second-hand items by utilizing our Other Items data tool. Input relevant details into the form, and our system, powered by web scraping and machine learning, will provide you with an accurate estimation based on a comprehensive dataset.");
}



// Common function to create a popup
function createPopup(box, text) {
    // Create an overlay element
    var overlay = document.createElement("div");
    overlay.className = "overlay";
    document.body.appendChild(overlay);

    // Create a pop-up element
    var popup = document.createElement("div");
    popup.className = "popup";

    // Replace newline characters with <br> tags
    text = text.replace(/\n/g, '<br>');

    // Set the font and font size
    popup.style.fontFamily = "Times New Roman, Times, serif";
    popup.style.fontSize = "18px"; // Adjust the font size as needed

    // Set the popup content
    popup.innerHTML = text;

    // Append the pop-up to the body
    document.body.appendChild(popup);

    // Position the pop-up in the center of the page
    var centerX = window.innerWidth / 2;
    var centerY = window.innerHeight / 2;

    popup.style.top = centerY - popup.offsetHeight / 2 + "px";
    popup.style.left = centerX - popup.offsetWidth / 2 + "px";
    popup.style.zIndex = 2; // Set the z-index to make sure it appears on top

    // Add the 'active' class to the popup to trigger the transition
    setTimeout(function () {
        popup.classList.add("active");
    }, 10);

    // Remove the pop-up and overlay when clicking outside the popup
    function removePopup(event) {
        if (!popup.contains(event.target)) {
            popup.classList.remove("active");
            // Remove the event listener to avoid multiple popups
            document.removeEventListener("click", removePopup);
            // Remove the popup and overlay after the transition
            setTimeout(function () {
                document.body.removeChild(popup);
                document.body.removeChild(overlay);
            }, 500); // Adjusted to match the longer transition duration
        }
    }

    // Add a click event listener to remove the popup when clicking outside of it
    document.addEventListener("click", removePopup);
}
