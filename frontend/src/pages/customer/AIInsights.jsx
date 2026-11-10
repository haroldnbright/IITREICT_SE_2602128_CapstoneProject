// AI insights page, customer: ask plain-English questions about your own order history
import { useState } from 'react'
import { api } from '../../api/client'

// Example questions shown as one-click chips
const SUGGESTIONS = [
  'Summarize my last five orders.',
  'Which of my orders are still not delivered?',
  'How much did I spend this week?',
  'Which food items have I ordered most frequently?',
]
// Questions shorter than this are ignored
const MIN_QUESTION_LENGTH = 3
// Longest question the input accepts
const MAX_QUESTION_LENGTH = 500

// Question box with suggestion chips and a list of past answers, newest first
export default function AIInsights() {
  const [question, setQuestion] = useState('')
  const [history, setHistory] = useState([]) // [{ question, answer }]
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  // Sends a question to the backend AI endpoint and adds the answer to the history
  const ask = async (text) => {
    const trimmedQuestion = text.trim()
    // Ignore very short questions and clicks while a request is still running
    if (trimmedQuestion.length < MIN_QUESTION_LENGTH || loading) return
    setLoading(true)
    setError('')
    try {
      const response = await api('/ai/insights', { method: 'POST', body: { question: trimmedQuestion } })
      // Put the newest answer first. History lives only in this page's state, so it resets when the user leaves.
      const newEntry = { question: trimmedQuestion, answer: response.answer }
      setHistory((previous) => [newEntry, ...previous])
      setQuestion('')
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  // Asks whatever is typed in the question box
  const handleSubmit = (event) => {
    event.preventDefault()
    ask(question)
  }

  // The Ask button stays disabled while waiting or while the question is too short
  const canAsk = !loading && question.trim().length >= MIN_QUESTION_LENGTH

  return (
    <section className="narrow">
      <h1>Ask about your orders</h1>
      <p className="muted">Answers are based only on your own CampusBite order history.</p>

      <div className="suggestions">
        {SUGGESTIONS.map((suggestion) => (
          <button key={suggestion} className="chip" onClick={() => ask(suggestion)} disabled={loading}>{suggestion}</button>
        ))}
      </div>

      <form className="ask-form" onSubmit={handleSubmit}>
        <input value={question} onChange={(e) => setQuestion(e.target.value)} maxLength={MAX_QUESTION_LENGTH}
          placeholder="e.g. What did I order from Spice Route?" aria-label="Your question" />
        <button className="btn btn-primary" disabled={!canAsk}>
          {loading ? 'Thinking...' : 'Ask'}
        </button>
      </form>

      {error && <p className="error-box" role="alert">{error}</p>}
      {loading && <p className="muted">Reading your orders...</p>}

      <div className="answers">
        {history.map((item, index) => (
          <div key={index} className="answer">
            <p className="answer-q">{item.question}</p>
            <div className="answer-a">{item.answer}</div>
          </div>
        ))}
      </div>
    </section>
  )
}
