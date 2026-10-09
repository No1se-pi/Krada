import { beforeEach, describe, expect, it, vi } from 'vitest';

class MemoryStorage implements Storage {
  private readonly values = new Map<string, string>();

  get length() {
    return this.values.size;
  }

  clear() {
    this.values.clear();
  }

  getItem(key: string) {
    return this.values.get(key) ?? null;
  }

  key(index: number) {
    return [...this.values.keys()][index] ?? null;
  }

  removeItem(key: string) {
    this.values.delete(key);
  }

  setItem(key: string, value: string) {
    this.values.set(key, value);
  }
}

describe('API idempotency', () => {
  beforeEach(() => {
    vi.resetModules();
    Object.defineProperty(globalThis, 'sessionStorage', {
      configurable: true,
      value: new MemoryStorage(),
    });
  });

  it('reuses the operation key after an ambiguous network failure', async () => {
    const fetchMock = vi
      .fn()
      .mockRejectedValueOnce(new TypeError('connection dropped'))
      .mockResolvedValueOnce({
        ok: true,
        json: async () => ({ id: 'raid-1', state: 'ACTIVE', score: 0, question: null }),
      });
    vi.stubGlobal('fetch', fetchMock);
    const { api } = await import('./api');

    await expect(api.startRaid()).rejects.toThrow('connection dropped');
    await expect(api.startRaid()).resolves.toMatchObject({ id: 'raid-1' });

    const firstHeaders = fetchMock.mock.calls[0][1].headers as Record<string, string>;
    const retryHeaders = fetchMock.mock.calls[1][1].headers as Record<string, string>;
    expect(firstHeaders['Idempotency-Key']).toBe(retryHeaders['Idempotency-Key']);
  });
});
