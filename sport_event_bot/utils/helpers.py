import datetime
import re
import urllib.request
from html.parser import HTMLParser
from typing import Callable, Optional

import parsedatetime
from loguru import logger


def parse_datetime(str_datetime_in_free_form: str, lang: str = "ru") -> Optional[datetime.datetime]:
    logger.info(f"parse_datetime: input='{str_datetime_in_free_form}', lang='{lang}'")
    
    # Try ISO/Common formats first
    coerced = _coerce_to_datetime(str_datetime_in_free_form)
    if coerced:
        logger.info(f"parse_datetime: coerced to {coerced}")
        return coerced

    try:
        # Map bot lang to parsedatetime locale
        # Handle cases where a translation function is passed instead of a lang string
        if not isinstance(lang, str):
            locale_id = "en_US"
        else:
            locale_map = {
                "ru": "ru_RU",
                "uk": "uk_UA",
                "en": "en_US",
                "pl": "pl_PL"
            }
            locale_id = locale_map.get(lang, "en_US")
        
        consts = parsedatetime.Constants(localeID=locale_id, usePyICU=False)
        consts.use24 = True
        cal = parsedatetime.Calendar(constants=consts, version=parsedatetime.VERSION_CONTEXT_STYLE)
        
        # parseDT returns (datetime, status)
        now = datetime.datetime.now()
        found_date, status = cal.parseDT(str_datetime_in_free_form, now)
        
        logger.info(f"parse_datetime: cal.parseDT found: {found_date}, status_type: {type(status)}")
        
        # Robust status check
        is_success = False
        if isinstance(status, int):
            is_success = (status > 0)
        elif hasattr(status, 'accuracy'):
            is_success = (status.accuracy > 0)
        else:
            is_success = bool(status)

        if not is_success:
            return None
            
        delta = found_date - now
        logger.info(f"parse_datetime: delta.days={delta.days}")
        
        # Allow dates from yesterday (for late night registrations) up to 120 days ahead
        if delta.days < -1 or delta.days > 120:
            logger.info("parse_datetime: date out of range, returning None")
            return None
            
        return found_date
    except Exception as e:
        logger.warning(f"Error parsing datetime '{str_datetime_in_free_form}': {e}")
        return None


def get_default_datetime():
    now = datetime.datetime.now()
    is_wednesday_target = False
    if now.weekday() == 6 and now.hour >= 12:  # Sunday afternoon
        is_wednesday_target = True
    elif now.weekday() in [0, 1]:  # Monday, Tuesday
        is_wednesday_target = True
    elif now.weekday() == 2 and now.hour < 12:  # Wednesday before noon
        is_wednesday_target = True

    if is_wednesday_target:
        days_ahead = 2 - now.weekday()
        if days_ahead < 0:
            days_ahead += 7
        target = now + datetime.timedelta(days=days_ahead)
        return target.replace(hour=20, minute=30, second=0, microsecond=0)
    else:
        days_ahead = 6 - now.weekday()
        if days_ahead <= 0:
            if now.weekday() == 6:
                days_ahead = 0
            else:
                days_ahead += 7
        target = now + datetime.timedelta(days=days_ahead)
        return target.replace(hour=11, minute=30, second=0, microsecond=0)


def parse_loose_json(text):
    pattern = r'(\w+)\s*:\s*("[^"]*"|\'[^\']*\'|[\w.:/\\\-]+)'
    matches = re.findall(pattern, text)
    result = {}
    for key, val in matches:
        if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
            val = val[1:-1]
        elif val.lower() == "true":
            val = True
        elif val.lower() == "false":
            val = False
        else:
            try:
                val = int(val)
            except ValueError:
                try:
                    val = float(val)
                except ValueError:
                    pass
        result[key] = val
    return result


class _MetaExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.og_title = None
        self.title = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            prop = d.get("property", "") or d.get("name", "")
            content = d.get("content", "")
            if prop == "og:title" and content:
                self.og_title = content

    def handle_data(self, data):
        if self._in_title and not self.title:
            self.title = data.strip()

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False


def _parse_url_title_sync(url: str) -> str:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            content_type = resp.headers.get_content_type()
            if "html" not in content_type:
                return ""
            raw = resp.read(65536)
            html = raw.decode("utf-8", errors="replace")
    except Exception:
        return ""
    parser = _MetaExtractor()
    try:
        parser.feed(html)
    except Exception:
        pass
    return (parser.og_title or parser.title or "").strip()


def _coerce_to_datetime(val: object) -> Optional[datetime.datetime]:
    if isinstance(val, datetime.datetime):
        return val
    if isinstance(val, str) and val.strip():
        s = val.strip()
        try:
            return datetime.datetime.fromisoformat(s)
        except ValueError:
            for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
                try:
                    return datetime.datetime.strptime(s, fmt)
                except ValueError:
                    pass
    return None
