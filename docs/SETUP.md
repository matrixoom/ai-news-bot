# GitHub Pages Setup Guide

This document explains how to set up GitHub Pages for the AI News Bot landing page.

## Steps to Enable GitHub Pages

1. **Push the docs folder to your GitHub repository**
   ```bash
   git add docs/
   git commit -m "Add GitHub Pages landing page"
   git push origin main
   ```

2. **Enable GitHub Pages in Repository Settings**
   - Go to your GitHub repository
   - Click on **Settings** tab
   - Scroll down to **Pages** section (in the left sidebar under "Code and automation")

3. **Configure GitHub Pages Source**
   - Under "Build and deployment"
   - Set **Source** to: `Deploy from a branch`
   - Set **Branch** to: `main`
   - Set **Folder** to: `/docs`
   - Click **Save**

4. **Wait for Deployment**
   - GitHub will automatically build and deploy your site
   - This usually takes 1-2 minutes
   - You'll see a green checkmark when it's ready

5. **Access Your Landing Page**
   - Your site will be available at: `https://YOUR_USERNAME.github.io/ai-news-bot/`
   - The URL will be shown in the Pages settings once deployment is complete

## Customize the Landing Page

Before publishing, update the placeholder links in `docs/index.html`:

1. Replace `YOUR_USERNAME` with your actual GitHub username
2. Update all GitHub repository URLs
3. Optionally add your own branding or styling

### Files to Update

**docs/index.html**: Replace all instances of:
- `https://github.com/YOUR_USERNAME/ai-news-bot` → Your actual repo URL

## Custom Domain (Optional)

If you want to use a custom domain:

1. Add a file named `CNAME` in the `docs/` directory
2. Put your domain name in the file (e.g., `ai-news-bot.yourdomain.com`)
3. Configure your DNS settings to point to GitHub Pages
4. See [GitHub's custom domain guide](https://docs.github.com/en/pages/configuring-a-custom-domain-for-your-github-pages-site)

## Troubleshooting

### Page Not Loading
- Check that the `docs/` folder is in the `main` branch
- Verify GitHub Pages is enabled in Settings → Pages
- Wait a few minutes after pushing changes

### 404 Error
- Ensure `index.html` exists in the `docs/` directory
- Check that the file is named exactly `index.html` (lowercase)
- Verify the branch and folder settings are correct

### Changes Not Showing
- GitHub Pages has a cache
- Try hard refresh: `Ctrl+Shift+R` (Windows) or `Cmd+Shift+R` (Mac)
- Wait 1-2 minutes for changes to propagate

## Local Testing

To test the landing page locally before pushing:

```bash
# Using Python's built-in server
cd docs
python -m http.server 8000

# Then visit: http://localhost:8000
```

## Additional Resources

- [GitHub Pages Documentation](https://docs.github.com/en/pages)
- [GitHub Pages Quickstart](https://docs.github.com/en/pages/quickstart)
- [Troubleshooting GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/troubleshooting-404-errors-for-github-pages-sites)
