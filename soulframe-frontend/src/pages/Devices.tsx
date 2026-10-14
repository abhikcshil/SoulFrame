import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { deviceApi, Device } from '../api/endpoints';
import { formatRelativeTime, isDeviceOnline } from '../utils/device';

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

  if (isLoading) {
    return (
      <Layout>
        <div className="container">
          <div className="page-heading"><div><h1>My Devices</h1><p>Your frames, at a glance.</p></div></div>
          <div className="device-grid" aria-label="Loading devices">
            {[0, 1, 2].map((item) => <div className="card device-card skeleton-card" key={item} />)}
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container">
        <div className="page-heading">
          <div><h1>My Devices</h1><p>Your frames, at a glance.</p></div>
          <Link to="/claim" className="btn btn-primary">+ Claim New Device</Link>
        </div>

        {error && <p className="text-error">{error}</p>}

        {devices.length === 0 ? (
          <div className="list-empty">
            <p>No devices yet</p>
            <p className="text-secondary">
              Scan the QR code on your frame to get started
            </p>
          </div>
        ) : (
          <div className="device-grid">
            {devices.map((device) => (
              <div key={device.id} className="card device-card">
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
                    <div className="device-card-visual"><span className="device-card-orb" aria-hidden="true" /><span className="device-card-label">SOULFRAME</span></div>
                    <div className="device-card-title">
                      <h3>{device.name}</h3>
                      <button
                        onClick={(event) => {
                          event.stopPropagation();
                          handleEdit(device);
                        }}
                        className="btn btn-small btn-secondary"
                      >
                        Edit
                      </button>
                    </div>

                    <div className="device-card-status">
                      <span
                        className={`status-dot ${
                          isDeviceOnline(device) ? 'status-online' : 'status-offline'
                        }`}
                      ></span>
                      <span className="text-secondary">
                        {isDeviceOnline(device)
                          ? 'Online'
                          : `Last seen ${formatRelativeTime(device.last_seen_at)}`}
                      </span>
                    </div>

                    <div className="device-card-actions">
                      <button onClick={() => navigate(`/devices/${device.id}`)} className="btn btn-primary">Runtime Monitor</button>
                      <button onClick={() => navigate(`/devices/${device.id}/assign`)} className="btn btn-secondary">Assign Content</button>
                    </div>
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
