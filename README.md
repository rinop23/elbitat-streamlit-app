# Elbitat Social Agent - Streamlit Deployment

This folder contains all the files needed to deploy the Elbitat Social Agent to Streamlit Cloud.

## 📦 Files Included

### Required Files for Deployment:
- `streamlit_app.py` - Main Streamlit application
- `requirements.txt` - Python dependencies
- `elbitat_agent/` - Core agent modules
- `.streamlit/config.toml` - Streamlit configuration
- `.streamlit/credentials.yaml` - User authentication (DO NOT commit with real passwords)
- `.gitignore` - Git exclusions for security

## 🚀 Deployment Steps

### 1. Prepare GitHub Repository

```bash
cd streamlit-deploy
git init
git add .
git commit -m "Initial commit - Elbitat Social Agent"
```

Create a new repository on GitHub (e.g., `elbitat-streamlit-app`), then:

```bash
git remote add origin https://github.com/YOUR_USERNAME/elbitat-streamlit-app.git
git branch -M main
git push -u origin main
```

### 2. Configure Secrets on Streamlit Cloud

**IMPORTANT:** Do NOT commit real API keys or passwords to GitHub!

After deploying to Streamlit Cloud, go to your app settings and add these secrets:

```toml
# .streamlit/secrets.toml (Streamlit Cloud only)

# Meta API Credentials
META_ACCESS_TOKEN = "your_meta_access_token_here"
META_INSTAGRAM_ACCOUNT_ID = "your_instagram_business_account_id"
META_PIXEL_ID = "your_pixel_id_for_conversions_api"

# TikTok API Credentials (if using)
TIKTOK_ACCESS_TOKEN = "your_tiktok_access_token"
TIKTOK_OPEN_ID = "your_tiktok_open_id"

# User Credentials
[credentials]
cookie_name = "elbitat_auth"
cookie_key = "random_signature_key_change_this"
cookie_expiry_days = 30

[credentials.usernames.admin]
email = "admin@elbitat.com"
name = "Admin User"
password = "$2b$12$6cu1qsgrlyLIUoN6adH2nezrZbgfNp0.39dIFYSZZRwrl0ynWXZtq"  # admin123

[credentials.usernames.elbitat]
email = "info@elbitat.com"
name = "Elbitat Team"
password = "$2b$12$x047S/8YsNREG2neeDws3.Db3WmN.RTUDYV9lyzgde3inZ6V43PTC"  # elbitat2025
```

### 3. Deploy to Streamlit Cloud

1. Go to https://share.streamlit.io/
2. Sign in with GitHub
3. Click "New app"
4. Select your repository: `YOUR_USERNAME/elbitat-streamlit-app`
5. Set main file path: `streamlit_app.py`
6. Click "Deploy"

### 4. Change Default Passwords

**CRITICAL SECURITY STEP:**

After deployment, immediately:
1. Log in to your app
2. Go to Settings → User Account Settings
3. Expand "Change Password"
4. Change passwords for all users

Or generate new password hashes locally:

```bash
python generate_password.py
```

Then update the secrets in Streamlit Cloud settings.

## 🔐 Security Checklist

- [ ] Changed default passwords
- [ ] Added all API keys to Streamlit Cloud secrets
- [ ] Verified `.gitignore` excludes sensitive files
- [ ] Removed any hardcoded credentials from code
- [ ] Set strong cookie_key in secrets
- [ ] Tested authentication flow

## 📝 Environment Variables

The app reads these from Streamlit secrets:

| Variable | Required | Description |
|----------|----------|-------------|
| `META_ACCESS_TOKEN` | Yes | Meta Graph API access token |
| `META_INSTAGRAM_ACCOUNT_ID` | Yes | Instagram Business Account ID |
| `META_PIXEL_ID` | Optional | For Conversions API tracking |
| `TIKTOK_ACCESS_TOKEN` | Optional | TikTok API access token |
| `TIKTOK_OPEN_ID` | Optional | TikTok Open ID |

## 🔄 Updating the App

To update your deployed app:

```bash
cd streamlit-deploy
git add .
git commit -m "Update: description of changes"
git push
```

Streamlit Cloud will automatically redeploy.

## 📁 Folder Structure

```
streamlit-deploy/
├── streamlit_app.py          # Main app
├── requirements.txt           # Dependencies
├── .gitignore                # Git exclusions
├── .streamlit/
│   ├── config.toml           # Theme & server config
│   └── credentials.yaml      # Local auth (template)
└── elbitat_agent/            # Core modules
    ├── __init__.py
    ├── main.py
    ├── models.py
    ├── file_storage.py
    ├── paths.py
    └── agents/
        ├── orchestrator.py
        ├── creative_agent.py
        ├── posting_agent.py
        └── conversions_api.py
```

## 🆘 Troubleshooting

### "ModuleNotFoundError"
- Ensure all dependencies are in `requirements.txt`
- Check that `elbitat_agent` folder is included

### "Authentication Failed"
- Verify credentials.yaml format
- Check that bcrypt hashes are valid
- Ensure secrets.toml is configured in Streamlit Cloud

### "API Error"
- Verify all API tokens in Streamlit Cloud secrets
- Check token permissions and expiry
- Review logs in Streamlit Cloud dashboard

## 📞 Support

For issues:
1. Check Streamlit Cloud logs
2. Review DEPLOYMENT_GUIDE.md in parent directory
3. Verify all secrets are properly configured

---

**Last Updated:** December 5, 2025
