import { useState, useEffect, useRef } from 'react';
import { Layout } from '../components/Layout';
import { mediaApi, Media } from '../api/endpoints';

export function MediaPage() {
  const [media, setMedia] = useState<Media[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
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

    try {
      const newMedia = await mediaApi.upload(file);
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

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
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

        {media.length === 0 ? (
          <div className="list-empty">
            <p>No media yet</p>
            <p className="text-secondary">
              Upload photos and videos to display on your frames
            </p>
          </div>
        ) : (
          <div className="media-grid">
            {media.map((item) => (
              <div key={item.id} className="media-card">
                <div className="media-card-content">
                  <p style={{ fontSize: '12px', wordBreak: 'break-all' }}>
                    {item.original_filename}
                  </p>
                  <p className="text-secondary" style={{ fontSize: '11px', marginTop: '4px' }}>
                    {formatFileSize(item.size_bytes)}
                  </p>
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
