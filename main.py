import asyncio
from playwright.async_api import async_playwright
import json
from datetime import datetime
import random
import os
import logging
import gspread
from google.oauth2.service_account import Credentials
import time

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

CONFIG = {
    "delays": {
        "general_action": {"min": 3, "max": 7},
        "typing_character": {"min": 200, "max": 500},
        "typing_pause": {"min": 1, "max": 2.5},
        "typing_random": {"min": 0.2, "max": 0.8},
        "typing_final": {"min": 2, "max": 4},
        "mouse_movement": {"min": 0.5, "max": 1.2},
        "scroll_delay": {"min": 3, "max": 6},
        "login_initial": {"min": 8, "max": 12},
        "login_page_load": {"min": 2, "max": 4},
        "login_reload": {"min": 2, "max": 6},
        "login_submit": {"min": 8, "max": 25},
        "login_buttons": {"min": 2, "max": 5},
        "login_retry": {"min": 8, "max": 15},
        "session_validation": {"min": 8, "max": 12},
        "profile_navigation": {"min": 10, "max": 15},
        "reels_tab": {"min": 2, "max": 5},
        "reels_initial_load": {"min": 8, "max": 12},
        "reels_retry": {"min": 8, "max": 15},
        "post_navigation": {"min": 3, "max": 6},
        "post_date_check": {"min": 3, "max": 6},
        "post_carousel_next": {"min": 1, "max": 3},
        "tag_button_search": {"min": 3, "max": 6},
        "tag_button_click": {"min": 3, "max": 5},
        "tag_dialog_wait": {"min": 4, "max": 8},
        "tag_dialog_close": {"min": 2, "max": 5},
        "profile_return": {"min": 5, "max": 10},
        "profile_return_scroll": {"min": 4, "max": 8},
        "between_posts": {"min": 8, "max": 15},
        "scroll_load": {"min": 5, "max": 10},
        "between_profiles": {"min": 10, "max": 30},
        "general_wait": {"min": 3, "max": 6},
        "reels_return": {"min": 2, "max": 5},
        "posts_to_reels": {"min": 5, "max": 10},
        "highlights_check": {"min": 4, "max": 10},
        "highlights_open": {"min": 4, "max": 9},
        "video_pause": {"min": 3, "max": 6},
        "tag_search": {"min": 3, "max": 6},
        "next_video": {"min": 2, "max": 6},
        "highlights_to_posts": {"min": 3, "max": 5},
        "scroll_wait": {"min": 3, "max": 8},
        "rate_limit_pause": {"min": 30, "max": 60},
        "long_pause": {"min": 60, "max": 300},
    },
    "retry": {
        "login_attempts": 3,
        "reels_load_attempts": 5,
        "max_scrolls": 350,
        "video_pause_attempts": 5,
        "max_empty_scrolls": 8,
        "max_rate_limit_retries": 5,
    },
    "target_year": 2021,
    "rate_limiting": {
        "requests_per_hour": 200,
        "pause_after_requests": 80,
        "long_pause_after_requests": 150,
    }
}

GOOGLE_SHEETS_CONFIG = {
    "credentials_file": "credentials.json",
    "spreadsheet_id": "1WCmFLdioC-mm_QtWdA3qNo_sEdEHZ3HTyCdqCaz_2MA",
    "worksheet_name": "Full Scrape"
}

class RateLimiter:
    def __init__(self):
        self.request_count = 0
        self.start_time = time.time()
        
    async def check_and_pause(self):
        self.request_count += 1
        current_time = time.time()
        elapsed_hours = (current_time - self.start_time) / 3600
        
        if elapsed_hours >= 1:
            self.request_count = 0
            self.start_time = current_time
            
        if self.request_count >= CONFIG["rate_limiting"]["requests_per_hour"]:
            logger.info("Rate limit reached, pausing for 1 hour...")
            await asyncio.sleep(120)
            self.request_count = 0
            self.start_time = time.time()
            
        elif self.request_count % CONFIG["rate_limiting"]["long_pause_after_requests"] == 0:
            logger.info("Long pause for safety...")
            await human_delay("long_pause")
            
        elif self.request_count % CONFIG["rate_limiting"]["pause_after_requests"] == 0:
            logger.info("Rate limiting pause...")
            await human_delay("rate_limit_pause")

rate_limiter = RateLimiter()

class GoogleSheetsManager:
    def __init__(self):
        self.gc = None
        self.worksheet = None
        self.headers = ["Account", "Tag", "Source_Type", "Post_URL", "Post_Date", "Scraping_Date"]
        
    def authenticate(self):
        try:
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            credentials = Credentials.from_service_account_file(
                GOOGLE_SHEETS_CONFIG["credentials_file"], 
                scopes=scope
            )
            self.gc = gspread.authorize(credentials)
            logger.info("Google Sheets authentication successful")
            return True
        except Exception as e:
            logger.error(f"Google Sheets authentication failed: {e}")
            return False
    
    def setup_worksheet(self):
        try:
            spreadsheet = self.gc.open_by_key(GOOGLE_SHEETS_CONFIG["spreadsheet_id"])
            
            try:
                self.worksheet = spreadsheet.worksheet(GOOGLE_SHEETS_CONFIG["worksheet_name"])
                logger.info(f"Worksheet '{GOOGLE_SHEETS_CONFIG['worksheet_name']}' found")
            except gspread.WorksheetNotFound:
                self.worksheet = spreadsheet.add_worksheet(
                    title=GOOGLE_SHEETS_CONFIG["worksheet_name"], 
                    rows=1000, 
                    cols=len(self.headers)
                )
                logger.info(f"Worksheet '{GOOGLE_SHEETS_CONFIG['worksheet_name']}' created")
            
            if self.worksheet.row_count == 0 or not self.worksheet.row_values(1):
                self.worksheet.append_row(self.headers)
                logger.info("Headers added to worksheet")
            
            return True
        except Exception as e:
            logger.error(f"Error setting up worksheet: {e}")
            return False
    
    def save_tag(self, tag_data):
        try:
            row_data = [
                tag_data.get("Account", ""),
                tag_data.get("Tag", ""),
                tag_data.get("Source_Type", ""),
                tag_data.get("Post_URL", ""),
                tag_data.get("Post_Date", ""),
                tag_data.get("Scraping_Date", "")
            ]
            self.worksheet.append_row(row_data)
            logger.info(f"Tag saved to Google Sheets: {tag_data['Tag']}")
        except Exception as e:
            logger.error(f"Error saving tag to Google Sheets: {e}")

