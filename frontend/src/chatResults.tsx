import { createContext, useContext, useState, type ReactNode } from "react";
import type { PageResults } from "./api";

/** Search results produced by the chat agent, shared with the Products page.
 *  Kept in sessionStorage so a page refresh doesn't lose them. */
const STORAGE_KEY = "cc_chat_results";

interface ChatResultsState {
  results: PageResults | null;
  show: (results: PageResults) => void;
  clear: () => void;
}

const ChatResultsContext = createContext<ChatResultsState | null>(null);

function load(): PageResults | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as PageResults) : null;
  } catch {
    return null;
  }
}

export function ChatResultsProvider({ children }: { children: ReactNode }) {
  const [results, setResults] = useState<PageResults | null>(load);

  function show(next: PageResults) {
    sessionStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    setResults(next);
  }

  function clear() {
    sessionStorage.removeItem(STORAGE_KEY);
    setResults(null);
  }

  return (
    <ChatResultsContext.Provider value={{ results, show, clear }}>{children}</ChatResultsContext.Provider>
  );
}

// eslint-disable-next-line react/only-export-components
export function useChatResults() {
  const ctx = useContext(ChatResultsContext);
  if (!ctx) throw new Error("useChatResults must be used inside <ChatResultsProvider>");
  return ctx;
}
