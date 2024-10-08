export const getAIMessage = async (userQuery) => {
  try {
    const sessionId = sessionStorage.getItem("sessionId") || ""; // Retrieve session ID from sessionStorage

    const response = await fetch(
      `https://partselect-chatbot.onrender.com/agent?message=${encodeURIComponent(
        userQuery
      )}&session=${encodeURIComponent(sessionId)}`,
      {
        method: "GET",
        headers: {
          "Content-Type": "application/json",
        },
      }
    );

    if (!response.ok) {
      throw new Error("Network response was not ok");
    }

    const data = await response.json();
    console.log("AI Response: ", data);

    const message = {
      role: "assistant",
      content: data.response, // Assuming the backend response has a 'message_received' field
    };

    return message;
  } catch (error) {
    console.error("Error fetching AI message: ", error);

    // Return a fallback message in case of an error
    return {
      role: "assistant",
      content: "Sorry, I couldn't process your request at this moment.",
    };
  }
};
