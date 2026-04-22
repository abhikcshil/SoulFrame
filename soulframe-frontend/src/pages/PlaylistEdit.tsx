import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { playlistApi, mediaApi, Playlist, Media } from '../api/endpoints';
import {
  formatDuration,
  formatResolution,
  isMediaReady,
  mediaStatusLabel,
  mediaTypeLabel,
  mediaUnavailableReason,
} from '../utils/media';

export function PlaylistEdit() {
  const { playlistId } = useParams<{ playlistId: string }>();
  const navigate = useNavigate();

  const [playlist, setPlaylist] = useState<Playlist | null>(null);
  const [allMedia, setAllMedia] = useState<Media[]>([]);
  const [playlistName, setPlaylistName] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);

  useEffect(() => {
    loadData();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playlistId]);

  const loadData = async () => {
    if (!playlistId) return;

    try {
      const [playlistsData, mediaData] = await Promise.all([
        playlistApi.list(),
        mediaApi.list(),
      ]);

      const found = playlistsData.find((p) => p.id === playlistId);
      if (!found) {
        setError('Playlist not found');
        return;
      }

      setPlaylist(found);
      setPlaylistName(found.name);
      setAllMedia(mediaData);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleSave = async () => {
    if (!playlist || !playlistId) return;

    setIsSaving(true);
    try {
      const items = playlist.items.map((item, index) => ({
        media_id: item.media_id,
        position: index,
      }));

      await playlistApi.update(playlistId, playlistName, items);
      navigate('/playlists');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsSaving(false);
    }
  };

  const handleAddMedia = (mediaId: string) => {
    if (!playlist) return;
    const media = allMedia.find((item) => item.id === mediaId);
    if (!isMediaReady(media)) {
      setError(media ? mediaUnavailableReason(media) || 'Media is not ready.' : 'Media is not available.');
      return;
    }

    const newItem = {
      id: `temp-${Date.now()}`,
      media_id: mediaId,
      position: playlist.items.length,
    };

    setPlaylist({
      ...playlist,
      items: [...playlist.items, newItem],
    });

    setShowAddModal(false);
  };

  const handleRemove = (index: number) => {
    if (!playlist) return;

    setPlaylist({
      ...playlist,
      items: playlist.items.filter((_, i) => i !== index),
    });
  };

  const handleMoveUp = (index: number) => {
    if (!playlist || index === 0) return;

    const newItems = [...playlist.items];
    [newItems[index - 1], newItems[index]] = [newItems[index], newItems[index - 1]];

    setPlaylist({
      ...playlist,
      items: newItems,
    });
  };

  const handleMoveDown = (index: number) => {
    if (!playlist || index === playlist.items.length - 1) return;

    const newItems = [...playlist.items];
    [newItems[index], newItems[index + 1]] = [newItems[index + 1], newItems[index]];

    setPlaylist({
      ...playlist,
      items: newItems,
    });
  };

  const getMediaName = (mediaId: string) => {
    const media = allMedia.find((m) => m.id === mediaId);
    return media?.original_filename || 'Unknown';
  };

  const getMedia = (mediaId: string) => allMedia.find((m) => m.id === mediaId);

  const selectedUnreadyCount = playlist?.items.filter((item) => !isMediaReady(getMedia(item.media_id))).length || 0;

  const mediaCandidates = allMedia.filter(
    (m) => !playlist?.items.some((item) => item.media_id === m.id)
  );

  if (isLoading) {
    return (
      <Layout showNav={false}>
        <div className="loading">Loading...</div>
      </Layout>
    );
  }

  if (!playlist) {
    return (
      <Layout showNav={false}>
        <div className="container">
          <p className="text-error">Playlist not found</p>
          <button onClick={() => navigate('/playlists')} className="btn btn-primary">
            Back to Playlists
          </button>
        </div>
      </Layout>
    );
  }

  return (
    <Layout showNav={false}>
      <div className="container">
        <button onClick={() => navigate('/playlists')} className="btn btn-secondary mb-24">
          ← Back
        </button>

        <h1>Edit Playlist</h1>

        {error && <p className="text-error">{error}</p>}

        <div className="info-box">
          Playlists can use ready media only. Processing or failed uploads stay visible in your library but cannot be sent to devices.
        </div>

        <div className="form-group mb-24">
          <label htmlFor="name" className="form-label">
            Playlist Name
          </label>
          <input
            id="name"
            type="text"
            className="form-input"
            value={playlistName}
            onChange={(e) => setPlaylistName(e.target.value)}
          />
        </div>

        <button onClick={() => setShowAddModal(true)} className="btn btn-secondary mb-24">
          + Add Media
        </button>

        {playlist.items.length === 0 ? (
          <div className="list-empty">
            <p>No items in this playlist</p>
            <p className="text-secondary">Add media from your library</p>
          </div>
        ) : (
          <div style={{ marginBottom: '24px' }}>
            {playlist.items.map((item, index) => (
              <div key={`${item.media_id}-${index}`} className="playlist-item">
                <div className="playlist-item-info">
                  <div className="playlist-item-name">{getMediaName(item.media_id)}</div>
                  <div className="text-secondary" style={{ fontSize: '12px' }}>
                    Position {index + 1}
                  </div>
                  {getMedia(item.media_id) && (
                    <div className="metadata-row">
                      <span className={`status-pill status-${getMedia(item.media_id)!.status}`}>
                        {mediaStatusLabel(getMedia(item.media_id)!)}
                      </span>
                      <span>{mediaTypeLabel(getMedia(item.media_id)!)}</span>
                      {formatResolution(getMedia(item.media_id)!) && (
                        <span>{formatResolution(getMedia(item.media_id)!)}</span>
                      )}
                      {formatDuration(getMedia(item.media_id)!.duration_seconds) && (
                        <span>{formatDuration(getMedia(item.media_id)!.duration_seconds)}</span>
                      )}
                    </div>
                  )}
                  {!isMediaReady(getMedia(item.media_id)) && (
                    <p className="media-error">
                      {getMedia(item.media_id)
                        ? mediaUnavailableReason(getMedia(item.media_id)!)
                        : 'This media is no longer available.'}
                    </p>
                  )}
                </div>

                <div className="playlist-item-controls">
                  <button
                    onClick={() => handleMoveUp(index)}
                    className="btn btn-small btn-secondary"
                    disabled={index === 0}
                  >
                    ↑
                  </button>

                  <button
                    onClick={() => handleMoveDown(index)}
                    className="btn btn-small btn-secondary"
                    disabled={index === playlist.items.length - 1}
                  >
                    ↓
                  </button>

                  <button
                    onClick={() => handleRemove(index)}
                    className="btn btn-small btn-danger"
                  >
                    ✕
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}

        {selectedUnreadyCount > 0 && (
          <p className="text-error mb-24">
            Remove {selectedUnreadyCount} not-ready item{selectedUnreadyCount === 1 ? '' : 's'} before saving this playlist.
          </p>
        )}

        <button onClick={handleSave} className="btn btn-primary" disabled={isSaving || selectedUnreadyCount > 0}>
          {isSaving ? 'Saving...' : 'Save Playlist'}
        </button>

        {/* Add Media Modal */}
        {showAddModal && (
          <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
            <div className="modal-sheet" onClick={(e) => e.stopPropagation()}>
              <div className="modal-header">
                <h3 style={{ margin: 0 }}>Add Media</h3>
                <button
                  onClick={() => setShowAddModal(false)}
                  className="btn btn-small btn-secondary"
                >
                  ✕
                </button>
              </div>

              <div className="modal-body">
                {mediaCandidates.length === 0 ? (
                  <p className="text-secondary text-center">No media available to add</p>
                ) : (
                  <div className="gap-8">
                    {mediaCandidates.map((media) => {
                      const ready = isMediaReady(media);
                      return (
                      <div
                        key={media.id}
                        className={`card ${ready ? 'card-clickable' : 'card-disabled'}`}
                        onClick={() => ready && handleAddMedia(media.id)}
                      >
                        <div style={{ fontSize: '14px', fontWeight: 600 }}>{media.original_filename}</div>
                        <div className="metadata-row">
                          <span className={`status-pill status-${media.status}`}>{mediaStatusLabel(media)}</span>
                          <span>{mediaTypeLabel(media)}</span>
                          {formatResolution(media) && <span>{formatResolution(media)}</span>}
                          {formatDuration(media.duration_seconds) && <span>{formatDuration(media.duration_seconds)}</span>}
                        </div>
                        {!ready && <p className="media-error">{mediaUnavailableReason(media)}</p>}
                      </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
