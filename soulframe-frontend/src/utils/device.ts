import type { Device, DeviceRuntimeStatus } from '../api/endpoints';
import { formatFileSize } from './media';

export function isDeviceOnline(device: Device) {
  return device.state === 'active';
}

export function formatRelativeTime(value?: string | null) {
  if (!value) return 'Never';

  const diff = Date.now() - new Date(value).getTime();
  const seconds = Math.max(0, Math.floor(diff / 1000));
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (seconds < 60) return 'Just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

export function formatUptime(seconds?: number | null) {
  if (!seconds) return 'Unknown';
  const hours = Math.floor(seconds / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (hours > 0) return `${hours}h ${minutes}m`;
  return `${minutes}m`;
}

export function runtimeStateLabel(device: Device, runtime?: DeviceRuntimeStatus | null) {
  if (device.state === 'unclaimed') return 'unpaired';
  if (device.state === 'offline') return 'offline';
  if (runtime?.health_status === 'degraded' || runtime?.last_error) return 'playback_error';
  if (runtime?.current_media_id) return 'playing';
  return 'idle';
}

export function runtimeHealthLabel(runtime?: DeviceRuntimeStatus | null) {
  if (!runtime) return 'No telemetry yet';
  if (runtime.health_status) return runtime.health_status;
  return runtime.last_error ? 'degraded' : 'unknown';
}

export function formatStorage(bytes?: number | null) {
  return bytes === null || bytes === undefined ? 'Unknown' : formatFileSize(bytes);
}
