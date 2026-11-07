# Profile cards

Open `README.MD` and press **Ctrl+Shift+V** in VS Code to preview the profile. For a dark browser preview, open `preview.html` directly.

Cards are SVG files stored in `assets/generated/`. The profile loads them through jsDelivr and GitHub's image proxy to avoid direct redirects to `raw.githubusercontent.com`. The CDN can cache an older image, so displayed statistics may lag behind a successful update. The local `preview.html` uses the SVG files directly.

## First update

1. Commit and push these changes to `main` in `Sar-Chanrithy/Sar-Chanrithy`.
2. Open **Actions → Update profile cards** and check that the run succeeds. You can also select **Run workflow**.
3. The workflow replaces the initial empty cards with real GitHub data, then refreshes every 12 hours.

The workflow uses GitHub's automatic `GITHUB_TOKEN`; no personal access token or paid hosting is needed. The repository must allow Actions. Rules requiring pull requests for every change can block the bot's push; use an allowed workflow update path or commit generated files through a pull request if those rules apply.

Initial cards show an awaiting-update message, not invented statistics. Failed API requests leave previous cards untouched.

## What is measured

- Contributions: GitHub's contribution calendar for the last year, as visible to the workflow token.
- Repositories and stars: all owned public repositories, excluding forks; pagination includes more than 100 repositories.
- Languages: code bytes reported by GitHub across those repositories. HTML and CSS are included. This measures code volume, not skill or time spent coding.
- Timeline: contributions per calendar week; first and last weeks may be partial.
- Landscape: each day is a column; height and color follow GitHub's contribution intensity levels. This is a decorative view, not GitHub's interactive profile calendar.

Competitive programming cards need your actual platform handles. The existing snake workflow is still available separately, but its animation is no longer embedded in the README.

## Local generation

Python 3.11 or newer is sufficient, with no packages to install:

```powershell
python scripts/generate_profile.py --placeholder
```

For live data, set `GITHUB_TOKEN` securely in your environment and run:

```powershell
python scripts/generate_profile.py
```

Do not commit a token. Edit `header.svg`, `assets/toolkit.svg`, and `README.MD` to customize the design. The browser preview is a snapshot of the README layout; update it if you change the profile text. Its images always use the current SVG files.

Run offline checks with:

```powershell
python -m unittest discover -s scripts -v
```
