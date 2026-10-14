import { ReactNode, useEffect, useRef, useState } from 'react';
import { MoreHorizontal, Play, Trash2, X } from 'lucide-react';
import { Media, MediaAssetUrls, mediaApi } from '../api/endpoints';
import { formatDuration, formatResolution, mediaStatusLabel, mediaTypeLabel } from '../utils/media';

const PREVIEW_DELAY_MS = 350;
export const isVideoMedia = (item: Media) => (item.playback_mime_type || item.original_mime_type || item.mime_type).startsWith('video/');

interface MediaPreviewCardProps {
  item: Media;
  selected?: boolean;
  disabled?: boolean;
  onSelect?: () => void;
  onDelete?: () => void;
  actions?: ReactNode;
}

export function MediaPreviewCard({ item, selected = false, disabled = false, onSelect, onDelete, actions }: MediaPreviewCardProps) {
  const cardRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement>(null);
  const hoverTimer = useRef<number | null>(null);
  const [visible, setVisible] = useState(false);
  const [assets, setAssets] = useState<MediaAssetUrls | null>(null);
  const [isPreviewing, setIsPreviewing] = useState(false);
  const [showModal, setShowModal] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [retriedThumbnail, setRetriedThumbnail] = useState(false);

  const loadAssets = async (refresh = false) => {
    if (assets && !refresh) return assets;
    const next = await mediaApi.assetUrls(item.id);
    setAssets(next);
    return next;
  };

  useEffect(() => {
    const element = cardRef.current;
    if (!element || !('IntersectionObserver' in window)) { setVisible(true); return; }
    const observer = new IntersectionObserver(([entry]) => setVisible(entry.isIntersecting), { rootMargin: '160px' });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);
  useEffect(() => { if (visible && item.thumbnail_available) loadAssets().catch(() => undefined); }, [visible, item.id, item.thumbnail_available]);
  useEffect(() => {
    const video = videoRef.current;
    if (isPreviewing && video) video.play().catch(() => undefined);
    if (!isPreviewing && video) { video.pause(); video.removeAttribute('src'); video.load(); }
  }, [isPreviewing, assets?.preview_url]);
  useEffect(() => () => { if (hoverTimer.current) window.clearTimeout(hoverTimer.current); }, []);

  const stopPreview = () => { if (hoverTimer.current) window.clearTimeout(hoverTimer.current); hoverTimer.current = null; setIsPreviewing(false); };
  const startPreview = () => {
    if (disabled || !isVideoMedia(item) || item.status !== 'ready') return;
    hoverTimer.current = window.setTimeout(() => loadAssets(true).then((next) => next.preview_url && setIsPreviewing(true)).catch(() => undefined), PREVIEW_DELAY_MS);
  };
  const openPreview = (event?: React.SyntheticEvent) => { event?.stopPropagation(); stopPreview(); setShowMenu(false); setShowModal(true); };
  const activateCard = () => { if (disabled) return; if (onSelect) onSelect(); else if (isVideoMedia(item) && item.status === 'ready') openPreview(); };
  const retryThumbnail = () => { if (retriedThumbnail) return; setRetriedThumbnail(true); loadAssets(true).catch(() => undefined); };
  const metadata = [formatDuration(item.duration_seconds), formatResolution(item)].filter(Boolean).join(' · ') || 'Metadata pending';
  const cardIsActionable = !disabled && (Boolean(onSelect) || (isVideoMedia(item) && item.status === 'ready'));

  return <>
    <div ref={cardRef} className={`media-card media-library-card ${selected ? 'media-card-selected' : ''} ${disabled ? 'media-card-disabled' : ''}`} onMouseEnter={startPreview} onMouseLeave={stopPreview} onFocus={startPreview} onBlur={stopPreview} onClick={activateCard} role={cardIsActionable ? 'button' : undefined} tabIndex={cardIsActionable ? 0 : -1} onKeyDown={(event) => { if (cardIsActionable && (event.key === 'Enter' || event.key === ' ')) { event.preventDefault(); activateCard(); } }}>
      <div className="media-thumbnail">
        {isPreviewing && assets?.preview_url ? <video ref={videoRef} src={assets.preview_url} muted loop playsInline preload="metadata" aria-label={`Preview ${item.original_filename}`} /> : visible && assets?.thumbnail_url ? <img src={assets.thumbnail_url} alt={`Thumbnail for ${item.original_filename}`} loading="lazy" onError={retryThumbnail} /> : <span>{isVideoMedia(item) ? 'Video' : mediaTypeLabel(item)}</span>}
        {isVideoMedia(item) && item.status === 'ready' && <button className="media-preview-control" onClick={openPreview} aria-label={`Preview ${item.original_filename}`}><Play size={15} fill="currentColor" aria-hidden="true" /></button>}
        {onDelete && <div className="media-overflow" onClick={(event) => event.stopPropagation()}>
          <button className="media-overflow-trigger" aria-label={`Actions for ${item.original_filename}`} aria-expanded={showMenu} onClick={() => setShowMenu((current) => !current)}><MoreHorizontal size={19} aria-hidden="true" /></button>
          {showMenu && <div className="media-overflow-menu" role="menu"><button role="menuitem" onClick={openPreview}><Play size={15} aria-hidden="true" /> Preview</button><button className="media-overflow-danger" role="menuitem" onClick={onDelete}><Trash2 size={15} aria-hidden="true" /> Delete</button></div>}
        </div>}
      </div>
      <div className="media-card-content"><div className="media-card-title" title={item.original_filename}>{item.original_filename}</div><div className="metadata-row"><span>{metadata}</span></div><div className="media-card-badges"><span className={`status-pill status-${item.status}`}>{mediaStatusLabel(item)}</span>{selected && <span className="status-pill status-ready">Selected</span>}</div>{item.status === 'failed' && <p className="media-error">{item.processing_error || 'Processing failed.'}</p>}{disabled && <p className="media-subtle">Ready media is required to assign.</p>}</div>
      {actions && <div className="media-card-actions" onClick={(event) => event.stopPropagation()}>{actions}</div>}
    </div>
    {showModal && <MediaPreviewModal item={item} onClose={() => setShowModal(false)} />}
  </>;
}

export function MediaPreviewModal({ item, onClose }: { item: Media; onClose: () => void }) {
  const [assets, setAssets] = useState<MediaAssetUrls | null>(null);
  useEffect(() => { mediaApi.assetUrls(item.id).then(setAssets).catch(() => undefined); }, [item.id]);
  return <div className="modal-overlay" onClick={onClose} role="presentation"><div className="modal-sheet media-preview-sheet" onClick={(event) => event.stopPropagation()} role="dialog" aria-modal="true" aria-label={`Preview ${item.original_filename}`}><div className="modal-header"><strong title={item.original_filename}>{item.original_filename}</strong><button className="btn btn-small btn-secondary" onClick={onClose} aria-label="Close preview"><X size={17} aria-hidden="true" /></button></div><div className="modal-body">{isVideoMedia(item) && assets?.preview_url ? <video className="media-preview-player" src={assets.preview_url} controls playsInline preload="metadata" autoPlay /> : assets?.thumbnail_url ? <img className="media-preview-image" src={assets.thumbnail_url} alt={item.original_filename} /> : <p className="text-secondary">Preview is unavailable while this media is processing or has no generated thumbnail.</p>}</div></div></div>;
}
