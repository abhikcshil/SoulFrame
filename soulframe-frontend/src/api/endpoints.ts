import { apiRequest } from './client';

// Types
export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface Device {
  id: string;
  name: string;
  last_seen_at: string | null;
  created_at: string;
  state: 'unclaimed' | 'active' | 'offline';
}

export interface DeviceRuntimeStatus {
  app_version: string | null;
  local_ip: string | null;
  uptime_seconds: number | null;
  storage_free_bytes: number | null;
  cache_free_bytes: number | null;
  current_media_id: string | null;
  current_playlist_id: string | null;
  health_status: string | null;
  last_error: string | null;
  updated_at: string | null;
}

export interface DeviceCommandStatus {
  id: string;
  command_type: string;
  status: string;
  result_status: string | null;
  result_message: string | null;
  created_at: string;
  delivered_at: string | null;
  acknowledged_at: string | null;
}

export type DeviceCommandType =
  | 'refresh_now'
  | 'restart_playback'
  | 'clear_cache'
  | 'reboot_client'
  | 'unassign_content'
  | 'run_health_check'
  | 'debug_message';

export interface Media {
  id: string;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  status: 'uploaded' | 'processing' | 'ready' | 'failed';
  source_storage_key: string | null;
  playback_storage_key: string | null;
  original_mime_type: string | null;
  playback_mime_type: string | null;
  original_size_bytes: number | null;
  playback_size_bytes: number | null;
  width: number | null;
  height: number | null;
  duration_seconds: number | null;
  normalized_at: string | null;
  processing_error: string | null;
  created_at: string;
}

export interface PlaylistItem {
  id: string;
  media_id: string;
  position: number;
}

export interface Playlist {
  id: string;
  name: string;
  created_at: string;
  items: PlaylistItem[];
}

// Auth endpoints
export const authApi = {
  signup: async (email: string, password: string): Promise<User> => {
    return apiRequest('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
      requiresAuth: false,
    });
  },

  login: async (email: string, password: string): Promise<{ access_token: string }> => {
    return apiRequest('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
      requiresAuth: false,
    });
  },

  getMe: async (): Promise<User> => {
    return apiRequest('/auth/me');
  },
};

// Device endpoints
export const deviceApi = {
  list: async (): Promise<Device[]> => {
    return apiRequest('/devices');
  },

  update: async (deviceId: string, name: string): Promise<Device> => {
    return apiRequest(`/devices/${deviceId}`, {
      method: 'PATCH',
      body: JSON.stringify({ name }),
    });
  },

  claim: async (pairingCode: string): Promise<Device> => {
    return apiRequest('/devices/claim', {
      method: 'POST',
      body: JSON.stringify({ pairing_code: pairingCode }),
    });
  },

  assign: async (deviceId: string, playlistId: string): Promise<{ message: string }> => {
    return apiRequest(`/devices/${deviceId}/assign/${playlistId}`, {
      method: 'POST',
    });
  },

  runtime: async (deviceId: string): Promise<DeviceRuntimeStatus> => {
    return apiRequest(`/devices/${deviceId}/runtime`);
  },

  commands: async (deviceId: string): Promise<DeviceCommandStatus[]> => {
    return apiRequest(`/devices/${deviceId}/commands`);
  },

  queueCommand: async (deviceId: string, commandType: DeviceCommandType): Promise<DeviceCommandStatus> => {
    return apiRequest(`/devices/${deviceId}/commands`, {
      method: 'POST',
      body: JSON.stringify({ command_type: commandType, payload: {} }),
    });
  },
};

// Media endpoints
export const mediaApi = {
  list: async (): Promise<Media[]> => {
    return apiRequest('/media');
  },

  upload: async (file: File): Promise<Media> => {
    const formData = new FormData();
    formData.append('file', file);

    const token = localStorage.getItem('token');
    const response = await fetch(`${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/media/upload`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.detail || 'Upload failed');
    }

    return response.json();
  },

  delete: async (mediaId: string): Promise<void> => {
    return apiRequest(`/media/${mediaId}`, {
      method: 'DELETE',
    });
  },
};

// Playlist endpoints
export const playlistApi = {
  list: async (): Promise<Playlist[]> => {
    return apiRequest('/playlists');
  },

  create: async (name: string): Promise<Playlist> => {
    return apiRequest('/playlists', {
      method: 'POST',
      body: JSON.stringify({ name }),
    });
  },

  update: async (
    playlistId: string,
    name: string,
    items: { media_id: string; position: number }[]
  ): Promise<Playlist> => {
    return apiRequest(`/playlists/${playlistId}`, {
      method: 'PUT',
      body: JSON.stringify({ name, items }),
    });
  },
};
