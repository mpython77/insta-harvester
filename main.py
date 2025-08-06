import asyncio
import json
import os
import random
from playwright.async_api import async_playwright
import time
import re
from typing import List, Tuple, Set, Dict
from datetime import datetime, timedelta
import logging
import gspread
from google.oauth2.service_account import Credentials
import schedule
from threading import Thread

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class InstagramProfileData:
    def __init__(self):
        self.username = ""
        self.name = ""
        self.bio = ""
        self.followers_count = 0
        self.following_count = 0
        self.posts_count = 0
        self.profile_category = ""
        self.email = ""
        self.website = ""
        self.verified = False
        self.tags_in_bio = []
        self.found_through = ""
        self.scraping_time = ""
        self.profile_picture_url = ""
        self.source_type = ""

class GoogleSheetsManager:
    def __init__(self, credentials_file="credentials.json"):
        self.credentials_file = credentials_file
        self.gc = None
        self.worksheet = None
        self.current_row = 1
        self.spreadsheet = None
        self.setup_credentials()
    
    def setup_credentials(self):
        try:
            if not os.path.exists(self.credentials_file):
                logger.error(f"Credentials file not found: {self.credentials_file}")
                return False
            
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive',
                'https://www.googleapis.com/auth/drive.file',
                'https://www.googleapis.com/auth/spreadsheets'
            ]
            
            credentials = Credentials.from_service_account_file(
                self.credentials_file, 
                scopes=scope
            )
            
            self.gc = gspread.authorize(credentials)
            logger.info("Google Sheets API successfully configured")
            return True
            
        except Exception as e:
            logger.error(f"Error setting up Google Sheets API: {e}")
            return False
    
    def get_monday_of_week(self, date_obj):
        days_since_monday = date_obj.weekday()
        monday = date_obj - timedelta(days=days_since_monday)
        return monday
    
    def get_week_sheet_name(self, date_obj):
        monday = self.get_monday_of_week(date_obj)
        sunday = monday + timedelta(days=6)
        return f"{monday.strftime('%d.%m.%Y')}-{sunday.strftime('%d.%m.%Y')}"
    
    def initialize_weekly_sheet(self, sheet_id, current_date):
        try:
            if sheet_id:
                try:
                    self.spreadsheet = self.gc.open_by_key(sheet_id)
                    logger.info(f"Spreadsheet opened: {self.spreadsheet.title}")
                except Exception as e:
                    logger.error(f"Error opening sheet by ID: {e}")
                    return None
            else:
                logger.error("Sheet ID is required")
                return None
            
            current_date_obj = datetime.strptime(current_date, "%d.%m.%Y")
            worksheet_name = self.get_week_sheet_name(current_date_obj)
            
            try:
                self.worksheet = self.spreadsheet.worksheet(worksheet_name)
                logger.info(f"Weekly worksheet found: {worksheet_name}")
                existing_data = self.worksheet.get_all_values()
                self.current_row = len(existing_data) + 1 if existing_data else 2
                
                monday_of_week = self.get_monday_of_week(current_date_obj)
                if current_date_obj.weekday() == 0:
                    logger.info(f"Today is Monday - continuing with existing sheet: {worksheet_name}")
                else:
                    logger.info(f"Continuing with existing weekly sheet: {worksheet_name}")
                    
            except gspread.WorksheetNotFound:
                self.worksheet = self.spreadsheet.add_worksheet(
                    title=worksheet_name, 
                    rows="1000", 
                    cols="20"
                )
                logger.info(f"New weekly worksheet created: {worksheet_name}")
                
                ers = [
                    'Main profil', 'Tag Account', 'Name', 'Source Type', 'Post/Story URL',
                    'Post/Story Time', 'Profile Scraped Time', 'Followers Count', 'Following Count',
                    'Posts Count', 'Verified', 'Bio/Description', 'Tags in Bio', 'Profile Category',
                    'Email', 'Website', 'Profile Picture URL'
                ]
                
                self.worksheet.update(values=[ers], range_name='A1:Q1')
                self.worksheet.format('A1:Q1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
                })
                self.current_row = 2
            
            return {
                'url': self.spreadsheet.url,
                'id': self.spreadsheet.id,
                'title': self.spreadsheet.title,
                'worksheet': self.worksheet.title
            }
            
        except Exception as e:
            logger.error(f"Error initializing weekly sheet: {e}")
            return None
    
    def save_single_profile(self, username, profile_info):
        try:
            if not self.worksheet:
                logger.error("Worksheet not initialized")
                return False
            
            profile_data = profile_info.get('data')
            if not profile_data:
                logger.warning(f"No profile data for {username}")
                return False
            
            row = [
                profile_info.get('found_through', ''),
                f"@{profile_data.username}",
                profile_data.name,
                profile_data.source_type,
                profile_info.get('post_url', ''),
                profile_info.get('post_time', ''),
                profile_data.scraping_time,
                profile_data.followers_count,
                profile_data.following_count,
                profile_data.posts_count,
                'Yes' if profile_data.verified else 'No',
                profile_data.bio,
                ', '.join([f"@{tag}" for tag in profile_data.tags_in_bio]) if profile_data.tags_in_bio else '',
                profile_data.profile_category,
                profile_data.email,
                profile_data.website,
                profile_data.profile_picture_url
            ]
            
            range_name = f'A{self.current_row}:Q{self.current_row}'
            self.worksheet.update(values=[row], range_name=range_name)
            
            logger.info(f"✅ Profile @{username} saved at row {self.current_row}")
            self.current_row += 1
            
            return True
            
        except Exception as e:
            logger.error(f"Error saving profile {username}: {e}")
            return False

