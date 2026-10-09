const baseUrl = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';
const tokenStorageKey = 'krada-session-token';
let token = sessionStorage.getItem(tokenStorageKey);

type ApiErrorBody = { detail?: { message?: string } | string };

/**
 * Return one stable key for the lifetime of a logical mutation.
 *
 * The key remains in sessionStorage when the network drops after the server commits. Retrying the
 * action therefore replays the same result instead of applying the mutation twice.
 */
function operationKey(operation: string): string {
  const storageKey = `krada-operation:${operation}`;
  const existing = sessionStorage.getItem(storageKey);
  if (existing) return existing;

  const created = crypto.randomUUID();
  sessionStorage.setItem(storageKey, created);
  return created;
}

function finishOperation(operation: string): void {
  sessionStorage.removeItem(`krada-operation:${operation}`);
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  });

  if (!response.ok) {
    // Proxies may return HTML or an empty body, so error parsing must never hide the HTTP failure.
    const body = (await response.json().catch(() => ({}))) as ApiErrorBody;
    const detail = body.detail;
    const message =
      typeof detail === 'object' ? detail?.message : detail;
    throw new Error(message ?? `Сервис временно недоступен (${response.status})`);
  }
  return response.json() as Promise<T>;
}

async function saveSession(loginRequest: Promise<Session>): Promise<void> {
  const session = await loginRequest;
  token = session.access_token;
  // sessionStorage limits token persistence to the current WebView/browser tab.
  sessionStorage.setItem(tokenStorageKey, token);
}

export const api = {
  hasSession: () => Boolean(token),

  login: (displayName: string) =>
    saveSession(
      request<Session>('/auth/mock', {
        method: 'POST',
        body: JSON.stringify({ display_name: displayName }),
      }),
    ),

  loginMax: (initData: string) =>
    saveSession(
      request<Session>('/auth/max', {
        method: 'POST',
        body: JSON.stringify({ init_data: initData }),
      }),
    ),

  me: () => request<Dashboard>('/me'),
  classes: () => request<GameClass[]>('/character-classes'),

  createCharacter: async (name: string, classKey: string) => {
    const operation = 'character:create';
    const result = await request<Character>('/characters', {
      method: 'POST',
      headers: { 'Idempotency-Key': operationKey(operation) },
      body: JSON.stringify({ name, class_key: classKey }),
    });
    finishOperation(operation);
    return result;
  },

  startRaid: async () => {
    const operation = 'raid:start';
    const result = await request<Raid>('/raids', {
      method: 'POST',
      headers: { 'Idempotency-Key': operationKey(operation) },
    });
    finishOperation(operation);
    return result;
  },

  answer: async (raidId: string, answer: string) => {
    const operation = `raid:answer:${raidId}`;
    const result = await request<Result>(`/raids/${raidId}/answer`, {
      method: 'POST',
      headers: { 'Idempotency-Key': operationKey(operation) },
      body: JSON.stringify({ answer }),
    });
    finishOperation(operation);
    return result;
  },

  logout: () => {
    token = null;
    sessionStorage.removeItem(tokenStorageKey);
    // Do not clear unrelated state if the Mini App ever shares an origin with another surface.
    for (let index = sessionStorage.length - 1; index >= 0; index -= 1) {
      const key = sessionStorage.key(index);
      if (key?.startsWith('krada-operation:')) sessionStorage.removeItem(key);
    }
  },
};

type Session = { access_token: string };

export type Character = {
  id: string;
  name: string;
  class_key: string;
  level: number;
  xp: number;
  visual_seed: number;
};

export type Dashboard = {
  display_name: string;
  school_name: string;
  class_name: string;
  embers: number;
  school_score: number;
  character: Character | null;
  active_raid: Raid | null;
};

export type GameClass = {
  key: string;
  title: string;
  description: string;
  stats: Record<string, number>;
};

export type Raid = {
  id: string;
  state: string;
  score: number;
  question: { id: string; text: string; options: string[]; subject: string } | null;
};

export type Result = {
  correct: boolean;
  explanation: string;
  score: number;
  xp_awarded: number;
  embers_awarded: number;
  embers_balance: number;
};
