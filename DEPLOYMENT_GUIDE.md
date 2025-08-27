# 🚀 Deployment Guide - Voice Email Agent

## Step 1: Containerization ✅ COMPLETED

The FastAPI backend is now containerized and ready for deployment.

### Files Created:
- `Dockerfile` - Optimized for WebSocket support and production
- `.dockerignore` - Minimizes build context for faster builds
- `fly.toml` - Fly.io configuration with WebSocket support
- `requirements.txt` - Consolidated production dependencies
- `test_docker.sh` - Local testing script

## Step 2: Deploy Backend to Fly.io

### Prerequisites:
1. Install Fly.io CLI: https://fly.io/docs/hands-on/install-flyctl/
2. Create Fly.io account: https://fly.io/app/sign-up

### Deployment Steps:

```bash
# 1. Test locally first (optional but recommended)
./test_docker.sh

# 2. Login to Fly.io
fly auth login

# 3. Launch the app (creates app and configures)
fly launch --no-deploy

# 4. Set required environment secrets
fly secrets set GEMINI_API_KEY=your_gemini_api_key_here
fly secrets set GOOGLE_CLIENT_ID=your_google_client_id
fly secrets set GOOGLE_CLIENT_SECRET=your_google_client_secret

# 5. Deploy the application
fly deploy

# 6. Check deployment status
fly status
fly logs
```

### Configuration Notes:

**App Name:** Update `fly.toml` line 4:
```toml
app = "your-unique-app-name"  # Change this!
```

**Region:** Update `fly.toml` line 5 for your preferred region:
```toml
primary_region = "ord"  # Chicago, change as needed
# Options: ord (Chicago), dfw (Dallas), lax (LA), ewr (NYC), etc.
```

**Your Backend URL will be:**
```
https://your-app-name.fly.dev
```

## Step 3: Deploy Frontend to Vercel

### Prerequisites:
1. Push code to GitHub repository
2. Create Vercel account: https://vercel.com/signup

### Deployment Steps:

1. **Import Project:**
   - Go to https://vercel.com/new
   - Import your GitHub repository
   - Select the `web/` directory as root

2. **Configure Environment Variables:**
   ```
   NEXT_PUBLIC_WS_URL=wss://your-app-name.fly.dev
   NEXT_PUBLIC_API_URL=https://your-app-name.fly.dev
   ```

3. **Deploy:**
   - Vercel will auto-deploy on push to main branch

**Your Frontend URL will be:**
```
https://your-project-name.vercel.app
```

## Step 4: Google OAuth Production Hardening

### Update Google Cloud Console:

1. **Go to:** https://console.cloud.google.com/apis/credentials
2. **Update OAuth 2.0 Client:**
   
   **Authorized JavaScript origins:**
   ```
   https://your-project-name.vercel.app
   ```
   
   **Authorized redirect URIs:**
   ```
   https://your-app-name.fly.dev/auth/callback
   ```

### Update Backend Configuration:

The OAuth service will automatically use the production URLs once deployed.

## Testing Production Deployment

### Backend Health Check:
```bash
curl https://your-app-name.fly.dev/health
```

### Frontend Access:
Visit `https://your-project-name.vercel.app`

### WebSocket Connection:
The frontend will automatically connect to the WebSocket at:
```
wss://your-app-name.fly.dev/ws/voice-session
```

## Monitoring & Maintenance

### Fly.io Commands:
```bash
fly logs              # View logs
fly status            # Check app status
fly scale count 1     # Scale to 1 instance
fly ssh console       # SSH into container
```

### Vercel Commands:
```bash
vercel logs           # View deployment logs
vercel --prod         # Manual production deployment
```

## Cost Estimates

- **Fly.io Backend:** ~$5-10/month (1GB RAM, shared CPU)
- **Vercel Frontend:** Free (hobby plan)
- **Total:** ~$5-10/month

## Security Checklist ✅

- ✅ WebSocket authentication required
- ✅ OAuth 2.0 with proper scopes
- ✅ HTTPS enforced
- ✅ Environment secrets properly configured
- ✅ Non-root container user
- ✅ Minimal container surface area
- ✅ Health checks configured

## Troubleshooting

### Common Issues:

**Build Fails:**
- Check `requirements.txt` dependencies
- Verify Docker is running locally

**WebSocket Connection Fails:**
- Ensure `force_https = true` in `fly.toml`
- Check CORS configuration in FastAPI

**OAuth Fails:**
- Verify callback URLs in Google Console
- Check environment secrets are set correctly

**Audio Issues:**
- Ensure frontend is served over HTTPS
- Check microphone permissions in browser
