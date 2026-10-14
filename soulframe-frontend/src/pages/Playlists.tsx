import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { playlistApi, Playlist } from '../api/endpoints';
import { ChevronRight, ListVideo, Plus } from 'lucide-react';

export function Playlists() {
  const [playlists, setPlaylists] = useState<Playlist[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState('');

  const navigate = useNavigate();

  useEffect(() => {
    loadPlaylists();
  }, []);

  const loadPlaylists = async () => {
    try {
      const data = await playlistApi.list();
      setPlaylists(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreate = async () => {
    const name = prompt('Playlist name:');
    if (!name) return;

    setIsCreating(true);
    try {
      const playlist = await playlistApi.create(name);
      navigate(`/playlists/${playlist.id}`);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setIsCreating(false);
    }
  };

  if (isLoading) {
    return (
      <Layout>
        <div className="container">
          <div className="page-heading"><div><h1>Playlists</h1><p>Sequence media for your frames.</p></div></div>
          <div className="playlist-list" aria-label="Loading playlists">{[0, 1, 2].map((item) => <div className="playlist-row skeleton-card" key={item} />)}</div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container">
        <div className="page-heading">
          <div><h1>Playlists</h1><p>Sequence media for your frames.</p></div>
          <button onClick={handleCreate} className="btn btn-primary" disabled={isCreating}>
            <Plus size={17} aria-hidden="true" /> {isCreating ? 'Creating...' : 'Create Playlist'}
          </button>
        </div>

        {error && <p className="text-error">{error}</p>}

        {playlists.length === 0 ? (
          <div className="list-empty">
            <p>No playlists yet</p>
            <p className="text-secondary">Create playlists to organize your media</p>
          </div>
        ) : (
          <div className="playlist-list">
            {playlists.map((playlist) => (
              <div
                key={playlist.id}
                className="playlist-row card-clickable"
                onClick={() => navigate(`/playlists/${playlist.id}`)}
              >
                <div className="playlist-cover"><ListVideo size={20} aria-hidden="true" /></div>
                <div className="playlist-row-copy"><h3>{playlist.name}</h3><p>{playlist.items.length} {playlist.items.length === 1 ? 'item' : 'items'}</p></div>
                <ChevronRight className="playlist-chevron" size={20} aria-hidden="true" />
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
