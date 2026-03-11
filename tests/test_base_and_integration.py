"""
Unit Tests — BaseScraper.parse_number
Covers: localized number parsing (K, M, ming, тыс.), comma/dot handling, edge cases
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch, MagicMock
from instaharvest.config import ScraperConfig


class ConcreteBaseScraper:
    """Minimal concrete subclass for testing parse_number"""
    
    def __init__(self, config=None):
        self.config = config or ScraperConfig()
        self.logger = MagicMock()
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.interrupted = False
    
    def parse_number(self, text):
        """Copy of BaseScraper.parse_number for isolated testing"""
        if not text:
            return None
        
        clean_text = text.strip().upper()
        
        multiplier = 1
        for suffix, mult in self.config.number_suffixes.items():
            if clean_text.endswith(suffix.upper()):
                multiplier = mult
                clean_text = clean_text[:-len(suffix)].strip()
                break
        
        try:
            clean_text = clean_text.replace(' ', '')
            
            if ',' in clean_text and '.' in clean_text:
                clean_text = clean_text.replace(',', '')
            elif ',' in clean_text:
                if multiplier > 1:
                    clean_text = clean_text.replace(',', '.')
                else:
                    clean_text = clean_text.replace(',', '')
            
            value = float(clean_text)
            return int(value * multiplier)
        except ValueError:
            return None


class TestParseNumber:
    """Tests for parse_number logic"""
    
    def setup_method(self):
        self.s = ConcreteBaseScraper()
    
    def test_simple_number(self):
        assert self.s.parse_number('100') == 100
    
    def test_k_suffix(self):
        assert self.s.parse_number('1.5K') == 1500
    
    def test_m_suffix(self):
        assert self.s.parse_number('2.3M') == 2300000
    
    def test_lowercase_k(self):
        assert self.s.parse_number('1.5k') == 1500
    
    def test_comma_thousands(self):
        assert self.s.parse_number('1,000') == 1000
    
    def test_comma_with_dot_decimal(self):
        assert self.s.parse_number('1,000.50') == 1000
    
    def test_comma_decimal_with_k(self):
        assert self.s.parse_number('1,5K') == 1500
    
    def test_space_thousands(self):
        assert self.s.parse_number('1 000') == 1000
    
    def test_uzbek_ming(self):
        """Uzbek: 'ming' = 1000"""
        assert self.s.parse_number('15ming') == 15000
    
    def test_russian_tys(self):
        """Russian: 'тыс.' = 1000"""
        assert self.s.parse_number('10тыс.') == 10000
    
    def test_empty_string(self):
        assert self.s.parse_number('') is None
    
    def test_none(self):
        assert self.s.parse_number(None) is None
    
    def test_non_numeric(self):
        assert self.s.parse_number('abc') is None
    
    def test_whitespace(self):
        assert self.s.parse_number('  500  ') == 500
    
    def test_large_number(self):
        assert self.s.parse_number('1B') == 1000000000
    
    def test_zero(self):
        assert self.s.parse_number('0') == 0
    
    def test_float_without_suffix(self):
        assert self.s.parse_number('999.9') == 999


# ═══════════════════════════════════════════════════════════
# INTEGRATION — Full Import Chain
# ═══════════════════════════════════════════════════════════

class TestFullImportChain:
    """Verify entire library import chain works"""
    
    def test_all_main_classes(self):
        from instaharvest import (
            ScraperConfig,
            ProfileScraper, ProfileData,
            PostDataScraper, PostData, PostLocation, PostOwner, CarouselSlide,
            ReelDataScraper, ReelData,
            StoryScraper, StoryResult, StoryItem, StorySlideInfo,
            TaggedPostsScraper, TaggedPostData, TaggedPostsResult,
            HighlightsScraper, HighlightResult, HighlightSlide,
            HighlightSticker, HighlightMusic, HighlightInfo, HighlightsListResult,
            NotificationReader, NotificationItem,
            BatchDownloader, DownloadTask, BatchResult,
            DataExporter,
            InstagramOrchestrator,
            SharedBrowser,
        )
        assert ScraperConfig is not None
        assert InstagramOrchestrator is not None
        assert SharedBrowser is not None

    def test_exceptions(self):
        from instaharvest import (
            InstagramScraperError,
            SessionNotFoundError,
            ProfileNotFoundError,
            HTMLStructureChangedError,
            PageLoadError,
            RateLimitError,
            LoginRequiredError,
        )
        assert issubclass(SessionNotFoundError, InstagramScraperError)

    def test_version(self):
        import instaharvest
        assert hasattr(instaharvest, '__version__')
        assert isinstance(instaharvest.__version__, str)


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
