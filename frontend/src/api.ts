async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const isForm = init.body instanceof FormData;
  const res = await fetch('/api' + path, {
    ...init,
    headers: isForm ? undefined : { 'Content-Type': 'application/json' },
  });
  if (!res.ok) {
    let message = `${res.status} ${res.statusText}`;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') message = body.detail;
      else if (Array.isArray(body.detail)) message = body.detail.map((d: { msg: string }) => d.msg).join(', ');
    } catch {
      /* 본문이 JSON이 아니면 상태 코드만 표시 */
    }
    throw new Error(message);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

function body(data: unknown): BodyInit {
  return data instanceof FormData ? data : JSON.stringify(data ?? {});
}

export function qs(params: Record<string, string | number | undefined | null>): string {
  const p = new URLSearchParams();
  Object.entries(params).forEach(([k, v]) => {
    if (v !== undefined && v !== null && v !== '') p.set(k, String(v));
  });
  const s = p.toString();
  return s ? `?${s}` : '';
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, data?: unknown) => request<T>(path, { method: 'POST', body: body(data) }),
  put: <T>(path: string, data?: unknown) => request<T>(path, { method: 'PUT', body: body(data) }),
  patch: <T>(path: string, data?: unknown) => request<T>(path, { method: 'PATCH', body: body(data) }),
  del: <T = void>(path: string) => request<T>(path, { method: 'DELETE' }),
};
