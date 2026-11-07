# Instagram Profile Cloner V1.0.0

A powerful, automated Instagram scraper and profile cloner built with Python, Selenium, and `undetected-chromedriver`. It allows you to scrape a target user's followers list, filter accounts, download high-definition profile pictures, extract complete profile metadata into JSON, capture profile screenshots, and download story highlights.

---
## 🚀 Features

- **Anti-Bot Bypass**: Powered by `undetected-chromedriver` and persistent Chrome profiles to prevent login hurdles and detection.
- **Followers List Extraction**: Automatically opens and scrolls through a target account's follower modal to scrape follower usernames.
- **Comprehensive Profile Parsing**:
  - Exact followers, following, and posts count (even when formatted as `1.8M`).
  - Target `user_id`, username, full name, category, and bio.
  - Verified badge detection.
  - External links & post links.
- **High-Definition Media Downloads**:
  - Downloads HD profile pictures (`profile.png`).
  - Optional profile screenshot (`screenshot.png`) running asynchronously in a background thread.
- **Story Highlights Archiving**:
  - Automatically clicks through the Instagram "View story" obstacle.
  - Traverses through highlight stories, saves each story media (`story_N.png`), and exports `highlight.json`.
- **Smart Filtering & Organization**:
  - Group profiles into tagged directory folders (e.g. `clone/tag-group/username`).
  - Filter out accounts without profile pictures (`must_have_profile_picture=True`).
  - Filter out accounts without highlights (`must_have_highlights=True`).
  - Duplicate detection to prevent re-scraping existing profiles.
- **Proxy Support**: Route all image and highlight media requests through HTTP/HTTPS proxies.
- **Live Terminal Progress Bar**: Real-time terminal animation with spinner, progress bar percentage, and status updates via `LivePrinter`.

---

## 📂 Output Folder Structure

Scraped profiles are organized cleanly by tag groups and usernames:

```text
clone/
└── tech-influencers/
    ├── no-pic.txt                  # Cache of accounts with missing avatars
    └── john_doe/
        ├── profile.png             # HD Profile Picture
        ├── screenshot.png          # Full Browser Screenshot (Optional)
        ├── profile.json            # Complete Profile Metadata
        └── highlights/             # Downloaded Highlights (Optional)
            └── 17555550123456789/
                ├── highlight.json  # Highlight Info & Links
                ├── story_1.png     # Story Media
                ├── story_2.png
                └── ...
```

---

## 🛠️ Installation & Prerequisites

### 1. Requirements
- Python 3.8+
- Google Chrome installed
- Compatible `chromedriver.exe` placed in the project directory (or in PATH). Download it from [Chrome Official WebDriver Download Page](https://developer.chrome.com/docs/chromedriver/downloads)

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

Or install manually:
```bash
pip install undetected-chromedriver selenium beautifulsoup4 requests
```

---

## 💻 Usage

### 1. Command Line Interface (CLI)

You can run the script directly from your terminal:

```bash
# View all available CLI options
python instagram_profile_cloner.py --help

# Basic usage
python instagram_profile_cloner.py target_username -t design art -n 24

# Full options example
python instagram_profile_cloner.py target_username \
    --tags fitness sports \
    --count 50 \
    --must-have-highlights \
    --download-highlights \
    --profile-screenshot \
    --override-duplicate \
    --headless \
    --proxy "http://127.0.0.1:7890"

# Allow accounts without profile pictures:
python instagram_profile_cloner.py target_username --no-must-have-profile-picture
```

### 2. Python Script Usage

```python
from instagram_profile_cloner import selenuim_clone

# Clone 24 followers from a target account under the 'design' tag
selenuim_clone(
    username="target_username",
    tags=["design", "architecture"],
    count=24,
    must_have_profile_picture=True,
    must_have_highlights=True,
    download_highlights=True,
    profile_screenshot=True,
    proxy="",                    # e.g. "http://127.0.0.1:7890"
    override_duplicate=False
)
```

---

## ⚙️ Function Reference: `selenuim_clone`

| Parameter | Type | Default | Description |
|---|---|---|---|
| `username` | `str` | *Required* | Target Instagram username whose followers will be scraped. |
| `tags` | `list` | *Required* | Tag or list of tags used to group cloned profiles under `clone/<tags>/`. |
| `count` | `int` | `12` | Target follower count to scrape. Set to `0` for infinite scrolling (up to 1,000 scrolls). |
| `must_have_profile_picture` | `bool` | `True` | Skip profiles that have default avatars or are listed in `no-pic.txt`. |
| `must_have_highlights` | `bool` | `False` | Skip profiles that do not have any story highlights. |
| `download_highlights` | `bool` | `False` | Automatically click and download story highlight images for each profile. |
| `profile_screenshot` | `bool` | `False` | Capture and save a full browser screenshot of each profile (`screenshot.png`). |
| `proxy` | `str` | `""` | Optional HTTP/HTTPS proxy string for media downloads. |
| `override_duplicate` | `bool` | `False` | When `True`, re-scrapes and updates accounts that already exist in the clone directory. |
| `headless  ` | `bool` | `False` | When `True`, it willn't show the web driver scrolling. You should see actions in 10s for main page to load. It may not work in some cases. |

---

## ⚠️ Disclaimer

This tool is intended for educational, research, and personal archiving purposes only. Please respect Instagram's Terms of Service and community guidelines. The authors assume no liability for misuse or account restrictions resulting from automated access.
