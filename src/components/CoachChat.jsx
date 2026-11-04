import { useState } from 'react';
import { suggestedQuestions, suggestedPrompt } from '../data/drivingScenarios.js';
import { askMockCoach } from '../services/mockChatApi.js';

export default function CoachChat({ onScenarioChange }) {
  const [selectedId, setSelectedId] = useState(null);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);

  const sendQuestion = async (text) => {
    const prompt = text.trim();
    if (!prompt || loading) return;
    setQuestion('');
    setMessages((current) => [...current, { role: 'user', content: prompt }]);
    setLoading(true);
    try {
      const response = await askMockCoach(prompt);
      const scenarioId = response.visualization?.scenario_id;
      if (scenarioId) {
        setSelectedId(scenarioId);
        onScenarioChange(scenarioId);
      }
      setMessages((current) => [...current, {
        role: 'assistant',
        content: response.answer,
        reminder: response.reminder,
        scenarioId,
      }]);
    } catch (error) {
      setMessages((current) => [...current, {
        role: 'assistant',
        content: `The mock coach could not respond: ${error.message}`,
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
          <p>Local mock coach <span className="separator">·</span> Driving practice</p>
        </div>
        <span className="verified-pill"><span />Practice mode</span>
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
                  {message.scenarioId && <span className="verified-pill"><span />Practice rule</span>}
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
