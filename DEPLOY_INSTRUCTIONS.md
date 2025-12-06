# Deployment Instructions

## Step 1: Push to GitHub

After creating a public GitHub repository, run these commands:

```bash
cd "c:\Users\hp\elbitat-social-agent\elbitat-social-agent\streamlit-deploy"

# Add your GitHub repository (replace with YOUR repository URL)
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git

# Push all commits
git push -u origin master
```

## Step 2: Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Sign in with GitHub
3. Click "New app"
4. Select your repository
5. Set:
   - **Branch:** master
   - **Main file path:** streamlit_app.py
6. Click "Advanced settings"
7. Add your secrets (copy from `.streamlit/secrets.toml.example`):

```toml
OPENAI_API_KEY = "your-actual-openai-api-key"

[meta]
access_token = "your-meta-access-token"
instagram_account_id = "your-instagram-id"
facebook_page_id = "your-facebook-page-id"

[credentials]
[credentials.usernames]
[credentials.usernames.admin]
name = "Administrator"
password = "$2b$12$6cu1qsgrlyLIUoN6adH2nezrZbgfNp0.39dIFYSZZRwrl0ynWXZtq"

[credentials.usernames.elbitat]
name = "Elbitat Team"
password = "$2b$12$x047S/8YsNREG2neeDws3.Db3WmN.RTUDYV9lyzgde3inZ6V43PTC"
```

8. Click "Deploy"

## Important Notes

- **OpenAI API Key:** Get from https://platform.openai.com/api-keys
- **Meta Access Token:** Get from Meta Developer Console
- **Repository must be PUBLIC** for free Streamlit Cloud tier
- Initial deployment takes 5-10 minutes

## Troubleshooting

If the app doesn't work in production:
1. Check Streamlit Cloud logs for errors
2. Verify all secrets are properly configured
3. Make sure `requirements.txt` includes all dependencies
4. Ensure OpenAI API key is valid and has credits

## Current Status

✅ All files committed and ready to push
✅ OpenAI integration configured
✅ Interactive edit mode added
✅ Quick action buttons fixed
⏳ Waiting for GitHub push
⏳ Waiting for Streamlit Cloud deployment
