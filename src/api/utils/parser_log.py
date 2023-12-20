import re
from typing import Dict, Optional
from datetime import datetime

from company.schemas import CompanyCreate, CompanyOut
from EventLog.schemas import LogEntry


def parse_log_line(log_line: str) -> LogEntry:

    log_entry_pattern = r"Timestamp: (?P<timestamp>.*?) \| " \
                        r"Logger: (?P<logger>.*?) \| " \
                        r"Level: (?P<level>.*?) \| " \
                        r"Message: (?P<message>.*?) \| " \
                        r"Event Type: (?P<event_type>.*?) \| " \
                        r"Object: (?P<obj>.*?) \| " \
                        r"Subject: (?P<subject>.*?) \| " \
                        r"Action: (?P<action>.*?) \| " \
                        r"Additional Information: (?P<additional_info>.*?)"

    match = re.match(log_entry_pattern, log_line)
    if match:
        log_data = match.groupdict()
        log_data['timestamp'] = datetime.strptime(log_data['timestamp'], "%Y-%m-%d %H:%M:%S,%f")
        log_data['message'] = log_data['message'].strip() if log_data['message'] else None
        return LogEntry(**log_data)
    return None



