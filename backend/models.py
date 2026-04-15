from sqlmodel import Field, Relationship, SQLModel
from typing import List, Optional
from datetime import datetime

class UserBase(SQLModel):
    username: str
    email: str = Field(index=True, unique=True, nullable=False)
    created_at: datetime = Field(default_factory=datetime.now)

class User(UserBase, table=True):
    __tablename__="users"

    id: int | None = Field(primary_key=True)
    tags: str | None = ""

class UserCreate(UserBase):
    pass

class UserUpdate(SQLModel):
    username: str | None = None
    email: str | None = None
    tags: str | None = None

class UserPublic(UserBase):
    id: int



class CourseBase(SQLModel):
    title: str
    description: str
    level: str

class Course(CourseBase, table=True):
    __tablename__="courses"

    id: int | None = Field(primary_key=True)
    tags: str | None = ""

class CourseCreate(CourseBase):
    tags: str | None = ""

class CoursePublic(CourseBase):
    id: int

class CourseUpdate(SQLModel):
    title: str | None = None
    description: str | None = None
    level: str | None = None
    tags: str | None = None



class LessonBase(SQLModel):
    title: str
    video_url: str
    order_idx: int
    duration_seconds: int
    course_id: int = Field(foreign_key="courses.id")

class Lesson(LessonBase, table=True):
    __tablename__="lessons"

    id: int | None = Field(primary_key=True)

class LessonCreate(LessonBase):
    pass

class LessonPublic(LessonBase):
    id: int

class LessonUpdate(SQLModel):
    title: str | None = None
    video_url: str | None = None
    order_idx: int | None = None
    duration_seconds: int | None = None



class UserLessonBase(SQLModel):
    user_id: int = Field(foreign_key="users.id")
    lesson_id: int = Field(foreign_key="lessons.id")
    watched: bool = False
    completed_at: datetime = Field(default_factory=datetime.now, nullable=True)

class UserLesson(UserLessonBase, table=True):
    __tablename__="user_lesson_progress"

    id:int | None = Field(primary_key=True)

class UserLessonCreate(UserLessonBase):
    pass

class UserLessonPublic(UserLessonBase):
    id: int

class UserLessonUpdate(SQLModel):
    watched: bool | None = None
    completed_at: datetime | None = None



class UserCourseBase(SQLModel):
    user_id: int = Field(foreign_key="users.id")
    course_id: int = Field(foreign_key="courses.id")
    completed: bool = False
    enrolled_at: datetime = Field(default_factory=datetime.now, nullable=True)

class UserCourse(UserCourseBase, table=True):
    __tablename__="user_course_progress"

    id: int | None = Field(primary_key=True)
    percent_complete: float = 0.0

class UserCourseCreate(UserCourseBase):
    percent_complete: float = 0.0

class UserCoursePublic(UserCourseBase):
    id: int
    percent_complete: float = 0.0

class UserCourseUpdate(SQLModel):
    completed: bool | None = None
    percent_complete: float | None = None
