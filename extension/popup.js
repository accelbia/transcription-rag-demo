// Wait for the DOM to fully load before executing the script
document.addEventListener("DOMContentLoaded", () => {
    // Query the currently active tab in the current window
    chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
        const currentTab = tabs[0]; // The active tab in the current window

        // Check if the current tab exists and is a YouTube link
        if (currentTab && isYoutubeLink(currentTab.url)) {
            const videoId = getVideoId(currentTab.url); // Extract the video ID from the URL

            if (videoId) {
                // Display elements with the class "youtube"
                document.querySelectorAll(".youtube").forEach(element => {
                    element.style.display = "flex";
                });

                // Get the video thumbnail URL and update the thumbnail element
                const thumbnailUrl = getVideoThumbnail(videoId);
                const thumbnailElement = document.getElementById("thumbnail");
                if (thumbnailElement) {
                    thumbnailElement.src = thumbnailUrl;
                    thumbnailElement.alt = `Thumbnail for video ID: ${videoId}`;
                } else {
                    console.error("Thumbnail element not found.");
                }
            } else {
                console.log("No valid video ID found in the URL.");
            }
        } else {
            console.log("No active tab found.");
        }
    });

    // Function to handle user input and fetch an answer
    const handleUserInput = async () => {
        const question = document.getElementById("userInput").value; // Get the user's input
        const sendButton = document.getElementById("sendButton"); // Reference to the send button

        // Validate the input
        if (question.trim() === "") {
            alert("Please enter a question.");
            return;
        }

        try {
            // Update the button text to indicate processing
            if (sendButton) sendButton.innerText = "Thinking...";

            // Fetch the answer from the server
            const answer = await getAnswer(question);
            console.log("Answer received:", answer);

            // Display the answer in the response box
            document.getElementById("responseBox").innerText = answer;
        } catch (error) {
            console.error("Error fetching answer:", error);
            document.getElementById("responseBox").innerText = "Error fetching answer. Please try again.";
        } finally {
            // Reset the button text
            if (sendButton) sendButton.innerText = "Send";
        }
    };

    // Add event listener to the send button
    document.getElementById("sendButton")?.addEventListener("click", handleUserInput);

    // Add event listener to handle "Enter" key press in the input field
    document.getElementById("userInput")?.addEventListener("keypress", (event) => {
        if (event.key === "Enter") {
            handleUserInput();
        }
    });
});

// Utility function to check if a URL is a YouTube link
const isYoutubeLink = (url) => {
    return url.includes("youtube.com/watch") || url.includes("youtu.be/");
};

// Utility function to extract the video ID from a YouTube URL
const getVideoId = (url) => {
    const urlObj = new URL(url);
    if (urlObj.hostname === "youtu.be") {
        return urlObj.pathname.slice(1); // Remove leading slash
    } else if (urlObj.hostname === "www.youtube.com" || urlObj.hostname === "youtube.com") {
        return urlObj.searchParams.get("v");
    }
    return null;
};

// Utility function to get the thumbnail URL for a YouTube video
const getVideoThumbnail = (videoId) => {
    return `https://img.youtube.com/vi/${videoId}/hqdefault.jpg`;
};

// Function to fetch an answer from the server
async function getAnswer(question) {
    // Query the currently active tab
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    const currentTab = tabs[0]; // The active tab in the current window

    // Validate the current tab and its URL
    if (!currentTab || !currentTab.url) {
        throw new Error("Unable to retrieve the current tab URL.");
    }

    // Extract the video ID from the URL
    const videoId = getVideoId(currentTab.url);
    if (!videoId) {
        throw new Error("Video ID is missing.");
    }

    // Send a POST request to the server with the video ID and question
    const response = await fetch("http://localhost:8000/ask", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            video_id: videoId,
            question: question
        })
    });

    // Check if the response is successful
    if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
    }

    // Parse and return the response data
    const data = await response.json();
    return data.answer;
}