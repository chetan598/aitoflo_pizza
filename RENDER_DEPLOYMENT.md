# Deploy Pizza Voice Agent to Render

## Prerequisites
1. GitHub repository with your code
2. Render account (free tier available)
3. All required API keys

## Step 1: Prepare Your Repository

Your repository should contain:
- `telephony_agent.py` ✅
- `requirements.txt` ✅
- `render.yaml` ✅
- `Dockerfile` ✅
- `Procfile` ✅
- `.gitignore` ✅

## Step 2: Deploy to Render

### Option A: Using Render Dashboard (Recommended)

1. **Go to Render Dashboard**
   - Visit: https://dashboard.render.com
   - Sign in with your GitHub account

2. **Create New Service**
   - Click "New +" → "Background Worker"
   - Connect your GitHub repository
   - Select your repository: `chetan598/aitoflo_pizza`

3. **Configure Service**
   - **Name**: `pizza-voice-agent`
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python telephony_agent.py`
   - **Plan**: `Starter` (Free)

4. **Add Environment Variables**
   ```
   LIVEKIT_URL=wss://your-livekit-url
   LIVEKIT_API_KEY=your-livekit-api-key
   LIVEKIT_API_SECRET=your-livekit-api-secret
   OPENAI_API_KEY=your-openai-api-key
   ELEVENLABS_API_KEY=your-elevenlabs-api-key
   DEEPGRAM_API_KEY=your-deepgram-api-key
   SUPABASE_URL=your-supabase-url
   SUPABASE_ANON_KEY=your-supabase-anon-key
   ```

5. **Deploy**
   - Click "Create Background Worker"
   - Wait for deployment to complete

### Option B: Using Render CLI

1. **Install Render CLI**
   ```bash
   npm install -g @render/cli
   ```

2. **Login to Render**
   ```bash
   render login
   ```

3. **Deploy from your local directory**
   ```bash
   cd C:\Users\Chetan\Downloads\livekit
   render deploy
   ```

## Step 3: Monitor Your Deployment

1. **Check Logs**
   - Go to your service dashboard
   - Click "Logs" tab
   - Look for "Agent ready for 10/10 performance!" message

2. **Test the Agent**
   - Use your LiveKit phone number to call
   - The agent should respond with "Thanks for calling Jimmy Neno's!"

## Step 4: Environment Variables Setup

Make sure to set these in Render dashboard:

### Required Variables:
- `LIVEKIT_URL`: Your LiveKit server URL
- `LIVEKIT_API_KEY`: Your LiveKit API key
- `LIVEKIT_API_SECRET`: Your LiveKit API secret
- `OPENAI_API_KEY`: Your OpenAI API key
- `ELEVENLABS_API_KEY`: Your ElevenLabs API key
- `DEEPGRAM_API_KEY`: Your Deepgram API key
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_ANON_KEY`: Your Supabase anonymous key

## Troubleshooting

### Common Issues:

1. **Build Fails**
   - Check `requirements.txt` has all dependencies
   - Ensure Python version compatibility

2. **Service Won't Start**
   - Verify all environment variables are set
   - Check logs for specific error messages

3. **Agent Not Responding**
   - Verify LiveKit credentials
   - Check if phone number is properly configured

### Logs to Check:
- Look for "Menu loaded from cache" or "Menu loaded from API"
- Check for "Agent ready for 10/10 performance!"
- Watch for any error messages

## Commands Summary

### Local Testing:
```bash
python telephony_agent.py
```

### Render Deployment:
```bash
# Using Dashboard (Recommended)
# Go to https://dashboard.render.com

# Using CLI
render deploy
```

### Check Status:
```bash
render status
```

## Cost Estimation
- **Free Tier**: 750 hours/month
- **Starter Plan**: $7/month for unlimited hours
- **Your agent**: Should run fine on free tier for testing

## Next Steps After Deployment
1. Test the voice agent with a phone call
2. Monitor logs for any issues
3. Scale up if needed (Starter plan)
4. Set up monitoring and alerts
