from pydantic import BaseModel, Field, constr
from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from uuid import UUID


class ChoiceBase(BaseModel):
    text: str
    choice_cover: Optional[str] = None


class Choice(ChoiceBase):
    id: int
    question_id: int

    class Config:
        orm_mode = True


class ChoiceCreate(BaseModel):
    text: str
    choice_cover: Optional[str] = None
    text_fields_count: Optional[int] = None


# schema for updating Choice
class ChoiceUpdate(Choice):
    id: int
    choice_text: str


# schema for deleting Choice
class ChoiceDelete(Choice):
    id: int


class QuestionType(str, Enum):
    SINGLE = "SINGLE ANSWER"
    PLURAL = "PLURAL ANSWER"
    FREE = "FREE ANSWER"
    FREE_TEXT = "FREE TEXT ANSWER"


class StatusPoll(str, Enum):
    DRAFT = 'DRAFT'
    PUBLISHED = 'PUBLISHED'
    CLOSED = 'CLOSED'
    ENDED = 'ENDED'
    ARCHIVED = 'ARCHIVED'


class QuestionBase(BaseModel):
    """Base model schemas question"""

    id: int
    type: QuestionType
    text: str
    question_cover: Optional[str] = None
    option_pass: Optional[bool] = True
    option_other_answer: Optional[bool] = True


class Question(QuestionBase):
    poll_id: int
    choice: Optional[List[Choice]] = []

    class Config:
        orm_mode = True


class QuestionPage(BaseModel):
    total_questions: Optional[int] = None
    questions: Optional[List[Question]] = []

    class Config:
        orm_mode = True


# schema for creating Question
class QuestionCreate(BaseModel):
    type: QuestionType
    text: str
    question_cover: Optional[str] = None
    option_pass: Optional[bool] = True
    option_other_answer: Optional[bool] = True
    choice: List[ChoiceCreate]


# schema for updating Question
class QuestionUpdate(BaseModel):
    text: Optional[str]
    question_cover: Optional[str] = None
    option_pass: Optional[bool] = True
    option_other_answer: Optional[bool] = True
    choice: List[ChoiceUpdate]

    class Config:
        orm_mode = True


# schema for plural question without choices
class PluralQuestion(Question):
    pass


# schema for updating Question
class UpdateQuestion(BaseModel):
    type: Optional[QuestionType]
    text: str
    question_cover: Optional[str] = None
    option_pass: Optional[bool] = True
    option_other_answer: Optional[bool] = True


# schema for deleting Question
class QuestionDelete(Question):
    id: int


class PollBase(BaseModel):
    """Base model schemas poll"""

    created_at: datetime = datetime.utcnow()
    title: str
    description: Optional[str] = None
    poll_cover: Optional[str] = None
    status_poll: StatusPoll = StatusPoll.DRAFT
    poll_url: Optional[str] = None
    user_id: int


class Poll(PollBase):
    id: int
    uuid: UUID
    question: Optional[List[Question]] = []

    class Config:
        orm_mode = True


class CreatePoll(Poll):
    question: Optional[List[Question]] = []


class CreateSimplePoll(BaseModel):
    title: str
    description: Optional[str] = None


class PollDetail(PollBase):
    question_count: Optional[int] = None

# class CreatePoll(Poll):
#     pass


class UpdatePoll(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    poll_cover: Optional[str] = None
    poll_status: StatusPoll = StatusPoll.DRAFT


class PollStatusUpdate(BaseModel):
    poll_status: bool = False


class ListPoll(Poll):
    pass


# schema for single poll with nested questions
class SinglePoll(Poll):
    question: Optional[List[Question]] = []


# schema for deleting Poll
class DeletePoll(Poll):
    id: int


# # schema for response
# class ResponseBase(BaseModel):
#
#     """Base model Response"""
#     created_at: datetime = datetime.utcnow()
#     poll_id: int
#     user_id: Optional[int] = None
#     question_id: int
#     choice_id: Optional[int] = None
#     answer_text: Optional[Dict[Any, Any]] = None
#     answer_choice: Optional[Dict[Any, Any]] = None


# class Response(ResponseBase):
#     id: int
#     created_at = datetime = datetime.utcnow()
#
#     class Config:
#         orm_mode = True


# schema for creating response
# class CreateResponse(BaseModel):
#     choice_id: Optional[int] = None
#     choice_ids: Optional[List[int]] = None
#     answer_text: Optional[Dict[Any, Any]] = None


class SingleChoiceResponse(BaseModel):
    question_id: int
    choice_id: int


class MultipleChoiceResponse(BaseModel):
    question_id: int
    choice_ids: List[int]
    choice_text: Optional[str] = None


class SingleTextResponse(BaseModel):
    question_id: int
    answer_text: constr(max_length=500, pattern=r"^[а-яА-ЯёЁa-zA-Z0-9\s]+$")


class MultipleTextResponse(BaseModel):
    question_id: int
    answer_text: List[constr(max_length=500, pattern=r"^[а-яА-ЯёЁa-zA-Z0-9\s]+$")]


class CreateSingleResponse(BaseModel):
    response: Union[SingleChoiceResponse, MultipleChoiceResponse, SingleTextResponse, MultipleTextResponse]


class ResponsePayload(BaseModel):
    question_id: int
    choice_id: Optional[int] = None
    choice_ids: Optional[List[int]] = None
    choice_text: Optional[str] = None
    choice_texts: Optional[Union[str, List[str]]] = None


class CreatePollResponse(BaseModel):
    responses: List[ResponsePayload]


class ListResponses(BaseModel):
    id: int
    created_at: datetime

    class Config:
        orm_mode = True


class ChoiceReport(BaseModel):
    choice_id: int
    choice_count: int
    percentage: float


class QuestionReport(BaseModel):
    question_id: int
    choices_report: Optional[List[ChoiceReport]]
    text_answers: Optional[List[str]]


class PollReportResponse(BaseModel):
    report: List[QuestionReport]
