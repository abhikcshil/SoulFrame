# SoulFrame frontend

The dashboard is a mobile-first React 18/TypeScript/Vite application for user authentication, devices, media uploads/previews, playlists, assignments, and runtime monitoring.

## Start development

```powershell
npm install
npm run dev:host
```

Open `http://localhost:5173`. `dev:host` binds Vite to `0.0.0.0` so a phone on the same LAN can open `http://<development-pc-lan-ip>:5173`.

## API URL behavior

`VITE_API_BASE_URL` is optional. The client defaults to the current page host on port `8000`. If a build/configuration supplies a loopback API URL but the dashboard is opened through a LAN host, the client replaces the loopback host with the page host. This prevents a phone from accidentally calling its own `localhost`.

Use `.env.example` as a reference and keep local environment files uncommitted. The backend must be reachable and permit the page origin through CORS.

## Scripts

```powershell
npm run build       # TypeScript check and production Vite bundle
npm run dev          # Standard Vite development server
npm run dev:host     # Vite on all interfaces, port 5173
npm run preview      # Serve a built bundle locally
```

There is no dedicated frontend test script in the current package manifest. Use `npm run build` plus manual coverage of login, mobile access, upload/processing, thumbnails/previews, direct assignment, playlists, and runtime pages.

For component workflows and troubleshooting, see the repository [development guide](../docs/DEVELOPMENT.md) and [features guide](../docs/FEATURES.md).
