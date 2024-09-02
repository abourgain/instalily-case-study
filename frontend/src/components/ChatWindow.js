// chatwindows.js
import React, { useState, useEffect, useRef } from "react";
import "./ChatWindow.css";
import { getAIMessage } from "../api/api";
import { marked } from "marked";

function ChatWindow() {
  const defaultMessage = [
    {
      role: "assistant",
      content: "Hi, how can I help you today?",
    },
  ];

  const [messages, setMessages] = useState(defaultMessage);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false); // Add a loading state

  const messagesEndRef = useRef(null);

  // Generate session ID if it doesn't exist
  useEffect(() => {
    if (!sessionStorage.getItem("sessionId")) {
      const sessionId = `session-${Math.random().toString(36).substr(2, 9)}`;
      sessionStorage.setItem("sessionId", sessionId); // Store session ID in sessionStorage
    }
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSend = async (input) => {
    if (input.trim() !== "") {
      // Set user message
      setMessages((prevMessages) => [
        ...prevMessages,
        { role: "user", content: input },
      ]);
      setInput("");

      // Show loading spinner
      setLoading(true);

      // Call API & set assistant message
      const newMessage = await getAIMessage(input);

      // Hide loading spinner
      setLoading(false);

      // Set assistant message
      setMessages((prevMessages) => [...prevMessages, newMessage]);
    }
  };

  return (
    <div className="chat-container">
      <div className="messages-container">
        {messages.map((message, index) => (
          <div key={index} className={`${message.role}-message-container`}>
            {message.content && (
              <div className={`message ${message.role}-message`}>
                <div
                  dangerouslySetInnerHTML={{
                    __html: marked(message.content).replace(/<p>|<\/p>/g, ""),
                  }}
                ></div>
              </div>
            )}
          </div>
        ))}
        <div ref={messagesEndRef} />
      </div>

      <div className="input-area">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
          onKeyPress={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              handleSend(input);
              e.preventDefault();
            }
          }}
          rows="3"
        />
        {loading ? (
          <div className="loading-spinner">
            <div className="spinner"></div>
          </div>
        ) : (
          <button className="send-button" onClick={() => handleSend(input)}>
            Send
          </button>
        )}
      </div>
    </div>
  );
}

export default ChatWindow;