class InstagramMonitoringSystem:
    def __init__(self, username, password, sheet_id, profiles_list, credentials_file="credentials.json", schedule_time="09:00"):
        self.username = username
        self.password = password
        self.sheet_id = sheet_id
        self.profiles_list = profiles_list
        self.schedule_time = schedule_time
        self.session_file = f"instagram_session_{username}.json"
        self.last_run_file = f"last_run_{username}.json"
        self.browser = None
        self.page = None
        self.max_retries = 3
        self.collected_users = set()
        self.profile_data = {}
        self.max_posts_to_check = 4
        self.last_run_time = None
        self.sheets_manager = GoogleSheetsManager(credentials_file)
        self.monitoring_active = True
        self.login_attempts = 0
        self.max_login_attempts = 3
        self.login_cooldown = 600
        self.last_login_attempt = None
        
    def check_daily_run_allowed(self):
        try:
            if not os.path.exists(self.last_run_file):
                return True
            
            with open(self.last_run_file, 'r') as f:
                last_run_data = json.load(f)
            
            last_run_date = datetime.fromisoformat(last_run_data['date'])
            current_date = datetime.now()
            
            if current_date.date() > last_run_date.date():
                return True
            else:
                logger.info(f"Daily run already completed today: {last_run_date.strftime('%Y-%m-%d %H:%M:%S')}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking daily run: {e}")
            return True
    
    def save_daily_run(self):
        try:
            run_data = {
                'date': datetime.now().isoformat(),
                'status': 'completed'
            }
            
            with open(self.last_run_file, 'w') as f:
                json.dump(run_data, f, indent=2)
            
            logger.info("Daily run saved successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error saving daily run: {e}")
            return False
    
    def check_login_cooldown(self):
        if self.last_login_attempt is None:
            return True
        
        time_since_last = (datetime.now() - self.last_login_attempt).total_seconds()
        if time_since_last < self.login_cooldown:
            remaining = self.login_cooldown - time_since_last
            logger.warning(f"Login cooldown active. Wait {remaining:.0f} seconds")
            return False
        
        return True
    
    async def refresh_session_aggressively(self):
        try:
            logger.info("🔄 Refreshing session aggressively...")
            
            current_url = self.page.url
            if "instagram.com" not in current_url:
                await self.page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
            
            await self.random_delay(2000, 4000)
            
            login_status = await self.check_login_status()
            if login_status:
                logger.info("✅ Session is still active")
                await self.save_session()
                return True
            else:
                logger.warning("❌ Session expired - attempting re-login")
                
                if not self.check_login_cooldown():
                    return False
                
                if self.login_attempts >= self.max_login_attempts:
                    logger.error(f"Max login attempts ({self.max_login_attempts}) reached")
                    self.last_login_attempt = datetime.now()
                    self.login_attempts = 0
                    await asyncio.sleep(self.login_cooldown)
                
                success = await self.login()
                if success:
                    self.login_attempts = 0
                    self.last_login_attempt = None
                else:
                    self.login_attempts += 1
                    self.last_login_attempt = datetime.now()
                
                return success
                
        except Exception as e:
            logger.error(f"Error refreshing session: {e}")
            return False
    
    async def check_profile_accessibility(self, profile_url):
        try:
            logger.info(f"🔍 Checking profile accessibility: {profile_url}")
            
            await self.page.goto(profile_url, wait_until="domcontentloaded")
            await self.random_delay(3000, 5000)
            
            current_url = self.page.url
            
            error_indicators = [
                'Sorry, this page isn\'t available',
                'The link you followed may be broken',
                'User not found',
                'This account is private',
                'Page Not Found'
            ]
            
            page_content = await self.page.content()
            
            for indicator in error_indicators:
                if indicator.lower() in page_content.lower():
                    logger.warning(f"❌ Profile not accessible: {indicator}")
                    return False
            
            if "login" in current_url.lower():
                logger.warning("❌ Redirected to login - session expired")
                return False
            
            profile_indicators = [
                'img[alt*="profile picture"]',
                'h2',
                'h1',
                'article',
                'div._ac7v'
            ]
            
            for indicator in profile_indicators:
                try:
                    element = await self.page.query_selector(indicator)
                    if element:
                        logger.info("✅ Profile is accessible")
                        return True
                except:
                    continue
            
            logger.warning("❌ Profile accessibility uncertain")
            return False
            
        except Exception as e:
            logger.error(f"Error checking profile accessibility: {e}")
            return False
        
    async def human_like_typing(self, selector, text, delay_range=(50, 150)):
        element = await self.page.wait_for_selector(selector)
        await element.click()
        await element.fill("")
        for char in text:
            await element.type(char)
            await asyncio.sleep(random.uniform(delay_range[0]/1000, delay_range[1]/1000))
    
    async def random_delay(self, min_ms=1000, max_ms=3000):
        delay = random.uniform(min_ms/1000, max_ms/1000)
        await asyncio.sleep(delay)
    
    async def human_like_scroll(self):
        scroll_height = random.randint(200, 600)
        await self.page.evaluate(f"window.scrollBy(0, {scroll_height})")
        await self.random_delay(500, 1500)
    
    def normalize_username(self, username):
        if not username:
            return None
        
        if username.startswith('@'):
            username = username[1:]
        
        username = username.rstrip('.')
        
        if len(username) < 2:
            return None
            
        if not re.match(r'^[a-zA-Z0-9._]+$', username):
            return None
            
        return username

    def extract_number(self, text):
        if not text:
            return 0
        
        match = re.search(r'([\d,]+\.?\d*)\s*([KkMm]?)', text.replace(',', ''))
        if match:
            number = float(match.group(1).replace(',', ''))
            suffix = match.group(2).upper()
            
            if suffix == 'K':
                return int(number * 1000)
            elif suffix == 'M':
                return int(number * 1000000)
            else:
                return int(number)
        return 0

    def is_post_within_24_hours(self, post_time_str):
        try:
            current_time = datetime.now()
            
            if "ago" in post_time_str.lower():
                number_match = re.search(r'(\d+)', post_time_str)
                if number_match:
                    number = int(number_match.group(1))
                    
                    if "hour" in post_time_str.lower() or "hr" in post_time_str.lower():
                        if number <= 24:
                            return True
                    elif "minute" in post_time_str.lower() or "min" in post_time_str.lower():
                        return True
                    elif "second" in post_time_str.lower() or "sec" in post_time_str.lower():
                        return True
                    
                return False
            
            try:
                if "T" in post_time_str and ("Z" in post_time_str or "+" in post_time_str or "-" in post_time_str):
                    post_time = datetime.fromisoformat(post_time_str.replace('Z', '+00:00'))
                    time_diff = current_time - post_time
                    return time_diff.total_seconds() <= 86400
            except:
                pass
            
            try:
                post_time = datetime.strptime(post_time_str, "%Y-%m-%d %H:%M:%S")
                time_diff = current_time - post_time
                return time_diff.total_seconds() <= 86400
            except:
                pass
            
            try:
                post_time = datetime.strptime(post_time_str, "%Y-%m-%d %H:%M:%S UTC")
                time_diff = current_time - post_time
                return time_diff.total_seconds() <= 86400
            except:
                pass
            
            return False
            
        except Exception as e:
            logger.warning(f"Error checking post time: {e}")
            return False

    async def extract_post_time(self):
        try:
            time_selectors = [
                'time[datetime]',
                'time',
                'a time',
                'span[title*="20"]',
                'span._aaqe',
                'div._aaqe',
                'a[href*="/p/"] time',
                'article time'
            ]
            
            for selector in time_selectors:
                try:
                    time_element = await self.page.query_selector(selector)
                    if time_element:
                        datetime_attr = await time_element.get_attribute('datetime')
                        if datetime_attr:
                            try:
                                parsed_time = datetime.fromisoformat(datetime_attr.replace('Z', '+00:00'))
                                return parsed_time.strftime("%Y-%m-%d %H:%M:%S UTC")
                            except:
                                return datetime_attr
                        
                        title_attr = await time_element.get_attribute('title')
                        if title_attr:
                            return title_attr
                        
                        time_text = await time_element.inner_text()
                        if time_text and time_text.strip():
                            return time_text.strip()
                except Exception as e:
                    logger.debug(f"Time selector {selector} failed: {e}")
                    continue
            
            logger.debug("Post time not found")
            return "Time not determined"
            
        except Exception as e:
            logger.warning(f"Error extracting post time: {e}")
            return "Error"

    async def dismiss_notification_popup(self):
        try:
            dismiss_selectors = [
                'div[data-bloks-name="bk.components.Flexbox"][role="button"][aria-label="Dismiss"]',
                'button[aria-label="Dismiss"]',
                'div[role="button"]:has-text("Dismiss")',
                'span:has-text("Dismiss")',
                'div.wbloks_1[role="button"][aria-label="Dismiss"]'
            ]
            
            for selector in dismiss_selectors:
                try:
                    dismiss_button = await self.page.query_selector(selector)
                    if dismiss_button:
                        await dismiss_button.click()
                        logger.info("Notification popup dismissed")
                        await self.random_delay(1000, 2000)
                        return True
                except Exception as e:
                    logger.debug(f"Dismiss selector {selector} failed: {e}")
                    continue
            
            return False
        except Exception as e:
            logger.debug(f"Error dismissing notification popup: {e}")
            return False

    async def save_session(self):
        try:
            cookies = await self.page.context.cookies()
            local_storage = {}
            session_storage = {}
            
            try:
                local_storage = await self.page.evaluate("() => Object.assign({}, localStorage)")
            except:
                logger.warning("Cannot access local storage")
            
            try:
                session_storage = await self.page.evaluate("() => Object.assign({}, sessionStorage)")
            except:
                logger.warning("Cannot access session storage")
            
            session_data = {
                'cookies': cookies,
                'local_storage': local_storage,
                'session_storage': session_storage,
                'user_agent': await self.page.evaluate("() => navigator.userAgent"),
                'saved_at': datetime.now().isoformat()
            }
            
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            
            logger.info(f"Session saved: {self.session_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving session: {e}")
            return False
    
    async def load_session(self):
        try:
            if not os.path.exists(self.session_file):
                logger.info("Session file not found, will login with credentials")
                return False
            
            logger.info(f"Loading session from: {self.session_file}")
            
            with open(self.session_file, 'r') as f:
                session_data = json.load(f)
            
            if 'saved_at' in session_data:
                saved_time = datetime.fromisoformat(session_data['saved_at'])
                if datetime.now() - saved_time > timedelta(hours=2):
                    logger.info("Session is older than 2 hours, will login fresh")
                    return False
            
            await self.page.goto("https://www.instagram.com/", wait_until="domcontentloaded")
            await self.random_delay(2000, 3000)
            
            if session_data.get('cookies'):
                try:
                    await self.page.context.add_cookies(session_data['cookies'])
                    logger.info("Cookies loaded successfully")
                except Exception as e:
                    logger.warning(f"Error loading cookies: {e}")
                    return False
            
            await self.page.reload(wait_until="domcontentloaded")
            await self.random_delay(3000, 5000)
            
            if session_data.get('local_storage'):
                try:
                    for key, value in session_data['local_storage'].items():
                        await self.page.evaluate(f"localStorage.setItem('{key}', '{value}')")
                    logger.info("Local storage loaded successfully")
                except Exception as e:
                    logger.warning(f"Error loading local storage: {e}")
            
            if session_data.get('session_storage'):
                try:
                    for key, value in session_data['session_storage'].items():
                        await self.page.evaluate(f"sessionStorage.setItem('{key}', '{value}')")
                    logger.info("Session storage loaded successfully")
                except Exception as e:
                    logger.warning(f"Error loading session storage: {e}")
            
            await self.page.reload(wait_until="domcontentloaded")
            await self.random_delay(3000, 5000)
            
            logger.info("Session loaded successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error loading session: {e}")
            return False
    
    async def check_login_status(self):
        try:
            logger.info("Checking login status...")
            
            await self.page.wait_for_load_state("domcontentloaded", timeout=15000)
            await self.random_delay(3000, 5000)
            
            current_url = self.page.url
            logger.info(f"Current URL: {current_url}")
            
            if "login" in current_url.lower() or "accounts/login" in current_url.lower():
                logger.info("Currently on login page - not logged in")
                return False
            
            login_selectors = [
                'input[name="username"]',
                'input[name="password"]',
                'button[type="submit"]:has-text("Log in")',
                'button[type="submit"]:has-text("Log In")'
            ]
            
            for selector in login_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        logger.info(f"Found login element: {selector} - not logged in")
                        return False
                except:
                    continue
            
            logged_in_selectors = [
                'svg[aria-label="Home"]',
                'a[href="/"]',
                'svg[aria-label="Search"]',
                'svg[aria-label="New post"]',
                'svg[aria-label="Find People"]',
                'svg[aria-label="Activity Feed"]',
                'svg[aria-label="Profile"]',
                'a[href="/direct/inbox/"]',
                'nav[role="navigation"]',
                'div[data-testid="mobile-nav-logged-in"]'
            ]
            
            for selector in logged_in_selectors:
                try:
                    element = await self.page.query_selector(selector)
                    if element:
                        logger.info(f"Found logged-in element: {selector} - LOGIN CONFIRMED")
                        return True
                except:
                    continue
            
            try:
                await self.page.goto(f"https://www.instagram.com/{self.username}/", wait_until="domcontentloaded")
                await self.random_delay(2000, 3000)
                
                current_url = self.page.url
                if "login" in current_url.lower():
                    logger.info("Redirected to login page when accessing profile - not logged in")
                    return False
                else:
                    logger.info("Successfully accessed profile page - LOGIN CONFIRMED")
                    return True
                    
            except Exception as e:
                logger.warning(f"Error checking profile access: {e}")
            
            logger.warning("Could not confirm login status")
            return False
            
        except Exception as e:
            logger.error(f"Error checking login status: {e}")
            return False
    
    async def login(self):
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Login attempt {attempt + 1}/{self.max_retries}")
                
                await self.page.goto("https://www.instagram.com/accounts/login/", wait_until="domcontentloaded")
                await self.random_delay(3000, 6000)
                await self.page.wait_for_load_state("networkidle", timeout=15000)
                
                try:
                    cookie_buttons = [
                        'button:has-text("Accept")',
                        'button:has-text("Accept All")',
                        'button:has-text("Allow essential and optional cookies")'
                    ]
                    for selector in cookie_buttons:
                        try:
                            button = await self.page.query_selector(selector)
                            if button:
                                await button.click()
                                await self.random_delay(1000, 2000)
                                break
                        except:
                            continue
                except:
                    pass
                
                username_selector = 'input[name="username"]'
                logger.info("Waiting for username field...")
                await self.page.wait_for_selector(username_selector, timeout=15000)
                logger.info("Typing username...")
                await self.human_like_typing(username_selector, self.username)
                await self.random_delay(800, 1800)
                
                password_selector = 'input[name="password"]'
                logger.info("Typing password...")
                await self.human_like_typing(password_selector, self.password)
                await self.random_delay(1000, 2500)
                
                logger.info("Clicking login button...")
                login_button = None
                selectors = [
                    'button[type="submit"]',
                    'button:has-text("Log in")',
                    'button:has-text("Log In")',
                    'div[role="button"]:has-text("Log in")'
                ]
                
                for selector in selectors:
                    try:
                        login_button = await self.page.query_selector(selector)
                        if login_button:
                            break
                    except:
                        continue
                
                if login_button:
                    await login_button.click()
                    logger.info("Login button clicked")
                else:
                    logger.warning("Login button not found")
                    continue
                
                logger.info("Waiting for login result...")
                await self.random_delay(5000, 10000)
                
                await self.dismiss_notification_popup()
                
                try:
                    security_code_input = await self.page.query_selector('input[name="verificationCode"]')
                    if security_code_input:
                        logger.info("2FA required. Enter code from phone:")
                        code = input("Verification code: ")
                        await self.human_like_typing('input[name="verificationCode"]', code)
                        await self.random_delay(1000, 2000)
                        
                        confirm_button = await self.page.query_selector('button:has-text("Confirm")')
                        if confirm_button:
                            await confirm_button.click()
                            await self.random_delay(3000, 5000)
                except:
                    pass
                
                if await self.check_login_status():
                    logger.info("LOGIN SUCCESSFUL!")
                    
                    if await self.save_session():
                        logger.info("Session saved successfully")
                    else:
                        logger.warning("Failed to save session")
                    
                    return True
                else:
                    logger.warning(f"Login failed (attempt {attempt + 1})")
                    if attempt < self.max_retries - 1:
                        await self.random_delay(5000, 10000)
                    
            except Exception as e:
                logger.error(f"Error during login (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await self.random_delay(5000, 10000)
        
        logger.error("All login attempts failed")
        return False

    async def start_browser(self):
        for attempt in range(self.max_retries):
            try:
                playwright = await async_playwright().start()
                
                user_agents = [
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
                    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
                ]
                
                self.browser = await playwright.chromium.launch(
                headless=True,
                #channel='chrome',
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
                
                context = await self.browser.new_context(
                    viewport={'width': 1366, 'height': 768},
                    user_agent=random.choice(user_agents)
                )
                
                self.page = await context.new_page()
                
                await self.page.add_init_script("""
                    Object.defineProperty(navigator, 'webdriver', {
                        get: () => undefined,
                    });
                    Object.defineProperty(navigator, 'plugins', {
                        get: () => [1, 2, 3, 4, 5],
                    });
                    Object.defineProperty(navigator, 'languages', {
                        get: () => ['en-US', 'en'],
                    });
                """)
                
                logger.info("Browser started successfully")
                return True
                
            except Exception as e:
                logger.error(f"Error starting browser (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(5)
                else:
                    return False
        return False
    
    async def close_browser(self):
        if self.browser:
            await self.browser.close()
            logger.info("Browser closed")

    async def get_stories_tags(self, profile_url, source_profile):
        tags = []
        seen_tags = set()
        
        try:
            username = profile_url.split('/')[-2] if profile_url.endswith('/') else profile_url.split('/')[-1]
            if username.startswith('@'):
                username = username[1:]
            
            logger.info(f"Checking stories for @{username}...")
            
            await self.page.goto(profile_url, wait_until="domcontentloaded")
            await self.random_delay(3000, 5000)
            
            story_selectors = [
                f'span[role="link"] img[alt*="{username}"]',
                'span[role="link"] img',
                'div[role="button"] img',
                'canvas + img',
                'div._ac3q img'
            ]
            
            story_opened = False
            for selector in story_selectors:
                try:
                    story_element = await self.page.wait_for_selector(selector, timeout=5000)
                    if story_element:
                        await story_element.click()
                        await self.random_delay(2000, 4000)
                        story_opened = True
                        logger.info(f"Stories opened for @{username}")
                        break
                except Exception as e:
                    logger.debug(f"Story selector {selector} failed: {e}")
                    continue
            
            if not story_opened:
                logger.warning(f"Could not open stories for @{username}")
                return []
            
            story_count = 0
            max_stories = 20
            
            while story_count < max_stories:
                story_count += 1
                logger.info(f"Processing story #{story_count} for @{username}")
                
                try:
                    pause_selectors = [
                        'svg[aria-label="Pause"]',
                        'button[aria-label="Pause"]'
                    ]
                    
                    for pause_selector in pause_selectors:
                        try:
                            pause_button = await self.page.query_selector(pause_selector)
                            if pause_button:
                                await pause_button.click()
                                await self.random_delay(1000, 2000)
                                logger.debug("Story paused")
                                break
                        except:
                            continue
                except Exception as e:
                    logger.debug(f"Error pausing story: {e}")
                
                try:
                    tag_selectors = [
                        'div[role="button"][style*="transform: translate(-50%, -50%)"]',
                        'div[role="button"][style*="position: absolute"]',
                        'div[style*="transform: translate(-50%, -50%)"]'
                    ]
                    
                    tags_found_in_story = False
                    processed_tags_in_story = 0
                    max_attempts = 20
                    
                    for attempt in range(max_attempts):
                        tag_buttons = []
                        for tag_selector in tag_selectors:
                            try:
                                found_buttons = await self.page.query_selector_all(tag_selector)
                                if found_buttons:
                                    tag_buttons.extend(found_buttons)
                                    break
                            except:
                                continue
                        
                        if not tag_buttons:
                            logger.debug(f"No tag buttons found in story #{story_count}, attempt #{attempt+1}")
                            break
                        
                        logger.info(f"Found {len(tag_buttons)} tag buttons in story #{story_count}, attempt #{attempt+1}")
                        
                        if processed_tags_in_story >= len(tag_buttons):
                            logger.debug(f"All {len(tag_buttons)} tags processed in story #{story_count}")
                            break
                        
                        if processed_tags_in_story < len(tag_buttons):
                            tag_button = tag_buttons[processed_tags_in_story]
                            
                            try:
                                try:
                                    pause_button = await self.page.query_selector('svg[aria-label="Pause"]')
                                    if pause_button:
                                        await pause_button.click()
                                        await self.random_delay(500, 1000)
                                except:
                                    pass
                                
                                await tag_button.click(force=True)
                                await self.random_delay(800, 1200)
                                
                                tag_selectors_popup = [
                                    'div.xu96u03.xm80bdy.x10l6tqk.x13vifvy a[href*="/"][role="link"]',
                                    'a[href*="/"][role="link"]',
                                    'div.x78zum5.x889kno.x2vl965.x1a8lsjc.xe2zdcy'
                                ]
                                
                                tag_found = False
                                for tag_selector_popup in tag_selectors_popup:
                                    try:
                                        tag_container = await self.page.query_selector(tag_selector_popup)
                                        if tag_container:
                                            tag_text_element = await tag_container.query_selector('div.x78zum5.x889kno.x2vl965.x1a8lsjc.xe2zdcy')
                                            tag_text = await tag_text_element.inner_text() if tag_text_element else "Unknown"
                                            tag_url = await tag_container.get_attribute('href')
                                            
                                            if (tag_text and not tag_text.startswith("See post") and 
                                                tag_url and not tag_url.startswith("/p/") and 
                                                not tag_url.startswith("/reel/")):
                                                
                                                if tag_url.startswith('/'):
                                                    username_from_url = tag_url.strip('/')
                                                else:
                                                    username_from_url = tag_url.split('/')[-2] if tag_url.endswith('/') else tag_url.split('/')[-1]
                                                
                                                normalized_username = self.normalize_username(username_from_url)
                                                if normalized_username:
                                                    tag_key = normalized_username
                                                    if tag_key not in seen_tags:
                                                        tags.append(normalized_username)
                                                        seen_tags.add(tag_key)
                                                        logger.info(f"Story tag found: @{normalized_username} (from {tag_text})")
                                                        tags_found_in_story = True
                                                        
                                                        if normalized_username not in self.profile_data:
                                                            self.profile_data[normalized_username] = {
                                                                'found_through': source_profile,
                                                                'post_url': f"Instagram Stories of {source_profile}",
                                                                'post_time': "Stories content",
                                                                'data': None
                                                            }
                                                        
                                                        tag_found = True
                                                        break
                                                    else:
                                                        logger.debug(f"Duplicate tag skipped: @{normalized_username}")
                                            break
                                    except:
                                        continue
                                
                                if not tag_found:
                                    logger.debug(f"Tag #{processed_tags_in_story+1} could not be processed")
                                
                                processed_tags_in_story += 1
                                
                                try:
                                    story_background_areas = [
                                        'div[style*="height: 100vh"]',
                                        'section[role="dialog"]',
                                        'div[role="dialog"]'
                                    ]
                                    
                                    popup_closed = False
                                    for bg_selector in story_background_areas:
                                        try:
                                            bg_element = await self.page.query_selector(bg_selector)
                                            if bg_element:
                                                await bg_element.click(position={'x': 50, 'y': 50})
                                                await self.random_delay(300, 600)
                                                popup_closed = True
                                                logger.debug("Popup closed by clicking background")
                                                break
                                        except:
                                            continue
                                    
                                    if not popup_closed:
                                        try:
                                            await self.page.click('body', position={'x': 100, 'y': 100})
                                            await self.random_delay(300, 600)
                                            logger.debug("Popup closed by clicking body")
                                        except:
                                            try:
                                                await self.page.keyboard.press('Escape')
                                                await self.random_delay(300, 600)
                                                logger.debug("Popup closed with Escape")
                                            except:
                                                pass
                                        
                                except Exception as e:
                                    logger.debug(f"Error closing tag popup: {e}")
                                    try:
                                        await self.page.keyboard.press('Escape')
                                        await self.random_delay(300, 600)
                                    except:
                                        pass
                                        
                            except Exception as e:
                                logger.warning(f"Error processing tag #{processed_tags_in_story+1}: {e}")
                                processed_tags_in_story += 1
                                continue
                        else:
                            break
                    
                    if not tags_found_in_story:
                        logger.debug(f"No tags found in story #{story_count} - moving to next story quickly")
                        await self.random_delay(1000, 2000)
                    else:
                        await self.random_delay(3000, 5000)
                            
                except Exception as e:
                    logger.warning(f"Error searching for tags in story #{story_count}: {e}")
                
                try:
                    next_selectors = [
                        'svg[aria-label="Next"]',
                        'button[aria-label="Next"]',
                        'div[role="button"]:has(svg[aria-label="Next"])'
                    ]
                    
                    next_clicked = False
                    for next_selector in next_selectors:
                        try:
                            next_button = await self.page.query_selector(next_selector)
                            if next_button:
                                await next_button.click()
                                await self.random_delay(1000, 2000)
                                next_clicked = True
                                logger.debug("Moved to next story")
                                break
                        except:
                            continue
                    
                    if not next_clicked:
                        logger.info("No more stories available")
                        break
                        
                except Exception as e:
                    logger.warning(f"Error moving to next story: {e}")
                    break
            
            logger.info(f"Stories processing completed for @{username}. Found {len(tags)} unique tags")
            return tags
            
        except Exception as e:
            logger.error(f"Error getting stories tags for {profile_url}: {e}")
            return []
    
    async def extract_profile_data(self, username):
        profile_data = InstagramProfileData()
        profile_data.username = username
        profile_data.scraping_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        if username in self.profile_data:
            if "Stories" in self.profile_data[username].get('post_url', ''):
                profile_data.source_type = "stories"
            else:
                profile_data.source_type = "post"
        else:
            profile_data.source_type = "direct"
        
        try:
            profile_url = f"https://www.instagram.com/{username}/"
            
            if not await self.check_profile_accessibility(profile_url):
                logger.warning(f"Profile @{username} is not accessible - skipping")
                return profile_data
            
            await self.random_delay(3000, 5000)
            
            try:
                name_selectors = [
                    'h2 span.x1lliihq.x1plvlek.xryxfnj',
                    'h1 span.x1lliihq.x1plvlek.xryxfnj',
                    'span.x1lliihq.x193iq5w.x6ikm8r.x10wlt62.xlyipyv.xuxw1ft'
                ]
                for selector in name_selectors:
                    try:
                        element = await self.page.query_selector(selector)
                        if element:
                            profile_data.name = await element.inner_text()
                            break
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Display name not found for {username}: {e}")

            try:
                verified_element = await self.page.query_selector('svg[aria-label="Verified"]')
                profile_data.verified = verified_element is not None
            except:
                pass

            try:
                stats_selectors = [
                    'ul.x78zum5.x1q0g3np.x1l1ennw li',
                    'section ul li',
                    'ul._ac2a li'
                ]
                
                for stats_selector in stats_selectors:
                    try:
                        stats_elements = await self.page.query_selector_all(stats_selector)
                        if len(stats_elements) >= 3:
                            posts_text = await stats_elements[0].inner_text()
                            profile_data.posts_count = self.extract_number(posts_text.split()[0])
                            
                            followers_text = await stats_elements[1].inner_text()
                            profile_data.followers_count = self.extract_number(followers_text.split()[0])
                            
                            following_text = await stats_elements[2].inner_text()
                            profile_data.following_count = self.extract_number(following_text.split()[0])
                            break
                    except Exception as e:
                        logger.warning(f"Error getting stats for {username}: {e}")
                        continue
            except Exception as e:
                logger.warning(f"General stats error for {username}: {e}")

            try:
                bio_selectors = [
                    'div._ap3a._aaco._aacu._aacy._aad6._aade',
                    'div[dir="auto"]._ap3a._aaco._aacu._aacy._aad6._aade',
                    'span._ap3a._aaco._aacu._aacx._aad7._aade'
                ]
                
                for bio_selector in bio_selectors:
                    try:
                        bio_element = await self.page.query_selector(bio_selector)
                        if bio_element:
                            bio_text = await bio_element.inner_text()
                            if bio_text and len(bio_text.strip()) > 0:
                                profile_data.bio = bio_text.strip()
                                
                                tags = re.findall(r'@[\w.]+', bio_text)
                                profile_data.tags_in_bio = [self.normalize_username(tag) for tag in tags if self.normalize_username(tag)]
                                break
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Error getting bio for {username}: {e}")

            try:
                category_selectors = [
                    'div._ap3a._aaco._aacu._aacy._aad6._aade[dir="auto"]',
                    'div._ap3a._aaco._aacu._aacw._aacx._aad7._aade',
                    'div[role="text"]',
                    'section div._ap3a._aaco._aacu._aacy._aad6._aade',
                    'header section div._ap3a._aaco._aacu._aacy._aad6._aade'
                ]
                
                category_keywords = [
                    'brand', 'business', 'company', 'corporation', 'enterprise', 'store', 'shop', 'boutique',
                    'restaurant', 'cafe', 'bar', 'hotel', 'agency', 'studio', 'salon', 'clinic', 'hospital',
                    'school', 'university', 'college', 'institute', 'academy', 'center', 'centre',
                    'creator', 'influencer', 'blogger', 'youtuber', 'content creator', 'digital creator',
                    'artist', 'musician', 'singer', 'actor', 'actress', 'model', 'photographer', 'designer',
                    'writer', 'author', 'journalist', 'coach', 'trainer', 'consultant', 'speaker',
                    'personal', 'public figure', 'entrepreneur', 'ceo', 'founder', 'director', 'manager',
                    'chef', 'doctor', 'lawyer', 'engineer', 'developer', 'scientist', 'researcher',
                    'fashion', 'beauty', 'fitness', 'health', 'food', 'travel', 'lifestyle', 'tech',
                    'gaming', 'sports', 'music', 'art', 'photography', 'education', 'finance',
                    'clothing', 'apparel', 'fashion brand', 'jewelry', 'accessories', 'shoes', 'bags',
                    'cosmetics', 'skincare', 'makeup', 'beauty brand',
                    'page', 'official', 'verified', 'entertainment', 'media', 'news', 'magazine',
                    'organization', 'nonprofit', 'charity', 'community', 'group', 'team', 'club'
                ]
                
                potential_categories = []
                
                for category_selector in category_selectors:
                    try:
                        category_elements = await self.page.query_selector_all(category_selector)
                        for element in category_elements:
                            text = await element.inner_text()
                            
                            if not text or len(text.strip()) == 0:
                                continue
                                
                            text = text.strip()
                            
                            if (len(text) > 100 or 
                                'http' in text.lower() or 
                                '@' in text or 
                                'www.' in text.lower() or
                                '.com' in text.lower() or
                                '.org' in text.lower() or
                                text.lower() == profile_data.name.lower() or
                                text.lower() == profile_data.username.lower()):
                                continue
                            
                            potential_categories.append(text)
                    except Exception as e:
                        logger.debug(f"Category selector {category_selector} failed: {e}")
                        continue
                
                best_category = None
                highest_score = 0
                
                for category in potential_categories:
                    score = 0
                    category_lower = category.lower()
                    
                    for keyword in category_keywords:
                        if keyword in category_lower:
                            if keyword == category_lower:
                                score += 10
                            elif category_lower.startswith(keyword) or category_lower.endswith(keyword):
                                score += 7
                            else:
                                score += 5
                    
                    if len(category) <= 30:
                        score += 3
                    if len(category) <= 15:
                        score += 2
                        
                    if any(pattern in category_lower for pattern in ['(brand)', '(official)', 'clothing brand', 'beauty brand']):
                        score += 8
                    
                    if score == 0 and len(category) <= 25 and len(category.split()) <= 3:
                        common_words = ['the', 'and', 'or', 'of', 'in', 'at', 'to', 'for', 'with', 'by']
                        if not any(word in category_lower.split() for word in common_words):
                            score += 2
                    
                    if score > highest_score:
                        highest_score = score
                        best_category = category
                
                if not best_category and potential_categories:
                    for category in sorted(potential_categories, key=len):
                        if (len(category) <= 40 and 
                            not any(char in category for char in ['🔥', '💎', '✨', '❤️', '🎯']) and
                            len([c for c in category if c.isupper()]) <= len(category) // 2):
                            best_category = category
                            break
                
                if best_category:
                    profile_data.profile_category = best_category
                    logger.debug(f"Category found: '{best_category}' (score: {highest_score})")
                else:
                    logger.debug(f"Category not found, {len(potential_categories)} variants checked")
                    
            except Exception as e:
                logger.warning(f"Error getting category for {username}: {e}")

            try:
                link_selectors = [
                    'a[href*="mailto:"]',
                    'div.x3nfvp2 a',
                    'a[rel="me nofollow noopener noreferrer"]'
                ]
                
                for link_selector in link_selectors:
                    try:
                        link_elements = await self.page.query_selector_all(link_selector)
                        for link in link_elements:
                            href = await link.get_attribute('href')
                            if href:
                                if 'mailto:' in href:
                                    profile_data.email = href.replace('mailto:', '')
                                elif 'http' in href and not profile_data.website:
                                    profile_data.website = await link.inner_text()
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Error getting links/email for {username}: {e}")

            try:
                img_selectors = [
                    'img[alt*="profile picture"]',
                    'img.x15mokao.x1ga7v0g.x16uus16.xbiv7yw'
                ]
                
                for img_selector in img_selectors:
                    try:
                        img_element = await self.page.query_selector(img_selector)
                        if img_element:
                            profile_data.profile_picture_url = await img_element.get_attribute('src')
                            break
                    except:
                        continue
            except Exception as e:
                logger.warning(f"Error getting profile picture URL for {username}: {e}")

            logger.info(f"Profile data collected: @{username} (source: {profile_data.source_type})")
            return profile_data
            
        except Exception as e:
            logger.error(f"General error collecting profile data for {username}: {e}")
            return profile_data

    async def extract_tagged_users(self):
        raw_users = set()
        
        try:
            caption_selectors = [
                'article div[role="main"] span',
                'article span',
                'div[data-testid="post-caption"] span'
            ]
            
            for selector in caption_selectors:
                try:
                    caption_element = await self.page.query_selector(selector)
                    if caption_element:
                        caption_text = await caption_element.inner_text()
                        tags = re.findall(r'@[\w.]+', caption_text)
                        raw_users.update(tags)
                        break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Error extracting caption tags: {e}")
        
        try:
            tag_selectors = [
                'div._aa1y a[href*="/"]',
                'div[data-visualcompletion="css-img"] a[href*="/"]',
                'article a[href^="/"][href*="/"]'
            ]
            
            for selector in tag_selectors:
                try:
                    tag_elements = await self.page.query_selector_all(selector)
                    for tag in tag_elements:
                        tag_href = await tag.get_attribute('href')
                        if tag_href and tag_href.startswith('/') and not tag_href.startswith('/p/') and not tag_href.startswith('/reel/'):
                            username = tag_href.strip('/')
                            if username and username not in ['explore', 'direct', 'accounts', 'stories', 'reels']:
                                raw_users.add(f"@{username}")
                    break
                except:
                    continue
        except Exception as e:
            logger.warning(f"Error extracting image tags: {e}")
        
        try:
            next_button_selector = 'button[aria-label="Next"]'
            image_count = 0
            max_images = 10
            
            while image_count < max_images:
                image_count += 1
                
                try:
                    img_elements = await self.page.query_selector_all('img[alt*="Photo"], img[alt*="Image"]')
                    for img in img_elements:
                        alt_text = await img.get_attribute('alt')
                        if alt_text:
                            tags = re.findall(r'@[\w.]+', alt_text)
                            raw_users.update(tags)
                except:
                    pass
                
                next_button = await self.page.query_selector(next_button_selector)
                if next_button:
                    await next_button.click()
                    await self.random_delay(1500, 3000)
                else:
                    break
                    
        except Exception as e:
            logger.warning(f"Error extracting carousel tags: {e}")
        
        normalized_users = set()
        for user in raw_users:
            normalized = self.normalize_username(user)
            if normalized:
                normalized_users.add(normalized)
        
        return list(normalized_users)
    
    async def is_post_pinned_from_grid(self, post_container):
        try:
            pin_indicators = [
                'svg[aria-label="Pinned post icon"]',
                'div.html-div svg',
                'svg[viewBox="0 0 24 24"]'
            ]
            
            for indicator in pin_indicators:
                try:
                    element = await post_container.query_selector(indicator)
                    if element:
                        aria_label = await element.get_attribute('aria-label')
                        if aria_label and 'pinned' in aria_label.lower():
                            logger.info(f"Found pinned post in grid view: {aria_label}")
                            return True
                        
                        title_elem = await element.query_selector('title')
                        if title_elem:
                            title_text = await title_elem.inner_text()
                            if title_text and 'pinned' in title_text.lower():
                                logger.info(f"Found pinned post in grid view via title: {title_text}")
                                return True
                        
                        path_elem = await element.query_selector('path')
                        if path_elem:
                            path_d = await path_elem.get_attribute('d')
                            if path_d and 'm22.707 7.583' in path_d:
                                logger.info(f"Found pinned post in grid view via path signature")
                                return True
                except:
                    continue
            
            container_html = await post_container.inner_html()
            if 'Pinned post icon' in container_html or 'm22.707 7.583' in container_html:
                logger.info(f"Found pinned post in grid view via HTML content")
                return True
            
            return False
        except Exception as e:
            logger.debug(f"Error checking if post is pinned from grid: {e}")
            return False

    async def is_post_pinned(self, post_element):
        try:
            page_content = await self.page.content()
            
            pinned_indicators = [
                'Pinned post icon',
                'pinned post icon', 
                'pinned',
                'm22.707 7.583-6.29-6.29',
                'aria-label="Pinned post icon"'
            ]
            
            for indicator in pinned_indicators:
                if indicator in page_content:
                    logger.info(f"Found pinned indicator in page: {indicator}")
                    return True
            
            all_svgs = await self.page.query_selector_all('svg')
            for svg in all_svgs:
                try:
                    aria_label = await svg.get_attribute('aria-label')
                    if aria_label and 'pinned' in aria_label.lower():
                        logger.info(f"Found pinned SVG with aria-label: {aria_label}")
                        return True
                    
                    title_elem = await svg.query_selector('title')
                    if title_elem:
                        title_text = await title_elem.inner_text()
                        if title_text and 'pinned' in title_text.lower():
                            logger.info(f"Found pinned SVG with title: {title_text}")
                            return True
                    
                    path_elem = await svg.query_selector('path')
                    if path_elem:
                        path_d = await path_elem.get_attribute('d')
                        if path_d and 'm22.707 7.583' in path_d:
                            logger.info(f"Found pinned SVG with path signature")
                            return True
                except:
                    continue
            
            pin_containers = await self.page.query_selector_all('div.html-div')
            for container in pin_containers:
                try:
                    container_html = await container.inner_html()
                    if 'pinned' in container_html.lower() or 'm22.707 7.583' in container_html:
                        logger.info(f"Found pinned indicator in container HTML")
                        return True
                except:
                    continue
            
            logger.info("No pinned indicators found - post is NOT pinned")
            return False
            
        except Exception as e:
            logger.error(f"Error checking if post is pinned: {e}")
            return False

    async def get_latest_non_pinned_post(self, profile_url, source_profile):
        for attempt in range(self.max_retries):
            try:
                logger.info(f"Navigating to {profile_url}... (attempt {attempt + 1})")
                
                if not await self.check_profile_accessibility(profile_url):
                    logger.warning(f"Profile not accessible: {profile_url}")
                    return None, [], "Profile not accessible"
                
                await self.random_delay(3000, 6000)
                await self.human_like_scroll()
                
                all_post_links = []
                
                try:
                    await self.page.wait_for_selector('div._ac7v', timeout=10000)
                    
                    post_grid_rows = await self.page.query_selector_all('div._ac7v.xat24cr.x1f01sob.xcghwft.xzboxd6')
                    
                    if post_grid_rows:
                        logger.info(f"Found {len(post_grid_rows)} post grid rows")
                        
                        for row_index, row in enumerate(post_grid_rows):
                            row_posts = await row.query_selector_all('div.x1lliihq.x1n2onr6.xh8yej3.x4gyw5p.x14z9mp.xzj7kzq.xbipx2v.x1j53mea')
                            
                            for col_index, post_container in enumerate(row_posts):
                                post_link = await post_container.query_selector('a[href*="/p/"], a[href*="/reel/"]')
                                if post_link:
                                    post_url = await post_link.get_attribute('href')
                                    if post_url.startswith('/'):
                                        post_url = f"https://www.instagram.com{post_url}"
                                    
                                    all_post_links.append({
                                        'url': post_url,
                                        'container': post_container,
                                        'position': f"Row {row_index + 1}, Col {col_index + 1}"
                                    })
                            
                            if len(all_post_links) >= self.max_posts_to_check:
                                break
                        
                        logger.info(f"Collected {len(all_post_links)} posts in correct order")
                    else:
                        logger.warning("No post grid rows found, trying alternative approach")
                        
                        post_selectors = [
                            'a[href*="/p/"]',
                            'a[href*="/reel/"]'
                        ]
                        
                        for selector in post_selectors:
                            try:
                                found_posts = await self.page.query_selector_all(selector)
                                for post in found_posts[:self.max_posts_to_check]:
                                    post_url = await post.get_attribute('href')
                                    if post_url.startswith('/'):
                                        post_url = f"https://www.instagram.com{post_url}"
                                    all_post_links.append({
                                        'url': post_url,
                                        'container': None,
                                        'position': f"Alternative method #{len(all_post_links) + 1}"
                                    })
                                break
                            except:
                                continue
                    
                    if not all_post_links:
                        logger.warning(f"No posts found for {profile_url}")
                        if attempt < self.max_retries - 1:
                            await self.random_delay(3000, 6000)
                            continue
                        return None, [], "Time not determined"
                    
                    logger.info(f"Processing {min(len(all_post_links), self.max_posts_to_check)} posts in order")
                    
                    for i, post_info in enumerate(all_post_links[:self.max_posts_to_check]):
                        try:
                            logger.info(f"Checking post #{i+1} ({post_info['position']})")
                            
                            is_pinned = await self.is_post_pinned_from_grid(post_info['container'])
                            
                            if is_pinned:
                                logger.info(f"Post #{i+1} is PINNED (detected from grid) - SKIPPING to next post")
                                continue
                            
                            await self.page.goto(post_info['url'], wait_until="domcontentloaded")
                            await self.random_delay(3000, 5000)
                            
                            article_element = await self.page.query_selector('article')
                            is_pinned_individual = await self.is_post_pinned(article_element) if article_element else False
                            
                            if is_pinned_individual:
                                logger.info(f"Post #{i+1} is PINNED (detected from individual page) - SKIPPING to next post")
                                continue
                            
                            logger.info(f"Post #{i+1} is NOT pinned - checking time")
                            post_time = await self.extract_post_time()
                            logger.info(f"Post #{i+1} time: {post_time}")
                            
                            if self.is_post_within_24_hours(post_time):
                                logger.info(f"✅ Post #{i+1} is within 24 hours - extracting tags")
                                tagged_users = await self.extract_tagged_users()
                                
                                for user in tagged_users:
                                    if user not in self.profile_data:
                                        self.profile_data[user] = {
                                            'found_through': source_profile,
                                            'post_url': post_info['url'],
                                            'post_time': post_time,
                                            'data': None
                                        }
                                
                                logger.info(f"✅ Found {len(tagged_users)} tags in recent post - FINISHED")
                                return post_info['url'], tagged_users, post_time
                            else:
                                logger.info(f"❌ Post #{i+1} is older than 24 hours - STOP checking posts")
                                return None, [], "No recent posts found"
                            
                        except Exception as e:
                            logger.warning(f"Error processing post #{i+1}: {e}")
                            continue
                    
                    logger.warning(f"All {len(all_post_links)} posts checked, no valid posts found")
                    return None, [], "No valid posts found"
                    
                except Exception as e:
                    logger.error(f"Error finding posts structure: {e}")
                    if attempt < self.max_retries - 1:
                        await self.random_delay(3000, 6000)
                        continue
                    return None, [], "Error finding posts"
                    
            except Exception as e:
                logger.error(f"Error getting latest post for {profile_url} (attempt {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    await self.random_delay(3000, 6000)
        
        return None, [], "Time not determined"

    async def collect_and_save_profile_data_realtime(self, usernames):
        logger.info(f"🔄 Collecting and saving data for {len(usernames)} profiles in real-time...")
        
        for i, username in enumerate(usernames):
            try:
                logger.info(f"[{i+1}/{len(usernames)}] Processing profile @{username}...")
                
                if i > 0:
                    pause_time = random.randint(3, 7)
                    logger.info(f"Waiting {pause_time} seconds before next profile...")
                    await asyncio.sleep(pause_time)
                
                await self.refresh_session_aggressively()
                
                profile_data = await self.extract_profile_data(username)
                
                if username in self.profile_data:
                    profile_data.found_through = self.profile_data[username]['found_through']
                    self.profile_data[username]['data'] = profile_data
                else:
                    profile_data.found_through = "Direct"
                    self.profile_data[username] = {
                        'found_through': "Direct",
                        'post_url': "",
                        'post_time': "Not available",
                        'data': profile_data
                    }
                
                success = self.sheets_manager.save_single_profile(username, self.profile_data[username])
                
                if success:
                    logger.info(f"✅ Profile @{username} saved successfully!")
                else:
                    logger.error(f"❌ Failed to save profile @{username}")
                
            except Exception as e:
                logger.error(f"Error collecting profile data for @{username}: {e}")
                continue

    async def daily_monitoring_cycle(self):
        max_attempts = 3
        attempt = 0
        
        while attempt < max_attempts:
            try:
                attempt += 1
                logger.info(f"🔄 Daily monitoring cycle attempt {attempt}/{max_attempts}")
                
                if not self.check_daily_run_allowed():
                    logger.info("Daily run already completed today. Skipping.")
                    return True
                
                current_date = datetime.now().strftime("%d.%m.%Y")
                logger.info(f"=" * 80)
                logger.info(f"STARTING DAILY MONITORING CYCLE - {current_date}")
                logger.info(f"=" * 80)
                
                sheet_result = self.sheets_manager.initialize_weekly_sheet(self.sheet_id, current_date)
                
                if not sheet_result:
                    logger.error("❌ Failed to initialize weekly sheet!")
                    if attempt < max_attempts:
                        logger.info(f"Waiting 10 minutes before retry...")
                        await asyncio.sleep(600)
                        continue
                    return False
                
                current_date_obj = datetime.strptime(current_date, "%d.%m.%Y")
                if current_date_obj.weekday() == 0:
                    logger.info(f"✅ Today is Monday - using weekly sheet: {sheet_result['worksheet']}")
                else:
                    logger.info(f"✅ Continuing with weekly sheet: {sheet_result['worksheet']}")
                
                logger.info(f"📊 Sheet URL: {sheet_result['url']}")
                
                if not await self.start_browser():
                    logger.error("Failed to start browser")
                    if attempt < max_attempts:
                        logger.info(f"Waiting 10 minutes before retry...")
                        await asyncio.sleep(600)
                        continue
                    return False
                
                try:
                    session_loaded = await self.load_session()
                    
                    if session_loaded:
                        login_status = await self.check_login_status()
                        if not login_status:
                            session_loaded = False
                    
                    if not session_loaded:
                        if not self.check_login_cooldown():
                            logger.error("Login cooldown active. Cannot proceed.")
                            if attempt < max_attempts:
                                logger.info(f"Waiting 10 minutes before retry...")
                                await asyncio.sleep(600)
                                continue
                            return False
                        
                        success = await self.login()
                        if not success:
                            logger.error("❌ Login failed!")
                            if attempt < max_attempts:
                                logger.info(f"Waiting 10 minutes before retry...")
                                await asyncio.sleep(600)
                                continue
                            return False
                    
                    logger.info("✅ Login confirmed - Starting daily monitoring...")
                    
                    all_found_users = set()
                    processed_profiles = 0
                    
                    for i, profile in enumerate(self.profiles_list):
                        try:
                            processed_profiles += 1
                            logger.info(f"\n🔄 [{processed_profiles}/{len(self.profiles_list)}] Processing profile: {profile}")
                            
                            if i > 0:
                                pause_time = random.randint(5, 10)
                                logger.info(f"Waiting {pause_time} seconds before next profile...")
                                await asyncio.sleep(pause_time)
                            
                            await self.refresh_session_aggressively()
                            
                            if not profile.startswith('http'):
                                if profile.startswith('@'):
                                    profile_name = profile[1:]
                                else:
                                    profile_name = profile.split('/')[-1]
                                profile_url = f"https://www.instagram.com/{profile_name}/"
                            else:
                                profile_url = profile
                                profile_name = profile.split('/')[-2] if profile.endswith('/') else profile.split('/')[-1]
                            
                            logger.info(f"📝 Scraping posts for @{profile_name}...")
                            post_url, tagged_users, post_time = await self.get_latest_non_pinned_post(profile_url, f"@{profile_name}")
                            
                            logger.info(f"📖 Scraping stories for @{profile_name}...")
                            stories_users = []
                            try:
                                stories_users = await self.get_stories_tags(profile_url, f"@{profile_name}")
                                if stories_users:
                                    logger.info(f"Found {len(stories_users)} users in stories")
                                else:
                                    logger.info("No users found in stories")
                            except Exception as e:
                                logger.warning(f"Error scraping stories for @{profile_name}: {e}")
                                stories_users = []
                            
                            all_users_from_profile = list(set(tagged_users + stories_users))
                            
                            if all_users_from_profile:
                                all_found_users.update(all_users_from_profile)
                                
                                logger.info(f"📊 Profile: {profile}")
                                logger.info(f"   Latest post: {post_url}")
                                logger.info(f"   Post time: {post_time}")
                                logger.info(f"   Post tags: {tagged_users}")
                                logger.info(f"   Stories tags: {stories_users}")
                                logger.info(f"   Total unique users: {len(all_users_from_profile)}")
                                
                                logger.info(f"🔄 Collecting and saving profile data for {len(all_users_from_profile)} users...")
                                await self.collect_and_save_profile_data_realtime(all_users_from_profile)
                                
                                logger.info(f"✅ Profile {profile} completed - {len(all_users_from_profile)} users saved!")
                            else:
                                logger.warning(f"❌ Profile: {profile} - No tags found")
                            
                            logger.info("-" * 60)
                            
                        except Exception as e:
                            logger.error(f"Error processing profile {profile}: {e}")
                            continue
                    
                    logger.info("\n" + "="*80)
                    logger.info(f"DAILY MONITORING COMPLETED - {current_date}")
                    logger.info("="*80)
                    
                    logger.info(f"📊 Google Sheets URL: {sheet_result['url']}")
                    logger.info(f"📋 Total unique users processed: {len(all_found_users)}")
                    logger.info(f"📅 Date: {current_date}")
                    logger.info(f"⏰ Completed at: {datetime.now().strftime('%H:%M:%S')}")
                    
                    if all_found_users:
                        total_followers = sum([info['data'].followers_count for info in self.profile_data.values() if info.get('data')])
                        avg_followers = total_followers / len(self.profile_data) if self.profile_data else 0
                        
                        post_users = len([info for info in self.profile_data.values() if info.get('data') and info['data'].source_type == 'post'])
                        stories_users = len([info for info in self.profile_data.values() if info.get('data') and info['data'].source_type == 'stories'])
                        
                        logger.info(f"📈 STATISTICS:")
                        logger.info(f"   • Total profiles processed: {len(all_found_users)}")
                        logger.info(f"   • From posts: {post_users}")
                        logger.info(f"   • From stories: {stories_users}")
                        logger.info(f"   • Total followers: {total_followers:,}")
                        logger.info(f"   • Average followers: {avg_followers:,.0f}")
                    
                    current_date_obj = datetime.strptime(current_date, "%d.%m.%Y")
                    if current_date_obj.weekday() == 0:
                        logger.info(f"🗓️ Today is Monday - Data saved to NEW weekly sheet")
                    else:
                        logger.info(f"🗓️ Data saved to CONTINUING weekly sheet")
                    
                    logger.info(f"✅ Daily cycle completed successfully!")
                    logger.info(f"💤 System will wait until tomorrow {self.schedule_time} for next cycle")
                    
                    self.save_daily_run()
                    self.profile_data.clear()
                    
                    return True
                    
                finally:
                    await self.close_browser()
                
            except Exception as e:
                logger.error(f"Error in daily monitoring cycle (attempt {attempt}): {e}")
                if attempt < max_attempts:
                    logger.info(f"Waiting 10 minutes before retry...")
                    await asyncio.sleep(600)
                    continue
                return False
        
        logger.error(f"All {max_attempts} attempts failed for daily monitoring cycle")
        return False

    def get_next_run_time(self):
        now = datetime.now()
        hour, minute = map(int, self.schedule_time.split(':'))
        next_run = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        
        if now.hour > hour or (now.hour == hour and now.minute >= minute):
            next_run += timedelta(days=1)
        
        return next_run

    def time_until_next_run(self):
        next_run = self.get_next_run_time()
        now = datetime.now()
        return next_run - now

    def schedule_monitoring(self):
        def run_monitoring():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self.daily_monitoring_cycle())
                loop.close()
                logger.info("✅ Daily monitoring cycle completed!")
                logger.info(f"💤 Waiting for next day at {self.schedule_time}...")
            except Exception as e:
                logger.error(f"Error in scheduled monitoring: {e}")
        
        schedule.every().day.at(self.schedule_time).do(run_monitoring)
        logger.info(f"📅 Monitoring scheduled to run daily at {self.schedule_time}")
        
        return run_monitoring

    async def start_monitoring_system(self):
        logger.info("🚀 INSTAGRAM WEEKLY MONITORING SYSTEM STARTED")
        logger.info("=" * 80)
        logger.info(f"📊 Sheet ID: {self.sheet_id}")
        logger.info(f"👥 Profiles to monitor: {len(self.profiles_list)}")
        logger.info(f"⏰ Schedule: Daily at {self.schedule_time}")
        logger.info(f"📅 Weekly worksheets (Monday to Sunday)")
        logger.info(f"🔄 Auto-recovery enabled with 3 retry attempts")
        logger.info(f"⏱️ 10-minute cooldown between failed attempts")
        logger.info("=" * 80)
        
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")
        hour, minute = map(int, self.schedule_time.split(':'))
        
        if now.hour < hour or (now.hour == hour and now.minute < minute):
            logger.info(f"🕐 Current time: {current_time}")
            logger.info(f"🔄 Running immediate monitoring cycle (before {self.schedule_time})...")
            await self.daily_monitoring_cycle()
            logger.info("✅ Initial cycle completed!")
        else:
            logger.info(f"🕐 Current time: {current_time}")
            logger.info(f"⏰ It's past {self.schedule_time}, will wait for tomorrow's cycle")
        
        run_monitoring = self.schedule_monitoring()
        
        logger.info("⏰ Starting daily scheduler...")
        while self.monitoring_active:
            try:
                schedule.run_pending()
                
                time_until_next = self.time_until_next_run()
                hours = int(time_until_next.total_seconds() // 3600)
                minutes = int((time_until_next.total_seconds() % 3600) // 60)
                
                if hours > 0 or minutes > 0:
                    logger.info(f"⏳ Next monitoring cycle in: {hours}h {minutes}m")
                
                await asyncio.sleep(1800)
                
            except KeyboardInterrupt:
                logger.info("🛑 Monitoring system stopped by user")
                self.monitoring_active = False
                break
            except Exception as e:
                logger.error(f"Error in monitoring system: {e}")
                logger.info("🔄 System will auto-recover in 5 minutes...")
                await asyncio.sleep(300)
        
        logger.info("🏁 Monitoring system stopped")

async def main():
    CONFIG = {
        'username': "boburjon5931",
        'password': "Doston0210####____",
        'sheet_id': "1WCmFLdioC-mm_QtWdA3qNo_sEdEHZ3HTyCdqCaz_2MA",
        'credentials_file': "credentials.json",
        'schedule_time': "17:20",
        'profiles_list': [

##
##            
##            "https://instagram.com/MarcelaVelozo",
##            "https://instagram.com/IsabelleMathersx",
##            "https://instagram.com/CallanJensen",
##            "https://instagram.com/ElleTrowbridge",
##            "https://instagram.com/ErgiBardhollari",
##            "https://instagram.com/JoseArnolds",
##            "https://instagram.com/LenaPerminova",
##            "https://instagram.com/LeneVoigt",
##            "https://instagram.com/MashaDerevianko",
##            "https://instagram.com/NanniIrene",
##            "https://instagram.com/RavilaNogueira",
##            "https://instagram.com/VictoriaTurnerr",
##            "https://instagram.com/Whitney_Thornqvist",
##            "https://instagram.com/AliceMarconcinii",
##            "https://instagram.com/AriadnaFigueras",
##            "https://instagram.com/Aylbhr",
##            "https://instagram.com/CaraCoc0",
##            "https://instagram.com/CarlotaEnsenat",
##            "https://instagram.com/CaroGuido",
##            "https://instagram.com/CaseyJamess_",
##            "https://instagram.com/CathlinUlrichsen",
##            "https://instagram.com/ClarissaSirica",
##            "https://instagram.com/CorinneAndrich",
##            "https://instagram.com/DaniWashington_",
##            "https://instagram.com/DianaGali_",
##            "https://instagram.com/Elisa_Matata",
##            "https://instagram.com/Eliza.Musial",
##            "https://instagram.com/ElsaMagnelli",
##            "https://instagram.com/GabriellaVignoni",
##            "https://instagram.com/Gizawiza",
##            "https://instagram.com/HaileyAnnHildenBrand",
##            "https://instagram.com/Hoxha_Aurela",
##            "https://instagram.com/Julianne.Steege",
##            "https://instagram.com/JulieRodrigo_",
##            "https://instagram.com/KristinaPeric26",
##            "https://instagram.com/Ksyander",
##            "https://instagram.com/Lenniiez",
##            "https://instagram.com/LorenaPeach",
##            "https://instagram.com/NaamaPasswell",
##            "https://instagram.com/Nellie.brl",
##            "https://instagram.com/PolinaMalinovskaya",
##            "https://instagram.com/RuslanaGee",
##            "https://instagram.com/Shanaeden_",
##            "https://instagram.com/SosoWave",
##            "https://instagram.com/TaraBakalian",
##            "https://instagram.com/ValentinaRueda.V",
##            "https://instagram.com/_Shangina",
##            "https://instagram.com/_Taladar",
##            "https://instagram.com/Aaliyah.Harmuth",
##            "https://instagram.com/AlexisFabie",
##            "https://instagram.com/AlinaChorba",
##            "https://instagram.com/AlliMartinez",
##            "https://instagram.com/AmandaBertho",
##            "https://instagram.com/AngelaKajo",
##            "https://instagram.com/AntoniaPruy",
##            "https://instagram.com/AshleyMarieDickerson",
##            "https://instagram.com/AtlantaPitman",
##            "https://instagram.com/BamWarang",
##            "https://instagram.com/CarmellaRose",
##            "https://instagram.com/Chantal.Ka",
##            "https://instagram.com/ChristianaRobinson",
##            "https://instagram.com/CindyPrado",
##            "https://instagram.com/ErikaHausser",
##            "https://instagram.com/HeheJihee",
##            "https://instagram.com/Ira_Asllani",
##            "https://instagram.com/Irene_Miley_Hermes",
##            "https://instagram.com/JuliaMuniz",
##            "https://instagram.com/JuliePraderee",
##            "https://instagram.com/KlaraHellqvist",
##            "https://instagram.com/Ksenia_Tsaritsina",
##            "https://instagram.com/KTLordahl",
##            "https://instagram.com/LovisaFahraeus",
##            "https://instagram.com/MadeleineAndren",
##            "https://instagram.com/MarieLouNurk",
##            "https://instagram.com/Maya.Turmalina",
##            "https://instagram.com/Nathalya.Cabral",
##            "https://instagram.com/Nayazof",
##            "https://instagram.com/PolinaViaa",
##            "https://instagram.com/SoyRosa",
##            "https://instagram.com/StacyZozo",
##            "https://instagram.com/TalishaJanssen",
##            "https://instagram.com/TatianaPanakal",
##            "https://instagram.com/XimenaMoral",
##            "https://instagram.com/YourChernous",
##            "https://instagram.com/ZoeHoad",
##            "https://instagram.com/Alessandraa.Vo",
##            "https://instagram.com/AlexisBumgarner",
##            "https://instagram.com/Amalia_Strand",
##            "https://instagram.com/Anastasia.Sapri",
##            "https://instagram.com/AndyIshh",
##            "https://instagram.com/Angiedi__",
##            "https://instagram.com/AnkuAnku_",
##            "https://instagram.com/Antonia_Thalia",
            "https://instagram.com/Arabella.Ovenden",
            "https://instagram.com/ArtemidaRey",
            "https://instagram.com/Audrey.Ig",
            "https://instagram.com/BethanyMoore",
            "https://instagram.com/BrookSill",
            "https://instagram.com/CarlaMartin3z",
            "https://instagram.com/DevonChristenson",
            "https://instagram.com/EmilieKull",
            "https://instagram.com/IamDarrriii",
            "https://instagram.com/Ichelles",
            "https://instagram.com/IsabelRoca_",
            "https://instagram.com/JelenaMarkovic___",
            "https://instagram.com/JennLeezy",
            "https://instagram.com/JohannaKullenbergs",
            "https://instagram.com/Kgulinaa",
            "https://instagram.com/Khanhlyn__",
            "https://instagram.com/KnapekOliwia",
            "https://instagram.com/MaceyAnderson",
            "https://instagram.com/MaraLorenzon",
            "https://instagram.com/NoemieNeuens",
            "https://instagram.com/PaulaDiezC",
            "https://instagram.com/PiaRequejo",
            "https://instagram.com/ReneeMourad",
            "https://instagram.com/SophieRothschild",
            "https://instagram.com/TooonyToony",
            "https://instagram.com/Vchirinoooo",
            "https://instagram.com/xSophiaPriceyx",
            "https://instagram.com/Alessacaiser",
            "https://instagram.com/Aria_Kaiserr",
            "https://instagram.com/CharlieHaywardddd",
            "https://instagram.com/_Kkaiix",
            "https://instagram.com/AbrilRaluy",
            "https://instagram.com/AdeleGrisoni",
            "https://instagram.com/Adelka_dd",
            "https://instagram.com/Adrianahughes",
            "https://instagram.com/Aleksandrakirienko",
            "https://instagram.com/AlesiaNoka",
            "https://instagram.com/AleVidalModel",
            "https://instagram.com/AlexsashNicole",
            "https://instagram.com/AlieDavis_",
            "https://instagram.com/Alina_Enero",
            "https://instagram.com/AlymaHovlic",
            "https://instagram.com/AlyshaBandy_",
            "https://instagram.com/AlyshaCaballero",
            "https://instagram.com/AmeliaFerland",
            "https://instagram.com/AngelaCastellanoss",
            "https://instagram.com/AnnaFernandezzg",
            "https://instagram.com/AnniHaase",
            "https://instagram.com/Antonia.Grigore",
            "https://instagram.com/Auste_Mi",
            "https://instagram.com/BiancaTijiani",
            "https://instagram.com/BibiBoric",
            "https://instagram.com/BrooklynEve_",
            "https://instagram.com/CaitlinNorthLewis",
            "https://instagram.com/CamilleGmrs",
            "https://instagram.com/CarlotaBurch",
            "https://instagram.com/CarolinaCubasq",
            "https://instagram.com/CataShank",
            "https://instagram.com/ChanelMrt",
            "https://instagram.com/ChefitaCarollina",
            "https://instagram.com/Chelsea_Kendra",
            "https://instagram.com/Chikileva_Dasha",
            "https://instagram.com/Claudia.Sanchiz",
            "https://instagram.com/CourtneyMay1",
            "https://instagram.com/Darivo_",
            "https://instagram.com/dCopperMan",
            "https://instagram.com/DunyaNavabi",
            "https://instagram.com/Elisha__H",
            "https://instagram.com/EmmilyElizabethh",
            "https://instagram.com/Estasique_",
            "https://instagram.com/EstherVis",
            "https://instagram.com/EveMinaeva",
            "https://instagram.com/EvieMareee",
            "https://instagram.com/FebeAnn",
            "https://instagram.com/Gabby_Adrian",
            "https://instagram.com/GeorginaMazzeo",
            "https://instagram.com/GretaBuz",
            "https://instagram.com/Guadadia",
            "https://instagram.com/HannaWeig",
            "https://instagram.com/iMilenaIoanna",
            "https://instagram.com/IsabellaGarwood",
            "https://instagram.com/ItsLeticiaSoares",
            "https://instagram.com/JacqueLinax",
            "https://instagram.com/JulianaHerz",
            "https://instagram.com/Kate_Demianova",
            "https://instagram.com/Kate.Noize",
            "https://instagram.com/KathiiSchr",
            "https://instagram.com/Kathleen_Paton",
            "https://instagram.com/Kseny_Bambi",
            "https://instagram.com/Kyla.Shay",
            "https://instagram.com/Lara.Helmer",
            "https://instagram.com/LauraElizabethWoo",
            "https://instagram.com/Lauren.Sintes",
            "https://instagram.com/LeaLukek_",
            "https://instagram.com/Lena_HelenaBusch",
            "https://instagram.com/Malisiri",
            "https://instagram.com/MalloryPruitt",
            "https://instagram.com/MariFumiere",
            "https://instagram.com/MartaLopezAlamo",
            "https://instagram.com/Mmargo.Dimova",
            "https://instagram.com/Nathalie.Soul",
            "https://instagram.com/Nephtys_Laurent",
            "https://instagram.com/NoraVentriglia",
            "https://instagram.com/PatriciaPerezBlanco",
            "https://instagram.com/Paulina.Hops",
            "https://instagram.com/Schaassi",
            "https://instagram.com/SelinaAsici",
            "https://instagram.com/Shahanateagan",
            "https://instagram.com/ShanneVillaReal",
            "https://instagram.com/Shir.Levyy",
            "https://instagram.com/SohniAhmed",
            "https://instagram.com/StephMandich",
            "https://instagram.com/TamFrancesconi",
            "https://instagram.com/TaraGoddard_",
            "https://instagram.com/TheLifeofLibs",
            "https://instagram.com/TynRar",
            "https://instagram.com/ValerieBois",
            "https://instagram.com/Vicky.Schab",
            "https://instagram.com/VickyPalacio",
            "https://instagram.com/VictoriaBell___",
            "https://instagram.com/VictoriaSilvstedt",
            "https://instagram.com/Victoriya.Solo",
            "https://instagram.com/VirginiaSanhouse",
            "https://instagram.com/Withkro",
            "https://instagram.com/XeniaBelskaya",
            "https://instagram.com/ZoePastelle",
            "https://instagram.com/MartinasDamiani",
            "https://instagram.com/OneeValdez",
            "https://instagram.com/ShettyKavita_",
            "https://instagram.com/MaisieKateYoung",
            "https://instagram.com/Gritsenko.Ks",
            "https://instagram.com/StillaTonik",
            "https://instagram.com/ArletteeSchuur",
            "https://instagram.com/Im_Oksi",
            "https://instagram.com/Lilyverrecchia",
            "https://instagram.com/JagodaLetowska",
            "https://instagram.com/JeenVital",
            "https://instagram.com/Cmooann",
            "https://instagram.com/ImKrist",
            "https://instagram.com/Kscnia",
            "https://instagram.com/Antonina_Kosior",
            "https://instagram.com/EliseFaust",
            "https://instagram.com/Katou.Sam",
            "https://instagram.com/Harlee_Ann",
            "https://instagram.com/Kauri_Eddie",
            "https://instagram.com/K_Malpica",
            "https://instagram.com/TessJantschek",
            "https://instagram.com/KristenManu_",
            "https://instagram.com/TaraZoeWoltjes",
            "https://instagram.com/Kealani.V",
            "https://instagram.com/Universo.De.Storm",
            "https://instagram.com/Kukianna_",
            "https://instagram.com/Julia.Corb",
            "https://instagram.com/Jaque.Kravtchenko",
            "https://instagram.com/DuniaShagiwal",
            "https://instagram.com/Anastasija.Bychkovva",
            "https://instagram.com/Micacanale",
            "https://instagram.com/Krisgoman",
            "https://instagram.com/Nanvelyn",
            "https://instagram.com/Willow_Dayyy",
            "https://instagram.com/Lavinia_Andrich",
            "https://instagram.com/Marimarinique",
            "https://instagram.com/AveryMilan",
            "https://instagram.com/MariMiranda_br",
            "https://instagram.com/Mmmvita",
            "https://instagram.com/NicolaKinghorn",
            "https://instagram.com/PaulaRubinn",
            "https://instagram.com/NinacDavy",
            "https://instagram.com/SophieKoehrmann",
            "https://instagram.com/AnavFiguera",
            "https://instagram.com/Nastya_Bers",
            "https://instagram.com/SabrineWaitkus",
            "https://instagram.com/Saschalve",
            "https://instagram.com/NikkiMclennan.x",
            "https://instagram.com/Rebekah__Leah",
            "https://instagram.com/Scarlett.Mayer_",
            "https://instagram.com/GustyTea",
            "https://instagram.com/Z.Kotaeva",
            "https://instagram.com/Victoria_Witthinrich",
            "https://instagram.com/Mikelamikii",
            "https://instagram.com/ZhdanovaDiary",
            "https://instagram.com/MisseBeqiri",
            "https://instagram.com/Violetadeaqua",
            "https://instagram.com/AntoniaMilla_",
            "https://instagram.com/Chinny_Chinnyy",
            "https://instagram.com/DaryaMalevych",
            "https://instagram.com/_LilliSophia_",
            "https://instagram.com/Shoam_Bittonn",
            "https://instagram.com/YasminVerheijen",
            "https://instagram.com/RusanaBae",
            "https://instagram.com/LetaFranka",
            "https://instagram.com/TaliTepuke",
            "https://instagram.com/SerenaMorizio",
            "https://instagram.com/EdenRosen_",
            "https://instagram.com/TianaKristi",
            "https://instagram.com/JevtiicAleksandra",
            "https://instagram.com/MiquelaVos",
            "https://instagram.com/Valgasca",
            "https://instagram.com/Misshamino",
            "https://www.instagram.com/an_stasiia__",
            "https://www.instagram.com/dasha.ilyushchyts",
            "https://www.instagram.com/oliviagrivas",
            "https://www.instagram.com/liekevdhoorn",
            "https://www.instagram.com/natasjamadsen",
            "https://www.instagram.com/itsmelauraazevedo",
            "https://www.instagram.com/nerize___",
            "https://www.instagram.com/telmaxlouise",
            "https://www.instagram.com/kristenkiehnle",
            "https://www.instagram.com/nathaliaern",
            "https://www.instagram.com/moriyaalia",
            "https://www.instagram.com/georgiebluck",
            "https://www.instagram.com/stellamaaya",
            "https://www.instagram.com/viviengutmann",
            "https://www.instagram.com/sonyazoloeva",
            "https://www.instagram.com/Jenndupuy",
            "https://www.instagram.com/dinadenoire",
            "https://www.instagram.com/gabrielafloresb_",
            "https://www.instagram.com/hollie.ford",
            "https://www.instagram.com/jaravalbracht",
            "https://www.instagram.com/jordandaniels",
            "https://www.instagram.com/bellaeftene",
            "https://www.instagram.com/brookpower",
            "https://www.instagram.com/juliatrevino",
            "https://www.instagram.com/kaylakrlowsky",
            "https://www.instagram.com/kxrpova",
            "https://www.instagram.com/larissajeannew",
            "https://www.instagram.com/leahhalton",
            "https://www.instagram.com/maddiefrancessca",
            "https://www.instagram.com/maggierawlins",
            "https://www.instagram.com/lenteisabellahugen",
            "https://www.instagram.com/alougee",
            "https://www.instagram.com/annalisedemmler",
            "https://www.instagram.com/stellaluciadeopito",
            "https://www.instagram.com/azzurraconticchi",
            "https://www.instagram.com/cenitch",
            "https://www.instagram.com/bridgetsatterlee",
            "https://www.instagram.com/laubsd",
            "https://www.instagram.com/lisa",
            "https://www.instagram.com/loydicarrion",
            "https://www.instagram.com/frida_aasen",
            "https://www.instagram.com/jannaaaeeee",
            "https://www.instagram.com/daria.miko",
            "https://www.instagram.com/jacelyntantay",
            "https://www.instagram.com/justine_mora",
            "https://www.instagram.com/louisemmikkelsen",
            "https://www.instagram.com/lyna_com2000",
            "https://www.instagram.com/wallenbergchloe",
            "https://www.instagram.com/yesly",
            "https://www.instagram.com/emmaellingsenn",
            "https://www.instagram.com/evelyn_ys",
            "https://www.instagram.com/anagargur",
            "https://www.instagram.com/carolinenavarroo",
            "https://www.instagram.com/cath3rina",
            "https://www.instagram.com/aneliamoor",
            "https://www.instagram.com/anikaehartje",
            "https://www.instagram.com/annette__kov",
            "https://www.instagram.com/ashley_moore_",
            "https://www.instagram.com/ashleysthompsonn",
            "https://www.instagram.com/axaxaaxaaxaa",
            "https://www.instagram.com/becamichie",
            "https://www.instagram.com/chloeambersheppard",
            "https://www.instagram.com/chane_husselmann",
            "https://www.instagram.com/ceceldn",
            "https://www.instagram.com/edenhoogveld",
            "https://www.instagram.com/dianasvrdv",
            "https://www.instagram.com/corneliazeile",
            "https://www.instagram.com/ellawex",
            "https://www.instagram.com/camillehulspas",
            "https://www.instagram.com/catnorris_",
            "https://www.instagram.com/elllielyon",
            "https://www.instagram.com/dakotaalvaa",
            "https://www.instagram.com/daniella.ford",
            "https://www.instagram.com/ceciliabooo",
            "https://www.instagram.com/chloehock",
            "https://www.instagram.com/brinley.steen",
            "https://www.instagram.com/brittanyjhamilton",
            "https://www.instagram.com/candyshepstone",
            "https://www.instagram.com/carolinaa_azevedo",
            "https://www.instagram.com/chloecxmpbell",
            "https://www.instagram.com/daniitorresl",
            "https://www.instagram.com/andreaamaryw",
            "https://www.instagram.com/giizeleoliveira",
            "https://www.instagram.com/millieleer",
            "https://www.instagram.com/graciecarvalho",
            "https://www.instagram.com/marion.pascale",
            "https://www.instagram.com/shirinaalina",
            "https://www.instagram.com/matcha_cha",
            "https://www.instagram.com/yambenaharon",
            "https://www.instagram.com/noyamiller",
            "https://www.instagram.com/_evewinter",
            "https://www.instagram.com/meganblakeirwin",
            "https://www.instagram.com/juliaernst",
            "https://www.instagram.com/vasilinskiy",
            "https://www.instagram.com/un__ya",
            "https://www.instagram.com/katelynernst3",
            "https://www.instagram.com/khmidan_yara",
            "https://www.instagram.com/kkarlakirschner",
            "https://www.instagram.com/lolahansen_",
            "https://www.instagram.com/llawri",
            "https://www.instagram.com/madhulikasharmaa",
            "https://www.instagram.com/lydiabielen",
            "https://www.instagram.com/mia.ortizz",
            "https://www.instagram.com/nicky_fletch",
            "https://www.instagram.com/kathrynelizabethwatts",
            "https://www.instagram.com/naomi_koch",
            "https://www.instagram.com/hannaedwinson",
            "https://www.instagram.com/hannahkirkelie",
            "https://www.instagram.com/hollyymueller",
            "https://www.instagram.com/sharon__golds",
            "https://www.instagram.com/leaseelenmeyer",
            "https://www.instagram.com/i.m.4.n.i",
            "https://www.instagram.com/gara.arias",
            "https://www.instagram.com/jessica_thompson27",
            "https://www.instagram.com/sgaliagaia",
            "https://www.instagram.com/jeyrocher",
            "https://www.instagram.com/sofia.vokhmina",
            "https://www.instagram.com/marielouisewedel",
            "https://www.instagram.com/torinicolebass",
            "https://www.instagram.com/sonyastrz",
            "https://www.instagram.com/emkrama",
            "https://www.instagram.com/michellebagarra",
            "https://www.instagram.com/jenaya.okpalanze",
            "https://www.instagram.com/rileyrrrussell",
            "https://www.instagram.com/martaricc",
            "https://www.instagram.com/kiana.flanet",
            "https://www.instagram.com/icenisia",
            "https://www.instagram.com/valeria_pilaa",
            "https://www.instagram.com/juliaperesg",
            "https://www.instagram.com/roberta.george",
            "https://www.instagram.com/leilanieddie",
            "https://www.instagram.com/olivvintage",
            "https://www.instagram.com/eredemiel",
            "https://www.instagram.com/gaia_giovannetti",
            "https://www.instagram.com/gracieunited",
            "https://www.instagram.com/irynaa.oc",
            "https://www.instagram.com/joceywriter",
            "https://www.instagram.com/mathilde__petersen",
            "https://www.instagram.com/merav_idan",
            "https://www.instagram.com/nuriaoliu",
            "https://www.instagram.com/ninasofey",
            "https://www.instagram.com/rachelle_v_waardhuizen",
            "https://www.instagram.com/raybitancourt",
            "https://www.instagram.com/yasminxeniaa",
            "https://www.instagram.com/viechidiac",
            "https://www.instagram.com/melitasuicaaaa",
            "https://www.instagram.com/rileyminford",
            "https://www.instagram.com/sienna.sacco",
            "https://www.instagram.com/alba.martin.c",
            "https://www.instagram.com/andreea_papuc",
            "https://www.instagram.com/annagoryainova",
            "https://www.instagram.com/juliarilynn",
            "https://www.instagram.com/katrielmanapua",
            "https://www.instagram.com/kennidyhunter",
            "https://www.instagram.com/emma.kaitalin",
            "https://www.instagram.com/issiewood",
            "https://www.instagram.com/giuliasalvadero",
            "https://www.instagram.com/sydhaneyy",
            "https://www.instagram.com/thelumagrothe",
            "https://www.instagram.com/thylaneblondeau",
            "https://www.instagram.com/valeryalapidus",
            "https://www.instagram.com/yookatrin",
            "https://www.instagram.com/anjaleuenberger",
            "https://www.instagram.com/annabelnorthlewis",
            "https://www.instagram.com/bentleymescall",
            "https://www.instagram.com/biancafinch",
            "https://www.instagram.com/bonniehefren",
            "https://www.instagram.com/bregjeheinen",
            "https://www.instagram.com/brittanynoon",
            "https://www.instagram.com/brriannaanderson",
            "https://www.instagram.com/brunalirio",
            "https://www.instagram.com/carla_guetta",
            "https://www.instagram.com/carmenbruendler",
            "https://www.instagram.com/cassieamato",
            "https://www.instagram.com/cate.collins",
            "https://www.instagram.com/cecisorian",
            "https://www.instagram.com/chanelmargaux",
            "https://www.instagram.com/cherienesss",
            "https://www.instagram.com/chiarasampaio",
            "https://www.instagram.com/christinanadin",
            "https://www.instagram.com/cindymello",
            "https://www.instagram.com/danikapienaar",
            "https://www.instagram.com/daphnegroeneveld",
            "https://www.instagram.com/darlaclaire",
            "https://www.instagram.com/dominiquelissa",
            "https://www.instagram.com/dorinagegici",
            "https://www.instagram.com/emiliasilberg",
            "https://www.instagram.com/emily.feld",
            "https://www.instagram.com/evarankiin",
            "https://www.instagram.com/freyatidy",
            "https://www.instagram.com/gabbiesul",
            "https://www.instagram.com/gayeannehazlewood",
            "https://www.instagram.com/gracey_hodge",
            "https://www.instagram.com/haileyclauson",
            "https://www.instagram.com/hollyylim",
            "https://www.instagram.com/hopekelesis",
            "https://www.instagram.com/idazeile",
            "https://www.instagram.com/inkawilliams",
            "https://www.instagram.com/jelenesan",
            "https://www.instagram.com/juliananalu",
            "https://www.instagram.com/katarina.deme",
            "https://www.instagram.com/katrinamotes",
            "https://www.instagram.com/kelseymerritt",
            "https://www.instagram.com/lea_peillard",
            "https://www.instagram.com/leonanaomii",
            "https://www.instagram.com/liniikennedy",
            "https://www.instagram.com/liv_blais",
            "https://www.instagram.com/lorena",
            "https://www.instagram.com/lucybramani",
            "https://www.instagram.com/lunabijl",
            "https://www.instagram.com/magui_corceiro",
            "https://www.instagram.com/maralafontan",
            "https://www.instagram.com/mari.lederman",
            "https://www.instagram.com/maria_hrodrigues",
            "https://www.instagram.com/marie_teissonniere",
            "https://www.instagram.com/mauramaurer",
            "https://www.instagram.com/meeyadugied",
            "https://www.instagram.com/meredithmickelson",
            "https://www.instagram.com/milana.vino",
            "https://www.instagram.com/mishkasilva",
            "https://www.instagram.com/natalia_sirotina",
            "https://www.instagram.com/naya___lima",
            "https://www.instagram.com/ngc1961",
            "https://www.instagram.com/ninaagdal",
            "https://www.instagram.com/paris.stubberfield",
            "https://www.instagram.com/pdm.clara",
            "https://www.instagram.com/raerodriguez_",
            "https://www.instagram.com/reneeherbert_",
            "https://www.instagram.com/ritasmota",
            "https://www.instagram.com/scarlett",
            "https://www.instagram.com/siennaschmidt",
            "https://www.instagram.com/ssupr",
            "https://www.instagram.com/tinakunakey",
            "https://www.instagram.com/victoriabrono",
            "https://www.instagram.com/yasminwijnaldum",
            "https://www.instagram.com/Yoventura",
            "https://www.instagram.com/zaharaadavis",
            "https://www.instagram.com/zoeebarnard",
            "https://www.instagram.com/_gracemeredith_",
            "https://www.instagram.com/freyawalton",
            "https://www.instagram.com/nourgal",
            "https://www.instagram.com/paigemhenry",
            "https://www.instagram.com/oliviaedit",
            "https://www.instagram.com/oliviaacolangelo",
            "https://www.instagram.com/rebeccawicklin",
            "https://www.instagram.com/robinholzken",
            "https://www.instagram.com/ryserjannaya",
            "https://www.instagram.com/salsisalsa",
            "https://www.instagram.com/racheluzeta",
            "https://www.instagram.com/sarafjohansen",
            "https://www.instagram.com/savannahshaerichards",
            "https://www.instagram.com/shimmamarie",
            "https://www.instagram.com/sophia",
            "https://www.instagram.com/sophiachugranis",
            "https://www.instagram.com/zaraburfitt_",
            "https://www.instagram.com/lianesabag",
            "https://www.instagram.com/olivialinkk",
            "https://www.instagram.com/katarinapruim",
            "https://www.instagram.com/laurentsears",
            "https://www.instagram.com/roma.sh.ka",
            "https://www.instagram.com/zoey_cks",
            "https://www.instagram.com/lizamartynchik",
            "https://www.instagram.com/audreyanamichelle",
            "https://www.instagram.com/ilona__marion",
            "https://www.instagram.com/efrat_elmalich",
            "https://www.instagram.com/noemi.hewa",
            "https://www.instagram.com/keilanilizbeth",
            "https://www.instagram.com/itsannakryuchkova",
            "https://www.instagram.com/erinmichellexo",
            "https://www.instagram.com/kinseygolden",
            "https://www.instagram.com/blondiestraw",
            "https://www.instagram.com/cristianadf_",
            "https://www.instagram.com/maya.poon",
            "https://www.instagram.com/poppy_fava",
            "https://www.instagram.com/tamika_fawcett",
            "https://www.instagram.com/kiarakennedy_",
            "https://www.instagram.com/aly_686",
            "https://www.instagram.com/jime_madf",
            "https://www.instagram.com/victoriaperusheva",
            "https://www.instagram.com/amayaancr",
            "https://www.instagram.com/brittbergmeister",
            "https://www.instagram.com/anyuta_rai",
            "https://www.instagram.com/cdenisaaa",
            "https://www.instagram.com/alishagonsalves",
            "https://www.instagram.com/ashtonwood",
            "https://www.instagram.com/baemillya",
            "https://www.instagram.com/chiaramoreira",
            "https://www.instagram.com/kyla.malena",
            "https://www.instagram.com/Gabbyepstein",
            "https://www.instagram.com/ariarne_lepine",
            "https://www.instagram.com/ellacervetto",
            "https://www.instagram.com/nicola",
            "https://www.instagram.com/olivia.mathers",
            "https://www.instagram.com/saskiateje",
            "https://www.instagram.com/kateli",
            "https://www.instagram.com/bibzz.z",
            "https://www.instagram.com/anfisaibadova",
            "https://www.instagram.com/ellaayalon",
            "https://www.instagram.com/leidy.amelia",
            "https://www.instagram.com/__noabarak__",
            "https://www.instagram.com/aishakatherina",
            "https://www.instagram.com/alexandrafabiancsics",
            "https://www.instagram.com/alexleeaillon",
            "https://www.instagram.com/brooklynkellyy",
            "https://www.instagram.com/faithcharnock",
            "https://www.instagram.com/oliviaphillipps",
            "https://www.instagram.com/sahara_ray",
            "https://www.instagram.com/sullivang_",
            "https://www.instagram.com/valeriarudy",
            "https://www.instagram.com/lilyjeanbridger",
            "https://www.instagram.com/ainhoalarretxi",
            "https://www.instagram.com/_adrianacasas",
            "https://www.instagram.com/camijls",
            "https://www.instagram.com/mariachuykova",
            "https://www.instagram.com/theopisti_p",
            "https://www.instagram.com/mariariieraa",
            "https://www.instagram.com/alex_pletnyova",
            "https://www.instagram.com/barbara_ines",
            "https://www.instagram.com/claudiamartingt",
            "https://www.instagram.com/danielarangel.l",
            "https://www.instagram.com/ashley_graves",
            "https://www.instagram.com/claraalinnea",
            "https://www.instagram.com/emmyhallman",
            "https://www.instagram.com/lir.bareket",
            "https://www.instagram.com/elladieke",
            "https://www.instagram.com/danazanatwinsss",
            "https://www.instagram.com/martynabalsam",
            "https://www.instagram.com/lifeofjipp",
            "https://www.instagram.com/taylorjustine",
            "https://www.instagram.com/madisonmartina",
            "https://www.instagram.com/alexghantous",
            "https://www.instagram.com/cocolikristina",
            "https://www.instagram.com/yambogdini",
            "https://www.instagram.com/nevrohaloo",
            "https://www.instagram.com/tutipon",
            "https://www.instagram.com/mika_levyy",
            "https://www.instagram.com/giulialacalce",
            "https://www.instagram.com/sadieemckennaa",
            "https://www.instagram.com/smolenskayeva",
            "https://www.instagram.com/jessicamarvisi",
            "https://www.instagram.com/gracemonfries",
            "https://www.instagram.com/p_heliophilia",
            "https://www.instagram.com/liliaweddell",
            "https://www.instagram.com/natalylorenzo",
            "https://www.instagram.com/miaatorrees",
            "https://www.instagram.com/si_eliza",
            "https://www.instagram.com/maanuness",
            "https://www.instagram.com/janellecaruso_",
            "https://www.instagram.com/inezzvalencia",
            "https://www.instagram.com/pollinoma",
            "https://www.instagram.com/evvnavarro",
            "https://www.instagram.com/tssdaria",
            "https://www.instagram.com/tarahrodgers",
            "https://www.instagram.com/crystalbellotti",
            "https://www.instagram.com/julia_cavanagh",
            "https://www.instagram.com/vasilisa_melnikova_",
            "https://www.instagram.com/giorgia.malerba",
            "https://www.instagram.com/moaaberg",
            "https://www.instagram.com/mkaaloha",
            "https://www.instagram.com/bretaseduarda",
            "https://www.instagram.com/sierrajeh_",
            "https://www.instagram.com/paulatruiz",
            "https://www.instagram.com/kristina.petrochuk",
            "https://www.instagram.com/tashgalgut",
            "https://www.instagram.com/vszrwc",
            "https://www.instagram.com/kiaralouise.e",
            "https://www.instagram.com/zoeseverini",
            "https://www.instagram.com/delmivieira_b",
            "https://www.instagram.com/katelynbyrd",
            "https://www.instagram.com/chelsnamsayin",
            "https://www.instagram.com/maiacotton",
            "https://www.instagram.com/olalais",
            "https://www.instagram.com/olasosnierz",
            "https://www.instagram.com/bauvers",
            "https://www.instagram.com/fattie._.maddie",
            "https://www.instagram.com/_mandy8",
            "https://www.instagram.com/ka_puanani_tia",
            "https://www.instagram.com/ireneeraggi",
            "https://www.instagram.com/annalisachristiane",
            "https://www.instagram.com/samantharaynerx",
            "https://www.instagram.com/bbrontte",
            "https://www.instagram.com/keren_lavy",
            "https://www.instagram.com/michelle_algrabli",
            "https://www.instagram.com/annselasse",
            "https://www.instagram.com/moskaleva.sasha",
            "https://www.instagram.com/lauraoganessian",
            "https://www.instagram.com/elsa.ctr",
            "https://www.instagram.com/amy_chapmanxx",
            "https://www.instagram.com/kateridion",
            "https://www.instagram.com/guadadiagosti",
            "https://www.instagram.com/titigirlyy",
            "https://www.instagram.com/annam.og",
            "https://www.instagram.com/theresehoffhansen",
            "https://www.instagram.com/lenapanovikova",
            "https://www.instagram.com/janettwohlfromm",
            "https://www.instagram.com/jean_watts",
            "https://www.instagram.com/lupita.ader",
            "https://www.instagram.com/irashewolfnew",
            "https://www.instagram.com/nadialeecohen",
            "https://www.instagram.com/nanettesolivan",
            "https://www.instagram.com/linazhuravell",
            "https://www.instagram.com/manixbby",
            "https://www.instagram.com/syrienna",
            "https://www.instagram.com/mayisee",
            "https://www.instagram.com/ariannaosthoff",
            "https://www.instagram.com/abigailculver",
            "https://www.instagram.com/isabellaxweis",
            "https://www.instagram.com/nailamatata",
            "https://www.instagram.com/chiarabimbattii",
            "https://www.instagram.com/nicoletteking",
            "https://www.instagram.com/ssophiemccann",
            "https://www.instagram.com/hannahganttt",
            "https://www.instagram.com/micacanale",
            "https://www.instagram.com/amritapalahey",
            "https://www.instagram.com/jacquelinebazbaz",
            "https://www.instagram.com/clairecsslmn",
            "https://www.instagram.com/ianasavi_",
            "https://www.instagram.com/alexpekarkova",
            "https://www.instagram.com/misha.bertman",
            "https://www.instagram.com/anna.asister",
            "https://www.instagram.com/maeurnscameraroll",
            "https://www.instagram.com/anetmlcak0va",
            "https://www.instagram.com/marionautran",
            "https://www.instagram.com/luanakstl",
            "https://www.instagram.com/christinegischler"

        ]
    }
    
    logger.info("🎯 Instagram Weekly Monitoring System")
    logger.info(f"📊 Configured to monitor {len(CONFIG['profiles_list'])} profiles")
    logger.info(f"📋 Weekly data will be saved to Google Sheets")
    logger.info(f"🔄 Automatic weekly cycle monitoring")
    logger.info(f"⏰ Scheduled to run daily at {CONFIG['schedule_time']}")
    logger.info(f"🛡️ Enhanced error recovery and session management")
    logger.info(f"📅 New sheet created only on Mondays")
    
    monitoring_system = InstagramMonitoringSystem(
        username=CONFIG['username'],
        password=CONFIG['password'], 
        sheet_id=CONFIG['sheet_id'],
        profiles_list=CONFIG['profiles_list'],
        credentials_file=CONFIG['credentials_file'],
        schedule_time=CONFIG['schedule_time']
    )
    
    try:
        await monitoring_system.start_monitoring_system()
    except KeyboardInterrupt:
        logger.info("🛑 System stopped by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.info("🔄 System will attempt to restart...")

if __name__ == "__main__":
    asyncio.run(main())
