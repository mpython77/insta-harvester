"""
Instagram Scraper - Advanced Diagnostics System
Detects HTML structure changes and provides detailed error context
"""

import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
import logging

from .config import ScraperConfig


@dataclass
class SelectorTest:
    """Test result for a single selector"""
    selector: str
    selector_type: str  # 'css', 'xpath', 'text'
    found: bool
    count: int = 0
    error: Optional[str] = None
    test_time: float = 0.0


@dataclass
class DiagnosticReport:
    """Comprehensive diagnostic report"""
    timestamp: str
    url: str
    content_type: str  # 'Post' or 'Reel'
    test_results: List[SelectorTest] = field(default_factory=list)
    overall_status: str = 'UNKNOWN'  # 'OK', 'PARTIAL', 'FAILED'
    recommendations: List[str] = field(default_factory=list)

    def add_test(self, test: SelectorTest):
        """Add test result"""
        self.test_results.append(test)

    def get_failed_selectors(self) -> List[str]:
        """Get list of failed selectors"""
        return [t.selector for t in self.test_results if not t.found]

    def get_success_rate(self) -> float:
        """Calculate success rate"""
        if not self.test_results:
            return 0.0
        passed = sum(1 for t in self.test_results if t.found)
        return (passed / len(self.test_results)) * 100


