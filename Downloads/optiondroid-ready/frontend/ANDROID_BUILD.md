# Android APK build guide

## 1) Set production API URL
Create `.env.local` in `frontend/`:

```env
NEXT_PUBLIC_API_BASE_URL=https://your-backend.up.railway.app
```

## 2) Install dependencies
```bash
npm install
```

## 3) Add Android platform once
```bash
npx cap add android
```

## 4) Build and sync
```bash
npm run mobile:sync
```

## 5) Open Android Studio
```bash
npm run mobile:open
```

Then build the APK from:
`Build > Build Bundle(s) / APK(s) > Build APK(s)`

## Notes
- The Android app cannot use your computer's localhost.
- Your backend must be deployed and reachable from the phone.
- Keep Robinhood credentials on the backend only.


## Production backend URL
Set the frontend API base URL to:

```env
NEXT_PUBLIC_API_BASE_URL=https://optiondroid-production.up.railway.app
```

## Android setup
From `frontend/` run:

```bash
npm install
npx cap add android
npm run mobile:sync
npm run mobile:open
```

Then in Android Studio build the APK from **Build > Build Bundle(s) / APK(s) > Build APK(s)**.
