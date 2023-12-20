from pydantic import BaseModel, Field, constr, validator
from typing import Optional, List, Dict, Any, Union
from datetime import datetime

from utils import CamelModelMixin


class LogEntry(CamelModelMixin):
    timestamp: datetime = Field(..., description="Timestamp of the log entry")
    logger: str = Field(..., description="Logger name")
    level: str = Field(..., description="Log level")
    message: str = Field("", description="Any message passed to logger")
    event_type: str = Field("", description="Type of event")
    object: str = Field("", description="Object related to the event")
    subject: str = Field("", description="Subject related to the event")
    action: str = Field("", description="Action performed")
    additional_info: str = Field("", description="Additional information")



