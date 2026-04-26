/**
 * Wraps fetch() so a 401 triggers the ReauthModal flow.
 *
 * On 401: dispatches "reauth-required", waits for "reauth-complete" (with the
 * new token in detail.token, or null if the user dismissed). On success the
 * request is retried once with the fresh Authorization header.
 *
 * Always pass the current token via options.headers.Authorization — apiFetch
 * does not automatically inject it on the initial call.
 */
export async function apiFetch(url, options = {}) {
  const res = await fetch(url, options);
  if (res.status !== 401) return res;

  const newToken = await requestReauth();
  if (!newToken) return res;

  return fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${newToken}`,
    },
  });
}

function requestReauth() {
  return new Promise((resolve) => {
    window.dispatchEvent(new CustomEvent("reauth-required"));
    function handler(e) {
      window.removeEventListener("reauth-complete", handler);
      resolve(e.detail.token);
    }
    window.addEventListener("reauth-complete", handler);
  });
}
