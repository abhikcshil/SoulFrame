import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { deviceApi, mediaApi, playlistApi, Device, Media, Playlist } from '../api/endpoints';
import { getPlaylistReadiness } from '../utils/media';

export function DeviceAssign() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();

  const [device, setDevice] = useState<Device | null>(null);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [media, setMedia] = useState<Media[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [devicesData, playlistsData, mediaData] = await Promise.all([
        deviceApi.list(),
        playlistApi.list(),
        mediaApi.list(),
      ]);

      const foundDevice = devicesData.find((d) => d.id === deviceId);
      if (!foundDevice) {
        setError('Device not found');
        return;
      }

      setDevice(foundDevice);
      setPlaylists(playlistsData);
      setMedia(mediaData);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAssign = async (playlistId: string) => {
    if (!deviceId) return;
    const playlist = playlists.find((item) => item.id === playlistId);
    const readiness = playlist ? getPlaylistReadiness(playlist, mediaById) : null;
    if (!readiness?.canAssign) {
      setError(readiness?.reason || 'This playlist is not ready for device playback.');
      return;
    }

    try {
      setError('');
      await deviceApi.assign(deviceId, playlistId);
      setSuccess(true);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const mediaById = new Map(media.map((item) => [item.id, item]));

  if (isLoading) {
    return (
      <Layout showNav={false}>
        <div className="loading">Loading...</div>
      </Layout>
    );
  }

  if (success) {
    return (
      <Layout showNav={false}>
        <div className="container">
          <div className="success-box">
            <h2>✓ Playlist Assigned!</h2>
            <p>Your device will start displaying the playlist.</p>
          </div>

          <button onClick={() => navigate('/devices')} className="btn btn-primary">
            Back to Devices
          </button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout showNav={false}>
      <div className="container">
        <button onClick={() => navigate('/devices')} className="btn btn-secondary mb-24">
          ← Back
        </button>

        <h1>Assign Playlist</h1>

        {device && (
          <div className="card mb-24">
            <h3>{device.name}</h3>
            <p className="text-secondary">
              Select a playlist backed entirely by ready optimized playback assets.
            </p>
          </div>
        )}

        <div className="info-box">
          Devices receive optimized playback files, not raw uploads. Playlists with processing or failed media are blocked until those items are ready or removed.
        </div>

        {error && <p className="text-error">{error}</p>}

        {playlists.length === 0 ? (
          <div className="list-empty">
            <p>No playlists yet</p>
            <button onClick={() => navigate('/playlists')} className="btn btn-primary">
              Create Playlist
            </button>
          </div>
        ) : (
          <div className="gap-8">
            {playlists.map((playlist) => {
              const readiness = getPlaylistReadiness(playlist, mediaById);
              return (
              <div
                key={playlist.id}
                className={`card ${readiness.canAssign ? 'card-clickable' : 'card-disabled'}`}
                onClick={() => handleAssign(playlist.id)}
              >
                <h3 style={{ margin: 0 }}>{playlist.name}</h3>
                <p className="text-secondary">
                  {readiness.readyCount} ready of {playlist.items.length} item{playlist.items.length === 1 ? '' : 's'}
                </p>
                {readiness.canAssign ? (
                  <div className="metadata-row">
                    <span className="status-pill status-ready">Assignable</span>
                  </div>
                ) : (
                  <p className="media-error">{readiness.reason}</p>
                )}
              </div>
              );
            })}
          </div>
        )}
      </div>
    </Layout>
  );
}