sheets_manager = GoogleSheetsManager()

async def human_delay(config_key):
    delay_config = CONFIG["delays"].get(config_key, {"min": 3, "max": 6})
    delay = random.uniform(delay_config["min"], delay_config["max"])
    logger.info(f"Waiting {delay:.2f} seconds...")
    await asyncio.sleep(delay)

async def type_like_human(page, selector, text):
    input_field = await page.query_selector(selector)
    if not input_field:
        raise Exception(f"Input field {selector} not found.")
    
    await input_field.click()
    await human_delay("typing_pause")
    
    typing_config = CONFIG["delays"]["typing_character"]
    for char in text:
        await input_field.type(char, delay=random.uniform(typing_config["min"], typing_config["max"]))
        if random.random() < 0.15:
            await human_delay("typing_random")
    
    await human_delay("typing_final")

async def random_mouse_movement(page):
    try:
        viewport = await page.viewport_size()
        if viewport:
            x = random.randint(100, viewport['width'] - 100)
            y = random.randint(100, viewport['height'] - 100)
            await page.mouse.move(x, y)
            await human_delay("mouse_movement")
    except:
        pass

async def human_scroll(page, direction="down"):
    try:
        scroll_amount = random.randint(300, 800)
        if direction == "down":
            await page.evaluate(f"window.scrollBy(0, {scroll_amount})")
        else:
            await page.evaluate(f"window.scrollBy(0, -{scroll_amount})")
        
        await human_delay("scroll_delay")
        await random_mouse_movement(page)
        await rate_limiter.check_and_pause()
    except:
        pass

async def check_for_errors(page):
    try:
        error_messages = [
            "Something went wrong",
            "Try again later",
            "We restrict certain activity",
            "Please wait a few minutes",
            "Action blocked",
            "Temporarily blocked"
        ]
        
        page_text = await page.inner_text("body")
        for error in error_messages:
            if error.lower() in page_text.lower():
                logger.warning(f"Detected error: {error}")
                return True
        return False
    except:
        return False

async def handle_rate_limiting(page):
    if await check_for_errors(page):
        logger.warning("Rate limiting detected, taking long break...")
        await human_delay("long_pause")
        
        try:
            await page.reload(timeout=90000)
            await human_delay("session_validation")
        except:
            pass
        
        return True
    return False

async def login_instagram(page, username, password):
    logger.info("Navigating to Instagram...")
    
    for attempt in range(3):
        try:
            await page.goto("https://www.instagram.com/", timeout=120000)
            await human_delay("login_initial")
            break
        except:
            logger.warning(f"Navigation attempt {attempt + 1} failed")
            if attempt == 2:
                return False
            await asyncio.sleep(10)
    
    await random_mouse_movement(page)

    profile_selectors = [
        'svg[aria-label="Your profile"]',
        'a[href="/accounts/activity/"]',
        'div:has-text("Home")',
        '[data-testid="user-avatar"]',
        'a[href*="/direct/inbox/"]'
    ]
    
    for selector in profile_selectors:
        try:
            await page.wait_for_selector(selector, timeout=15000)
            logger.info("Already logged in.")
            return True
        except:
            continue

    if await handle_rate_limiting(page):
        return False

    for attempt in range(CONFIG["retry"]["login_attempts"]):
        try:
            await page.wait_for_selector('input[name="username"]', timeout=45000)
            logger.info("Login page loaded.")
            await human_delay("login_page_load")
            break
        except:
            logger.info(f"Login attempt {attempt + 1} failed, retrying...")
            await page.reload(timeout=120000)
            await human_delay("login_reload")
            if attempt == CONFIG["retry"]["login_attempts"] - 1:
                return False

    await random_mouse_movement(page)
    await type_like_human(page, 'input[name="username"]', username)
    await random_mouse_movement(page)
    await type_like_human(page, 'input[name="password"]', password)

    try:
        await random_mouse_movement(page)
        await page.locator('button[type="submit"]').click()
        await human_delay("login_submit")
    except Exception as e:
        logger.error(f"Login failed: {e}")
        return False

    try:
        error_message = await page.query_selector('p[id="slfErrorAlert"]')
        if error_message:
            error_text = await error_message.inner_text()
            logger.error(f"Login error: {error_text}")
            return False
    except:
        pass

    button_selectors = [
        'button:has-text("Save Info")',
        'button:has-text("Save info")',
        'button:has-text("Not Now")',
        'button:has-text("Not now")',
        'button:has-text("Maybe Later")'
    ]
    
    for button_selector in button_selectors:
        try:
            await page.locator(button_selector).click(timeout=15000)
            await human_delay("login_buttons")
            break
        except:
            continue

    try:
        if await page.query_selector('input[name="verificationCode"]') or await page.query_selector('form[role="presentation"]'):
            logger.warning("2FA or captcha detected. Manual intervention required.")
            return False
    except:
        pass

    for attempt in range(CONFIG["retry"]["login_attempts"]):
        for selector in profile_selectors:
            try:
                await page.wait_for_selector(selector, timeout=30000)
                logger.info("Login successful.")
                return True
            except:
                continue
        await human_delay("login_retry")
    
    return False

async def validate_session(page):
    logger.info("Validating session...")
    try:
        await page.goto("https://www.instagram.com/", timeout=120000)
        await human_delay("session_validation")
        
        if await handle_rate_limiting(page):
            return False
        
        profile_selectors = [
            'svg[aria-label="Your profile"]',
            'a[href="/accounts/activity/"]',
            'div:has-text("Home")',
            '[data-testid="user-avatar"]',
            'a[href*="/direct/inbox/"]'
        ]
        
        for selector in profile_selectors:
            try:
                await page.wait_for_selector(selector, timeout=20000)
                logger.info("Session valid.")
                return True
            except:
                continue
                
        return False
    except:
        return False

async def save_session(context, session_file):
    try:
        storage_state = await context.storage_state()
        with open(session_file, 'w') as f:
            json.dump(storage_state, f, indent=2)
        logger.info(f"Session saved to {session_file}")
    except Exception as e:
        logger.error(f"Error saving session: {e}")

