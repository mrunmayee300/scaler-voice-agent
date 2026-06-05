"use client";

import { useCallback, useEffect, useState } from "react";
import { Phone, PhoneOff, Mic, Loader2 } from "lucide-react";
import { Button } from "@/components/ui/button";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type VoiceConfig = {
  publicKey: string;
  assistantId: string;
  candidateName: string;
  configured: boolean;
};

async function warmBackend(): Promise<void> {
  try {
    await fetch(`${API_URL}/health`, { cache: "no-store" });
  } catch {
    /* best-effort wake-up for Render free-tier cold starts */
  }
}

function isBenignVapiError(e: unknown): boolean {
  const text = JSON.stringify(e).toLowerCase();
  return text.includes("meeting has ended") || text.includes("call ended");
}

export function VoiceAgent() {
  const [vapi, setVapi] = useState<InstanceType<typeof import("@vapi-ai/web").default> | null>(null);
  const [connected, setConnected] = useState(false);
  const [status, setStatus] = useState("idle");
  const [config, setConfig] = useState<VoiceConfig | null>(null);
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    warmBackend();
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadConfig() {
      const envFallback: VoiceConfig = {
        publicKey: process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY || "",
        assistantId: process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID || "",
        candidateName: process.env.NEXT_PUBLIC_CANDIDATE_NAME || "Candidate",
        configured: Boolean(
          process.env.NEXT_PUBLIC_VAPI_PUBLIC_KEY && process.env.NEXT_PUBLIC_VAPI_ASSISTANT_ID
        ),
      };

      try {
        const res = await fetch(`${API_URL}/api/voice/client-config`);
        if (res.ok) {
          const data = (await res.json()) as VoiceConfig;
          const merged: VoiceConfig = {
            publicKey: data.publicKey || envFallback.publicKey,
            assistantId: data.assistantId || envFallback.assistantId,
            candidateName: data.candidateName || envFallback.candidateName,
            configured: Boolean(
              (data.publicKey || envFallback.publicKey) &&
                (data.assistantId || envFallback.assistantId)
            ),
          };
          if (!cancelled) {
            setConfig(merged);
            setLoadingConfig(false);
            return;
          }
        }
      } catch {
        /* fall through */
      }

      if (!cancelled) {
        setConfig(envFallback);
        setLoadingConfig(false);
      }
    }

    loadConfig();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    if (!config?.publicKey) return;
    import("@vapi-ai/web").then(({ default: Vapi }) => {
      const instance = new Vapi(config.publicKey);
      instance.on("call-start", () => {
        setConnected(true);
        setStatus("connected");
        setStarting(false);
      });
      instance.on("call-end", () => {
        setConnected(false);
        setStatus("idle");
        setStarting(false);
      });
      instance.on("speech-start", () => setStatus("listening"));
      instance.on("speech-end", () => setStatus("connected"));
      instance.on("error", (e: unknown) => {
        if (isBenignVapiError(e)) return;
        console.error("Vapi error:", e);
        setStarting(false);
        setStatus("error — try again in a moment");
      });
      setVapi(instance);
    });
  }, [config?.publicKey]);

  const startCall = useCallback(async () => {
    if (!vapi || !config?.assistantId) return;
    setStarting(true);
    setStatus("warming up server…");
    await warmBackend();
    setStatus("connecting…");
    vapi.start(config.assistantId);
  }, [vapi, config?.assistantId]);

  const endCall = () => {
    vapi?.stop();
  };

  if (loadingConfig) {
    return (
      <div className="text-center p-8 text-muted-foreground">
        <Loader2 className="h-8 w-8 mx-auto mb-4 animate-spin" />
        <p>Loading voice configuration…</p>
      </div>
    );
  }

  if (!config?.configured) {
    return (
      <div className="text-center p-8 text-muted-foreground">
        <Mic className="h-12 w-12 mx-auto mb-4 opacity-50" />
        <p>Voice agent requires Vapi configuration.</p>
        <p className="text-sm mt-2">
          On Render, set <code className="text-xs">VAPI_PUBLIC_KEY</code> and{" "}
          <code className="text-xs">VAPI_ASSISTANT_ID</code>. On Vercel, set{" "}
          <code className="text-xs">NEXT_PUBLIC_API_URL</code> to your Render URL.
        </p>
      </div>
    );
  }

  const candidateName = config.candidateName;

  return (
    <div className="flex flex-col items-center justify-center p-8 gap-6">
      <div className="text-center">
        <h3 className="text-xl font-semibold mb-2">Voice Interview with {candidateName}</h3>
        <p className="text-muted-foreground text-sm max-w-md">
          Start a voice conversation. Ask about experience, projects, or schedule an interview.
          First call may take up to a minute while the server wakes up.
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
        <Button size="lg" onClick={startCall} disabled={starting} className="gap-2">
          {starting ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Phone className="h-5 w-5" />
          )}
          {starting ? "Starting…" : "Start Voice Call"}
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
