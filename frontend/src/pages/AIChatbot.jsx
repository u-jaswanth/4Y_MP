import { useEffect, useRef, useState } from "react";

import { sendChatMessage } from "../services/api";

import AppNav from "../components/AppNav";
import RichText from "../components/RichText";


function AIChatbot() {

  const [messages, setMessages] = useState([
    {
      role: "assistant",
      content:
        "Hi, I'm the MediConnect AI assistant. Ask me about your " +
        "analyzed reports, or ask a general medical question.",
    },
  ]);

  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");

  const scrollRef = useRef(null);


  // ==========================================
  // AUTO-SCROLL TO LATEST MESSAGE
  // ==========================================

  useEffect(() => {

    if (scrollRef.current) {
      scrollRef.current.scrollTop =
        scrollRef.current.scrollHeight;
    }

  }, [messages, sending]);


  // ==========================================
  // SEND MESSAGE
  // ==========================================

  async function handleSend(event) {

    event.preventDefault();

    const trimmed = input.trim();

    if (!trimmed || sending) {
      return;
    }

    setError("");

    const userMessage = { role: "user", content: trimmed };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSending(true);

    try {

      // Send the prior turns along with the new message so the
      // assistant can resolve follow-ups like "is that high?" -
      // previously every message was sent with zero context about
      // what had already been discussed.
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const data = await sendChatMessage(trimmed, history);

      setMessages((prev) => [
        ...prev,
        { role: "assistant", content: data.answer },
      ]);

    } catch (err) {

      setError(err.message);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content:
            "Sorry, I couldn't process that question right now.",
        },
      ]);

    } finally {

      setSending(false);

    }

  }


  // ==========================================
  // CHATBOT PAGE
  // ==========================================

  return (

    <div className="dashboard-page">

      {/* ======================================
          NAVBAR
      ====================================== */}

      <AppNav active="chat" />


      {/* ======================================
          MAIN CONTENT
      ====================================== */}

      <main className="dashboard-content">

        <div className="dashboard-header">
          <h1>AI Health Assistant</h1>
          <p>
            Ask questions about your analyzed reports or general
            medical topics.
          </p>
        </div>

        <div className="dashboard-card chatbot-card">

          <div className="chatbot-messages" ref={scrollRef}>

            {messages.map((message, index) => (

              <div
                key={index}
                className={
                  message.role === "user"
                    ? "chat-bubble chat-bubble-user"
                    : "chat-bubble chat-bubble-assistant"
                }
              >
                {message.role === "user" ? (
                  message.content
                ) : (
                  <RichText>{message.content}</RichText>
                )}
              </div>

            ))}

            {sending && (
              <div className="chat-bubble chat-bubble-assistant">
                <div className="loading-spinner"></div>
              </div>
            )}

          </div>

          {error && (
            <div className="error-message">{error}</div>
          )}

          <form className="chatbot-input-row" onSubmit={handleSend}>

            <input
              type="text"
              value={input}
              placeholder="Ask about your results, e.g. 'What is my ALT?'"
              onChange={(event) => setInput(event.target.value)}
              disabled={sending}
            />

            <button
              type="submit"
              className="primary-btn"
              disabled={sending || !input.trim()}
            >
              Send
            </button>

          </form>

        </div>

      </main>

    </div>

  );

}


export default AIChatbot;
