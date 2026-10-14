function getDefaultApiBaseUrl() {
  const hostname = window.location.hostname || 'localhost';
  return `${window.location.protocol}//${hostname}:8000`;
}

function resolveApiBaseUrl() {
  const configured = import.meta.env.VITE_API_BASE_URL;
  const pageHost = window.location.hostname || 'localhost';
  if (!configured) {
    return getDefaultApiBaseUrl();
  }

  try {
    const configuredUrl = new URL(configured);
    const configuredIsLocalhost = ['localhost', '127.0.0.1', '0.0.0.0', '[::]', '::'].includes(configuredUrl.hostname);
    const pageIsLocalhost = pageHost === 'localhost' || pageHost === '127.0.0.1';
    if (configuredIsLocalhost && !pageIsLocalhost) {
      // A build made with a loopback API must still work when opened from a
      // phone. Keep the port, but use the host that served this page.
      configuredUrl.hostname = pageHost;
      return configuredUrl.toString().replace(/\/$/, '');
    }
  } catch {
    return configured;
  }

  return configured;
}

const API_BASE_URL = resolveApiBaseUrl();

export function getApiBaseUrl() {
  return API_BASE_URL;
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public data?: any
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

interface RequestOptions extends RequestInit {
  requiresAuth?: boolean;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const { requiresAuth = true, ...fetchOptions } = options;

  const headers = new Headers(fetchOptions.headers);

  // Add auth token if required
  if (requiresAuth) {
    const token = localStorage.getItem('token');
    if (token) {
      headers.set('Authorization', `Bearer ${token}`);
    }
  }

  // Add Content-Type for JSON bodies
  if (fetchOptions.body && typeof fetchOptions.body === 'string') {
    headers.set('Content-Type', 'application/json');
  }

  const url = `${API_BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...fetchOptions,
      headers,
    });

    // Handle 401 Unauthorized
    if (response.status === 401 && requiresAuth) {
      localStorage.removeItem('token');
      // Redirect to login with return URL
      const currentPath = window.location.pathname + window.location.search;
      window.location.href = `/login?returnUrl=${encodeURIComponent(currentPath)}`;
      throw new ApiError('Unauthorized', 401);
    }

    // Handle non-2xx responses
    if (!response.ok) {
      let errorData;
      try {
        errorData = await response.json();
      } catch {
        errorData = { detail: response.statusText };
      }
      throw new ApiError(
        errorData.detail || `Request failed with status ${response.status}`,
        response.status,
        errorData
      );
    }

    // Handle 204 No Content
    if (response.status === 204) {
      return undefined as T;
    }

    // Parse JSON response
    const data = await response.json();
    return data;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    throw new ApiError(
      error instanceof Error ? error.message : 'Network error',
      0
    );
  }
}
