import datetime
from typing import Optional, Callable
import parsedatetime
from recurrent.event_parser import RecurringEvent

def parse_datetime(str_datetime_in_free_form: str, translate: Callable[[str], str]) -> Optional[datetime.datetime]:
    try:
        # Use 'en_US' as base but ensure it doesn't crash if translate is used oddly
        locale_id = 'en_US'
        consts = parsedatetime.Constants(localeID=locale_id, usePyICU=False)
        consts.use24 = True
        r_event = RecurringEvent(parse_constants=consts)
        found_date = r_event.parse(str_datetime_in_free_form)
        
        if not found_date:
            print(f"No date found for: {str_datetime_in_free_form}")
            return None
        
        if isinstance(found_date, str):
            print(f"Got string instead of datetime: {found_date}")
            return None
            
        return found_date
    except Exception as e:
        print(f"Error parsing datetime '{str_datetime_in_free_form}': {e}")
        return None

def translate(text): return text

test_cases = [
    "tomorrow 18:00",
    "2026-04-17 14:00",
    "at 8pm on friday",
    "next monday 10:30",
    "nonsense"
]

for tc in test_cases:
    res = parse_datetime(tc, translate)
    print(f"Input: {tc} -> Output: {res}")
