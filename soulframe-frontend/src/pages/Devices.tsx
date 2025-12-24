import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { deviceApi, Device } from '../api/endpoints';

export function Devices() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState('');

  const navigate = useNavigate();

  useEffect(() => {
    loadDevices();
  }, []);

  const loadDevices = async () => {
    try {
      const data = await deviceApi.list();
      setDevices(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleEdit = (device: Device) => {
    setEditingId(device.id);
    setEditName(device.name);
  };

  const handleSave = async (deviceId: string) => {
    try {
      await deviceApi.update(deviceId, editName);
      setDevices(
        devices.map((d) => (d.id === deviceId ? { ...d, name: editName } : d))
      );
      setEditingId(null);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handleCancel = () => {
    setEditingId(null);
    setEditName('');
  };

  const isOnline = (lastSeen: string | null) => {
    if (!lastSeen) return false;
    const diff = Date.now() - new Date(lastSeen).getTime();
    return diff < 60000; // 60 seconds
  };

  const formatLastSeen = (lastSeen: string | null) => {
    if (!lastSeen) return 'Never';

    const diff = Date.now() - new Date(lastSeen).getTime();
    const seconds = Math.floor(diff / 1000);
    const minutes = Math.floor(seconds / 60);
    const hours = Math.floor(minutes / 60);
    const days = Math.floor(hours / 24);

    if (seconds < 60) return 'Just now';
    if (minutes < 60) return `${minutes}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="loading">Loading devices...</div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container">
        <h1>My Devices</h1>

        {error && <p className="text-error">{error}</p>}

        <Link to="/claim" className="btn btn-primary mb-24">
          + Claim New Device
        </Link>

        {devices.length === 0 ? (
          <div className="list-empty">
            <p>No devices yet</p>
            <p className="text-secondary">
              Scan the QR code on your frame to get started
            </p>
          </div>
        ) : (
          <div className="gap-8">
            {devices.map((device) => (
              <div key={device.id} className="card">
                {editingId === device.id ? (
                  <div className="inline-edit">
                    <input
                      type="text"
                      className="form-input"
                      value={editName}
                      onChange={(e) => setEditName(e.target.value)}
                      autoFocus
                    />
                    <button
                      onClick={() => handleSave(device.id)}
                      className="btn btn-small btn-primary"
                    >
                      Save
                    </button>
                    <button
                      onClick={handleCancel}
                      className="btn btn-small btn-secondary"
                    >
                      Cancel
                    </button>
                  </div>
                ) : (
                  <>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        alignItems: 'center',
                        marginBottom: '8px',
                      }}
                    >
                      <h3 style={{ margin: 0 }}>{device.name}</h3>
                      <button
                        onClick={() => handleEdit(device)}
                        className="btn btn-small btn-secondary"
                      >
                        Edit
                      </button>
                    </div>

                    <div
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '8px',
                        marginBottom: '12px',
                      }}
                    >
                      <span
                        className={`status-dot ${
                          isOnline(device.last_seen_at) ? 'status-online' : 'status-offline'
                        }`}
                      ></span>
                      <span className="text-secondary">
                        {isOnline(device.last_seen_at)
                          ? 'Online'
                          : `Last seen ${formatLastSeen(device.last_seen_at)}`}
                      </span>
                    </div>

                    <button
                      onClick={() => navigate(`/devices/${device.id}/assign`)}
                      className="btn btn-secondary"
                    >
                      Assign Playlist
                    </button>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
