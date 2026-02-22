"use client";

import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import ProtectedRoute from "@/components/ProtectedRoute";
import Navbar from "@/components/Navbar";
import api, { getApiErrorMessage } from "@/lib/api";

interface Message {
  id: string;
  role: "user" | "assistant" | "error";
  content: string;
  hospital?: string;
  time?: number;
}

const SUGGESTIONS = [
  "Why is the forecast for HOSP_1 going up over the next 7 days?",
  "Explain the admission trend for HOSP_3",
  "What factors are driving HOSP_5 forecast?",
  "Analyze the outlook for HOSP_2 this week",
];

export default function AgentPage() {
  return (
    <ProtectedRoute>
      <AgentContent />
    </ProtectedRoute>
  );
}

function AgentContent() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [hospitals, setHospitals] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    loadHospitals();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const loadHospitals = async () => {
    try {
      const res = await api.get("/hospitals");
      setHospitals(res.data.hospitals || []);
    } catch {
      // silent
    }
  };

  const sendQuery = async (question: string) => {
    if (!question.trim() || loading) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: "user",
      content: question,
    };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res = await api.post("/agent/query", { question });
      const assistantMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: res.data.analysis,
        hospital: res.data.hospital,
        time: res.data.inference_time_seconds,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: unknown) {
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: "error",
        content: getApiErrorMessage(err, "Failed to get analysis. Please try again."),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    sendQuery(input);
  };

  return (
    <main className="min-h-screen bg-navy grid-overlay flex flex-col">
      <Navbar />

      <div className="flex-1 max-w-4xl w-full mx-auto px-4 md:px-8 pt-24 pb-4 flex flex-col">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-6"
        >
          <h1 className="text-2xl md:text-3xl font-bold mb-1">
            <span className="gradient-text">AI Forecast Analyst</span>
          </h1>
          <p className="text-slate-400 text-sm">
            Ask questions about any hospital — the agent uses real forecast data, admission
            history, and external signals from the database.
          </p>
        </motion.div>

        {/* Messages area */}
        <div className="flex-1 overflow-y-auto space-y-4 mb-4 min-h-0">
          {messages.length === 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.2 }}
              className="flex flex-col items-center justify-center h-full py-16"
            >
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-cyan/20 to-blue-600/20 border border-cyan/20 flex items-center justify-center mb-6">
                <svg
                  width="28"
                  height="28"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="1.5"
                  className="text-cyan"
                >
                  <path d="M12 2a7 7 0 0 1 7 7c0 2.38-1.19 4.47-3 5.74V17a2 2 0 0 1-2 2h-4a2 2 0 0 1-2-2v-2.26C6.19 13.47 5 11.38 5 9a7 7 0 0 1 7-7z" />
                  <path d="M10 21h4" />
                  <path d="M9 17v2" />
                  <path d="M15 17v2" />
                </svg>
              </div>
              <p className="text-slate-400 text-sm mb-6 text-center max-w-md">
                Ask a question about any hospital to get an AI-powered analysis grounded in
                real database data.
              </p>

              {/* Suggestions */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 w-full max-w-lg">
                {SUGGESTIONS.map((s, i) => (
                  <button
                    key={i}
                    onClick={() => sendQuery(s)}
                    className="text-left text-xs text-slate-300 glass-card rounded-lg px-3 py-2.5 hover:border-cyan/30 hover:text-cyan transition-all"
                  >
                    {s}
                  </button>
                ))}
              </div>

              {/* Hospital chips */}
              {hospitals.length > 0 && (
                <div className="mt-6">
                  <p className="text-xs text-slate-500 mb-2 text-center">Available hospitals</p>
                  <div className="flex flex-wrap gap-1.5 justify-center">
                    {hospitals.map((h) => (
                      <span
                        key={h}
                        className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan/10 text-cyan/70 border border-cyan/10"
                      >
                        {h}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          <AnimatePresence>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.3 }}
                className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {msg.role === "user" ? (
                  <div className="max-w-[80%] bg-gradient-to-r from-cyan/20 to-blue-600/20 border border-cyan/20 rounded-2xl rounded-br-md px-4 py-3">
                    <p className="text-sm text-slate-100">{msg.content}</p>
                  </div>
                ) : msg.role === "error" ? (
                  <div className="max-w-[85%] bg-red-500/10 border border-red-500/20 rounded-2xl rounded-bl-md px-4 py-3">
                    <p className="text-sm text-red-400">{msg.content}</p>
                  </div>
                ) : (
                  <div className="max-w-[85%] glass-card rounded-2xl rounded-bl-md px-4 py-3">
                    {msg.hospital && (
                      <div className="flex items-center gap-2 mb-2">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-cyan/10 text-cyan border border-cyan/20">
                          {msg.hospital}
                        </span>
                        {msg.time && (
                          <span className="text-[10px] text-slate-500">
                            {msg.time.toFixed(1)}s
                          </span>
                        )}
                      </div>
                    )}
                    <div className="text-sm text-slate-200 leading-relaxed whitespace-pre-wrap">
                      {msg.content}
                    </div>
                  </div>
                )}
              </motion.div>
            ))}
          </AnimatePresence>

          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex justify-start"
            >
              <div className="glass-card rounded-2xl rounded-bl-md px-4 py-3">
                <div className="flex items-center gap-2">
                  <div className="flex gap-1">
                    <span className="w-2 h-2 bg-cyan rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 bg-cyan rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-2 h-2 bg-cyan rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                  <span className="text-xs text-slate-400">Analyzing with AI...</span>
                </div>
              </div>
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <motion.form
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          onSubmit={handleSubmit}
          className="flex gap-2 items-center"
        >
          <div className="flex-1 relative">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask about a hospital... (e.g. Why is HOSP_1 forecast rising?)"
              disabled={loading}
              className="w-full px-4 py-3 pr-12 glass-card rounded-xl text-sm text-slate-100 placeholder:text-slate-500 focus:outline-none focus:border-cyan/40 disabled:opacity-50"
            />
          </div>
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="px-5 py-3 bg-gradient-to-r from-cyan to-blue-600 text-white font-medium rounded-xl hover:shadow-lg hover:shadow-cyan/25 transition-all disabled:opacity-40 disabled:cursor-not-allowed flex-shrink-0"
          >
            {loading ? (
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
            ) : (
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M22 2L11 13" />
                <path d="M22 2L15 22L11 13L2 9L22 2Z" />
              </svg>
            )}
          </button>
        </motion.form>
      </div>
    </main>
  );
}

