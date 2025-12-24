import { useState, useEffect, FormEvent } from 'react';
import { useSearchParams, useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../auth/AuthContext';
import { deviceApi } from '../api/endpoints';

export function Claim() {
  const [searchParams] = useSearchParams();
  const codeFromUrl = searchParams.get('code') || '';

  const [pairingCode, setPairingCode] = useState(codeFromUrl);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [claimedDeviceId, setClaimedDeviceId] = useState<string | null>(null);

  const { token, login } = useAuth();
  const navigate = useNavigate();

  // Auto-claim if logged in and code present
  useEffect(() => {
    if (token && codeFromUrl && !success) {
      handleClaim(codeFromUrl);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, codeFromUrl]);

  const handleClaim = async (code: string) => {
    setError('');
    setIsLoading(true);

    try {
      const device = await deviceApi.claim(code);
      setSuccess(true);
      setClaimedDeviceId(device.id);
    } catch (err: any) {
      setError(err.message || 'Failed to claim device');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoginAndClaim = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setIsLoading(true);

    try {
      await login(email, password);
      // After login, auto-claim will trigger via useEffect
    } catch (err: any) {
      setError(err.message || 'Login failed');
      setIsLoading(false);
    }
  };

  const handleManualClaim = async (e: FormEvent) => {
    e.preventDefault();

    if (!pairingCode.trim()) {
      setError('Please enter a pairing code');
      return;
    }

    await handleClaim(pairingCode.trim().toUpperCase());
  };

  // Success state
  if (success && claimedDeviceId) {
    return (
      <div className="centered-container">
        <div style={{ width: '100%', maxWidth: '400px' }}>
          <div className="success-box">
            <h2>✓ Device Claimed!</h2>
            <p>Your device has been successfully paired.</p>
          </div>

          <button onClick={() => navigate(`/devices`)} className="btn btn-primary">
            Go to Devices
          </button>
        </div>
      </div>
    );
  }

  // Not logged in - show login form
  if (!token) {
    return (
      <div className="centered-container">
        <div style={{ width: '100%', maxWidth: '400px' }}>
          <h1 className="text-center">Claim Device</h1>

          {codeFromUrl && (
            <div className="card mb-24">
              <p className="text-secondary text-center">Pairing Code</p>
              <h2
                className="text-center"
                style={{ fontSize: '32px', letterSpacing: '4px' }}
              >
                {codeFromUrl}
              </h2>
            </div>
          )}

          <p className="text-secondary text-center mb-24">
            Sign in to claim your device
          </p>

          <form onSubmit={handleLoginAndClaim} className="form">
            <div className="form-group">
              <label htmlFor="email" className="form-label">
                Email
              </label>
              <input
                id="email"
                type="email"
                className="form-input"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoComplete="email"
              />
            </div>

            <div className="form-group">
              <label htmlFor="password" className="form-label">
                Password
              </label>
              <input
                id="password"
                type="password"
                className="form-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                autoComplete="current-password"
              />
            </div>

            {error && <p className="text-error">{error}</p>}

            <button type="submit" className="btn btn-primary" disabled={isLoading}>
              {isLoading ? 'Signing in...' : 'Sign In & Claim'}
            </button>
          </form>

          <p className="text-center text-secondary mt-16">
            Don't have an account?{' '}
            <Link to="/signup" className="link">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    );
  }

  // Logged in - show manual claim form
  return (
    <div className="centered-container">
      <div style={{ width: '100%', maxWidth: '400px' }}>
        <h1 className="text-center">Claim Device</h1>

        <form onSubmit={handleManualClaim} className="form">
          <div className="form-group">
            <label htmlFor="code" className="form-label">
              Pairing Code
            </label>
            <input
              id="code"
              type="text"
              className="form-input"
              value={pairingCode}
              onChange={(e) => setPairingCode(e.target.value.toUpperCase())}
              placeholder="Enter pairing code"
              required
              style={{ textAlign: 'center', fontSize: '24px', letterSpacing: '2px' }}
            />
          </div>

          {error && <p className="text-error">{error}</p>}

          <button type="submit" className="btn btn-primary" disabled={isLoading}>
            {isLoading ? 'Claiming...' : 'Claim Device'}
          </button>
        </form>

        <p className="text-center text-secondary mt-16">
          <Link to="/devices" className="link">
            Back to devices
          </Link>
        </p>
      </div>
    </div>
  );
}
