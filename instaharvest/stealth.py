"""
Instagram Scraper - Stealth Mode Module
Anti-Detection and Human Behavior Simulation

This module provides comprehensive anti-bot detection measures:
- playwright-stealth integration
- Custom anti-detection script injection
- Human-like mouse movement (Bezier curves)
- Human-like typing with variable speed
- Fingerprint masking (WebGL, Canvas, Audio)
- Random delay variance
"""

import random
import time
import math
from typing import Optional, List, Tuple, TYPE_CHECKING
from dataclasses import dataclass
import logging

if TYPE_CHECKING:
    from playwright.sync_api import Page, BrowserContext
    from .config import ScraperConfig


@dataclass
class MousePoint:
    """Represents a point in mouse movement path"""
    x: float
    y: float


class StealthManager:
    """
    Central manager for all anti-detection and stealth operations.
    
    Features:
    - Applies playwright-stealth patches
    - Injects custom anti-detection scripts
    - Simulates human-like behavior
    - Manages fingerprint consistency
    
    Usage:
        stealth = StealthManager(config, logger)
        stealth.apply_context_stealth(context)
        stealth.apply_page_stealth(page)
    """
    
    # Anti-detection JavaScript (injected before page loads)
    ANTI_DETECTION_SCRIPT = """
    () => {
        // ============================================
        // CORE: Remove automation indicators
        // ============================================
        
        // 1. Delete navigator.webdriver (primary detection method)
        Object.defineProperty(navigator, 'webdriver', {
            get: () => undefined,
            configurable: true
        });
        
        // Also delete from prototype
        delete Object.getPrototypeOf(navigator).webdriver;
        
        // 2. Mock Chrome runtime (headless Chrome lacks this)
        if (!window.chrome) {
            window.chrome = {};
        }
        if (!window.chrome.runtime) {
            window.chrome.runtime = {
                connect: () => {},
                sendMessage: () => {},
                onMessage: { addListener: () => {} }
            };
        }
        
        // 3. Mock plugins array (headless has 0 plugins)
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                const plugins = [
                    { 
                        name: 'Chrome PDF Plugin',
                        filename: 'internal-pdf-viewer',
                        description: 'Portable Document Format',
                        length: 1,
                        item: (i) => null,
                        namedItem: (name) => null,
                        [Symbol.iterator]: function* () { yield this; }
                    },
                    {
                        name: 'Chrome PDF Viewer',
                        filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai',
                        description: '',
                        length: 1,
                        item: (i) => null,
                        namedItem: (name) => null,
                        [Symbol.iterator]: function* () { yield this; }
                    },
                    {
                        name: 'Native Client',
                        filename: 'internal-nacl-plugin',
                        description: '',
                        length: 2,
                        item: (i) => null,
                        namedItem: (name) => null,
                        [Symbol.iterator]: function* () { yield this; }
                    }
                ];
                plugins.length = 3;
                plugins.item = (i) => plugins[i] || null;
                plugins.namedItem = (name) => plugins.find(p => p.name === name) || null;
                plugins.refresh = () => {};
                return plugins;
            },
            configurable: true
        });
        
        // 4. Mock languages (consistent fingerprint)
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en'],
            configurable: true
        });
        
        // 5. Mock mimeTypes
        Object.defineProperty(navigator, 'mimeTypes', {
            get: () => {
                const mimeTypes = [
                    { type: 'application/pdf', suffixes: 'pdf', description: 'Portable Document Format' },
                    { type: 'text/pdf', suffixes: 'pdf', description: 'Portable Document Format' }
                ];
                mimeTypes.length = 2;
                mimeTypes.item = (i) => mimeTypes[i] || null;
                mimeTypes.namedItem = (name) => mimeTypes.find(m => m.type === name) || null;
                return mimeTypes;
            },
            configurable: true
        });
        
        // 6. Permissions API mock
        if (navigator.permissions) {
            const originalQuery = navigator.permissions.query;
            navigator.permissions.query = (parameters) => {
                if (parameters.name === 'notifications') {
                    return Promise.resolve({ state: Notification.permission, onchange: null });
                }
                return originalQuery.call(navigator.permissions, parameters);
            };
        }
        
        // 7. Hide automation-specific properties
        const automationProps = [
            'domAutomation',
            'domAutomationController', 
            '_Selenium_IDE_Recorder',
            '_selenium',
            '__webdriver_script_fn',
            '__driver_evaluate',
            '__webdriver_evaluate',
            '__selenium_evaluate',
            '__fxdriver_evaluate',
            '__driver_unwrapped',
            '__webdriver_unwrapped',
            '__selenium_unwrapped',
            '__fxdriver_unwrapped',
            '__webdriver_script_func',
            '$cdc_',
            '$chrome_asyncScriptInfo'
        ];
        
        automationProps.forEach(prop => {
            try {
                if (prop in window) delete window[prop];
                if (prop in document) delete document[prop];
            } catch (e) {}
        });
        
        // 8. Consistent deviceMemory (some bots have unusual values)
        Object.defineProperty(navigator, 'deviceMemory', {
            get: () => 8,
            configurable: true
        });
        
        // 9. Consistent hardwareConcurrency
        Object.defineProperty(navigator, 'hardwareConcurrency', {
            get: () => 4,
            configurable: true
        });
        
        // 10. Mock connection API
        if (navigator.connection) {
            Object.defineProperty(navigator.connection, 'rtt', {
                get: () => 50,
                configurable: true
            });
        }
        
        // 11. Prevent iframe detection
        try {
            Object.defineProperty(HTMLIFrameElement.prototype, 'contentWindow', {
                get: function() {
                    return null;
                }
            });
        } catch (e) {}
        
        // 12. Console.debug trap (some sites use this to detect automation)
        const originalDebug = console.debug;
        console.debug = function(...args) {
            if (args.some(arg => String(arg).includes('webdriver'))) {
                return;
            }
            return originalDebug.apply(console, args);
        };
        
        console.log('[Stealth] Anti-detection scripts loaded');
    }
    """
    
    # Additional WebGL fingerprint protection
    WEBGL_PROTECTION_SCRIPT = """
    () => {
        // Randomize WebGL fingerprint slightly
        const getParameterOriginal = WebGLRenderingContext.prototype.getParameter;
        WebGLRenderingContext.prototype.getParameter = function(parameter) {
            // UNMASKED_VENDOR_WEBGL
            if (parameter === 37445) {
                return 'Intel Inc.';
            }
            // UNMASKED_RENDERER_WEBGL
            if (parameter === 37446) {
                return 'Intel Iris OpenGL Engine';
            }
            return getParameterOriginal.call(this, parameter);
        };
        
        // Apply same to WebGL2
        if (typeof WebGL2RenderingContext !== 'undefined') {
            const getParameter2Original = WebGL2RenderingContext.prototype.getParameter;
            WebGL2RenderingContext.prototype.getParameter = function(parameter) {
                if (parameter === 37445) return 'Intel Inc.';
                if (parameter === 37446) return 'Intel Iris OpenGL Engine';
                return getParameter2Original.call(this, parameter);
            };
        }
    }
    """
    
    # Canvas fingerprint protection
    CANVAS_PROTECTION_SCRIPT = """
    () => {
        // Add slight noise to canvas operations
        const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
        HTMLCanvasElement.prototype.toDataURL = function(type) {
            if (type === 'image/png' || type === undefined) {
                const canvas = this;
                const context = canvas.getContext('2d');
                if (context) {
                    // Add invisible noise
                    const imageData = context.getImageData(0, 0, canvas.width, canvas.height);
                    const data = imageData.data;
                    for (let i = 0; i < data.length; i += 4) {
                        // Modify alpha channel slightly (invisible to human eye)
                        if (data[i + 3] > 0 && data[i + 3] < 255) {
                            data[i + 3] = data[i + 3] ^ (Math.random() > 0.5 ? 1 : 0);
                        }
                    }
                }
            }
            return originalToDataURL.call(this, type);
        };
    }
    """
    
    def __init__(self, config: 'ScraperConfig', logger: Optional[logging.Logger] = None):
        """
        Initialize StealthManager
        
        Args:
            config: ScraperConfig instance with stealth settings
            logger: Logger instance
        """
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        
        # State tracking
        self._playwright_stealth_available = False
        self._check_playwright_stealth()
        
        self.logger.info("🛡️ StealthManager initialized")
        self.logger.info(f"   Stealth Level: {getattr(config, 'stealth_level', 'aggressive')}")
        self.logger.info(f"   playwright-stealth: {'✓ Available' if self._playwright_stealth_available else '✗ Not installed'}")
    
    def _check_playwright_stealth(self) -> None:
        """Check if playwright-stealth library is available"""
        try:
            from playwright_stealth import stealth
            self._playwright_stealth_available = True
        except ImportError:
            self._playwright_stealth_available = False
            self.logger.warning("playwright-stealth not installed. Using built-in stealth only.")
            self.logger.warning("For better stealth: pip install playwright-stealth")
    
    def apply_context_stealth(self, context: 'BrowserContext') -> None:
        """
        Apply stealth measures at the browser context level.
        This injects scripts that run BEFORE any page loads.
        
        Args:
            context: Playwright BrowserContext
        """
        self.logger.debug("Applying context-level stealth...")
        
        stealth_level = getattr(self.config, 'stealth_level', 'aggressive')
        
        # Always inject core anti-detection script
        context.add_init_script(self.ANTI_DETECTION_SCRIPT)
        self.logger.debug("✓ Core anti-detection script injected")
        
        # WebGL protection (moderate+)
        if stealth_level in ('moderate', 'aggressive'):
            if getattr(self.config, 'mask_webgl', True):
                context.add_init_script(self.WEBGL_PROTECTION_SCRIPT)
                self.logger.debug("✓ WebGL fingerprint protection applied")
        
        # Canvas protection (aggressive only)
        if stealth_level == 'aggressive':
            if getattr(self.config, 'mask_canvas', True):
                context.add_init_script(self.CANVAS_PROTECTION_SCRIPT)
                self.logger.debug("✓ Canvas fingerprint protection applied")
        
        self.logger.info("🛡️ Context-level stealth applied")
    
    def apply_page_stealth(self, page: 'Page') -> None:
        """
        Apply stealth measures at the page level.
        Uses playwright-stealth library if available.
        
        Args:
            page: Playwright Page
        """
        self.logger.debug("Applying page-level stealth...")
        
        # Use playwright-stealth if available
        if self._playwright_stealth_available:
            try:
                from playwright_stealth import Stealth
                # Create Stealth instance with default settings
                stealth_plugin = Stealth() 
                stealth_plugin.apply_stealth_sync(page)
                self.logger.debug("✓ playwright-stealth patches applied (class-based)")
            except Exception as e:
                self.logger.warning(f"playwright-stealth failed: {e}")
        
        self.logger.info("🛡️ Page-level stealth applied")
    
    # ============================================
    # Human Behavior Simulation
    # ============================================
    
    def random_delay(self, base_delay: float) -> float:
        """
        Add human-like variance to a delay.
        
        Args:
            base_delay: Base delay in seconds
            
        Returns:
            Randomized delay
        """
        variance_min = getattr(self.config, 'delay_variance_min', 0.8)
        variance_max = getattr(self.config, 'delay_variance_max', 1.4)
        return base_delay * random.uniform(variance_min, variance_max)
    
    def sleep_human(self, base_seconds: float) -> None:
        """
        Sleep with human-like variance
        
        Args:
            base_seconds: Base sleep time in seconds
        """
        actual_delay = self.random_delay(base_seconds)
        time.sleep(actual_delay)
    
    def _bezier_point(self, t: float, points: List[MousePoint]) -> MousePoint:
        """
        Calculate point on Bezier curve at parameter t.
        
        Args:
            t: Parameter 0-1
            points: Control points
            
        Returns:
            Point on curve
        """
        n = len(points) - 1
        x = 0.0
        y = 0.0
        
        for i, point in enumerate(points):
            # Bernstein polynomial
            binomial = math.comb(n, i)
            basis = binomial * (t ** i) * ((1 - t) ** (n - i))
            x += basis * point.x
            y += basis * point.y
        
        return MousePoint(x, y)
    
    def _generate_bezier_path(
        self, 
        start: MousePoint, 
        end: MousePoint,
        num_points: int = 30
    ) -> List[MousePoint]:
        """
        Generate a human-like mouse path using Bezier curves.
        
        Args:
            start: Starting point
            end: Ending point
            num_points: Number of points in path
            
        Returns:
            List of points along the path
        """
        # Generate 1-2 random control points for natural curve
        num_control_points = random.randint(1, 2)
        control_points = [start]
        
        for _ in range(num_control_points):
            # Control points deviate from straight line
            mid_x = (start.x + end.x) / 2
            mid_y = (start.y + end.y) / 2
            
            # Random offset (more natural movement)
            offset_x = random.uniform(-100, 100)
            offset_y = random.uniform(-50, 50)
            
            control_points.append(MousePoint(mid_x + offset_x, mid_y + offset_y))
        
        control_points.append(end)
        
        # Generate path points
        path = []
        for i in range(num_points + 1):
            t = i / num_points
            point = self._bezier_point(t, control_points)
            path.append(point)
        
        return path
    
    def move_mouse_human(
        self, 
        page: 'Page',
        target_x: float,
        target_y: float,
        duration: float = 0.5
    ) -> None:
        """
        Move mouse to target coordinates with human-like motion.
        Uses Bezier curves for natural movement patterns.
        
        Args:
            page: Playwright page
            target_x: Target X coordinate
            target_y: Target Y coordinate
            duration: Approximate duration of movement
        """
        if not getattr(self.config, 'human_like_mouse', True):
            page.mouse.move(target_x, target_y)
            return
        
        # Get current mouse position (estimate from viewport center if unknown)
        viewport = page.viewport_size
        if viewport:
            start_x = viewport['width'] / 2
            start_y = viewport['height'] / 2
        else:
            start_x = 500
            start_y = 400
        
        start = MousePoint(start_x, start_y)
        end = MousePoint(target_x, target_y)
        
        # Generate path
        num_points = random.randint(20, 40)
        path = self._generate_bezier_path(start, end, num_points)
        
        # Calculate delay between points
        point_delay = duration / len(path)
        
        # Move along path
        for point in path:
            page.mouse.move(point.x, point.y)
            # Add micro-variance to timing
            time.sleep(point_delay * random.uniform(0.5, 1.5))
    
    def click_human(
        self,
        page: 'Page',
        x: float,
        y: float,
        button: str = 'left'
    ) -> None:
        """
        Click at coordinates with human-like behavior.
        Includes mouse movement and natural click timing.
        
        Args:
            page: Playwright page
            x: X coordinate
            y: Y coordinate
            button: Mouse button ('left', 'right', 'middle')
        """
        # Move to target with human motion
        self.move_mouse_human(page, x, y, duration=random.uniform(0.3, 0.7))
        
        # Small pause before click (humans don't click instantly)
        time.sleep(random.uniform(0.05, 0.15))
        
        # Click with natural timing
        page.mouse.click(x, y, button=button, delay=random.uniform(50, 150))
    
    def type_human(
        self,
        page: 'Page',
        selector: str,
        text: str,
        clear_first: bool = True
    ) -> None:
        """
        Type text with human-like behavior.
        Includes variable speed, pauses, and occasional typos.
        
        Args:
            page: Playwright page
            selector: Element selector to type into
            text: Text to type
            clear_first: Clear existing text first
        """
        if not getattr(self.config, 'human_like_typing', True):
            if clear_first:
                page.fill(selector, '')
            page.type(selector, text)
            return
        
        # Click on element first
        element = page.locator(selector)
        element.click()
        time.sleep(random.uniform(0.1, 0.3))
        
        # Clear if needed
        if clear_first:
            page.keyboard.press('Control+a')
            time.sleep(random.uniform(0.05, 0.1))
            page.keyboard.press('Backspace')
            time.sleep(random.uniform(0.1, 0.2))
        
        # Type character by character
        for i, char in enumerate(text):
            # Occasional typo (2% chance, only for longer texts)
            if random.random() < 0.02 and len(text) > 15:
                # Type wrong character
                wrong_chars = 'qwertyuiopasdfghjklzxcvbnm'
                wrong_char = random.choice(wrong_chars)
                page.keyboard.type(wrong_char)
                time.sleep(random.uniform(0.1, 0.25))
                
                # Notice mistake and backspace
                page.keyboard.press('Backspace')
                time.sleep(random.uniform(0.08, 0.15))
            
            # Type actual character
            page.keyboard.type(char)
            
            # Variable delay between characters
            base_delay = random.uniform(0.04, 0.12)
            
            # Longer pause after punctuation
            if char in '.!?':
                base_delay *= random.uniform(2.0, 4.0)
            elif char in ',;:':
                base_delay *= random.uniform(1.3, 2.0)
            elif char == ' ':
                # Occasional longer pause between words
                if random.random() < 0.1:
                    base_delay *= random.uniform(1.5, 3.0)
            
            time.sleep(base_delay)
    
    def scroll_human(
        self,
        page: 'Page',
        direction: str = 'down',
        distance: int = 300
    ) -> None:
        """
        Scroll with human-like behavior.
        Uses variable speed and sometimes overshoots.
        
        Args:
            page: Playwright page
            direction: 'up' or 'down'
            distance: Approximate scroll distance in pixels
        """
        if not getattr(self.config, 'human_like_scrolling', True):
            delta = distance if direction == 'down' else -distance
            page.mouse.wheel(0, delta)
            return
        
        # Break scroll into smaller segments
        num_segments = random.randint(3, 7)
        segment_distance = distance / num_segments
        
        # Sometimes overshoot and correct
        overshoot = random.random() < 0.15
        
        for i in range(num_segments):
            delta = segment_distance if direction == 'down' else -segment_distance
            
            # Add variance to each segment
            delta *= random.uniform(0.7, 1.3)
            
            page.mouse.wheel(0, int(delta))
            time.sleep(random.uniform(0.02, 0.08))
        
        # Overshoot correction
        if overshoot:
            time.sleep(random.uniform(0.1, 0.2))
            correction = random.uniform(20, 60)
            correction_delta = -correction if direction == 'down' else correction
            page.mouse.wheel(0, int(correction_delta))
    
    # ============================================
    # Fingerprint Generation
    # ============================================
    
    def get_randomized_viewport(self) -> Tuple[int, int]:
        """
        Get slightly randomized viewport dimensions.
        Helps avoid fingerprinting by exact viewport size.
        
        Returns:
            Tuple of (width, height)
        """
        if not getattr(self.config, 'randomize_viewport', True):
            return (self.config.viewport_width, self.config.viewport_height)
        
        # Common viewport sizes
        common_sizes = [
            (1920, 1080),
            (1366, 768),
            (1536, 864),
            (1440, 900),
            (1280, 720),
        ]
        
        # Pick a base size
        base_width, base_height = random.choice(common_sizes)
        
        # Add slight variance (-10 to +10 pixels)
        width = base_width + random.randint(-10, 10)
        height = base_height + random.randint(-10, 10)
        
        return (width, height)


# ============================================
# Utility Functions
# ============================================

def apply_stealth_to_context(context: 'BrowserContext', config: 'ScraperConfig', logger: logging.Logger) -> StealthManager:
    """
    Convenience function to apply stealth to a browser context.
    
    Args:
        context: Playwright BrowserContext
        config: ScraperConfig instance
        logger: Logger instance
        
    Returns:
        StealthManager instance for further use
    """
    manager = StealthManager(config, logger)
    manager.apply_context_stealth(context)
    return manager
