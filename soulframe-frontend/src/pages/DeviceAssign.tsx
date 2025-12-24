import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { deviceApi, playlistApi, Device, Playlist } from '../api/endpoints';

export function DeviceAssign() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();

  const [device, setDevice] = useState<Device | null>(null);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [devicesData, playlistsData] = await Promise.all([
        deviceApi.list(),
        playlistApi.list(),
      ]);

      const foundDevice = devicesData.find((d) => d.id === deviceId);
      if (!foundDevice) {
        setError('Device not found');
        return;
      }

      setDevice(foundDevice);
      setPlaylists(playlistsData);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleAssign = async (playlistId: string) => {
    if (!deviceId) return;

    try {
      await deviceApi.assign(deviceId, playlistId);
      setSuccess(true);
    } catch (err: any) {
      setError(err.message);
    }
  };

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
              Select a playlist to display on this device
            </p>
          </div>
        )}

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
            {playlists.map((playlist) => (
              <div
                key={playlist.id}
                className="card card-clickable"
                onClick={() => handleAssign(playlist.id)}
              >
                <h3 style={{ margin: 0 }}>{playlist.name}</h3>
                <p className="text-secondary">{playlist.items.length} items</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
