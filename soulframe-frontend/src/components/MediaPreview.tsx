import { ReactNode, useEffect, useRef, useState } from 'react';
import { Media, MediaAssetUrls, mediaApi } from '../api/endpoints';
import { formatDuration, formatFileSize, formatResolution, mediaStatusLabel, mediaTypeLabel } from '../utils/media';

const PREVIEW_DELAY_MS = 350;
export const isVideoMedia = (item: Media) => (item.playback_mime_type || item.original_mime_type || item.mime_type).startsWith('video/');

export function MediaPreviewCard({ item, selected = false, disabled = false, onSelect, actions }: { item: Media; selected?: boolean; disabled?: boolean; onSelect?: () => void; actions?: ReactNode }) {
  const cardRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const hoverTimer = useRef<number | null>(null);
  const [visible, setVisible] = useState(false);
  const [assets, setAssets] = useState<MediaAssetUrls | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const loadAssets = async (refresh = false) => {
    if (assets && !refresh) return assets;
    const next = await mediaApi.assetUrls(item.id); setAssets(next); return next;
  };
  useEffect(() => {
    const element = cardRef.current;
    if (!element || !('IntersectionObserver' in window)) { setVisible(true); return; }
    const observer = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting), { rootMargin: '160px' }); observer.observe(element); return () => observer.disconnect();
  }, []);
  useEffect(() => { if (visible && item.thumbnail_available) loadAssets().catch(() => undefined); }, [visible, item.id, item.thumbnail_available]);
  useEffect(() => { const video = videoRef.current; if (isPreviewing && video) video.play().catch(() => undefined); if (!isPreviewing && video) { video.pause(); video.removeAttribute('src'); video.load(); } }, [isPreviewing, assets?.preview_url]);
  useEffect(() => () => { if (hoverTimer.current) window.clearTimeout(hoverTimer.current); }, []);
  const startPreview = () => {
    if (disabled || !isVideoMedia(item) || item.status !== 'ready') return;
    hoverTimer.current = window.setTimeout(() => loadAssets(true).then((next) => next.preview_url && setIsPreviewing(true)).catch(() => undefined), PREVIEW_DELAY_MS);
  };
  const stopPreview = () => { if (hoverTimer.current) window.clearTimeout(hoverTimer.current); hoverTimer.current = null; setIsPreviewing(false); };
  const openPreview = (event: React.MouseEvent | React.KeyboardEvent) => { event.stopPropagation(); stopPreview(); setShowModal(true); };
  const metadata = [formatResolution(item), formatDuration(item.duration_seconds)].filter(Boolean).join(' · ') || 'Metadata pending';
  return <>
    <div ref={cardRef} className={`media-card media-library-card ${selected ? 'media-card-selected' : ''} ${disabled ? 'media-card-disabled' : ''}`} onMouseEnter={startPreview} onMouseLeave={stopPreview} onFocus={startPreview} onBlur={stopPreview} onClick={() => !disabled && onSelect?.()} role={onSelect ? 'button' : undefined} tabIndex={onSelect && !disabled ? 0 : -1} onKeyDown={(event) => { if (!disabled && onSelect && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); onSelect(); } }}>
      <div className="media-thumbnail">{isPreviewing && assets?.preview_url ? <video ref={videoRef} src={assets.preview_url} muted loop playsInline preload="metadata" aria-label={`Preview ${item.original_filename}`} /> : visible && assets?.thumbnail_url ? <img src={assets.thumbnail_url} alt={`Thumbnail for ${item.original_filename}`} loading="lazy" /> : <span>{isVideoMedia(item) ? 'Video' : mediaTypeLabel(item)}</span>}{isVideoMedia(item) && item.status === 'ready' && <button className="media-preview-control" onClick={openPreview} aria-label={`Preview ${item.original_filename}`}>▶</button>}</div>
      <div className="media-card-content"><div className="media-card-title" title={item.original_filename}>{item.original_filename}</div><div className="media-card-badges"><span className={`status-pill status-${item.status}`}>{mediaStatusLabel(item)}</span><span className="media-type-badge">{mediaTypeLabel(item)}</span>{selected && <span className="status-pill status-ready">Selected</span>}</div><div className="metadata-row"><span>{metadata}</span></div><div className="metadata-row"><span>{formatFileSize(item.playback_size_bytes || item.original_size_bytes || item.size_bytes)}</span></div>{item.status === 'failed' && <p className="media-error">{item.processing_error || 'Processing failed.'}</p>}{disabled && <p className="media-subtle">Ready media is required to assign.</p>}</div>
      {actions && <div className="media-card-actions" onClick={(event) => event.stopPropagation()}>{actions}</div>}
    </div>
    {showModal && <MediaPreviewModal item={item} onClose={() => setShowModal(false)} />}
  </>;
}

export function MediaPreviewModal({ item, onClose }: { item: Media; onClose: () => void }) {
  const [assets, setAssets] = useState<MediaAssetUrls | null>(null);
  useEffect(() => { mediaApi.assetUrls(item.id).then(setAssets).catch(() => undefined); }, [item.id]);
  return <div className="modal-overlay" onClick={onClose} role="presentation"><div className="modal-sheet media-preview-sheet" onClick={(event) => event.stopPropagation()}><div className="modal-header"><strong>{item.original_filename}</strong><button className="btn btn-small btn-secondary" onClick={onClose}>Close</button></div><div className="modal-body">{isVideoMedia(item) && assets?.preview_url ? <video className="media-preview-player" src={assets.preview_url} controls playsInline preload="metadata" autoPlay /> : assets?.thumbnail_url ? <img className="media-preview-image" src={assets.thumbnail_url} alt={item.original_filename} /> : <p className="text-secondary">Preview is unavailable while this media is processing or has no generated thumbnail.</p>}</div></div></div>;
}
