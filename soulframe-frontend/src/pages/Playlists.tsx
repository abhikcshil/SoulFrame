import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { playlistApi, Playlist } from '../api/endpoints';

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
        <div className="loading">Loading playlists...</div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="container">
        <h1>Playlists</h1>

        {error && <p className="text-error">{error}</p>}

        <button
          onClick={handleCreate}
          className="btn btn-primary mb-24"
          disabled={isCreating}
        >
          {isCreating ? 'Creating...' : '+ Create Playlist'}
        </button>

        {playlists.length === 0 ? (
          <div className="list-empty">
            <p>No playlists yet</p>
            <p className="text-secondary">Create playlists to organize your media</p>
          </div>
        ) : (
          <div className="gap-8">
            {playlists.map((playlist) => (
              <div
                key={playlist.id}
                className="card card-clickable"
                onClick={() => navigate(`/playlists/${playlist.id}`)}
              >
                <h3 style={{ margin: 0 }}>{playlist.name}</h3>
                <p className="text-secondary">{playlist.items.length} items</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </Layout>
  );
}
