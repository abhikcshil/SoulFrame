import { useNavigate } from 'react-router-dom';
import { Layout } from '../components/Layout';
import { useAuth } from '../auth/AuthContext';

export function Account() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <Layout>
      <div className="container">
        <h1>Account</h1>

        <div className="card mb-24">
          <h3>Profile</h3>
          <p className="text-secondary">Email</p>
          <p style={{ fontSize: '18px', marginBottom: '8px' }}>{user?.email}</p>
          <p className="text-secondary" style={{ fontSize: '12px' }}>
            Member since{' '}
            {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
          </p>
        </div>

        <button onClick={handleLogout} className="btn btn-danger">
          Sign Out
        </button>
      </div>
    </Layout>
  );
}
