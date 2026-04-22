import type { Media, Playlist } from '../api/endpoints';

export function formatFileSize(bytes?: number | null) {
  if (!bytes) return 'Unknown size';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function formatDuration(seconds?: number | null) {
  if (!seconds) return null;
  const rounded = Math.round(seconds);
  const minutes = Math.floor(rounded / 60);
  const remainingSeconds = rounded % 60;
  if (minutes === 0) return `${remainingSeconds}s`;
  return `${minutes}:${String(remainingSeconds).padStart(2, '0')}`;
}

export function formatResolution(media: Media) {
  if (!media.width || !media.height) return null;
  return `${media.width} x ${media.height}`;
}

export function mediaTypeLabel(media: Media) {
  const mimeType = media.playback_mime_type || media.original_mime_type || media.mime_type;
  if (mimeType?.startsWith('video/')) return 'Video';
  if (mimeType?.startsWith('image/')) return 'Image';
  return 'Media';
}

export function mediaStatusLabel(media: Media) {
  if (media.status === 'ready') return 'Ready';
  if (media.status === 'failed') return 'Failed';
  if (media.status === 'processing') return 'Processing';
  return 'Uploaded';
}

export function mediaUnavailableReason(media: Media) {
  if (media.status === 'ready') return null;
  if (media.status === 'failed') return media.processing_error || 'Processing failed. Upload a new copy to try again.';
  if (media.status === 'processing') return 'Optimized playback file is still being prepared.';
  return 'Waiting to start optimization.';
}

export function isMediaReady(media?: Media) {
  return Boolean(media && media.status === 'ready' && media.playback_storage_key);
}

export function getPlaylistReadiness(playlist: Playlist, mediaById: Map<string, Media>) {
  const mediaItems = playlist.items.map((item) => mediaById.get(item.media_id)).filter(Boolean) as Media[];
  const missingCount = playlist.items.length - mediaItems.length;
  const unreadyItems = mediaItems.filter((media) => !isMediaReady(media));
  const readyCount = mediaItems.filter((media) => isMediaReady(media)).length;

  return {
    readyCount,
    unreadyCount: unreadyItems.length + missingCount,
    canAssign: playlist.items.length > 0 && missingCount === 0 && unreadyItems.length === 0,
    reason:
      playlist.items.length === 0
        ? 'Add ready media before assigning this playlist.'
        : missingCount > 0
          ? 'Some playlist media could not be found.'
          : unreadyItems.length > 0
            ? 'Contains media that is not ready for device playback.'
            : null,
  };
}
