import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Layout } from '../components/Layout';
import {
  authApi,
  deviceApi,
  Device,
  DeviceCommandStatus,
  DeviceCommandType,
  DeviceRuntimeStatus,
  mediaApi,
  Media,
  playlistApi,
  Playlist,
  User,
} from '../api/endpoints';
import {
  formatRelativeTime,
  formatStorage,
  formatUptime,
  isDeviceOnline,
  runtimeHealthLabel,
  runtimeStateLabel,
} from '../utils/device';

const POLL_INTERVAL_MS = 10000;

const commandLabels: { type: DeviceCommandType; label: string }[] = [
  { type: 'refresh_now', label: 'Refresh Now' },
  { type: 'restart_playback', label: 'Restart Playback' },
  { type: 'clear_cache', label: 'Clear Cache' },
];

function DetailRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="runtime-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

export function DeviceDetail() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();

  const [device, setDevice] = useState<Device | null>(null);
  const [runtime, setRuntime] = useState<DeviceRuntimeStatus | null>(null);
  const [commands, setCommands] = useState<DeviceCommandStatus[]>([]);
  const [media, setMedia] = useState<Media[]>([]);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [account, setAccount] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [queuedCommand, setQueuedCommand] = useState<DeviceCommandType | null>(null);
  const [error, setError] = useState('');

  const loadData = useCallback(async (quiet = false) => {
    if (!deviceId) return;
    if (!quiet) setIsRefreshing(true);

    try {
      const [devicesData, playlistsData, mediaData, accountData] = await Promise.all([
        deviceApi.list(),
        playlistApi.list(),
        mediaApi.list(),
        authApi.getMe(),
      ]);

      const foundDevice = devicesData.find((item) => item.id === deviceId);
      if (!foundDevice) {
        setError('Device not found');
        return;
      }

      setDevice(foundDevice);
      setPlaylists(playlistsData);
      setMedia(mediaData);
      setAccount(accountData);

      try {
        const runtimeData = await deviceApi.runtime(deviceId);
        setRuntime(runtimeData);
      } catch (err: any) {
        if (err.status === 404) {
          setRuntime(null);
        } else {
          throw err;
        }
      }

      const commandData = await deviceApi.commands(deviceId);
      setCommands(commandData);
      setError('');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }, [deviceId]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    const timer = window.setInterval(() => loadData(true), POLL_INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [loadData]);

  const currentMedia = useMemo(
    () => media.find((item) => item.id === runtime?.current_media_id),
    [media, runtime?.current_media_id]
  );

  const currentPlaylist = useMemo(
    () => playlists.find((item) => item.id === runtime?.current_playlist_id),
    [playlists, runtime?.current_playlist_id]
  );

  const assignedMedia = useMemo(
    () => media.find((item) => item.id === runtime?.assigned_media_id),
    [media, runtime?.assigned_media_id]
  );

  const assignedPlaylist = useMemo(
    () => playlists.find((item) => item.id === runtime?.assigned_playlist_id),
    [playlists, runtime?.assigned_playlist_id]
  );

  const assignedContentLabel = useMemo(() => {
    if (!runtime || runtime.assignment_type === 'none') return 'None';
    if (runtime.assignment_type === 'media') {
      return assignedMedia?.original_filename || runtime.assigned_media_id || 'Direct media';
    }
    return assignedPlaylist?.name || runtime.assigned_playlist_id || 'Playlist';
  }, [assignedMedia, assignedPlaylist, runtime]);

  const handleCommand = async (commandType: DeviceCommandType) => {
    if (!deviceId) return;
    setQueuedCommand(commandType);
    setError('');
    try {
      await deviceApi.queueCommand(deviceId, commandType);
      await loadData(true);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setQueuedCommand(null);
    }
  };

  if (isLoading) {
    return (
      <Layout showNav={false}>
        <div className="loading">Loading device runtime...</div>
      </Layout>
    );
  }

  if (!device) {
    return (
      <Layout showNav={false}>
        <div className="container">
          <p className="text-error">Device not found</p>
          <button onClick={() => navigate('/devices')} className="btn btn-primary">
            Back to Devices
          </button>
        </div>
      </Layout>
    );
  }

  const runtimeState = runtimeStateLabel(device, runtime);

  return (
    <Layout showNav={false}>
      <div className="container">
        <button onClick={() => navigate('/devices')} className="btn btn-secondary mb-24">
          Back
        </button>

        <div className="runtime-header">
          <div>
            <h1 style={{ marginBottom: '8px' }}>{device.name}</h1>
            <div className="runtime-badges">
              <span className={`status-pill ${isDeviceOnline(device) ? 'status-ready' : 'status-failed'}`}>
                {isDeviceOnline(device) ? 'Online' : 'Offline'}
              </span>
              <span className={`status-pill ${runtimeState === 'playback_error' ? 'status-failed' : 'status-processing'}`}>
                {runtimeState}
              </span>
            </div>
          </div>
          <button onClick={() => loadData()} className="btn btn-small btn-secondary" disabled={isRefreshing}>
            {isRefreshing ? 'Refreshing...' : 'Refresh'}
          </button>
        </div>

        {error && <p className="text-error">{error}</p>}

        <div className="info-box">
          Runtime data is refreshed every 10 seconds from the backend. Command results update after the device polls and acknowledges them.
        </div>

        <section className="card">
          <h3>Playback</h3>
          <DetailRow label="Assigned content" value={assignedContentLabel} />
          <DetailRow label="Assigned at" value={formatRelativeTime(runtime?.assigned_at)} />
          <DetailRow label="Health" value={runtimeHealthLabel(runtime)} />
          <DetailRow label="Device state" value={runtime?.device_state || runtimeState} />
          <DetailRow label="Current playlist" value={currentPlaylist?.name || runtime?.current_playlist_id || 'Unknown'} />
          <DetailRow label="Current media" value={currentMedia?.original_filename || runtime?.current_media_id || 'Unknown'} />
          <DetailRow label="Last error" value={runtime?.last_error || 'None'} />
          <DetailRow label="Playback errors" value={runtime?.playback_errors == null ? 'Unknown' : String(runtime.playback_errors)} />
          <DetailRow label="Dropped frames" value={runtime?.dropped_frames == null ? 'Unknown' : String(runtime.dropped_frames)} />
        </section>

        <section className="card">
          <h3>Sync & Telemetry</h3>
          <DetailRow label="Account" value={account?.email || 'Unknown'} />
          <DetailRow label="Last seen" value={formatRelativeTime(device.last_seen_at)} />
          <DetailRow label="Last runtime update" value={formatRelativeTime(runtime?.updated_at)} />
          <DetailRow label="App version" value={runtime?.app_version || 'Unknown'} />
          <DetailRow label="IP address" value={runtime?.local_ip || 'Unknown'} />
          <DetailRow label="Uptime" value={formatUptime(runtime?.uptime_seconds)} />
          <DetailRow label="Media storage free" value={formatStorage(runtime?.storage_free_bytes)} />
          <DetailRow label="Cache free" value={formatStorage(runtime?.cache_free_bytes)} />
          <DetailRow label="Temperature" value={runtime?.temperature_c == null ? 'Unknown' : `${runtime.temperature_c.toFixed(1)} C`} />
          <DetailRow label="CPU frequency" value={runtime?.cpu_frequency_mhz == null ? 'Unknown' : `${Math.round(runtime.cpu_frequency_mhz)} MHz`} />
        </section>

        <section className="card">
          <h3>Debug Actions</h3>
          <div className="debug-actions">
            {commandLabels.map((command) => (
              <button
                key={command.type}
                onClick={() => handleCommand(command.type)}
                className="btn btn-small btn-secondary"
                disabled={queuedCommand !== null}
              >
                {queuedCommand === command.type ? 'Queued...' : command.label}
              </button>
            ))}
          </div>
        </section>

        <section className="card">
          <h3>Recent Device Logs</h3>
          {!runtime?.recent_logs?.length ? (
            <p className="text-secondary">No log lines reported yet</p>
          ) : (
            <pre className="log-tail">{runtime.recent_logs.slice(-12).join('\n')}</pre>
          )}
        </section>

        <section className="card">
          <h3>Recent Commands</h3>
          {commands.length === 0 ? (
            <p className="text-secondary">No commands queued yet</p>
          ) : (
            <div className="command-list">
              {commands.slice(0, 6).map((command) => (
                <div key={command.id} className="command-row">
                  <div>
                    <strong>{command.command_type}</strong>
                    <p className="text-secondary">
                      Created {formatRelativeTime(command.created_at)}
                      {command.acknowledged_at ? ` / acknowledged ${formatRelativeTime(command.acknowledged_at)}` : ''}
                    </p>
                    {command.result_message && <p className="media-error">{command.result_message}</p>}
                  </div>
                  <span className={`status-pill ${command.result_status === 'failed' ? 'status-failed' : 'status-processing'}`}>
                    {command.result_status || command.status}
                  </span>
                </div>
              ))}
            </div>
          )}
        </section>

        <button onClick={() => navigate(`/devices/${device.id}/assign`)} className="btn btn-primary">
          Assign Content
        </button>
      </div>
    </Layout>
  );
}
