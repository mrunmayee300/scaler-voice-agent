"use client";

import { useEffect, useState } from "react";
import { Phone, PhoneOff, Mic } from "lucide-react";
import { Button } from "@/components/ui/button";

export function VoiceAgent() {
  const [vapi, setVapi] = useState<InstanceType<typeof import("@vapi-ai/web").default> | null>(null);
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState("idle");

  const publicKey = process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY;
  const assistantId = process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID;
  const candidateName = process.env.NEXT_PUBLIC_CANDIDATE_NAME || "Candidate";

  useEffect(() => {
    if (!publicKey) return;
    import("@vapi-ai/web").then(({ default: Vapi }) => {
      const instance = new Vapi(publicKey);
      instance.on("call-start", () => {
        setConnected(true);
        setStatus("connected");
      });
      instance.on("call-end", () => {
        setConnected(false);
        setStatus("idle");
      });
      instance.on("speech-start", () => setStatus("listening"));
      instance.on("speech-end", () => setStatus("connected"));
      instance.on("error", (e: unknown) => {
        console.error("Vapi error:", e);
        const msg =
          e && typeof e === "object" && "message" in e
            ? String((e as { message?: string }).message)
            : "Voice connection failed";
        setStatus(`error: ${msg}`);
      });
      setVapi(instance);
    });
  }, [publicKey]);

  const startCall = () => {
    if (!vapi || !assistantId) {
      alert("Configure NEXT_PUBLIC_VAPI_PUBLIC_KEY and NEXT_PUBLIC_VAPI_ASSISTANT_ID");
      return;
    }
    vapi.start(assistantId);
  };

  const endCall = () => {
    vapi?.stop();
  };

  if (!publicKey || !assistantId) {
    return (
      <div className="text-center p-8 text-muted-foreground">
        <Mic className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>Voice agent requires Vapi configuration.</p>
        <p className="text-sm mt-2">
          Set NEXT_PUBLIC_VAPI_PUBLIC_KEY and NEXT_PUBLIC_VAPI_ASSISTANT_ID in Vercel
          env vars, then redeploy.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center p-8 gap-6">
      <div className="text-center">
        <h3 className="text-xl font-semibold mb-2">Voice Interview with {candidateName}</h3>
        <p className="text-muted-foreground text-sm max-w-md">
          Start a voice conversation. Ask about experience, projects, or schedule an interview.
          Supports interruptions and natural dialogue.
        </p>
      </div>

      <div
        className={`w-32 h-32 rounded-full flex items-center justify-center transition-all ${
          connected
            ? "bg-primary/20 ring-4 ring-primary animate-pulse"
            : "bg-secondary"
        }`}
      >
        <Mic className={`h-12 w-12 ${connected ? "text-primary" : "text-muted-foreground"}`} />
      </div>

      <p className="text-sm text-muted-foreground capitalize">Status: {status}</p>

      {!connected ? (
        <Button size="lg" onClick={startCall} className="gap-2">
          <Phone className="h-5 w-5" />
          Start Voice Call
        </Button>
      ) : (
        <Button size="lg" variant="outline" onClick={endCall} className="gap-2">
          <PhoneOff className="h-5 w-5" />
          End Call
        </Button>
      )}
    </div>
  );
}
