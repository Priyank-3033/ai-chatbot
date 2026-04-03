export const API_BASE_URL = import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
export const WS_BASE_URL = API_BASE_URL.replace(/^http/i, "ws");

export function createApiClient({ getToken, onUnauthorized } = {}) {
  async function parseError(response) {
    let detail = "Request failed.";
    try {
      const data = await response.json();
      detail = data?.detail || detail;
    } catch {
      detail = response.statusText || detail;
    }
    return detail;
  }

  async function request(path, { method = "GET", body, token, headers = {} } = {}) {
    const authToken = token ?? getToken?.() ?? "";
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        ...headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      if (response.status === 401) {
        try {
          window.localStorage.removeItem("smart-chat-token-v1");
        } catch {
          // ignore storage failures
        }
        onUnauthorized?.();
      }
      throw new Error(await parseError(response));
    }

    return response.json();
  }

  async function formRequest(path, formData, { method = "POST", token, headers = {} } = {}) {
    const authToken = token ?? getToken?.() ?? "";
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      cache: "no-store",
      headers: {
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        ...headers,
      },
      body: formData,
    });

    if (!response.ok) {
      if (response.status === 401) {
        try {
          window.localStorage.removeItem("smart-chat-token-v1");
        } catch {
          // ignore storage failures
        }
        onUnauthorized?.();
      }
      throw new Error(await parseError(response));
    }

    return response.json();
  }

  async function streamRequest(path, { method = "POST", body, token, headers = {} } = {}) {
    const authToken = token ?? getToken?.() ?? "";
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
        ...headers,
      },
      body: body ? JSON.stringify(body) : undefined,
    });

    if (!response.ok) {
      if (response.status === 401) {
        try {
          window.localStorage.removeItem("smart-chat-token-v1");
        } catch {
          // ignore storage failures
        }
        onUnauthorized?.();
      }
      throw new Error(await parseError(response));
    }

    return response;
  }

  return {
    request,
    formRequest,
    streamRequest,
  };
}
