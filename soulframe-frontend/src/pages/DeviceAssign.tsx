import { useEffect, useMemo, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { deviceApi, Device, Media, mediaApi, Playlist, playlistApi } from '../api/endpoints';
import { formatFileSize, getPlaylistReadiness } from '../utils/media';

type AssignMode = 'library' | 'upload' | 'playlist';

export function DeviceAssign() {
  const { deviceId } = useParams<{ deviceId: string }>();
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [device, setDevice] = useState<Device | null>(null);
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [media, setMedia] = useState<Media[]>([]);
  const [mode, setMode] = useState<AssignMode>('library');
  const [isLoading, setIsLoading] = useState(true);
  const [isAssigning, setIsAssigning] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

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

      const foundDevice = devicesData.find((item) => item.id === deviceId);
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

  const mediaById = useMemo(() => new Map(media.map((item) => [item.id, item])), [media]);
  const readyMedia = useMemo(
    () => media.filter((item) => item.status === 'ready' && item.playback_storage_key),
    [media]
  );

  const handleAssignMedia = async (mediaId: string) => {
    if (!deviceId) return;
    const item = mediaById.get(mediaId);
    if (!item || item.status !== 'ready' || !item.playback_storage_key) {
      setError('Only ready media can be assigned directly.');
      return;
    }

    try {
      setError('');
      setIsAssigning(true);
      await deviceApi.assignMedia(deviceId, mediaId);
      setSuccess('Media assigned. The device will pick it up on its next sync.');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsAssigning(false);
    }
  };

  const handleAssignPlaylist = async (playlistId: string) => {
    if (!deviceId) return;
    const playlist = playlists.find((item) => item.id === playlistId);
    const readiness = playlist ? getPlaylistReadiness(playlist, mediaById) : null;
    if (!readiness?.canAssign) {
      setError(readiness?.reason || 'This playlist is not ready for device playback.');
      return;
    }

    try {
      setError('');
      setIsAssigning(true);
      await deviceApi.assign(deviceId, playlistId);
      setSuccess('Playlist assigned. The device will pick it up on its next sync.');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsAssigning(false);
    }
  };

  const handleUploadAndAssign = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !deviceId) return;

    setError('');
    setSuccess('');
    setIsUploading(true);
    setUploadProgress(0);

    try {
      const uploaded = await mediaApi.upload(file, setUploadProgress);
      setMedia((current) => [uploaded, ...current.filter((item) => item.id !== uploaded.id)]);

      if (uploaded.status === 'ready' && uploaded.playback_storage_key) {
        await deviceApi.assignMedia(deviceId, uploaded.id);
        setSuccess('Upload complete and media assigned.');
      } else {
        setSuccess('Upload complete. Media is processing and can be assigned when ready.');
      }
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
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
            <h2>Assigned</h2>
            <p>{success}</p>
          </div>

          <button onClick={() => navigate(`/devices/${deviceId}`)} className="btn btn-primary mb-24">
            View Device
          </button>
          <button onClick={() => setSuccess('')} className="btn btn-secondary">
            Assign Something Else
          </button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout showNav={false}>
      <div className="container">
        <button onClick={() => navigate(`/devices/${deviceId}`)} className="btn btn-secondary mb-24">
          Back
        </button>

        <h1>Assign Content</h1>

        {device && (
          <div className="card mb-24">
            <h3>{device.name}</h3>
            <p className="text-secondary">Pick one ready item, upload a new file, or use a playlist.</p>
          </div>
        )}

        <div className="assign-tabs">
          <button className={mode === 'library' ? 'active' : ''} onClick={() => setMode('library')}>
            Assign from Library
          </button>
          <button className={mode === 'upload' ? 'active' : ''} onClick={() => setMode('upload')}>
            Upload and Assign
          </button>
          <button className={mode === 'playlist' ? 'active' : ''} onClick={() => setMode('playlist')}>
            Assign Playlist
          </button>
        </div>

        {error && <p className="text-error">{error}</p>}

        {mode === 'library' && (
          <>
            <div className="info-box">
              Direct assignment is for fast testing and simple playback. Only ready optimized media can be selected.
            </div>

            {readyMedia.length === 0 ? (
              <div className="list-empty">
                <p>No ready media yet</p>
                <p className="text-secondary">Upload a file or wait for processing to finish.</p>
              </div>
            ) : (
              <div className="gap-8">
                {readyMedia.map((item) => (
                  <div key={item.id} className="card assign-row">
                    <div>
                      <h3 style={{ margin: 0 }}>{item.original_filename}</h3>
                      <p className="text-secondary">
                        {formatFileSize(item.playback_size_bytes || item.size_bytes)}
                      </p>
                    </div>
                    <button
                      onClick={() => handleAssignMedia(item.id)}
                      className="btn btn-small btn-primary"
                      disabled={isAssigning}
                    >
                      {isAssigning ? 'Assigning...' : 'Assign'}
                    </button>
                  </div>
                ))}
              </div>
            )}
          </>
        )}

        {mode === 'upload' && (
          <div className="card">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*,video/*"
              onChange={handleUploadAndAssign}
              style={{ display: 'none' }}
            />
            <h3>Upload and Assign</h3>
            <p className="text-secondary mb-24">
              Ready results are assigned immediately. Files that need processing stay in the library until ready.
            </p>
            {isUploading && (
              <div className="upload-status">
                <div className="upload-status-header">
                  <strong>{uploadProgress < 100 ? 'Uploading' : 'Processing'}</strong>
                  <span>{uploadProgress}%</span>
                </div>
                <div className="progress-track">
                  <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
                </div>
                {uploadProgress === 100 && (
                  <p className="text-secondary">Upload finished. Waiting for processing status.</p>
                )}
              </div>
            )}
            <button
              onClick={() => fileInputRef.current?.click()}
              className="btn btn-primary"
              disabled={isUploading}
            >
              {isUploading ? 'Uploading...' : 'Choose File'}
            </button>
          </div>
        )}

        {mode === 'playlist' && (
          <div>
            <div className="info-box">
              Playlists are still supported. Any processing or failed item blocks assignment until it is ready or removed.
            </div>

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
                      onClick={() => readiness.canAssign && handleAssignPlaylist(playlist.id)}
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
        )}
      </div>
    </Layout>
  );
}
