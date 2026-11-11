import { useState } from 'react';
import { suggestedQuestions, suggestedPrompt } from '../data/drivingScenarios.js';
import { askCoach } from '../services/chatApi.js';
import { clearChatHistory, loadChatHistory, saveChatHistory } from '../services/chatHistory.js';

function isKnownVisualization(visualization) {
  if (visualization?.scene === 'intersection') {
    return scenarios.some(({ id }) => id === visualization.scenario_id);
  }
  if (visualization?.scene === 'parking') {
    return parkingScenarios.some(({ id }) => id === visualization.scenario_id);
  }
  return false;
}

export default function CoachChat({ onVisualization }) {
  const [selectedId, setSelectedId] = useState(null);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState(loadChatHistory);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    saveChatHistory(messages);
  }, [messages]);

  const startNewConversation = () => {
    if (loading) return;
    clearChatHistory();
    setMessages([]);
    setSelectedId(null);
    setQuestion('');
  };

  const sendQuestion = async (text) => {
    const prompt = text.trim();
    if (!prompt || loading) return;
    setQuestion('');
    setMessages((current) => [...current, { role: 'user', content: prompt }]);
    setLoading(true);
    try {
      const response = await askCoach(prompt);
      const visualization = isKnownVisualization(response.visualization)
        ? response.visualization
        : null;
      if (visualization) {
        setSelectedId(visualization.scenario_id);
        onVisualization?.(visualization);
      }
      setMessages((current) => [...current, {
        role: 'assistant',
        content: response.answer,
        reminder: response.reminder,
        visualization,
      }]);
    } catch (error) {
      setMessages((current) => [...current, {
        role: 'assistant',
        content: `The Django backend could not respond: ${error.message}`,
      }]);
    } finally {
      setLoading(false);
    }
  };

  const submitQuestion = (event) => {
    event.preventDefault();
    void sendQuestion(question);
  };

  return (
    <section className="panel chat-panel" id="conversation" aria-labelledby="coach-heading">
      <div className="panel-heading">
        <div className="avatar" aria-hidden="true">DW</div>
        <div>
          <h2 id="coach-heading">Your driving coach</h2>
          <p>Django API <span className="separator">·</span> Driving practice</p>
        </div>
        <span className="verified-pill"><span />Practice mode</span>
        <button
          className="clear-chat-button"
          type="button"
          onClick={startNewConversation}
          disabled={loading || messages.length === 0}
          title="Clear this conversation and start fresh"
        >
          New conversation
        </button>
      </div>

      <div className="conversation" aria-live="polite">
        {messages.length === 0 && (
          <div className="empty-state">
            <div className="empty-icon" aria-hidden="true">✦</div>
            <h3>Ask DriveWise about a driving rule</h3>
            <p>Choose a suggested question below or ask your own.</p>
          </div>
        )}
        {messages.map((message, index) => (
          <div className={message.role === 'user' ? 'learner-message' : 'coach-message'} key={index}>
            {message.role === 'user' ? (
              <>
                <span className="message-label">YOU</span>
                <p>{message.content}</p>
              </>
            ) : (
              <>
                <div className="message-author">
                  <span className="avatar avatar-small">DW</span>
                  DriveWise coach
                  {message.visualization && (
                    <span className="verified-pill"><span />Demo opened</span>
                  )}
                </div>
                <p>{message.content}</p>
                {message.reminder && <div className="remember-box"><strong>Remember</strong><br />{message.reminder}</div>}
              </>
            )}
          </div>
        ))}
        {loading && (
          <div className="coach-message loading-message" role="status" aria-label="Coach is preparing a response">
            <div className="message-author"><span className="avatar avatar-small">DW</span> DriveWise coach</div>
            <div className="skeleton skeleton-wide" />
            <div className="skeleton" />
            <div className="skeleton skeleton-short" />
          </div>
        )}
      </div>

      <form className="question-form" onSubmit={submitQuestion}>
        <textarea
          className="question-input"
          aria-label="Ask about a driving rule"
          placeholder={suggestedPrompt}
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          rows={2}
          disabled={loading}
        />
        <button className="action-button" type="submit" disabled={!question.trim() || loading}>Ask coach <span aria-hidden="true">↗</span></button>
      </form>

      <div className="prompt-area" id="sample-prompts">
        <div className="prompt-heading"><h3>Suggested questions</h3><span>Try a prepared example</span></div>
        <div className="prompt-list">
          {suggestedQuestions.map((prompt, index) => (
            <button
              className={`prompt-chip ${selectedId === 'four_way_stop' && index === 0 ? 'prompt-chip-active' : ''}`}
              key={prompt}
              onClick={() => void sendQuestion(prompt)}
              type="button"
              disabled={loading}
            >
              <span className="prompt-number">0{index + 1}</span>{prompt}
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}
