import argparse
import os
import pathlib
import re
import requests
import time
import json
import sys
import threading
import sys
import logging
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.keys import Keys
import selenium.common.exceptions 
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup

TOOL_NAME = "INSTAGRAM PROFILES CLONER"
TOOL_VERSION = "v1.0.0"
TOOL_BANNER = """                   
       __    __     ______   ______    
      /\ "-./  \   /\  == \ /\  ___\   
      \ \ \-./\ \  \ \  _-/ \ \___  \  
       \ \_\ \ \_\  \ \_\    \/\_____\ 
        \/_/  \/_/   \/_/     \/_____/ 
                                 
           < Mass Panda Tools >
 @MassPandaTools | Instagram, Telegram & Github
 
 """

logging.basicConfig(
    filename="errors.txt",
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

def handle_unhandled_exception(exc_type, exc_value, exc_traceback):
    """Logs unhandled exceptions to file instead of printing tracebacks to stderr."""
    # Allow KeyboardInterrupt (Ctrl+C) to exit cleanly without being logged
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    logging.error(
        "Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback)
    )
    print("An unexpected error occurred. Details have been saved to log.txt.")

sys.excepthook = handle_unhandled_exception

class LivePrinter:
    def __init__(self, header: str, footer: str, total_steps: int = 100, bar_length: int = 25):
        self.header = header
        self.footer = footer
        self.total_steps = total_steps
        self.bar_length = bar_length
        self.current_step = 0
        self.spinner_frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.spinner_idx = 0
        self.first_render = True

    def _render_bar(self) -> str:
        percent = min(1.0, max(0.0, self.current_step / self.total_steps))
        filled = int(self.bar_length * percent)
        bar = "█" * filled + "░" * (self.bar_length - filled)
        return f"[{bar}] {int(percent * 100):>3}%"

    def update(self, dynamic_text: str, step: int = None):
        """Pass only your changing text message, and optionally the current step."""
        if step is not None:
            self.current_step = step

        spinner = self.spinner_frames[self.spinner_idx % len(self.spinner_frames)]
        self.spinner_idx += 1

        bar = self._render_bar()
        middle_line = f"[>] {dynamic_text}  {bar}"

        if self.first_render:
            # Draw initial 3 lines
            sys.stdout.write(f"{self.header}\n{middle_line}\n{self.footer}\n")
            self.first_render = False
        else:
            # 1. Move up 2 lines to the middle line (\033[2A)
            # 2. Go to line start (\r)
            # 3. Clear existing text (\033[K)
            # 4. Print updated dynamic text
            # 5. Move down 1 line to footer (\033[1B)
            sys.stdout.write(f"\033[2A\r\033[K{middle_line}\n\033[1B")

        sys.stdout.flush()

    def finish(self, final_text: str = "Done!"):
        """Call when execution completes to finalize cursor position."""
        self.update(final_text, step=self.total_steps)
        sys.stdout.write("\n")
        sys.stdout.flush()

def get_tag_group(tags) -> str:
    # 1. If passed as a single string, split it into elements
    if isinstance(tags, str):
        # Splits by comma, hyphen, space, or underscore
        tags = re.split(r'[, \-_]+', tags)
    
    # 2. Clean whitespace, lowercase, and deduplicate
    normalized = sorted({tag.strip().lower() for tag in tags if tag.strip()})
    
    # 3. Join with hyphens
    return "-".join(normalized)

def clean_invisible_chars(obj):
    pattern = re.compile(r'[\u200e\u200f\u200b\u200c\u200d\ufeff]')
    
    if isinstance(obj, str):
        return pattern.sub('', obj).strip()
    elif isinstance(obj, dict):
        return {clean_invisible_chars(k): clean_invisible_chars(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_invisible_chars(item) for item in obj]
    return obj

def _parse_int_safely(val: Optional[str]) -> Optional[int]:
    """Strip commas/dots and convert to int if possible."""
    if not val:
        return None
    cleaned = val.replace(",", "").replace(".", "").strip()
    return int(cleaned) if cleaned.isdigit() else None

def extract_instagram_profile(html_content: str) -> Dict[str, Any]:
    """Parse Instagram profile HTML and extract all profile details as a dictionary."""
    soup = BeautifulSoup(html_content, "html.parser")

    # 1. Target user_id extraction
    user_id = None
    m_uid = (
        re.search(r'"profile_id":"(\d+)"', html_content)
        or re.search(r'"props":\{"id":"(\d+)"', html_content)
        or re.search(r'"page_id":"profilePage_(\d+)"', html_content)
        or re.search(r'"container_id":"(\d+)"', html_content)
    )
    if m_uid:
        user_id = m_uid.group(1)

    # 2. Meta / OpenGraph information
    meta_info: Dict[str, str] = {}
    for m in soup.find_all("meta"):
        prop = m.get("property") or m.get("name")
        content = m.get("content")
        if prop and content:
            meta_info[prop] = content

    og_url = meta_info.get("og:url", "")
    canonical_link = soup.find("link", rel="canonical")
    canonical_url = canonical_link.get("href", "") if canonical_link else og_url

    # Target username
    target_username = ""
    ios_url = meta_info.get("al:ios:url", "")
    if "username=" in ios_url:
        target_username = ios_url.split("username=")[-1].split("&")[0]
    elif canonical_url:
        match = re.search(r"instagram\.com/([^/?#]+)", canonical_url)
        if match:
            target_username = match.group(1)

    og_title = meta_info.get("og:title", "")
    og_desc = meta_info.get("og:description", "")
    meta_desc = meta_info.get("description", "")

    # Full name from og:title
    full_name_meta = ""
    if og_title and target_username:
        title_match = re.search(
            r"^(?:[\u200e\u200f\s]*)(.*?)(?:[\u200e\u200f\s]*)\s*\(@(?:www\.)?"
            + re.escape(target_username)
            + r"\)",
            og_title,
        )
        if title_match:
            full_name_meta = title_match.group(1).strip("\u200e\u200f ")

    # Metrics from description tag
    followers_meta = None
    following_meta = None
    posts_meta = None
    desc_to_parse = og_desc or meta_desc
    if desc_to_parse:
        m_counts = re.search(
            r"([\d\.,KMkm]+)\s+Followers,\s+([\d\.,KMkm]+)\s+Following,\s+([\d\.,KMkm]+)\s+Posts",
            desc_to_parse,
        )
        if m_counts:
            followers_meta = m_counts.group(1)
            following_meta = m_counts.group(2)
            posts_meta = m_counts.group(3)

    # 3. Header elements from DOM
    header = soup.find("header")
    header_texts: List[str] = list(header.stripped_strings) if header else []

    header_username = None
    h2 = header.find("h2") if header else None
    if h2:
        header_username = h2.get_text(strip=True)
    if not target_username and header_username:
        target_username = header_username

    # Verification status
    is_verified = False
    if header:
        for tag in header.find_all(True):
            if (
                tag.get("title") == "Verified"
                or tag.get("aria-label") == "Verified"
                or "Verified" in tag.stripped_strings
            ):
                is_verified = True
                break

    # Profile avatar image
    profile_pic_url = meta_info.get("og:image")
    if header:
        img_avatar = header.find("img")
        if img_avatar and img_avatar.get("src"):
            profile_pic_url = img_avatar.get("src")

    # Counts & exact numbers
    posts_count_str = posts_meta
    followers_count_str = followers_meta
    following_count_str = following_meta

    followers_exact_str = None
    following_exact_str = None
    posts_exact_str = posts_meta

    if header:
        # Search for exact followers count (often in title="1,874,241" attribute on span)
        for a in header.find_all("a"):
            a_text = a.text
            if "followers" in a_text:
                span_title = a.find("span", title=True)
                if span_title and span_title.get("title"):
                    followers_exact_str = span_title["title"]
            elif "following" in a_text:
                span_title = a.find("span", title=True)
                if span_title and span_title.get("title"):
                    following_exact_str = span_title["title"]
                else:
                    for t in a.stripped_strings:
                        if t.isdigit() or t.replace(",", "").isdigit():
                            following_exact_str = t
                            break

    if header_texts:
        for i, text in enumerate(header_texts):
            if text == "posts" and i > 0:
                posts_count_str = header_texts[i - 1]
                if not posts_exact_str:
                    posts_exact_str = header_texts[i - 1]
            elif text == "followers" and i > 0:
                followers_count_str = header_texts[i - 1]
            elif text == "following" and i > 0:
                following_count_str = header_texts[i - 1]
                if not following_exact_str:
                    following_exact_str = header_texts[i - 1]

    # Convert exact numbers to integers
    followers_exact_num = _parse_int_safely(followers_exact_str) or _parse_int_safely(followers_count_str)
    following_exact_num = _parse_int_safely(following_exact_str) or _parse_int_safely(following_count_str)
    posts_exact_num = _parse_int_safely(posts_exact_str) or _parse_int_safely(posts_count_str)

    # Full name, category, bio, links
    full_name = full_name_meta
    category = None
    bio = None
    external_links_text = None

    if header_texts:
        try:
            posts_idx = header_texts.index("posts")
            if posts_idx >= 2:
                candidate = header_texts[posts_idx - 2]
                if candidate not in ["Options", "Verified", header_username]:
                    full_name = candidate
        except ValueError:
            pass

        try:
            following_idx = header_texts.index("following")
            remaining = header_texts[following_idx + 1 :]
            filtered_remaining = []
            for item in remaining:
                if item in ["Following", "Message", "Down chevron icon", "Options"]:
                    break
                filtered_remaining.append(item)

            for item in filtered_remaining:
                if (
                    "youtube.com" in item
                    or ("and " in item and "more" in item)
                    or "Link icon" in item
                ):
                    external_links_text = item.replace("Link icon", "").strip()
                elif not category and item in [
                    "Blogger",
                    "Creator",
                    "Artist",
                    "Musician/band",
                    "Public figure",
                    "Entrepreneur",
                    "Author",
                ]:
                    category = item
                elif not bio and len(item) > 1 and item != "Link icon":
                    if category and item != category:
                        bio = item
                    elif not category:
                        bio = item
        except ValueError:
            pass

    # Bio fallback from meta description
    if not bio and meta_desc:
        bio_match = re.search(
            r'on Instagram:\s*"(?:[\u200e\u200f\s]*)"?(.*?)"?(?:[\u200e\u200f\s]*)"$',
            meta_desc,
        )
        if bio_match:
            bio = bio_match.group(1).strip('\u200e\u200f "')

    # External links summary
    external_links = None
    if external_links_text:
        external_links = {"summary": external_links_text}
        m_more = re.search(r"and\s+(\d+)\s+more", external_links_text)
        if m_more:
            external_links["additional_links_count"] = int(m_more.group(1))
            external_links["primary_link_display"] = external_links_text.split(" and ")[0].strip()
        else:
            external_links["primary_link_display"] = external_links_text

    # 4. Story Highlights (with exact highlight links and IDs)
    highlights: List[Dict[str, Any]] = []
    hl_links = soup.find_all("a", href=lambda h: h and "/stories/highlights/" in h)
    for a in hl_links:
        href = a["href"]
        full_link = f"https://www.instagram.com{href}" if href.startswith("/") else href
        m_hl_id = re.search(r"/stories/highlights/(\d+)", href)
        hl_id = m_hl_id.group(1) if m_hl_id else None

        img = a.find("img")
        cover_url = img.get("src") if img else None

        title = None
        span = a.find("span")
        if span:
            title = span.get_text(strip=True)
        if not title:
            strings = list(a.stripped_strings)
            if strings:
                title = strings[0]

        highlights.append({
            "title": title,
            "link": full_link,
            "highlight_id": hl_id,
            "cover_image_url": cover_url,
        })

    # Fallback for highlights from img tags if anchor tags aren't present
    if not highlights:
        highlight_imgs = soup.find_all("img", alt=lambda a: a and "highlight story" in a)
        for img in highlight_imgs:
            parent = img.find_parent(
                lambda tag: tag.name in ["li", "div"] and tag.find("span") is not None
            )
            title = None
            if parent:
                span = parent.find("span")
                if span:
                    title = span.get_text(strip=True)
            highlights.append({
                "title": title,
                "link": None,
                "highlight_id": None,
                "cover_image_url": img.get("src"),
            })

    # 5. Posts / Media Feed
    posts: List[Dict[str, Any]] = []
    post_links = soup.find_all("a", href=lambda h: h and ("/p/" in h or "/reel/" in h))
    for a in post_links:
        href = a["href"]
        m_code = re.search(r"/(p|reel)/([^/?#]+)", href)
        if not m_code:
            continue
        p_type = "reel" if m_code.group(1) == "reel" else "post"
        shortcode = m_code.group(2)

        m_author = re.search(r"^/([^/]+)/(?:p|reel)/", href)
        author = m_author.group(1) if m_author else target_username

        inner_texts = list(a.stripped_strings)
        is_pinned = "Pinned post icon" in inner_texts
        is_carousel = "Carousel" in inner_texts
        if "Clip" in inner_texts:
            p_type = "reel"
        elif is_carousel:
            p_type = "carousel"

        img = a.find("img")
        caption = img.get("alt") if img else None
        thumbnail_url = img.get("src") if img else None

        posts.append({
            "shortcode": shortcode,
            "type": p_type,
            "url": f"https://www.instagram.com{href}" if href.startswith("/") else href,
            "author_username": author,
            "is_collaboration_or_tagged": author != target_username,
            "is_pinned": is_pinned,
            "caption": caption,
            "thumbnail_url": thumbnail_url,
        })

    return {
        "profile": {
            "user_id": user_id,
            "username": target_username,
            "full_name": full_name,
            "is_verified": is_verified,
            "category": category,
            "biography": bio,
            "profile_picture_url": profile_pic_url,
            "profile_url": canonical_url or f"https://www.instagram.com/{target_username}/",
            "stats": {
                "posts_count": {
                    "header_display": posts_count_str,
                    "meta_display": posts_meta,
                    "exact_number": posts_exact_num,
                    "exact_number_str": posts_exact_str,
                },
                "followers_count": {
                    "header_display": followers_count_str,
                    "meta_display": followers_meta,
                    "exact_number": followers_exact_num,
                    "exact_number_str": followers_exact_str or followers_count_str,
                },
                "following_count": {
                    "header_display": following_count_str,
                    "meta_display": following_meta,
                    "exact_number": following_exact_num,
                    "exact_number_str": following_exact_str or following_count_str,
                },
            },
            "external_links": external_links,
            "highlights_count": len(highlights),
            "highlights": highlights,
            "posts_count_loaded": len(posts),
            "posts": posts,
        },
        "metadata": {
            "og_title": og_title,
            "og_description": og_desc,
            "og_image": meta_info.get("og:image"),
            "og_url": og_url,
            "app_links": {
                "ios": meta_info.get("al:ios:url"),
                "android": meta_info.get("al:android:url"),
            },
        },
    }

def get_current_story_media(driver) -> Optional[Dict[str, str]]:
    """
    Extract active story media (video or image) currently playing on screen.
    Returns dict with {'type': 'video'|'image', 'url': str}.
    """
    js_extract = """
    const result = { type: null, url: null };
    
    // 1. Check for active visible video tag
    const videos = Array.from(document.querySelectorAll('section video, div[role="dialog"] video, video'));
    for (const v of videos) {
        const rect = v.getBoundingClientRect();
        if (rect.width > 100 && rect.height > 100) {
            let src = v.currentSrc || v.src;
            if (!src) {
                const source = v.querySelector('source');
                if (source) src = source.src;
            }
            if (src && !src.startsWith('blob:')) {
                result.type = 'video';
                result.url = src;
                return result;
            }
        }
    }

    // 2. If video was blob or no direct video tag, check browser performance network entries for mp4
    const entries = performance.getEntriesByType('resource');
    const mp4Entries = entries.filter(e => e.name.includes('.mp4') || (e.name.includes('/v/t') && e.name.includes('video')));
    if (mp4Entries.length > 0) {
        const hasVisibleVideo = videos.some(v => {
            const r = v.getBoundingClientRect();
            return r.width > 100 && r.height > 100;
        });
        if (hasVisibleVideo) {
            result.type = 'video';
            result.url = mp4Entries[mp4Entries.length - 1].name;
            return result;
        }
    }

    // 3. Check for active visible image tag
    const imgs = Array.from(document.querySelectorAll('section img, div[role="dialog"] img, img'));
    for (const img of imgs) {
        const rect = img.getBoundingClientRect();
        if (rect.width > 200 && rect.height > 300) {
            let src = img.currentSrc || img.src;
            if (!src && img.srcset) {
                const parts = img.srcset.split(',');
                src = parts[parts.length - 1].trim().split(' ')[0];
            }
            if (src && !src.includes('profile_pic') && !src.includes('150x150')) {
                result.type = 'image';
                result.url = src;
                return result;
            }
        }
    }

    // 4. Fallback to largest image entry from performance log
    const imgEntries = entries.filter(e => e.name.includes('/v/t51.') && !e.name.includes('150x150'));
    if (imgEntries.length > 0) {
        result.type = 'image';
        result.url = imgEntries[imgEntries.length - 1].name;
        return result;
    }

    return result;
    """
    try:
        media_info = driver.execute_script(js_extract)
        if media_info and media_info.get("url"):
            return media_info
    except Exception as e:
        print(f"    [Warning] JS media extraction error: {e}")

    return None

def click_next_story(driver) -> bool:
    """Click the 'Next' button or send Arrow Right key to advance the story."""
    selectors = [
        'button[aria-label="Next"]',
        'div[role="button"] svg[aria-label="Next"]',
        'svg[aria-label="Next"]',
        'button._a9_u',
    ]
    for sel in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, sel)
            for el in elements:
                if el.is_displayed():
                    clickable = el
                    if el.tag_name == "svg":
                        clickable = el.find_element(By.XPATH, "..")
                    driver.execute_script("arguments[0].click();", clickable)
                    return True
        except Exception:
            continue

    # Fallback to Arrow Right key
    try:
        body = driver.find_element(By.TAG_NAME, "body")
        body.send_keys(Keys.ARROW_RIGHT)
        return True
    except Exception:
        pass

    # Fallback: click right side of the screen
    try:
        driver.execute_script("""
            const evt = new MouseEvent('click', {
                clientX: window.innerWidth * 0.75,
                clientY: window.innerHeight * 0.5,
                bubbles: true
            });
            document.elementFromPoint(window.innerWidth * 0.75, window.innerHeight * 0.5)?.dispatchEvent(evt);
        """)
        return True
    except Exception:
        pass

    return False

def selenuim_clone(username:str, tags:list, count:int = 12, must_have_profile_picture:bool = True, must_have_highlights:bool = False, download_highlights:bool = False, profile_screenshot:bool = False, proxy:str = "", override_duplicate=False, headless:bool = False):
    """Automates scraping and cloning Instagram follower profiles for a target account.

    Opens Chrome via undetected-chromedriver, navigates to the target user's followers list,
    scrolls to scrape follower usernames, and clones each discovered profile into an organized
    folder structure with full profile metadata (JSON), HD profile pictures, optional full-page
    screenshots, and story highlights.

    Args:
        username (str): The target Instagram username whose followers will be scraped.
        tags (list): A list or string of category tags used to group cloned accounts
            into subdirectories under `clone/<tagGroup>/`.
        count (int, optional): The target number of follower profiles to clone. If set to 0,
            it performs continuous scrolling (up to 1,000 scrolls). Defaults to 12.
        must_have_profile_picture (bool, optional): If True, skips accounts that do not have a
            custom profile picture or are listed in `clone/no-pic.txt`. Defaults to True.
        must_have_highlights (bool, optional): If True, skips accounts that have no story
            highlights. Defaults to False.
        download_highlights (bool, optional): If True, navigates through each story highlight of
            the cloned user, handles the 'View story' obstacle button, and downloads story images
            along with highlight metadata. Defaults to False.
        profile_screenshot (bool, optional): If True, captures and saves a full browser screenshot
            (`screenshot.png`) of the profile in a background thread. Defaults to False.
        proxy (str, optional): HTTP/HTTPS proxy URL string (e.g., 'http://127.0.0.1:7890')
            to route media download requests. Defaults to "".
        override_duplicate (bool, optional): If True, re-scrapes and overwrites profiles that
            already exist in the destination tag directory. Defaults to False.
        headless (bool, optional): If True, it willn't show the web driver scrolling. You should
            see actions in 10s for main page to load. It may not work in some cases. Defaults to False.

    Returns:
        None: Cloned data (metadata, avatars, screenshots, and highlights) is written directly
            to disk in the `clone/<tagGroup>/<username>/` directory.
    """
    
    if count <= 12: scrolls = 0
    elif count != 0: scrolls = int(count/12)
    else: scrolls = 1000
    
    tagGroup = get_tag_group(tags)
    os.makedirs("clone/"+ tagGroup, exist_ok=True)
    
    if must_have_profile_picture:
        file_path = pathlib.Path("clone/no-pic.txt")
        file_path.touch(exist_ok=True)
        with open("clone/no-pic.txt", "r") as f:
            noPics = f.read()
    
    scriptDirectory = pathlib.Path().absolute()
    directPath = str(scriptDirectory)+"\\"+"profiles/cloneProfile"
    
    options = uc.ChromeOptions()
    options.add_argument("--log-level=3")
    options.add_argument("--silent")

    if headless:
        options.add_argument("--headless=new")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-gpu")
        
    options.add_argument(f"--user-data-dir={directPath}")
    
    try:
        driver = uc.Chrome(driver_executable_path="chromedriver.exe", options=options)
    except FileNotFoundError:
        print("[x] chromedriver.exe is not found install the webdriver in this location with same name. install from https://developer.chrome.com/docs/chromedriver/downloads")
        exit()
    except:
        print("[x] chromedriver.exe version doesn't support your Chrome browser's version. install from https://developer.chrome.com/docs/chromedriver/downloads")
        exit()
    
    driver.maximize_window()
    driver.get(f"https://instagram.com/{username}")    
    
    if "/accounts/emailsignup/" in driver.page_source:
        print("[!] Please log in any account then press enter, this is one time setup")
        input("press ENTER after login to procced")
        driver.get(f"https://instagram.com/{username}")
    
    try:
        WebDriverWait(driver, 5).until( 
            EC.visibility_of_element_located((By.XPATH, "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[2]/div[2]/section/main/div/div/header/div/section[2]/div[1]/div[3]/div[2]/a"))
        )
        time.sleep(3)
        driver.find_element(By.XPATH, "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[2]/div[2]/section/main/div/div/header/div/section[2]/div[1]/div[3]/div[2]/a").click()
    except:
        WebDriverWait(driver, 5).until( 
            EC.visibility_of_element_located((By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[2]/div[2]/section/main/div/div/header/div/section[2]/div[1]/div[3]/div[2]/a"))
        )
        time.sleep(3)
        driver.find_element(By.XPATH, "/html/body/div[2]/div/div/div[2]/div/div/div[1]/div[2]/div[2]/section/main/div/div/header/div/section[2]/div[1]/div[3]/div[2]/a").click()
    
    time.sleep(5)
    if "We limit certain things you can see, like someone’s followers or following lists, to protect our community." in driver.page_source or "Followers list hidden" in driver.page_source:
        print(f"[!] @{username} followers lists are hidden")
        return
    try: scroll_box = WebDriverWait(driver, 3).until(EC.visibility_of_element_located((By.XPATH, "/html/body/div[4]/div[2]/div/div[1]/div/div[2]/div/div/div/div/div[2]/div/div/div[3]")))
    except: scroll_box = WebDriverWait(driver, 3).until(EC.visibility_of_element_located((By.XPATH, "/html/body/div[4]/div[2]/div/div[1]/div/div[2]/div/div/div/div/div/div/div[2]")))

    last_height = driver.execute_script("return arguments[0].scrollHeight;", scroll_box)

    for i in range(scrolls):
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scroll_box)
        time.sleep(2)
        new_height = driver.execute_script("return arguments[0].scrollHeight;", scroll_box)
        if new_height == last_height:
            time.sleep(1.5)
            new_height = driver.execute_script("return arguments[0].scrollHeight;", scroll_box)
            if new_height == last_height:
                break
                
        last_height = new_height
    
    element = WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.XPATH, "/html/body/div[4]/div[2]/div/div[1]/div/div[2]/div/div/div"))
    )
    outer_html = element.get_attribute("outerHTML")
    
    pattern = r'href="/([a-zA-Z0-9_.]+)/"'
    usernames = re.findall(pattern, outer_html)
    usernames = list(dict.fromkeys(usernames))
    
    printer = LivePrinter(
        header=f"================ {TOOL_NAME} {TOOL_VERSION} ================",
        footer="===================================================",
        total_steps=len(usernames),
        bar_length=20
    )
    
    for i, username in enumerate(usernames):
        try:
            printer.update(f"Scraping @{username} [{i+1}/{len(usernames)}] ...", step=i)
            
            if must_have_profile_picture:
                if username in noPics: continue
                with open("clone/no-pic.txt", "r") as f:
                    noPics = f.read()
            
            if username in os.listdir("clone/" + tagGroup): 
                printer.update(f"Data @{username} already saved", step=i)
                continue
            
            cloneProfilePath = "clone/" + tagGroup + "/" + username
            if override_duplicate:
                if username in os.listdir("clone/" + tagGroup):
                    continue
                
            os.makedirs(cloneProfilePath, exist_ok=True)

            driver.get(f"https://www.instagram.com/{username}/")
            if profile_screenshot: 
                def takeSC():
                    time.sleep(1.5)
                    driver.save_screenshot(cloneProfilePath + "/screenshot.png")
                th = threading.Thread(target=takeSC)
                th.daemon = True
                th.start()
            
            if "Sorry, this page isn't available." in driver.page_source:
                with open("clone/no-pic.txt", "a") as f:
                    f.write(f"{username}\n")
                continue
            try: 
                WebDriverWait(driver, 5).until( 
                    EC.visibility_of_element_located((By.XPATH, "/html/body/div[1]/div/div/div[2]/div/div/div[1]/div[2]/div[2]/section/main/div/div/header"))
                )
            except Exception as e:
                print(e)
                if "Sorry, this page isn't available." in  driver.page_source:
                    with open("clone/no-pic.txt", "a") as f:
                        f.write(f"{username}\n")
                continue
            
            html = driver.page_source
            profile = extract_instagram_profile(html)
            if must_have_highlights:
                if not profile["profile"]["highlights"]: continue
            
            try: 
                if proxy:
                    proxies = {
                        "http": proxy,
                        "https": proxy,
                    }
                    session = requests.Session()
                    session.proxies.update(proxies)
                    img = session.get(profile["profile"]["profile_picture_url"], timeout=20).content
                else: img = requests.get(profile["profile"]["profile_picture_url"], timeout=20).content
            except requests.exceptions.MissingSchema: 
                with open("clone/no-pic.txt", "a") as f:
                    f.write(f"{username}\n")
                continue
            
            with open(f"{cloneProfilePath}/profile.png", "wb") as f:
                f.write(img)

            profile["tags"] = tagGroup
            data = clean_invisible_chars(profile)
            with open(f"{cloneProfilePath}/profile.json", "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            if download_highlights and data["profile"]["highlights"]:
                for highlight in data["profile"]["highlights"]:
                    try:
                        highlightURL = highlight["link"]
                        cloneProfileHighlightPath = cloneProfilePath + "/highlights/" + highlightURL.split("/")[-2]
                        os.makedirs(cloneProfileHighlightPath, exist_ok=True)
                        with open(f"{cloneProfileHighlightPath}/highlight.json", "w", encoding="utf-8") as f:
                            json.dump(highlight, f, ensure_ascii=False, indent=4)
                        
                        driver.get(highlightURL)
                        time.sleep(1)
                        WebDriverWait(driver, 10).until(
                            EC.element_to_be_clickable(
                                (By.CSS_SELECTOR, '[class="x1i10hfl xdl72j9 x2lah0s x3ct3a4 xdj266r x14z9mp xat24cr x1lziwak x2lwn1j xeuugli xexx8yu x18d9i69 x1hl2dhg xggy1nq x1ja2u2z x1t137rt x1q0g3np x1lku1pv x1a2a7pz x6s0dn4 xjyslct x9f619 x1ypdohk x78zum5 x1f6kntn xwhw2v2 xl56j7k x17ydfre x1n2onr6 x2b8uid xlyipyv x87ps6o x14atkfc x5c86q x18br7mf x1i0vuye x6nl9eh x1a5l9x9 x7vuprf x1mg3h75 xn3w4p2 x106a9eq x1xnnf8n xc58f59 x1uwqpi5 x19hv4p6 xqi6rai x13fuv20 x18b5jzi x1q0q8m5 x1t7ytsu x178xt8z x1lun4ml xso031l xpilrb4 x9bdzbf"]')
                            )
                        ).click()
                        time.sleep(2)
                        
                        stories_in_highlight = driver.page_source.count("x1lix1fw xr9e8f9 x1e4oeot x1ui04y5 x6en5u8 x1iyjqo2 x36qwtl x6ikm8r x10wlt62 x1n2onr6")
                        
                        story_downloadded = 1
                        for i in range(stories_in_highlight):
                            try:
                                media_info = get_current_story_media(driver)
                                if media_info["type"] == "image":
                                    if proxy:
                                        proxies = {
                                            "http": proxy,
                                            "https": proxy,
                                        }
                                        session = requests.Session()
                                        session.proxies.update(proxies)
                                        img = session.get(media_info["url"], timeout=20).content
                                    else: img = requests.get(media_info["url"], timeout=20).content
                                    
                                    with open(f"{cloneProfileHighlightPath}/story_{story_downloadded}.png", "wb") as f:
                                        f.write(img)
                                    story_downloadded += 1
                                
                                time.sleep(1)
                                click_next_story(driver)
                            except: pass
                    except: pass
            printer.update(f"Data @{username} saved ✅", step=i)
        except:
            pass
    printer.update(f"Scraping completed ✅", step=i)

def parse_args():
    parser = argparse.ArgumentParser(
        description="Instagram Profile Cloner - Scrapes followers and clones profile data, pictures, and highlights.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    parser.add_argument(
        "username",
        nargs="?",
        default=None,
        help="Target Instagram username whose followers will be scraped"
    )
    parser.add_argument(
        "-u", "--user", "--username",
        dest="username_opt",
        default=None,
        help="Target Instagram username (alternative flag)"
    )
    parser.add_argument(
        "-t", "--tags",
        nargs="+",
        default=["default"],
        help="Category tags to organize cloned profiles under clone/<tagGroup>/"
    )
    parser.add_argument(
        "-n", "--count",
        type=int,
        default=12,
        help="Number of follower profiles to clone (set 0 for continuous scroll up to 1,000)"
    )
    parser.add_argument(
        "--must-have-profile-picture",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Only clone accounts that have a custom profile picture"
    )
    parser.add_argument(
        "--must-have-highlights",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Only clone accounts that have story highlights"
    )
    parser.add_argument(
        "--download-highlights",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Download all story highlights media for cloned accounts"
    )
    parser.add_argument(
        "--profile-screenshot",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Capture full-page screenshot (screenshot.png) for each profile"
    )
    parser.add_argument(
        "--proxy",
        type=str,
        default="",
        help="HTTP/HTTPS proxy string for media downloads (e.g. 'http://127.0.0.1:7890')"
    )
    parser.add_argument(
        "--override-duplicate",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Re-scrape and overwrite profiles that already exist in destination tag directory"
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Hides the pop-up Chrome driver"
    )
    return parser

if __name__ == "__main__":
    parser = parse_args()
    args = parser.parse_args()

    target_user = args.username or args.username_opt
    if not target_user:
        target_user = input("Enter target Instagram username: ").strip()
        if not target_user:
            parser.error("A target username is required.")

    group_tags = args.username or args.username_opt
    if not group_tags:
        group_tags = input("Enter group tags seprated by comma eg: female,usa,shopping: ").strip()
        group_tags = [group.replace(" ", "") for group in group_tags.split(",")]
        if not group_tags:
            parser.error("A target group tags is required.")
            
    os.system("cls" if os.name == "nt" else "clear")
    print(TOOL_BANNER)
    
    selenuim_clone(
        username=target_user,
        tags=args.tags,
        count=args.count,
        must_have_profile_picture=args.must_have_profile_picture,
        must_have_highlights=args.must_have_highlights,
        download_highlights=args.download_highlights,
        profile_screenshot=args.profile_screenshot,
        proxy=args.proxy,
        override_duplicate=args.override_duplicate,
        headless=args.headless,
    )
