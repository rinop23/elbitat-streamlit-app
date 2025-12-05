⚠️ SECURITY NOTICE - READ BEFORE DEPLOYING ⚠️
================================================

This repository is PUBLIC. The following files are NOT included in git:

✅ EXCLUDED (Safe):
- .streamlit/credentials.yaml (contains password hashes)
- .streamlit/secrets.toml (API keys)
- ElbitatAds/ (local data)
- Foto Elbitat/ (images)

These files are protected by .gitignore and will NEVER be pushed to GitHub.

📝 DEPLOYMENT CHECKLIST:

1. ✅ Create PUBLIC GitHub repository at https://github.com/new
   - Name: elbitat-streamlit-app
   - Visibility: PUBLIC (required for Streamlit Community Cloud free tier)
   - Do NOT initialize with README

2. ✅ Push code to GitHub:
   git remote add origin https://github.com/YOUR_USERNAME/elbitat-streamlit-app.git
   git branch -M main
   git push -u origin main

3. ✅ Deploy on Streamlit Cloud (https://share.streamlit.io/)
   - Sign in with GitHub
   - Click "New app"
   - Select: YOUR_USERNAME/elbitat-streamlit-app
   - Main file: streamlit_app.py
   - Click "Deploy"

4. ✅ CRITICAL: Add Secrets in Streamlit Cloud
   - Go to app settings → Secrets
   - Copy content from .streamlit/secrets.toml.example
   - Add your real credentials:
     * META_ACCESS_TOKEN
     * META_INSTAGRAM_ACCOUNT_ID
     * META_PIXEL_ID (optional)
     * User passwords (bcrypt hashes)
     * Cookie secret key

5. ✅ Change Default Passwords
   - Log in to deployed app
   - Go to Settings → Change Password
   - Update passwords for admin and elbitat users

🔒 SECURITY NOTES:

- credentials.yaml is LOCAL ONLY - never committed to git
- All API keys must be added via Streamlit Cloud Secrets
- Never hardcode credentials in code
- Repository is public but secrets are safe in Streamlit Cloud
- .gitignore protects sensitive files

Need help? Check README.md for detailed instructions.
