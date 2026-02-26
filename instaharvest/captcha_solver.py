"""
Instagram Scraper - Captcha Solver Integration

Auto-detect and solve CAPTCHAs using 2Captcha or Anti-Captcha services.
Integrates with Playwright pages for seamless captcha handling.

Usage:
    from instaharvest import CaptchaSolver

    solver = CaptchaSolver(
        api_key='YOUR_2CAPTCHA_API_KEY',
        provider='2captcha',
    )

    # Auto-detect and solve on any page
    if solver.detect_captcha(page):
        solver.solve(page)
"""

import time
import json
import base64
import logging
from typing import Optional, Dict, Any
from enum import Enum

try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

try:
    import requests as req_lib
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False

logger = logging.getLogger(__name__)


class CaptchaProvider(Enum):
    """Supported captcha solving providers"""
    TWO_CAPTCHA = "2captcha"
    ANTI_CAPTCHA = "anticaptcha"


class CaptchaSolver:
    """
    Professional CAPTCHA solver for Instagram scraping.

    Supports:
    - reCAPTCHA v2 (checkbox and invisible)
    - reCAPTCHA v3
    - Image-based CAPTCHAs
    - Instagram challenge verification

    Providers:
    - 2Captcha (twocaptcha.com)
    - Anti-Captcha (anti-captcha.com)

    Features:
    - Auto-detect CAPTCHA type on page
    - Seamless solving with callback injection
    - Balance checking
    - Configurable timeout and polling
    - Error handling with retries
    """

    # Provider API URLs
    PROVIDER_URLS = {
        CaptchaProvider.TWO_CAPTCHA: {
            'submit': 'https://2captcha.com/in.php',
            'result': 'https://2captcha.com/res.php',
            'balance': 'https://2captcha.com/res.php',
        },
        CaptchaProvider.ANTI_CAPTCHA: {
            'submit': 'https://api.anti-captcha.com/createTask',
            'result': 'https://api.anti-captcha.com/getTaskResult',
            'balance': 'https://api.anti-captcha.com/getBalance',
        },
    }

    # Instagram reCAPTCHA site keys (known)
    INSTAGRAM_SITE_KEYS = [
        '6Ld_LMAUAAAAALlB08IeNGG0SQWZJ_lTMqAf6edj',
        '6LcOf2cUAAAAADqkHtNpqmS3FDE7x2WRXF1fKKmq',
    ]

    def __init__(
        self,
        api_key: str = '',
        provider: str = '2captcha',
        timeout: int = 120,
        poll_interval: int = 5,
        logger: Optional[logging.Logger] = None,
    ):
        """
        Initialize CaptchaSolver.

        Args:
            api_key: API key from captcha service provider
            provider: '2captcha' or 'anticaptcha'
            timeout: Max seconds to wait for solution
            poll_interval: Seconds between polling for result
            logger: Optional logger
        """
        self.api_key = api_key
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.logger = logger or logging.getLogger(__name__)

        # Parse provider
        if provider in ('2captcha', 'twocaptcha'):
            self.provider = CaptchaProvider.TWO_CAPTCHA
        elif provider in ('anticaptcha', 'anti-captcha'):
            self.provider = CaptchaProvider.ANTI_CAPTCHA
        else:
            self.provider = CaptchaProvider.TWO_CAPTCHA

        self._urls = self.PROVIDER_URLS[self.provider]
        self._stats = {'solved': 0, 'failed': 0, 'balance': None}

    # ==================== Detection ====================

    def detect_captcha(self, page) -> bool:
        """
        Detect if a CAPTCHA is present on the page.

        Args:
            page: Playwright page object

        Returns:
            True if CAPTCHA detected
        """
        try:
            # Check for reCAPTCHA iframe
            recaptcha_selectors = [
                'iframe[src*="recaptcha"]',
                'iframe[src*="google.com/recaptcha"]',
                '#recaptcha',
                '.g-recaptcha',
                '[data-sitekey]',
            ]

            for selector in recaptcha_selectors:
                try:
                    el = page.locator(selector).first
                    if el.count() > 0:
                        self.logger.info(f"CAPTCHA detected: {selector}")
                        return True
                except Exception:
                    continue

            # Check for Instagram challenge
            challenge_selectors = [
                'form[action*="challenge"]',
                '#challenge',
                '[data-testid="challenge"]',
                'text="Verify"',
            ]

            for selector in challenge_selectors:
                try:
                    el = page.locator(selector).first
                    if el.count() > 0:
                        self.logger.info(f"Instagram challenge detected: {selector}")
                        return True
                except Exception:
                    continue

            # Check page URL
            url = page.url
            if 'challenge' in url or 'captcha' in url:
                self.logger.info(f"CAPTCHA URL detected: {url}")
                return True

        except Exception as e:
            self.logger.debug(f"Detection error: {e}")

        return False

    # ==================== Solving ====================

    def solve(self, page) -> bool:
        """
        Auto-detect and solve CAPTCHA on page.

        Args:
            page: Playwright page object

        Returns:
            True if solved successfully
        """
        if not self.api_key:
            self.logger.error("No API key configured for captcha solver")
            return False

        try:
            # Try reCAPTCHA first
            site_key = self._get_site_key(page)
            if site_key:
                return self.solve_recaptcha(site_key, page.url, page)

            # Try image captcha
            captcha_img = self._get_captcha_image(page)
            if captcha_img:
                return self.solve_image_captcha(captcha_img, page)

            self.logger.warning("CAPTCHA detected but type unknown")
            return False

        except Exception as e:
            self.logger.error(f"Solve failed: {e}")
            self._stats['failed'] += 1
            return False

    def solve_recaptcha(
        self,
        site_key: str,
        page_url: str,
        page=None,
    ) -> bool:
        """
        Solve reCAPTCHA v2/v3.

        Args:
            site_key: Google reCAPTCHA site key
            page_url: URL of the page with captcha
            page: Playwright page (for injecting response)

        Returns:
            True if solved
        """
        self.logger.info(f"Solving reCAPTCHA: site_key={site_key[:20]}...")

        if self.provider == CaptchaProvider.TWO_CAPTCHA:
            return self._solve_recaptcha_2captcha(site_key, page_url, page)
        else:
            return self._solve_recaptcha_anticaptcha(site_key, page_url, page)

    def solve_image_captcha(self, image_base64: str, page=None) -> bool:
        """
        Solve image-based CAPTCHA.

        Args:
            image_base64: Base64-encoded captcha image
            page: Playwright page (for inputting answer)

        Returns:
            True if solved
        """
        self.logger.info("Solving image CAPTCHA...")

        if self.provider == CaptchaProvider.TWO_CAPTCHA:
            return self._solve_image_2captcha(image_base64, page)
        else:
            return self._solve_image_anticaptcha(image_base64, page)

    # ==================== 2Captcha Implementation ====================

    def _solve_recaptcha_2captcha(self, site_key: str, page_url: str, page) -> bool:
        """Solve reCAPTCHA using 2Captcha API"""
        try:
            # Submit task
            submit_data = {
                'key': self.api_key,
                'method': 'userrecaptcha',
                'googlekey': site_key,
                'pageurl': page_url,
                'json': 1,
            }

            resp = self._http_post(self._urls['submit'], data=submit_data)
            if not resp or resp.get('status') != 1:
                self.logger.error(f"2Captcha submit failed: {resp}")
                return False

            task_id = resp.get('request')
            self.logger.info(f"2Captcha task submitted: {task_id}")

            # Poll for result
            token = self._poll_2captcha(task_id)
            if not token:
                return False

            # Inject solution
            if page:
                self._inject_recaptcha_token(page, token)

            self._stats['solved'] += 1
            self.logger.info("reCAPTCHA solved successfully!")
            return True

        except Exception as e:
            self.logger.error(f"2Captcha reCAPTCHA error: {e}")
            self._stats['failed'] += 1
            return False

    def _poll_2captcha(self, task_id: str) -> Optional[str]:
        """Poll 2Captcha for result"""
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            time.sleep(self.poll_interval)

            result_data = {
                'key': self.api_key,
                'action': 'get',
                'id': task_id,
                'json': 1,
            }

            resp = self._http_get(self._urls['result'], params=result_data)

            if resp and resp.get('status') == 1:
                return resp.get('request')

            if resp and resp.get('request') == 'CAPCHA_NOT_READY':
                self.logger.debug("Waiting for solution...")
                continue

            if resp and 'ERROR' in str(resp.get('request', '')):
                self.logger.error(f"2Captcha error: {resp}")
                return None

        self.logger.error("2Captcha timeout")
        return None

    def _solve_image_2captcha(self, image_b64: str, page) -> bool:
        """Solve image CAPTCHA using 2Captcha"""
        try:
            submit_data = {
                'key': self.api_key,
                'method': 'base64',
                'body': image_b64,
                'json': 1,
            }

            resp = self._http_post(self._urls['submit'], data=submit_data)
            if not resp or resp.get('status') != 1:
                return False

            task_id = resp.get('request')
            answer = self._poll_2captcha(task_id)

            if answer and page:
                self._input_captcha_answer(page, answer)
                self._stats['solved'] += 1
                return True

            return False

        except Exception as e:
            self.logger.error(f"2Captcha image error: {e}")
            return False

    # ==================== Anti-Captcha Implementation ====================

    def _solve_recaptcha_anticaptcha(self, site_key: str, page_url: str, page) -> bool:
        """Solve reCAPTCHA using Anti-Captcha API"""
        try:
            payload = {
                'clientKey': self.api_key,
                'task': {
                    'type': 'RecaptchaV2TaskProxyless',
                    'websiteURL': page_url,
                    'websiteKey': site_key,
                },
            }

            resp = self._http_post(self._urls['submit'], json_data=payload)
            if not resp or resp.get('errorId', 1) != 0:
                self.logger.error(f"Anti-Captcha submit failed: {resp}")
                return False

            task_id = resp.get('taskId')
            token = self._poll_anticaptcha(task_id)

            if token and page:
                self._inject_recaptcha_token(page, token)
                self._stats['solved'] += 1
                return True

            return False

        except Exception as e:
            self.logger.error(f"Anti-Captcha error: {e}")
            return False

    def _poll_anticaptcha(self, task_id) -> Optional[str]:
        """Poll Anti-Captcha for result"""
        start_time = time.time()

        while time.time() - start_time < self.timeout:
            time.sleep(self.poll_interval)

            payload = {
                'clientKey': self.api_key,
                'taskId': task_id,
            }

            resp = self._http_post(self._urls['result'], json_data=payload)

            if resp and resp.get('status') == 'ready':
                return resp.get('solution', {}).get('gRecaptchaResponse')

            if resp and resp.get('status') == 'processing':
                continue

            if resp and resp.get('errorId', 0) != 0:
                self.logger.error(f"Anti-Captcha error: {resp}")
                return None

        self.logger.error("Anti-Captcha timeout")
        return None

    def _solve_image_anticaptcha(self, image_b64: str, page) -> bool:
        """Solve image CAPTCHA using Anti-Captcha"""
        try:
            payload = {
                'clientKey': self.api_key,
                'task': {
                    'type': 'ImageToTextTask',
                    'body': image_b64,
                },
            }

            resp = self._http_post(self._urls['submit'], json_data=payload)
            if not resp or resp.get('errorId', 1) != 0:
                return False

            task_id = resp.get('taskId')
            start_time = time.time()

            while time.time() - start_time < self.timeout:
                time.sleep(self.poll_interval)
                poll_resp = self._http_post(
                    self._urls['result'],
                    json_data={'clientKey': self.api_key, 'taskId': task_id}
                )
                if poll_resp and poll_resp.get('status') == 'ready':
                    answer = poll_resp.get('solution', {}).get('text')
                    if answer and page:
                        self._input_captcha_answer(page, answer)
                        self._stats['solved'] += 1
                        return True

            return False

        except Exception as e:
            self.logger.error(f"Anti-Captcha image error: {e}")
            return False

    # ==================== Balance ====================

    def get_balance(self) -> Optional[float]:
        """Check account balance"""
        try:
            if self.provider == CaptchaProvider.TWO_CAPTCHA:
                resp = self._http_get(
                    self._urls['balance'],
                    params={'key': self.api_key, 'action': 'getbalance', 'json': 1}
                )
                if resp and resp.get('status') == 1:
                    balance = float(resp.get('request', 0))
                    self._stats['balance'] = balance
                    return balance

            elif self.provider == CaptchaProvider.ANTI_CAPTCHA:
                resp = self._http_post(
                    self._urls['balance'],
                    json_data={'clientKey': self.api_key}
                )
                if resp and resp.get('errorId') == 0:
                    balance = float(resp.get('balance', 0))
                    self._stats['balance'] = balance
                    return balance

        except Exception as e:
            self.logger.error(f"Balance check failed: {e}")

        return None

    # ==================== Page Helpers ====================

    def _get_site_key(self, page) -> Optional[str]:
        """Extract reCAPTCHA site key from page"""
        try:
            # Check data-sitekey attribute
            el = page.locator('[data-sitekey]').first
            if el.count() > 0:
                key = el.get_attribute('data-sitekey')
                if key:
                    return key

            # Check iframe src
            iframe = page.locator('iframe[src*="recaptcha"]').first
            if iframe.count() > 0:
                src = iframe.get_attribute('src') or ''
                if 'k=' in src:
                    key = src.split('k=')[1].split('&')[0]
                    return key

            # Use known Instagram keys
            for key in self.INSTAGRAM_SITE_KEYS:
                return key  # Return first known key

        except Exception:
            pass
        return None

    def _get_captcha_image(self, page) -> Optional[str]:
        """Extract captcha image as base64"""
        try:
            img_selectors = [
                'img[alt*="captcha"]',
                'img.captcha',
                '#captcha_image',
            ]
            for selector in img_selectors:
                el = page.locator(selector).first
                if el.count() > 0:
                    # Screenshot the element
                    screenshot = el.screenshot()
                    return base64.b64encode(screenshot).decode('utf-8')
        except Exception:
            pass
        return None

    def _inject_recaptcha_token(self, page, token: str) -> None:
        """Inject reCAPTCHA solution token into the page"""
        try:
            page.evaluate(f"""
                () => {{
                    // Set textarea
                    const textarea = document.getElementById('g-recaptcha-response');
                    if (textarea) {{
                        textarea.value = '{token}';
                        textarea.style.display = 'block';
                    }}

                    // Also try all textareas
                    document.querySelectorAll('textarea[name="g-recaptcha-response"]').forEach(el => {{
                        el.value = '{token}';
                    }});

                    // Call callback if available
                    if (typeof ___grecaptcha_cfg !== 'undefined') {{
                        try {{
                            Object.keys(___grecaptcha_cfg.clients).forEach(key => {{
                                const client = ___grecaptcha_cfg.clients[key];
                                if (client) {{
                                    Object.keys(client).forEach(k => {{
                                        const val = client[k];
                                        if (val && val.callback) val.callback('{token}');
                                    }});
                                }}
                            }});
                        }} catch(e) {{}}
                    }}
                }}
            """)
            time.sleep(1.0)
            self.logger.info("reCAPTCHA token injected")
        except Exception as e:
            self.logger.error(f"Token injection failed: {e}")

    def _input_captcha_answer(self, page, answer: str) -> None:
        """Input image captcha answer"""
        try:
            input_selectors = [
                'input[name*="captcha"]',
                'input#captcha',
                'input[placeholder*="captcha"]',
            ]
            for selector in input_selectors:
                el = page.locator(selector).first
                if el.count() > 0:
                    el.fill(answer)
                    time.sleep(0.5)
                    # Submit
                    page.keyboard.press('Enter')
                    time.sleep(2.0)
                    return
        except Exception as e:
            self.logger.error(f"Answer input failed: {e}")

    # ==================== HTTP Helpers ====================

    def _http_get(self, url: str, params: Dict = None) -> Optional[Dict]:
        """Make HTTP GET request"""
        try:
            if HAS_HTTPX:
                r = httpx.get(url, params=params, timeout=30)
                return r.json()
            elif HAS_REQUESTS:
                r = req_lib.get(url, params=params, timeout=30)
                return r.json()
        except Exception as e:
            self.logger.debug(f"HTTP GET error: {e}")
        return None

    def _http_post(self, url: str, data: Dict = None, json_data: Dict = None) -> Optional[Dict]:
        """Make HTTP POST request"""
        try:
            if HAS_HTTPX:
                if json_data:
                    r = httpx.post(url, json=json_data, timeout=30)
                else:
                    r = httpx.post(url, data=data, timeout=30)
                return r.json()
            elif HAS_REQUESTS:
                if json_data:
                    r = req_lib.post(url, json=json_data, timeout=30)
                else:
                    r = req_lib.post(url, data=data, timeout=30)
                return r.json()
        except Exception as e:
            self.logger.debug(f"HTTP POST error: {e}")
        return None

    # ==================== Stats ====================

    @property
    def stats(self) -> Dict[str, Any]:
        return {
            'provider': self.provider.value,
            'solved': self._stats['solved'],
            'failed': self._stats['failed'],
            'balance': self._stats['balance'],
        }
