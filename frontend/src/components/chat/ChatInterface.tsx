"use client";

import { useCallback, useRef, useState } from "react";
import { Send, Loader2, BookOpen, Shield } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { streamMessage, type Citation } from "@/lib/api";
import { cn } from "@/lib/utils";

interface Message {
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  confidence?: number;
  refused?: boolean;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [conversationId, setConversationId] = useState<string>();
  const [typing, setTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = useCallback(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, []);

  const handleSend = async () => {
    if (!input.trim() || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((prev) => [...prev, { role: "user", content: userMsg }]);
    setLoading(true);
    setTyping(true);

    let assistantContent = "";
    let citations: Citation[] = [];
    let confidence = 0;

    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      await streamMessage(
        userMsg,
        conversationId,
        (token) => {
          assistantContent += token;
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: "assistant",
              content: assistantContent,
              citations,
              confidence,
            };
            return updated;
          });
          scrollToBottom();
        },
        (cits) => {
          citations = cits;
        },
        (data) => {
          setConversationId(data.conversation_id);
          confidence = data.confidence ?? 0;
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: "assistant",
              content: assistantContent,
              citations,
              confidence,
            };
            return updated;
          });
        },
        (error) => {
          setMessages((prev) => {
            const updated = [...prev];
            updated[updated.length - 1] = {
              role: "assistant",
              content: `Sorry, something went wrong: ${error}`,
            };
            return updated;
          });
        }
      );
    } finally {
      setLoading(false);
      setTyping(false);
      scrollToBottom();
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-muted-foreground py-12">
            <p className="text-lg mb-2">Ask me anything about my background</p>
            <p className="text-sm">
              Experience, projects, GitHub repos, skills, or schedule an interview
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn(
              "flex",
              msg.role === "user" ? "justify-end" : "justify-start"
            )}
          >
            <div
              className={cn(
                "max-w-[80%] rounded-lg px-4 py-3",
                msg.role === "user"
                  ? "bg-primary text-primary-foreground"
                  : "bg-card border border-border"
              )}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
              {msg.citations && msg.citations.length > 0 && (
                <div className="mt-3 pt-3 border-t border-border/50">
                  <p className="text-xs text-muted-foreground flex items-center gap-1 mb-2">
                    <BookOpen className="h-3 w-3" /> Sources
                  </p>
                  {msg.citations.slice(0, 3).map((c, j) => (
                    <p key={j} className="text-xs text-muted-foreground truncate">
                      {c.repo || c.source}: {c.excerpt.slice(0, 80)}...
                    </p>
                  ))}
                </div>
              )}
              {msg.confidence !== undefined && msg.confidence > 0 && (
                <p className="text-xs text-muted-foreground mt-2 flex items-center gap-1">
                  <Shield className="h-3 w-3" />
                  Confidence: {(msg.confidence * 100).toFixed(0)}%
                </p>
              )}
            </div>
          </div>
        ))}
        {typing && (
          <div className="flex items-center gap-2 text-muted-foreground text-sm">
            <Loader2 className="h-4 w-4 animate-spin" />
            Thinking...
          </div>
        )}
      </div>
      <div className="p-4 border-t border-border">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend();
          }}
          className="flex gap-2"
        >
          <Input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask about experience, projects, skills..."
            disabled={loading}
            className="flex-1"
          />
          <Button type="submit" disabled={loading || !input.trim()}>
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </form>
      </div>
    </div>
  );
}
