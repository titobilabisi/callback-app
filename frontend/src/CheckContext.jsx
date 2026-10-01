import { createContext, useContext, useState } from 'react'

// Holds the answers to the four risk questions for one in-progress check,
// plus the mocked outcome used by this prototype until the real backend
// (Chunk 2 and Chunk 3 of the project timeline) is wired in.
const CheckContext = createContext(null)

export const RISK_QUESTIONS = [
  { key: 'money', text: 'Are they asking you for money or gift cards?' },
  { key: 'secrecy', text: 'Did they ask you to keep this a secret?' },
  { key: 'urgency', text: 'Did they say you need to act right now?' },
  { key: 'unusualContact', text: 'Did this call come from an unknown number?' },
]

export function CheckProvider({ children }) {
  const [answers, setAnswers] = useState({})

  function answer(key, value) {
    setAnswers((prev) => ({ ...prev, [key]: value }))
  }

  function reset() {
    setAnswers({})
  }

  return (
    <CheckContext.Provider value={{ answers, answer, reset }}>
      {children}
    </CheckContext.Provider>
  )
}

export function useCheck() {
  const ctx = useContext(CheckContext)
  if (!ctx) throw new Error('useCheck must be used inside CheckProvider')
  return ctx
}
