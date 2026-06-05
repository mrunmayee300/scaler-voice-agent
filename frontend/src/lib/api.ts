const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface Citation {
  source: string;
  source_type: string;
  repo?: string;
  commit_hash?: string;
  date?: string;
  file?: string;
  excerpt: string;
  relevance_score: number;
}

export interface ChatResponse {
  answer: string;
  conversation_id: string;
  citations: Citation[];
  confidence: number;
  grounded: boolean;
  refused: boolean;
  refusal_reason?: string;
}

export async function sendMessage(
  message: string,
  conversationId?: string
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export async function streamMessage(
  message: string,
  conversationId: string | undefined,
  onToken: (token: string) => void,
  onCitations: (citations: Citation[]) => void,
  onDone: (data: { conversation_id: string; confidence: number }) => void,
  onError: (error: string) => void
): Promise<void> {
  const res = await fetch(`${API_URL}/api/chat/stream`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, conversation_id: conversationId }),
  });

  if (!res.ok || !res.body) {
    onError(`Stream failed: ${res.status}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      if (line.startsWith("data: ")) {
        try {
          const data = JSON.parse(line.slice(6));
          if (data.type === "token" && data.content) onToken(data.content);
          if (data.type === "citation" && data.citations) onCitations(data.citations);
          if (data.type === "done") onDone(data);
          if (data.type === "error") onError(data.content);
        } catch {
          /* skip malformed */
        }
      }
    }
  }
}

export interface TimePreferenceWindow {
  date: string;
  start_time: string;
  end_time: string;
}

export interface SlotsResponse {
  slots: { start: string; end: string; available: boolean }[];
  grouped_by_date?: Record<string, { start: string; end: string; available: boolean }[]>;
  timezone?: string;
  meeting_duration_minutes?: number;
  business_hours?: { start: number; end: number };
}

export async function getAvailableSlots(
  params:
    | { start_date: string; end_date: string; timezone: string; windows?: never }
    | { timezone: string; windows: TimePreferenceWindow[]; start_date?: string; end_date?: string }
): Promise<SlotsResponse> {
  const res = await fetch(`${API_URL}/api/calendar/slots`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      start_date: params.start_date ?? "",
      end_date: params.end_date ?? "",
      timezone: params.timezone,
      windows: params.windows ?? [],
    }),
  });
  if (!res.ok) throw new Error(`Slots API error: ${res.status}`);
  return res.json();
}

export async function bookMeeting(data: {
  start_time: string;
  attendee_email: string;
  attendee_name: string;
  notes?: string;
  timezone: string;
}) {
  const res = await fetch(`${API_URL}/api/calendar/book`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  return res.json();
}
