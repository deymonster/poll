import logging
import os
from datetime import datetime


class PollLogger(logging.Logger):
    def __init__(self, app_name):
        log_dir = 'logs'
        super().__init__(app_name)
        try:
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
        except Exception as e:
            print(f"Error creating log file: {e}")

        self.logger = logging.getLogger(app_name)
        self.logger.setLevel(logging.INFO)
        self.handler_console = logging.StreamHandler()
        self.handler_file = logging.FileHandler('logs/all_logs.log')
        self.formatter = logging.Formatter('Timestamp: %(asctime)s | Logger: %(name)s | Level: %(levelname)s | %(message)s')
        self.handler_console.setFormatter(self.formatter)
        self.handler_file.setFormatter(self.formatter)
        self.logger.addHandler(self.handler_console)
        self.logger.addHandler(self.handler_file)

    def info(self, msg=None, *, event_type=None, obj=None, subj=None, action=None, additional_info=None):
        log_entry = {
            'timestamp': datetime.now(),
            'logger': self.name,
            'level': 'INFO',
            'event_type': event_type if event_type else "",
            'object': obj if obj else "",
            'subject': subj if subj else "",
            'action': action if action else "",
            'additional_info': additional_info if additional_info else ""
        }
        log_entry_str = "| Event Type: %(event_type)s | Object: %(object)s " \
                        "| Subject: %(subject)s | Action: %(action)s " \
                        "| Additional Information: %(additional_info)s"

        formatted_log = f"Message: {msg} {log_entry_str}" % log_entry

        self.logger.info(formatted_log)
