import { useState, useEffect, useRef } from 'react';
import { Layout } from '../components/Layout';
import { mediaApi, Media } from '../api/endpoints';
import {
  formatDuration,
  formatFileSize,
  formatResolution,
  mediaStatusLabel,
  mediaTypeLabel,
} from '../utils/media';

export function MediaPage() {
  const [media, setMedia] = useState<Media[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    loadMedia();
  }, []);

  const loadMedia = async () => {
    try {
      const data = await mediaApi.list();
      setMedia(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setError('');
    setIsUploading(true);
    setUploadProgress(0);

    try {
      const newMedia = await mediaApi.upload(file, setUploadProgress);
      setMedia([newMedia, ...media]);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleDelete = async (mediaId: string) => {
    if (!confirm('Delete this media file?')) return;

    try {
      await mediaApi.delete(mediaId);
      setMedia(media.filter((m) => m.id !== mediaId));
    } catch (err: any) {
      setError(err.message);
    }
  };

  const metadata = (item: Media) => {
    const values = [
      formatResolution(item),
      formatDuration(item.duration_seconds),
      formatFileSize(item.playback_size_bytes || item.original_size_bytes || item.size_bytes),
    ].filter(Boolean);
    return values.length ? values.join(' / ') : 'Metadata pending';
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="loading">Loading media...</div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container">
        <h1>Media Library</h1>

        {error && <p className="text-error">{error}</p>}

        <div className="info-box">
          Upload originals here. SoulFrame prepares optimized playback files for devices and only ready media can be added to playlists.
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="image/*,video/*"
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />

        <button
          onClick={handleUploadClick}
          className="btn btn-primary mb-24"
          disabled={isUploading}
        >
          {isUploading ? 'Uploading...' : '+ Upload Media'}
        </button>

        {isUploading && (
          <div className="upload-status mb-24">
            <div className="upload-status-header">
              <strong>{uploadProgress < 100 ? 'Uploading' : 'Processing'}</strong>
              <span>{uploadProgress}%</span>
            </div>
            <div className="progress-track">
              <div className="progress-fill" style={{ width: `${uploadProgress}%` }} />
            </div>
            {uploadProgress === 100 && (
              <p className="text-secondary">Upload complete. SoulFrame is preparing the playback file.</p>
            )}
          </div>
        )}

        {media.length === 0 ? (
          <div className="list-empty">
            <p>No media yet</p>
            <p className="text-secondary">
              Uploaded originals will be optimized before devices can play them.
            </p>
          </div>
        ) : (
          <div className="media-grid">
            {media.map((item) => (
              <div key={item.id} className="media-card">
                <div className="media-card-content">
                  <div>
                    <div className="media-card-title">{item.original_filename}</div>
                    <div className="media-card-preview">{mediaTypeLabel(item)}</div>
                  </div>

                  <div>
                    <div className="media-card-badges">
                      <span className={`status-pill status-${item.status}`}>
                        {mediaStatusLabel(item)}
                      </span>
                      <span className="media-type-badge">{mediaTypeLabel(item)}</span>
                    </div>
                    <div className="metadata-row">
                      <span>{metadata(item)}</span>
                    </div>
                    {item.original_size_bytes && item.playback_size_bytes && (
                      <div className="metadata-row">
                        <span>Original {formatFileSize(item.original_size_bytes)}</span>
                        <span>Playback {formatFileSize(item.playback_size_bytes)}</span>
                      </div>
                    )}
                    {item.status === 'failed' && (
                      <p className="media-error">{item.processing_error || 'Processing failed.'}</p>
                    )}
                  </div>
                </div>

                <div className="media-card-actions">
                  <button
                    onClick={() => handleDelete(item.id)}
                    className="btn btn-small btn-danger"
                    style={{ padding: '4px 8px', fontSize: '12px', minHeight: '32px' }}
                  >
                    🗑️
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
