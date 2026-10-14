import { useEffect, useRef, useState } from 'react';
import { Layout } from '../components/Layout';
import { Media, mediaApi } from '../api/endpoints';
import { MediaPreviewCard } from '../components/MediaPreview';
import { Upload } from 'lucide-react';

const PROCESSING_POLL_MS = 2000;
const waitForProcessingTick = () => new Promise((resolve) => window.setTimeout(resolve, PROCESSING_POLL_MS));

export function MediaPage() {
  const [media, setMedia] = useState<Media[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState<'uploading' | 'processing'>('uploading');
  const [error, setError] = useState('');
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { loadMedia(); }, []);
  const loadMedia = async () => { try { setMedia(await mediaApi.list()); } catch (err: any) { setError(err.message); } finally { setIsLoading(false); } };
  const handleFileChange = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]; if (!file) return;
    setError(''); setIsUploading(true); setUploadProgress(0); setUploadStage('uploading');
    try {
      const uploaded = await mediaApi.upload(file, setUploadProgress); setMedia((current) => [uploaded, ...current]); setUploadStage('processing');
      let processed = uploaded;
      while (processed.status === 'uploaded' || processed.status === 'processing') { await waitForProcessingTick(); processed = await mediaApi.get(uploaded.id); setMedia((current) => [processed, ...current.filter((item) => item.id !== processed.id)]); }
      if (processed.status === 'failed') setError(processed.processing_error || 'Media processing failed.');
    } catch (err: any) { setError(err.message); } finally { setIsUploading(false); if (fileInputRef.current) fileInputRef.current.value = ''; }
  };
  const handleDelete = async (mediaId: string) => { if (!confirm('Delete this media file?')) return; try { await mediaApi.delete(mediaId); setMedia((current) => current.filter((item) => item.id !== mediaId)); } catch (err: any) { setError(err.message); } };
  if (isLoading) return <Layout><div className="container"><div className="page-heading"><div><h1>Media Library</h1><p>Your videos, ready for a frame.</p></div></div><div className="media-grid" aria-label="Loading media">{[0, 1, 2, 3].map((item) => <div className="card skeleton-card" key={item} />)}</div></div></Layout>;
  return <Layout><div className="container"><div className="page-heading"><div><h1>Media Library</h1><p>Your videos, ready for a frame.</p></div><button onClick={() => fileInputRef.current?.click()} className="btn btn-primary" disabled={isUploading}><Upload size={17} aria-hidden="true" /> {isUploading ? 'Uploading...' : 'Upload Media'}</button></div>{error && <p className="text-error">{error}</p>}<input ref={fileInputRef} type="file" accept="image/*,video/*" onChange={handleFileChange} style={{ display: 'none' }} />{isUploading && <div className="upload-status mb-24"><div className="upload-status-header"><strong>{uploadStage === 'uploading' ? 'Uploading' : 'Processing'}</strong><span>{uploadStage === 'uploading' ? `${uploadProgress}%` : '100%'}</span></div><div className="progress-track"><div className="progress-fill" style={{ width: `${uploadProgress}%` }} /></div>{uploadStage === 'processing' && <p className="text-secondary">Upload complete. SoulFrame is preparing playback and thumbnail assets.</p>}</div>}{media.length === 0 ? <div className="list-empty"><p>No media yet</p><p className="text-secondary">Uploaded originals will be optimized before devices can play them.</p></div> : <div className="media-grid">{media.map((item) => <MediaPreviewCard key={item.id} item={item} onDelete={() => handleDelete(item.id)} />)}</div>}</div></Layout>;
}
