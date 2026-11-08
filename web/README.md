# Zenith Official Website & Landing Page

This directory contains the production-ready static landing page for **Zenith**.

## Design Tokens & Theming
- Built with the exact same **Google Stitch & Soft Modernism** design system as the desktop app.
- Shared dark squircle iconography (`zenith_logo.svg`, `icon.png`, `favicon.ico`).
- Real-time acoustic equalizer canvas simulator matching the desktop HUD.
- Direct download integration pointing to the **v1.0.2** GitHub releases.

## Local Preview
Run any local static server:
```bash
# Python
python -m http.server 3000 --directory web

# Or with Node
npx serve web
```
Then open: [http://localhost:3000](http://localhost:3000)

## Deploying to GitHub Pages
1. Go to your GitHub repository **Settings** → **Pages**.
2. Under **Build and deployment** → **Source**, select **Deploy from a branch**.
3. Choose branch `main` and folder `/web`.
4. Click **Save** — your site will be live at `https://adbhut1234.github.io/Zenith/`!
