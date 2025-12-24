import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './auth/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { Signup } from './pages/Signup';
import { Claim } from './pages/Claim';
import { Devices } from './pages/Devices';
import { DeviceAssign } from './pages/DeviceAssign';
import { MediaPage } from './pages/Media';
import { Playlists } from './pages/Playlists';
import { PlaylistEdit } from './pages/PlaylistEdit';
import { Account } from './pages/Account';

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/signup" element={<Signup />} />
          <Route path="/claim" element={<Claim />} />

          <Route
            path="/devices"
            element={
              <ProtectedRoute>
                <Devices />
              </ProtectedRoute>
            }
          />

          <Route
            path="/devices/:deviceId/assign"
            element={
              <ProtectedRoute>
                <DeviceAssign />
              </ProtectedRoute>
            }
          />

          <Route
            path="/media"
            element={
              <ProtectedRoute>
                <MediaPage />
              </ProtectedRoute>
            }
          />

          <Route
            path="/playlists"
            element={
              <ProtectedRoute>
                <Playlists />
              </ProtectedRoute>
            }
          />

          <Route
            path="/playlists/:playlistId"
            element={
              <ProtectedRoute>
                <PlaylistEdit />
              </ProtectedRoute>
            }
          />

          <Route
            path="/account"
            element={
              <ProtectedRoute>
                <Account />
              </ProtectedRoute>
            }
          />

          <Route path="/" element={<Navigate to="/devices" replace />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;