async def create_context_with_session(browser, session_file):
    user_agents = [
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36',
        'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    ]
    
    context_options = {
        'user_agent': random.choice(user_agents),
        'locale': random.choice(['en-US', 'en-GB']),
        'timezone_id': random.choice(['America/New_York', 'Europe/London', 'America/Los_Angeles']),
        'viewport': {'width': random.randint(1366, 1920), 'height': random.randint(768, 1080)},
        'java_script_enabled': True,
        'extra_http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br, zstd',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'sec-ch-ua': '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }
    }
    
    if os.path.exists(session_file):
        try:
            context_options['storage_state'] = session_file
            return await browser.new_context(**context_options), True
        except:
            logger.warning("Failed to load session file, creating new session")
    
    return await browser.new_context(**context_options), False

async def is_pinned_post(page, post_element):
    try:
        pinned_icon = await post_element.query_selector('svg[aria-label="Pinned post icon"]')
        return pinned_icon is not None
    except:
        return False

async def get_post_date(page, post_url):
    try:
        await page.goto(post_url, timeout=90000)
        await human_delay("post_date_check")
        
        if await handle_rate_limiting(page):
            return None
        
        date_element = await page.query_selector('time[datetime]')
        if date_element:
            datetime_str = await date_element.get_attribute('datetime')
            return datetime.strptime(datetime_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        return None
    except:
        return None

async def scrape_tags_from_post(page, post_url, username):
    tags_data = []
    unique_tags = set()
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        for retry in range(3):
            try:
                await page.goto(post_url, timeout=90000)
                await human_delay("post_navigation")
                
                if await handle_rate_limiting(page):
                    if retry < 2:
                        continue
                    return tags_data, None
                break
            except:
                if retry == 2:
                    return tags_data, None
                await asyncio.sleep(10)
        
        post_date = await get_post_date(page, post_url)

        while True:
            await human_delay("general_wait")
            tag_elements = await page.query_selector_all('div._aa1y a span._aa1p')
            
            for tag_element in tag_elements:
                tag_text = await tag_element.inner_text()
                if tag_text:
                    clean_tag = tag_text.strip()
                    if clean_tag and clean_tag not in unique_tags:
                        unique_tags.add(clean_tag)
                        tag_data = {
                            "Account": username,
                            "Tag": clean_tag,
                            "Source_Type": "post",
                            "Post_URL": post_url,
                            "Post_Date": post_date.strftime("%Y-%m-%d %H:%M:%S") if post_date else "Unknown",
                            "Scraping_Date": current_time
                        }
                        tags_data.append(tag_data)
                        sheets_manager.save_tag(tag_data)

            next_button = await page.query_selector('button[aria-label="Next"]')
            if next_button:
                await next_button.click()
                await human_delay("post_carousel_next")
            else:
                break

    except Exception as e:
        logger.error(f"Error scraping post {post_url}: {e}")

    await rate_limiter.check_and_pause()
    return tags_data, post_date

async def scrape_tags_from_reel(page, reel_url, username):
    tags_data = []
    unique_tags = set()
    post_date = None
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        for retry in range(3):
            try:
                await page.goto(reel_url, timeout=90000)
                await human_delay("post_navigation")
                
                if await handle_rate_limiting(page):
                    if retry < 2:
                        continue
                    return tags_data, None
                break
            except:
                if retry == 2:
                    return tags_data, None
                await asyncio.sleep(10)
        
        post_date = await get_post_date(page, reel_url)

        tag_button_selectors = [
            'button svg[aria-label="Tags"]',
            'button:has(svg[aria-label="Tags"])',
            'button._acan._acao._acas._aj1-._ap30'
        ]

        tag_button = None
        for selector in tag_button_selectors:
            try:
                await human_delay("tag_button_search")
                tag_button = await page.query_selector(selector)
                if tag_button:
                    break
            except:
                continue

        if tag_button:
            await tag_button.click()
            await human_delay("tag_button_click")
            
            try:
                await page.wait_for_selector('div[role="dialog"]', timeout=8000)
                tagged_user_links = await page.query_selector_all('div[role="dialog"] a[href^="/"][role="link"]')
                
                for link in tagged_user_links:
                    try:
                        href = await link.get_attribute('href')
                        if href and href.startswith('/') and href.endswith('/') and len(href) > 2:
                            username_from_href = href.strip('/').split('/')[0]
                            
                            if (username_from_href and 
                                len(username_from_href) > 1 and 
                                username_from_href.replace('_', '').replace('.', '').isalnum() and
                                not any(skip in username_from_href for skip in ['accounts', 'explore', 'reels', 'direct', 'stories'])):
                                
                                if username_from_href not in unique_tags:
                                    unique_tags.add(username_from_href)
                                    tag_data = {
                                        "Account": username,
                                        "Tag": username_from_href,
                                        "Source_Type": "reel",
                                        "Post_URL": reel_url,
                                        "Post_Date": post_date.strftime("%Y-%m-%d %H:%M:%S") if post_date else "Unknown",
                                        "Scraping_Date": current_time
                                    }
                                    tags_data.append(tag_data)
                                    sheets_manager.save_tag(tag_data)
                    except:
                        continue
                        
                close_button = await page.query_selector('div[role="dialog"] button[type="button"] svg[aria-label="Close"]')
                if close_button:
                    await close_button.click()
                    await human_delay("tag_dialog_close")
                    
            except:
                logger.info("Tags dialog not found")

    except Exception as e:
        logger.error(f"Error scraping reel {reel_url}: {e}")

    await rate_limiter.check_and_pause()
    return tags_data, post_date

async def get_visible_content(page, content_type="posts"):
    urls_with_elements = []
    try:
        await human_delay("general_wait")
        if content_type == "posts":
            elements = await page.query_selector_all('div._ac7v a[href*="/p/"]')
            url_pattern = "/p/"
        else:
            elements = await page.query_selector_all('div._ac7v a[href*="/reel/"]')
            url_pattern = "/reel/"
            
        for element in elements:
            href = await element.get_attribute('href')
            if href and url_pattern in href:
                if not href.startswith('https://'):
                    href = f"https://www.instagram.com{href}"
                urls_with_elements.append((href, element))
    except:
        pass
    return urls_with_elements

async def scroll_to_load_more(page):
    try:
        before_count = len(await get_visible_content(page, "posts")) + len(await get_visible_content(page, "reels"))
        
        await human_scroll(page, "down")
        
        await human_delay("scroll_wait")
        
        after_count = len(await get_visible_content(page, "posts")) + len(await get_visible_content(page, "reels"))
        
        logger.info(f"Scroll: {before_count} -> {after_count} content items")
        return after_count > before_count
    except Exception as e:
        logger.error(f"Error in scroll_to_load_more: {e}")
        return False

async def save_scroll_position(page):
    return await page.evaluate("window.pageYOffset")

async def restore_scroll_position(page, position):
    await page.evaluate(f"window.scrollTo(0, {position})")
    await human_delay("profile_return_scroll")

async def process_content(page, username, profile_url, content_type="posts", scraper_func=None):
    all_tags_data = []
    scraped_urls = set()
    should_continue_scraping = True
    scroll_count = 0
    empty_scroll_count = 0
    current_scroll_position = 0
    target_year_reached = False
    rate_limit_retries = 0

    logger.info(f"Starting {content_type} processing for {username}")

    while (should_continue_scraping and 
           scroll_count < CONFIG["retry"]["max_scrolls"] and 
           empty_scroll_count < CONFIG["retry"]["max_empty_scrolls"] and
           rate_limit_retries < CONFIG["retry"]["max_rate_limit_retries"]):
        
        if await handle_rate_limiting(page):
            rate_limit_retries += 1
            continue
        
        current_urls_with_elements = await get_visible_content(page, content_type)
        
        if not current_urls_with_elements:
            logger.info(f"No {content_type} found on current view")
            if await scroll_to_load_more(page):
                scroll_count += 1
                empty_scroll_count = 0
                await human_delay("scroll_load")
                continue
            else:
                empty_scroll_count += 1
                logger.info(f"Empty scroll attempt {empty_scroll_count}/{CONFIG['retry']['max_empty_scrolls']}")
                if empty_scroll_count >= CONFIG["retry"]["max_empty_scrolls"]:
                    logger.info("Maximum empty scrolls reached, stopping")
                    break
                await human_delay("scroll_load")
                continue

        new_urls_with_elements = [(url, element) for url, element in current_urls_with_elements if url not in scraped_urls]
        
        if not new_urls_with_elements:
            logger.info(f"No new {content_type} found, scrolling for more")
            if await scroll_to_load_more(page):
                scroll_count += 1
                empty_scroll_count = 0
                current_scroll_position = await save_scroll_position(page)
                await human_delay("scroll_load")
                continue
            else:
                empty_scroll_count += 1
                logger.info(f"No new content loaded after scroll {empty_scroll_count}/{CONFIG['retry']['max_empty_scrolls']}")
                if empty_scroll_count >= CONFIG["retry"]["max_empty_scrolls"]:
                    logger.info("No more content to load")
                    break
                await human_delay("scroll_load")
                continue

        for i, (url, element) in enumerate(new_urls_with_elements):
            if target_year_reached:
                logger.info(f"Target year {CONFIG['target_year']} reached, stopping content processing")
                should_continue_scraping = False
                break
                
            is_pinned = await is_pinned_post(page, element)
            
            if is_pinned and content_type == "posts":
                logger.info(f"Skipping pinned post: {url}")
                scraped_urls.add(url)
                continue
                
            logger.info(f"Processing {content_type[:-1]} {len(scraped_urls)+1}: {url}")
            current_scroll_position = await save_scroll_position(page)
            
            try:
                tags_data, post_date = await scraper_func(page, url, username)
                all_tags_data.extend(tags_data)
                scraped_urls.add(url)

                if post_date and post_date.year < CONFIG["target_year"]:
                    logger.info(f"Found {content_type[:-1]} from {post_date.year} (older than {CONFIG['target_year']}). Target year reached!")
                    target_year_reached = True
                    should_continue_scraping = False
                    
                    try:
                        if content_type == "reels":
                            await page.goto(f"https://www.instagram.com/{username}/reels/", timeout=90000)
                            await human_delay("reels_return")
                        else:
                            await page.goto(profile_url, timeout=90000)
                            await human_delay("profile_return")
                    except Exception as e:
                        logger.error(f"Error returning to profile after target year reached: {e}")
                    break
                else:
                    logger.info(f"Post from {post_date.year if post_date else 'unknown year'}, continuing...")

            except Exception as e:
                logger.error(f"Error processing {content_type[:-1]} {url}: {e}")
                scraped_urls.add(url)

            try:
                if content_type == "reels":
                    await page.goto(f"https://www.instagram.com/{username}/reels/", timeout=90000)
                    await human_delay("reels_return")
                else:
                    await page.goto(profile_url, timeout=90000)
                    await human_delay("profile_return")
                
                await restore_scroll_position(page, current_scroll_position)
                
            except Exception as e:
                logger.error(f"Error returning to {content_type}: {e}")

            await human_delay("between_posts")

        if should_continue_scraping and not target_year_reached:
            logger.info(f"Processed {len(new_urls_with_elements)} new {content_type}, scrolling for more...")
            if await scroll_to_load_more(page):
                scroll_count += 1
                empty_scroll_count = 0
                await human_delay("scroll_load")
            else:
                empty_scroll_count += 1
                logger.info(f"Failed to load more content {empty_scroll_count}/{CONFIG['retry']['max_empty_scrolls']}")
                if empty_scroll_count >= CONFIG["retry"]["max_empty_scrolls"]:
                    logger.info("Maximum empty scrolls reached")
                    break
                await human_delay("scroll_load")

    logger.info(f"{content_type.capitalize()} scraping completed for {username}:")
    logger.info(f"  - Total processed: {len(scraped_urls)}")
    logger.info(f"  - Total tags found: {len(all_tags_data)}")
    logger.info(f"  - Target year reached: {target_year_reached}")
    logger.info(f"  - Scroll attempts: {scroll_count}")
    
    return all_tags_data

async def check_highlights(page):
    try:
        logger.info("Checking for highlights...")
        await human_delay("highlights_check")
        
        highlights_selectors = [
            'li._acaz div.html-div',
            'ul._acay li._acaz', 
            'section.xc3tme8 ul._acay li._acaz',
            '[role="menu"] ul li'
        ]
        
        for selector in highlights_selectors:
            try:
                highlights = await page.query_selector_all(selector)
                if highlights and len(highlights) > 0:
                    first_highlight = highlights[0]
                    await first_highlight.click()
                    await human_delay("highlights_open")
                    logger.info("First highlight opened successfully!")
                    return True
            except:
                continue
        
        logger.info("Could not open first highlight.")
        return False
        
    except Exception as e:
        logger.error(f"Error opening highlight: {e}")
        return False

async def pause_video(page):
    try:
        logger.info("Pausing video...")
        
        for attempt in range(CONFIG["retry"]["video_pause_attempts"]):
            logger.info(f"Pause attempt {attempt + 1}/{CONFIG['retry']['video_pause_attempts']}")
            
            pause_selectors = [
                'svg[aria-label="Pause"]',
                'svg[aria-label="pause"]',
                'button[aria-label="Pause"]',
                'div[role="button"] svg[aria-label="Pause"]',
                'div[role="button"] svg[aria-label="pause"]'
            ]
            
            pause_found = False
            
            for selector in pause_selectors:
                try:
                    pause_buttons = await page.query_selector_all(selector)
                    for pause_button in pause_buttons:
                        is_visible = await pause_button.is_visible()
                        if is_visible:
                            await pause_button.click()
                            await human_delay("video_pause")
                            logger.info("Video paused successfully!")
                            pause_found = True
                            break
                    if pause_found:
                        break
                except:
                    continue
            
            if pause_found:
                break
            
            try:
                play_pause_area = await page.query_selector('video, div[role="button"]')
                if play_pause_area:
                    await play_pause_area.click()
                    await human_delay("video_pause")
                    logger.info("Video paused via play/pause area")
                    break
            except:
                pass
            
            logger.info("Video still loading, waiting...")
            await human_delay("highlights_check")
        
        return True
        
    except Exception as e:
        logger.error(f"Error pausing video: {e}")
        return False

async def get_highlight_post_date(page):
    try:
        date_selectors = [
            'time[datetime]',
            'time.x197sbye',
            'span time[datetime]',
            'div.x13fj5qh time',
            'time.x197sbye.xuxw1ft'
        ]
        
        for selector in date_selectors:
            try:
                time_element = await page.query_selector(selector)
                if time_element:
                    datetime_attr = await time_element.get_attribute('datetime')
                    if datetime_attr:
                        try:
                            from datetime import datetime as dt
                            parsed_date = dt.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                            formatted_date = parsed_date.strftime('%Y-%m-%d')
                            logger.info(f"Post date found: {formatted_date}")
                            return formatted_date
                        except:
                            pass
                    
                    title_attr = await time_element.get_attribute('title')
                    if title_attr:
                        logger.info(f"Post date (title): {title_attr}")
                        return title_attr
                    
                    inner_text = await time_element.inner_text()
                    if inner_text:
                        logger.info(f"Post date (text): {inner_text}")
                        return inner_text
            except:
                continue
        
        logger.info("Post date not found")
        return "Unknown"
        
    except Exception as e:
        logger.error(f"Error getting date: {e}")
        return "Unknown"

async def get_current_highlight_url(page):
    try:
        current_url = page.url
        if '/stories/highlights/' in current_url:
            return current_url
        return current_url
    except:
        return "Unknown"

async def is_clickable_tag_button(button):
    try:
        tabindex = await button.get_attribute('tabindex')
        style = await button.get_attribute('style')
        bbox = await button.bounding_box()
        
        if not bbox or not style:
            return False
        
        if tabindex == "-1":
            return False
        
        if bbox['width'] < 10 or bbox['height'] < 10:
            return False
        
        if ('width: 0%' in style or 'height: 0%' in style or 
            'width:0%' in style or 'height:0%' in style):
            return False
        
        width_percent = None
        height_percent = None
        
        if 'width:' in style:
            for part in style.split(';'):
                if 'width:' in part and '%' in part:
                    try:
                        width_val = part.split('width:')[1].split('%')[0].strip()
                        width_percent = float(width_val)
                    except:
                        pass
                if 'height:' in part and '%' in part:
                    try:
                        height_val = part.split('height:')[1].split('%')[0].strip()
                        height_percent = float(height_val)
                    except:
                        pass
        
        if width_percent is not None and width_percent < 1:
            return False
        if height_percent is not None and height_percent < 1:
            return False
        
        if width_percent is not None and width_percent > 50:
            return False
        if height_percent is not None and height_percent > 50:
            return False
        
        return True
        
    except Exception as e:
        return False

async def find_and_process_highlight_tags(page, target_username, unique_tags_global):
    try:
        logger.info("Searching for tag buttons...")
        await human_delay("tag_search")
        
        tags_found = []
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        post_date = await get_highlight_post_date(page)
        current_post_url = await get_current_highlight_url(page)
        
        tag_button_selectors = [
            'div.x47corl div.x1i10hfl[role="button"]',
            'div.x47corl div[role="button"]',
            'div[role="button"][style*="height:"][style*="width:"][style*="left:"][style*="top:"]',
            'div.x1i10hfl[role="button"][tabindex]',
            'div[class*="x1i10hfl"][role="button"]'
        ]
        
        tag_buttons = []
        
        for selector in tag_button_selectors:
            try:
                logger.info(f"Trying selector: {selector}")
                buttons = await page.query_selector_all(selector)
                logger.info(f"Found {len(buttons)} buttons")
                
                if buttons and len(buttons) > 0:
                    for button in buttons:
                        if await is_clickable_tag_button(button):
                            is_duplicate = False
                            button_bbox = await button.bounding_box()
                            
                            for existing in tag_buttons:
                                existing_bbox = await existing.bounding_box()
                                if existing_bbox and button_bbox:
                                    if (abs(button_bbox['x'] - existing_bbox['x']) < 10 and 
                                        abs(button_bbox['y'] - existing_bbox['y']) < 10):
                                        is_duplicate = True
                                        break
                            
                            if not is_duplicate:
                                tag_buttons.append(button)
                                logger.info(f"Tag button added: {button_bbox['width']:.1f}x{button_bbox['height']:.1f}")
                    break
            except Exception as e:
                logger.error(f"Selector error: {e}")
                continue
        
        logger.info(f"Total {len(tag_buttons)} real tag buttons found!")
        
        if len(tag_buttons) == 0:
            logger.info("No tag buttons found")
            return []
        
        for i, tag_button in enumerate(tag_buttons):
            try:
                logger.info(f"Clicking tag button {i+1}/{len(tag_buttons)}...")
                
                style = await tag_button.get_attribute('style')
                tabindex = await tag_button.get_attribute('tabindex')
                bbox = await tag_button.bounding_box()
                logger.info(f"Button info: tabindex={tabindex}, size={bbox['width']:.1f}x{bbox['height']:.1f}")
                
                await tag_button.scroll_into_view_if_needed()
                await human_delay("general_wait")
                
                try:
                    await tag_button.click(timeout=8000)
                    logger.info(f"Button {i+1} clicked!")
                except Exception as click_error:
                    logger.error(f"Button {i+1} click error: {click_error}")
                    continue
                
                await human_delay("tag_dialog_wait")
                
                dialog_selectors = [
                    'div[role="dialog"]',
                    'div.xu96u03',
                    'div.x1uvtmcs',
                    'div[class*="xu96u03"]',
                    'div[class*="x1uvtmcs"]'
                ]
                
                dialog_found = False
                dialog_element = None
                
                for selector in dialog_selectors:
                    try:
                        dialog_element = await page.wait_for_selector(selector, timeout=5000)
                        if dialog_element:
                            is_visible = await dialog_element.is_visible()
                            if is_visible:
                                logger.info(f"Tag dialog opened: {selector}")
                                dialog_found = True
                                break
                    except:
                        continue
                
                if not dialog_found:
                    logger.info("Tag dialog not opened - no tag here")
                    continue
                
                main_tag_selectors = [
                    'div[role="dialog"] div.x1i5p2am a._a6hd[href^="/"]',
                    'div.x1i5p2am a._a6hd[href^="/"]',
                    'a._a6hd[href^="/"]',
                    'div[role="dialog"] div:first-child a[href^="/"]'
                ]
                
                main_tag_link = None
                
                for selector in main_tag_selectors:
                    try:
                        links = await page.query_selector_all(selector)
                        if links and len(links) > 0:
                            first_link = links[0]
                            href = await first_link.get_attribute('href')
                            text = await first_link.inner_text()
                            
                            logger.info(f"Main tag link found: {href} - {text}")
                            
                            if (href and href.startswith('/') and href.endswith('/') and 
                                len(href) > 2 and not any(invalid in href for invalid in 
                                ['followers', 'following', 'posts', 'reels', 'tagged', 'p/', 'reel/', 
                                 'legal/', 'explore/', 'web/', 'accounts/', 'direct/', 'stories/'])):
                                
                                main_tag_link = {
                                    'href': href,
                                    'text': text
                                }
                                logger.info(f"Real tag link validated!")
                                break
                            else:
                                logger.info(f"Link validation failed: {href}")
                    except:
                        continue
                    
                    if main_tag_link:
                        break
                
                if not main_tag_link:
                    logger.info("Real tag link not found")
                    await page.keyboard.press('Escape')
                    await human_delay("tag_dialog_close")
                    continue
                
                try:
                    href = main_tag_link['href']
                    text = main_tag_link['text']
                    username_from_href = href.strip('/').split('/')[0]
                    
                    if (username_from_href and 
                        len(username_from_href) > 1 and 
                        username_from_href.replace('_', '').replace('.', '').isalnum() and
                        not username_from_href.startswith('l.instagram.com') and
                        'visit' not in text.lower() and
                        'link' not in text.lower()):
                        
                        tag_key = f"{target_username}_{username_from_href}"
                        if tag_key not in unique_tags_global:
                            unique_tags_global.add(tag_key)
                            tag_data = {
                                "Account": target_username,
                                "Tag": username_from_href,
                                "Source_Type": "highlight",
                                "Post_URL": current_post_url,
                                "Post_Date": post_date,
                                "Scraping_Date": current_time
                            }
                            tags_found.append(tag_data)
                            
                            sheets_manager.save_tag(tag_data)
                            
                            logger.info(f"TAG SAVED: {username_from_href} ({text})")
                        else:
                            logger.info(f"Tag already exists: {username_from_href}")
                    else:
                        logger.info(f"Username validation failed: {username_from_href}")
                except Exception as e:
                    logger.error(f"Tag saving error: {e}")
                
                logger.info("Closing dialog...")
                await page.keyboard.press('Escape')
                await human_delay("tag_dialog_close")
                
            except Exception as e:
                logger.error(f"Button {i+1} error: {e}")
                try:
                    await page.keyboard.press('Escape')
                    await human_delay("tag_dialog_close")
                except:
                    pass
                continue
        
        logger.info(f"This video: {len(tags_found)} REAL tags found!")
        if tags_found:
            logger.info("Found tags:")
            for tag in tags_found:
                logger.info(f"   {tag['Tag']}")
        
        return tags_found
        
    except Exception as e:
        logger.error(f"Tag search general error: {e}")
        return []

async def go_to_next_video(page):
    try:
        logger.info("Going to next video...")
        await human_delay("next_video")
        
        next_button_selectors = [
            'svg[aria-label="Next"] path[d*="12.005.503"]',
            'svg[aria-label="Next"]',
            'button[aria-label="Next"]',
            'div[role="button"] svg[aria-label="Next"]'
        ]
        
        next_button_found = False
        
        for selector in next_button_selectors:
            try:
                if 'path' in selector:
                    next_story_button = await page.query_selector(selector)
                    if next_story_button:
                        parent_button = await next_story_button.evaluate_handle('element => element.closest("div[role=\\"button\\"]")')
                        if parent_button:
                            await parent_button.click()
                            await human_delay("next_video")
                            logger.info("Next video opened!")
                            next_button_found = True
                            break
                else:
                    elements = await page.query_selector_all(selector)
                    for element in elements:
                        is_visible = await element.is_visible()
                        is_enabled = await element.is_enabled()
                        
                        if is_visible and is_enabled:
                            bbox = await element.bounding_box()
                            if bbox and bbox['width'] > 0 and bbox['height'] > 0:
                                logger.info("Next button found and clicking...")
                                await element.click()
                                await human_delay("next_video")
                                logger.info("Successfully moved to next video!")
                                next_button_found = True
                                break
                    if next_button_found:
                        break
            except:
                continue
        
        if not next_button_found:
            logger.info("Next button not found - VIDEOS ENDED!")
            return False
        
        return True
        
    except Exception as e:
        logger.error(f"Error going to next video: {e}")
        return False

async def scrape_all_highlight_videos(page, target_username, unique_tags_global):
    try:
        logger.info(f"Starting highlight videos scraping for {target_username}...")
        
        all_tags = []
        video_count = 0
        
        while True:
            video_count += 1
            logger.info(f"{'='*50}")
            logger.info(f"VIDEO {video_count} - SCRAPING STARTED for {target_username}")
            logger.info(f"{'='*50}")
            
            await pause_video(page)
            
            video_tags = await find_and_process_highlight_tags(page, target_username, unique_tags_global)
            
            if video_tags:
                all_tags.extend(video_tags)
                logger.info(f"Video {video_count}: {len(video_tags)} tags added")
                for tag in video_tags:
                    logger.info(f"   {tag['Tag']}")
            else:
                logger.info(f"Video {video_count}: no tags found")
            
            logger.info(f"Total tags from {target_username} so far: {len(all_tags)}")
            
            has_next = await go_to_next_video(page)
            
            if not has_next:
                logger.info(f"NO NEXT BUTTON - HIGHLIGHTS ENDED for {target_username}!")
                logger.info(f"All videos for {target_username} processed successfully")
                break
            
            if video_count >= 100:
                logger.info(f"Maximum video limit reached (100) for {target_username}")
                break
            
            await human_delay("general_wait")
        
        logger.info(f"HIGHLIGHTS SCRAPING COMPLETED for {target_username}!")
        logger.info(f"Total videos processed for {target_username}: {video_count}")
        logger.info(f"Total tags found for {target_username}: {len(all_tags)}")
        
        return all_tags
        
    except Exception as e:
        logger.error(f"Error scraping highlight videos for {target_username}: {e}")
        return []

async def scrape_highlights(page, username, unique_tags_global):
    try:
        profile_url = f"https://www.instagram.com/{username}/"
        logger.info(f"Scraping highlights for: {username}")
        
        try:
            await page.goto(profile_url, timeout=120000)
            await human_delay("profile_navigation")
            
            if await handle_rate_limiting(page):
                return []
        except Exception as e:
            logger.error(f"Error navigating to profile {profile_url}: {e}")
            return []
        
        has_highlights = await check_highlights(page)
        
        if not has_highlights:
            logger.info(f"No highlights found for {username}")
            return []
        
        logger.info(f"{username} has highlights!")
        
        logger.info(f"First highlight opened for {username}. Starting scraping!")
        
        highlights_tags = await scrape_all_highlight_videos(page, username, unique_tags_global)
        
        logger.info(f"Highlights scraping completed for {username}. Total tags: {len(highlights_tags)}")
        return highlights_tags
        
    except Exception as e:
        logger.error(f"Error scraping highlights for {username}: {e}")
        return []

async def scrape_profile(page, username, unique_tags_global):
    profile_url = f"https://www.instagram.com/{username}/"
    logger.info(f"Scraping profile: {username}")
    
    try:
        await page.goto(profile_url, timeout=120000)
        await human_delay("profile_navigation")
        
        if await handle_rate_limiting(page):
            logger.error(f"Rate limited while accessing profile {username}")
            return []
    except Exception as e:
        logger.error(f"Error navigating to profile {profile_url}: {e}")
        return []

    all_tags_data = []
    
    logger.info(f"Starting posts scraping for {username}...")
    posts_data = await process_content(page, username, profile_url, "posts", scrape_tags_from_post)
    all_tags_data.extend(posts_data)
    
    await human_delay("posts_to_reels")
    
    logger.info(f"Starting reels scraping for {username}...")
    try:
        reels_url = f"https://www.instagram.com/{username}/reels/"
        await page.goto(reels_url, timeout=120000)
        await human_delay("reels_tab")
        
        if await handle_rate_limiting(page):
            logger.error(f"Rate limited while accessing reels for {username}")
        else:
            await human_delay("reels_initial_load")
            
            for retry in range(CONFIG["retry"]["reels_load_attempts"]):
                current_reels = await get_visible_content(page, "reels")
                if current_reels:
                    logger.info(f"Found {len(current_reels)} reels after {retry + 1} attempts")
                    break
                await human_scroll(page)
                await human_delay("reels_retry")
            
            reels_data = await process_content(page, username, profile_url, "reels", scrape_tags_from_reel)
            all_tags_data.extend(reels_data)
        
    except Exception as e:
        logger.error(f"Error accessing reels for {username}: {e}")

    await human_delay("highlights_to_posts")
    
    logger.info(f"Starting highlights scraping for {username}...")
    highlights_data = await scrape_highlights(page, username, unique_tags_global)
    all_tags_data.extend(highlights_data)

    logger.info(f"Complete scraping finished for {username}. Total tags: {len(all_tags_data)}")
    return all_tags_data

async def main():
    if not sheets_manager.authenticate():
        logger.error("Failed to authenticate with Google Sheets. Exiting.")
        return
    
    if not sheets_manager.setup_worksheet():
        logger.error("Failed to setup worksheet. Exiting.")
        return

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
           # channel='chrome',
            args=[
                '--start-maximized',
                '--disable-blink-features=AutomationControlled',
                '--disable-web-security',
                '--no-first-run',
                '--disable-popup-blocking',
                '--disable-dev-shm-usage',
                '--no-sandbox',
                '--disable-background-timer-throttling',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-ipc-flooding-protection'
            ]
        )
        
        username = "boburjon5931"
        password = "Doston0210####____"
        session_file = "instagram_session.json"

        context, session_loaded = await create_context_with_session(browser, session_file)
        page = await context.new_page()
        
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4});
            window.chrome = {runtime: {}};
            delete navigator.__proto__.webdriver;
        """)

        if session_loaded and await validate_session(page):
            logger.info("Session is valid, proceeding with scraping.")
        else:
            logger.info("Invalid session or no session, attempting login...")
            if session_loaded:
                await context.close()
                if os.path.exists(session_file):
                    os.remove(session_file)
                context, _ = await create_context_with_session(browser, session_file)
                page = await context.new_page()
                await page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                    Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
                    Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']});
                    Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
                    Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 4});
                    window.chrome = {runtime: {}};
                    delete navigator.__proto__.webdriver;
                """)
            
            if not await login_instagram(page, username, password):
                logger.error("Failed to log in. Exiting.")
                await browser.close()
                return
            await save_session(context, session_file)

        profiles = [
                "marieonee",
                "elen.dali",
                "goicoechea",
                "thedonofclass",
                "bambaswim",
                "lavarice_",
                "balibody",
                "Sommer.Swim",
                "anchieswim",
                "aguacocosw",
                "alexandramiro",
                "januaryandjune.swim",
                "ta3",
                "amazoniabkinis",
                "nelblu_______",
                "aguadocepraia",
                "laraswim",
                "salinas",
                "boho_ar",
                "Mondayswimwear",
                "paindesucre_officiel",
                "montce_swim",
                "ascenolondon",
                "solidandstriped",
                "Gooseberry.Seaside",
                "odiseaswimwear",
                "bilali_thelabel",
                "baindeminuitswim",
                "maoiswim",
                "tea_you",
                "rarus.shop",
                "etam",
                "fkofficial.it",
                "gracejacobswim",
                "oneoneswim",
                "onia",
                "vitaminaswim",
                "sophiedeloudi",
                "ailablue",
                "alessi.swim",
                "cooke.swim",
                "celestial_swim",
                "fae",
                "leniswims",
                "loleiaswim",
                "lilyrose.us",
                "meshkiswim",
                "uhlalabyll",
                "netta",
                "skatie",
                "stonefoxswim",
                "wildloverslondon",
                "moon_swim_",
                "twswimwear",
                "Bikinibibleuk",
                "belamer.studio",
                "triangl",
                "Adoraswim",
                "almarieswim",
                "amazuin.official",
                "aquamanilewear",
                "bananhot",
                "benoaswim",
                "natasiaswim",
                "biondaswim",
                "bondeyeswim",
                "melissasimoneswim",
                "casajaguarswim",
                "cleonie.swim",
                "emmaswimwear",
                "getsunkissed",
                "gypsy_beach",
                "halfnakd_swim",
                "thehoneyswim",
                "Horseandberries",
                "jetsaustralia",
                "kiohne_",
                "lea_thelabel",
                "lounge_",
                "bosskiniswim",
                "matinee__official",
                "gigibeachbabes",
                "myraswim",
                "odysseytenswimwear",
                "oyeswimwear",
                "osulisboa",
                "reinaolga_beachwear",
                "same",
                "swim.seasalt",
                "shanishemerswimwear",
                "seashellitalia",
                "shopfollowsuit",
                "shimaiswim",
                "osereeswimwear",
                "arabellalondon",
                "khavenswimwear",
                "khamiswim",
                "whitesandsswim",
                "Bambaswim",
                "forloveandlemons",
                "lebleuswim",
                "Kotomi_Swim",
                "encoreswim",
                "sinipesa",
                "lulifamaswimwear",
                "cleome",
                "itsnowcool",
                "bananamoonofficial",
                "bikinilasirene",
                "ondademar",
                "adg_swimwear",
                "pinkshopbrazil",
                "novaswim",
                "swimwavebabe",
                "whitefoxswim",
                "goi",
                "Jaded_Swim",
                "matteau",
                "nowthenlabel",
                "awaythatday",
                "mellothelabel",
                "roar.cruise",
                "fellaswim",
                "eres",
                "setstudiobrand",
                "cantelisboa",
                "changit_official",
                "maygelcoronelofficial",
                "vixpaulahermannybrasil",
                "calarena_official",
                "Lavarice_",
                "oneillwomens",
                "rhythmswimwear",
                "matiabeachwear",
                "truetoneswim",
                "mai.swimwear_",
                "blackseatribe",
                "prettylittlething",
                "Vilebrequin",
                "shopbeachcity",
                "berlookofficial",
                "robincollection",
                "bikinidolls",
                "malaiswimwear",
                "decoroswim",
                "triya_brasil",
                "talentmodelmgmt",
                "imgmodels",
                "wilhelminamodels",
                "katemossagency",
                "next",
                "nymmg",
                "amanagementde",
                "twomanagement",
                "elitenyc",
                "dnamodels",
                "lamodels",
                "elite_paris",
                "stormmodels",
                "fomomodels",
                "TheSocietyNYC",
                "womenmanagementny",
                "newyorkmodels",
                "elitemiami",
                "elite_london",
                "MarilynAgencyNY",
                "models1",
                "premiermodels",
                "women_milano",
                "megamodelbrasil",
                "elite_milan",
                "scoutmodelagency",
                "onemanagement",
                "majormodelsny",
                "waymodel",
                "premium_models",
                "thelionsmgmt",
                "mgm.models",
                "modelwerk",
                "fashionmodel.it",
                "fordmodelsbrasil",
                "women_paris",
                "FusionModelsNYC",
                "evvmodels",
                "thenumanetwork",
                "vnymodels",
                "whynotmodels",
                "nevsmodels",
                "elite_barcelona"

        ]

        unique_tags_global = set()
        
        all_results = {}
        for profile in profiles:
            logger.info(f"{'='*60}")
            logger.info(f"STARTING COMPLETE SCRAPING FOR: {profile}")
            logger.info(f"{'='*60}")
                                          
            tags_data = await scrape_profile(page, profile, unique_tags_global)
            all_results[profile] = tags_data
            
            logger.info(f"COMPLETED SCRAPING FOR: {profile}")
            logger.info(f"Total tags found: {len(tags_data)}")
            
            await human_delay("between_profiles")

        all_data = []
        for profile, tags_data in all_results.items():
            all_data.extend(tags_data)
        
        logger.info(f"{'='*60}")
        logger.info(f"FINAL SUMMARY")
        logger.info(f"{'='*60}")
        logger.info(f"Total profiles scraped: {len(profiles)}")
        logger.info(f"Total tags found: {len(all_data)}")
        
        profile_stats = {}
        source_stats = {"post": 0, "reel": 0, "highlight": 0}
        
        for tag in all_data:
            profile = tag['Account']
            source = tag['Source_Type']
            
            if profile not in profile_stats:
                profile_stats[profile] = {"post": 0, "reel": 0, "highlight": 0, "total": 0}
            
            profile_stats[profile][source] += 1
            profile_stats[profile]["total"] += 1
            source_stats[source] += 1
        
        for profile, stats in profile_stats.items():
            logger.info(f"{profile}: {stats['total']} tags (Posts: {stats['post']}, Reels: {stats['reel']}, Highlights: {stats['highlight']})")
        
        logger.info(f"By source: Posts: {source_stats['post']}, Reels: {source_stats['reel']}, Highlights: {source_stats['highlight']}")
        logger.info(f"All data saved to Google Sheets: Spreadsheet ID '{GOOGLE_SHEETS_CONFIG['spreadsheet_id']}' - '{GOOGLE_SHEETS_CONFIG['worksheet_name']}'")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())


