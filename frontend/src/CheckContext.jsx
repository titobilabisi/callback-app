import { createContext, useCallback, useContext, useEffect, useState } from 'react'
import { api } from './api'

// State for one in-progress call check: the questions (served by the
// backend so the wording lives in one place), the answers so far, and the
// verification request once it has been sent.
//
// The route (one family member or two) is decided by the server from the
// answers. This file never works it out.
const CheckContext = createContext(null)

const STORAGE_KEY = 'callback.requestId'

// Remembering the open request lets the waiting screen survive a page
// refresh. Wrapped in try/catch because storage can be blocked.
function readStoredId() {
  try {
    const v = sessionStorage.getItem(STORAGE_KEY)
    return v ? Number(v) : null
  } catch {
    return null
  }
}

function writeStoredId(id) {
  try {
    if (id == null) sessionStorage.removeItem(STORAGE_KEY)
    else sessionStorage.setItem(STORAGE_KEY, String(id))
  } catch {
    // Nothing to do; the check still works without it.
  }
}

export function CheckProvider({ children }) {
  const [questions, setQuestions] = useState(null)
  const [questionsError, setQuestionsError] = useState('')
  const [answers, setAnswers] = useState({})
  const [requestId, setRequestId] = useState(readStoredId)
  const [lastRequest, setLastRequest] = useState(null)

  useEffect(() => {
    let cancelled = false
    api('/risk/questions')
      .then((q) => !cancelled && setQuestions(q))
      .catch((err) => !cancelled && setQuestionsError(err.message))
    return () => {
      cancelled = true
    }
  }, [])

  const answer = useCallback((key, value) => {
    setAnswers((prev) => ({ ...prev, [key]: value }))
  }, [])

  const reset = useCallback(() => {
    setAnswers({})
    setRequestId(null)
    setLastRequest(null)
    writeStoredId(null)
  }, [])

  // Sends the answers. Throws an ApiError the caller can show.
  const submit = useCallback(async (finalAnswers) => {
    const req = await api('/requests', { method: 'POST', body: { answers: finalAnswers } })
    setRequestId(req.id)
    setLastRequest(req)
    writeStoredId(req.id)
    return req
  }, [])

  // Keeps fields from the first response (like can_be_completed) that the
  // later status polls do not repeat.
  const updateRequest = useCallback((req) => {
    setLastRequest((prev) => ({ ...prev, ...req }))
  }, [])

  return (
    <CheckContext.Provider
      value={{ questions, questionsError, answers, answer, reset, submit, requestId, lastRequest, updateRequest }}
    >
      {children}
    </CheckContext.Provider>
  )
}

export function useCheck() {
  const ctx = useContext(CheckContext)
  if (!ctx) throw new Error('useCheck must be used inside CheckProvider')
  return ctx
}
