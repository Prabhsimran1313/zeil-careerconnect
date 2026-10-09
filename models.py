from pydantic import BaseModel, Field, ConfigDict


class Shape(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Task(Shape):
    title: str = Field(min_length=1)
    skill: str = Field(min_length=1)
    description: str = Field(min_length=1)
    deliverable: str = Field(min_length=1)
    duration_minutes: int = Field(ge=15, le=480)


class Week(Shape):
    week: int = Field(ge=1, le=4)
    focus: str = Field(min_length=1)
    tasks: list[Task] = Field(min_length=2, max_length=3)


class Question(Shape):
    category: str = Field(pattern='^(Technical|Behavioural)$')
    question: str = Field(min_length=1)


class CareerRoadmap(Shape):
    detected_job_title: str = Field(min_length=1)
    role_mismatch_note: str
    strengths: list[str]
    preparation_priorities: list[str] = Field(min_length=1)
    weeks: list[Week] = Field(min_length=1, max_length=4)
    interview_questions: list[Question] = Field(min_length=2)


class PlanReview(Shape):
    needs_revision: bool
    summary: str
    issues: list[str]
    recommendations: list[str]


class InterviewFeedback(Shape):
    accuracy: int = Field(ge=0, le=10)
    completeness: int = Field(ge=0, le=10)
    clarity: int = Field(ge=0, le=10)
    relevance: int = Field(ge=0, le=10)
    assessment: str = Field(pattern='^(Incorrect|Incomplete|Strong)$')
    strengths: list[str]
    improvements: list[str]
    suggested_answer: str = Field(min_length=1)
    next_practice_task: str = Field(min_length=1)
