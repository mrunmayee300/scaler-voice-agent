const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

const WARMUP_TIMEOUT_MS = 90_000;
const API_TIMEOUT_MS = 120_000;

/** Wake Render free-tier before chat, voice, or calendar calls. */
export async function warmBackend(): Promise<void> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), WARMUP_TIMEOUT_MS);
  try {
    await fetch(`${API_URL}/health`, { cache: "no-store", signal: controller.signal });
  } catch {
    /* best-effort */
  } finally {
    clearTimeout(timer);
  }
}

/** Ping /health until success or attempts exhausted (handles cold starts). */
export async function ensureBackendReady(maxAttempts = 3): Promise<boolean> {
  for (let i = 0; i < maxAttempts; i++) {
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), WARMUP_TIMEOUT_MS);
      const res = await fetch(`${API_URL}/health`, {
        cache: "no-store",
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (res.ok) return true;
    } catch {
      /* retry */
    }
    if (i < maxAttempts - 1) {
      await new Promise((r) => setTimeout(r, 2000));
    }
  }
  return false;
}

export async function apiFetch(
  path: string,
  init?: RequestInit,
  options?: { warmup?: boolean; retries?: number }
): Promise<Response> {
  const warmup = options?.warmup ?? true;
  const retries = options?.retries ?? 2;

  if (warmup) {
    await ensureBackendReady(2);
  }

  let lastError: unknown;
  for (let attempt = 0; attempt <= retries; attempt++) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
    try {
      const res = await fetch(`${API_URL}${path}`, {
        ...init,
        signal: controller.signal,
      });
      clearTimeout(timer);
      if (res.status === 502 || res.status === 503 || res.status === 504) {
        if (attempt < retries) {
          await warmBackend();
          continue;
        }
      }
      return res;
    } catch (e) {
      clearTimeout(timer);
      lastError = e;
      if (attempt < retries) {
        await warmBackend();
        continue;
      }
    }
  }
  throw lastError instanceof Error ? lastError : new Error("API request failed");
}
