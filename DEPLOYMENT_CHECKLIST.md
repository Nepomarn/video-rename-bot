# Render Deployment Checklist

## Pre-Deployment

- [ ] Get bot token from @BotFather on Telegram
- [ ] Create GitHub account (if you don't have one)
- [ ] Create Render account at render.com

## Files to Upload to GitHub

- [ ] bot.py
- [ ] requirements.txt
- [ ] runtime.txt
- [ ] .gitignore
- [ ] README.md

## Render Configuration

- [ ] Create new Web Service on Render
- [ ] Connect GitHub repository
- [ ] Set Runtime to "Python"
- [ ] Set Build Command: pip install -r requirements.txt
- [ ] Set Start Command: python bot.py
- [ ] Select "Free" instance type
- [ ] Add environment variable BOT_TOKEN with your token
- [ ] Click "Create Web Service"

## Post-Deployment

- [ ] Wait for deployment to complete (5-15 minutes)
- [ ] Check logs for "✅ Bot started successfully on Render!"
- [ ] Test bot by sending /start command
- [ ] Test file renaming with a small video file

## Troubleshooting

**Bot doesn't respond:**
- Check BOT_TOKEN is set correctly (no spaces, no quotes)
- Check logs for errors in Render dashboard

**"Module not found" error:**
- Verify requirements.txt was uploaded
- Check build logs in Render

**File processing fails:**
- Ensure file is under 500MB
- Check if file format is supported
- Review error message in bot response

## Support

If you encounter issues:
1. Check Render logs in dashboard
2. Verify all files uploaded correctly
3. Confirm BOT_TOKEN environment variable is set
4. Test with a small file first (under 10MB)
