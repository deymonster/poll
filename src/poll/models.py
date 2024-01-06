from db.base_class import Base
from enum import Enum
from sqlalchemy.dialects.postgresql import ENUM, UUID
from sqlalchemy import Boolean, Column, ForeignKey, Integer, String, DateTime, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
from user.models import User


class TypeQuestion(str, Enum):
    SINGLE = "SINGLE ANSWER"
    PLURAL = "PLURAL ANSWER"
    FREE = "FREE ANSWER"  # multiple text fields for answer
    FREE_TEXT = "FREE TEXT ANSWER"  # one text field for answer


class PollStatus(str, Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CLOSED = "CLOSED"
    ENDED = "ENDED"
    ARCHIVED = "ARCHIVED"


class Poll(Base):
    """Model poll"""

    id = Column(Integer, primary_key=True, index=True)
    uuid = Column(UUID(as_uuid=True), unique=True, default=uuid.uuid4)
    created_at = Column(DateTime, default=datetime.utcnow)
    title = Column(String, index=True)
    description = Column(String, index=True)
    poll_cover = Column(String, nullable=True)
    poll_status = Column(ENUM(PollStatus), default=PollStatus.DRAFT)
    poll_url = Column(String)
    user_id = Column(Integer, ForeignKey("user.id"))
    user = relationship(User, back_populates="polls")
    question = relationship("Question", back_populates="poll")
    response = relationship("Response", back_populates="poll")


class Question(Base):
    """Model question"""

    id = Column(Integer, primary_key=True, index=True)
    type = Column(ENUM(TypeQuestion), nullable=False, index=True)
    text = Column(String, index=True)
    question_cover = Column(String, nullable=True)
    option_pass = Column(Boolean, default=False)
    option_other_answer = Column(Boolean, default=False)
    poll_id = Column(Integer, ForeignKey("poll.id"))
    order = Column(Integer, default=10, index=True)
    poll = relationship("Poll", back_populates="question")
    choice = relationship("Choice", back_populates="question")
    response = relationship("Response", back_populates="question")


# Model choice
class Choice(Base):
    """Model choice"""

    id = Column(Integer, primary_key=True, index=True)
    text = Column(String, index=True)
    choice_cover = Column(String, nullable=True)
    text_fields_count = Column(Integer, nullable=True)
    question_id = Column(Integer, ForeignKey("question.id"))
    question = relationship("Question", back_populates="choice")
    response = relationship("Response", back_populates="choice")


# Model Response
class Response(Base):
    """Model response"""

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    poll_id = Column(Integer, ForeignKey("poll.id"))
    poll = relationship("Poll", back_populates="response")
    question_id = Column(Integer, ForeignKey("question.id"))
    question = relationship("Question", back_populates="response")
    choice_id = Column(Integer, ForeignKey("choice.id"))
    choice = relationship("Choice", back_populates="response")
    answer_text = Column(JSON, nullable=True)
    answer_choice = Column(JSON, nullable=True)
