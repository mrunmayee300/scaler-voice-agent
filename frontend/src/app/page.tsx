"use client";

import { MessageSquare, Mic, Calendar } from "lucide-react";
import { ChatInterface } from "@/components/chat/ChatInterface";
import { VoiceAgent } from "@/components/voice/VoiceAgent";
import { BookingForm } from "@/components/booking/BookingForm";

const candidateName = process.env.NEXT_PUBLIC_CANDIDATE_NAME || "Candidate";

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col">
      <header className="border-b border-border px-6 py-4">
        <h1 className="text-2xl font-bold">{candidateName}</h1>
        <p className="text-muted-foreground text-sm">AI Professional Representative</p>
      </header>

      <div className="flex-1 grid lg:grid-cols-3 gap-0 divide-x divide-border">
        <section className="lg:col-span-2 flex flex-col min-h-[600px]">
          <div className="flex border-b border-border">
            <div className="flex items-center gap-2 px-4 py-3 border-b-2 border-primary text-sm font-medium">
              <MessageSquare className="h-4 w-4" />
              Chat
            </div>
          </div>
          <ChatInterface />
        </section>

        <aside className="flex flex-col">
          <div className="border-b border-border p-4">
            <div className="flex items-center gap-2 text-sm font-medium mb-4">
              <Mic className="h-4 w-4" />
              Voice
            </div>
            <VoiceAgent />
          </div>
          <div className="border-t border-border flex-1">
            <div className="flex items-center gap-2 px-4 py-3 text-sm font-medium">
              <Calendar className="h-4 w-4" />
              Book Interview
            </div>
            <BookingForm />
          </div>
        </aside>
      </div>

      <footer className="border-t border-border px-6 py-3 text-xs text-muted-foreground text-center">
        Grounded AI · Answers only from verified sources · Prompt injection protected
      </footer>
    </main>
  );
}