class HTMLDiagnostics:
    """
    Advanced HTML structure diagnostics

    Features:
    - Validates all critical selectors
    - Detects HTML structure changes
    - Provides actionable error messages
    - Generates detailed reports
    """

    def __init__(self, page, logger: Optional[logging.Logger] = None, config: Optional[ScraperConfig] = None):
        """
        Initialize diagnostics

        Args:
            page: Playwright page object
            logger: Logger instance
            config: ScraperConfig instance
        """
        self.page = page
        self.logger = logger or logging.getLogger(__name__)
        self.config = config if config is not None else ScraperConfig()

        # Load selectors from config
        self.POST_SELECTORS = self.config.diagnostics_post_selectors
        self.REEL_SELECTORS = self.config.diagnostics_reel_selectors

    def test_selector(
        self,
        selector: str,
        selector_type: str = 'css',
        timeout: Optional[int] = None
    ) -> SelectorTest:
        """
        Test a single selector

        Args:
            selector: CSS selector or XPath
            selector_type: Type of selector
            timeout: Timeout in milliseconds

        Returns:
            SelectorTest result
        """
        if timeout is None:
            timeout = self.config.selector_test_timeout

        start_time = time.time()
        test = SelectorTest(
            selector=selector,
            selector_type=selector_type,
            found=False
        )

        try:
            if selector_type == 'css':
                count = self.page.locator(selector).count()
                test.found = count > 0
                test.count = count
            elif selector_type == 'xpath':
                count = self.page.locator(f'xpath={selector}').count()
                test.found = count > 0
                test.count = count

            test.test_time = time.time() - start_time

        except Exception as e:
            test.error = str(e)
            test.test_time = time.time() - start_time

        return test

    def diagnose_post(self, url: str) -> DiagnosticReport:
        """
        Run full diagnostics on a Post

        Args:
            url: Post URL

        Returns:
            DiagnosticReport
        """
        report = DiagnosticReport(
            timestamp=datetime.now().strftime(self.config.datetime_format),
            url=url,
            content_type='Post'
        )

        self.logger.info(f"🔍 Running POST diagnostics: {url}")

        # Test all post selectors
        for name, selector in self.POST_SELECTORS.items():
            self.logger.debug(f"  Testing: {name} -> {selector}")
            test = self.test_selector(selector)
            report.add_test(test)

            if test.found:
                self.logger.debug(f"    ✓ Found {test.count} elements ({test.test_time:.3f}s)")
            else:
                self.logger.warning(f"    ✗ NOT FOUND ({test.test_time:.3f}s)")

        # Determine overall status
        success_rate = report.get_success_rate()
        if success_rate >= self.config.diagnostics_success_threshold_ok:
            report.overall_status = 'OK'
        elif success_rate >= self.config.diagnostics_success_threshold_partial:
            report.overall_status = 'PARTIAL'
            report.recommendations.append(
                "⚠️ Some selectors failed. Instagram may have updated HTML structure."
            )
        else:
            report.overall_status = 'FAILED'
            report.recommendations.append(
                "❌ CRITICAL: Most selectors failed. Instagram HTML structure has changed!"
            )
            report.recommendations.append(
                f"Failed selectors: {', '.join(report.get_failed_selectors())}"
            )

        self.logger.info(
            f"Diagnostics complete: {report.overall_status} "
            f"({success_rate:.1f}% success rate)"
        )

        return report

    def diagnose_reel(self, url: str) -> DiagnosticReport:
        """
        Run full diagnostics on a Reel

        Args:
            url: Reel URL

        Returns:
            DiagnosticReport
        """
        report = DiagnosticReport(
            timestamp=datetime.now().strftime(self.config.datetime_format),
            url=url,
            content_type='Reel'
        )

        self.logger.info(f"🔍 Running REEL diagnostics: {url}")

        # Test all reel selectors
        for name, selector in self.REEL_SELECTORS.items():
            self.logger.debug(f"  Testing: {name} -> {selector}")
            test = self.test_selector(selector)
            report.add_test(test)

            if test.found:
                self.logger.debug(f"    ✓ Found {test.count} elements ({test.test_time:.3f}s)")
            else:
                self.logger.warning(f"    ✗ NOT FOUND ({test.test_time:.3f}s)")

        # Determine overall status
        success_rate = report.get_success_rate()
        if success_rate >= self.config.diagnostics_reel_success_threshold_ok:
            report.overall_status = 'OK'
        elif success_rate >= self.config.diagnostics_reel_success_threshold_partial:
            report.overall_status = 'PARTIAL'
            report.recommendations.append(
                "⚠️ Some reel selectors failed. Check if tag button exists or HTML changed."
            )
        else:
            report.overall_status = 'FAILED'
            report.recommendations.append(
                "❌ CRITICAL: Most reel selectors failed. Instagram Reels HTML structure has changed!"
            )
            report.recommendations.append(
                f"Failed selectors: {', '.join(report.get_failed_selectors())}"
            )

        self.logger.info(
            f"Diagnostics complete: {report.overall_status} "
            f"({success_rate:.1f}% success rate)"
        )

        return report

    def quick_validate(self, selector: str, element_name: str) -> bool:
        """
        Quick validation of a selector before using it

        Args:
            selector: CSS selector
            element_name: Human-readable name for logging

        Returns:
            True if selector found elements
        """
        try:
            count = self.page.locator(selector).count()
            if count == 0:
                self.logger.warning(
                    f"⚠️ HTML CHANGE DETECTED: '{element_name}' selector failed!\n"
                    f"   Selector: {selector}\n"
                    f"   This may indicate Instagram updated their HTML structure."
                )
                return False
            return True
        except Exception as e:
            self.logger.error(
                f"❌ SELECTOR ERROR: '{element_name}' selector crashed!\n"
                f"   Selector: {selector}\n"
                f"   Error: {e}"
            )
            return False

    def generate_report_text(self, report: DiagnosticReport) -> str:
        """Generate human-readable report"""
        sep_width = self.config.report_separator_width
        lines = [
            "=" * sep_width,
            f"DIAGNOSTIC REPORT - {report.content_type}",
            "=" * sep_width,
            f"Timestamp: {report.timestamp}",
            f"URL: {report.url}",
            f"Overall Status: {report.overall_status}",
            f"Success Rate: {report.get_success_rate():.1f}%",
            "",
            "Selector Tests:",
        ]

        for test in report.test_results:
            status = "✓" if test.found else "✗"
            lines.append(
                f"  {status} {test.selector:<50} "
                f"(count: {test.count}, time: {test.test_time:.3f}s)"
            )
            if test.error:
                lines.append(f"     Error: {test.error}")

        if report.recommendations:
            lines.append("")
            lines.append("Recommendations:")
            for rec in report.recommendations:
                lines.append(f"  {rec}")

        lines.append("=" * sep_width)

        return "\n".join(lines)


def run_diagnostic_mode(page, url: str, logger: logging.Logger):
    """
    Run full diagnostic mode on a URL

    This is useful for debugging when scraping fails

    Args:
        page: Playwright page
        url: URL to diagnose
        logger: Logger instance
    """
    diagnostics = HTMLDiagnostics(page, logger)

    # Detect type
    is_reel = '/reel/' in url

    # Run diagnostics
    if is_reel:
        report = diagnostics.diagnose_reel(url)
    else:
        report = diagnostics.diagnose_post(url)

    # Print report
    report_text = diagnostics.generate_report_text(report)
    logger.info("\n" + report_text)

    return report
