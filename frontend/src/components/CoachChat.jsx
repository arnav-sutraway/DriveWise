import { useEffect, useState } from 'react';
import { scenarios, suggestedQuestions, suggestedPrompt } from '../data/drivingScenarios.js';
import { parkingScenarios } from '../data/parkingScenarios.js';
import { askCoach } from '../services/chatApi.js';
import { clearChatHistory, loadChatHistory, saveChatHistory } from '../services/chatHistory.js';
import { normalizeSources, sourceLabel, splitCitations } from '../services/citations.js';
import { intentLabel } from '../services/intents.js';

const linkProps = { target: '_blank', rel: 'noopener noreferrer' };

// Answer text with each "[n]" linked to the passage it cites, when that source has a link.
function AnswerText({ content, sources }) {
  const byNumber = new Map(sources.map((source) => [source.number, source]));
  return splitCitations(content).map((part, index) => {
    if (part.type === 'text') return part.value;
    const source = byNumber.get(part.number);
    const label = `[${part.number}]`;
    if (!source?.url) return label;
    return (
      <a key={index} className="citation-link" href={source.url} title={sourceLabel(source)} {...linkProps}>
        {label}
      </a>
    );
  });
}

function SourceList({ sources }) {
  if (sources.length === 0) return null;
  return (
    <div className="source-list">
      <span className="source-list-label">Sources</span>
      <ol>
        {sources.map((source) => (
          <li key={source.number}>
            <span className="source-number">[{source.number}]</span>
            {source.url
              ? <a href={source.url} {...linkProps}>{sourceLabel(source)}</a>
              : <span>{sourceLabel(source)}</span>}
            {source.officialUrl && source.officialUrl !== source.url && (
              <a className="source-official" href={source.officialUrl} {...linkProps}>Official source ↗</a>
            )}
          </li>
        ))}
      </ol>
    </div>
  );
}

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
        intent: response.grounded ? response.intent : null,
        reminder: response.reminder,
        sources: normalizeSources(response.sources),
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
                  {intentLabel(message.intent) && (
                    <span className="intent-pill" title="Question type the coach answered as">
                      {intentLabel(message.intent)}
                    </span>
                  )}
                  {message.visualization && (
                    <span className="verified-pill"><span />Demo opened</span>
                  )}
                </div>
                <p className="answer-text"><AnswerText content={message.content} sources={normalizeSources(message.sources)} /></p>
                <SourceList sources={normalizeSources(message.sources)} />
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
