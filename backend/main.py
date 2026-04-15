from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlmodel import Session, select
import uvicorn

from connectdb import create_db_and_tables, engine
from models import (
    Course,
    CourseCreate,
    CoursePublic,
    CourseUpdate,
    Lesson,
    LessonCreate,
    LessonPublic,
    LessonUpdate,
    User,
    UserCourse,
    UserCoursePublic,
    UserCourseUpdate,
    UserCreate,
    UserLesson,
    UserLessonCreate,
    UserLessonPublic,
    UserLessonUpdate,
    UserPublic,
    UserUpdate,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/createuser", response_model=UserPublic)
def create_user(user: UserCreate):
    with Session(engine) as session:
        db_user = User.model_validate(user)
        session.add(db_user)
        session.commit()
        session.refresh(db_user)
        return db_user


@app.get("/courses", response_model=list[CoursePublic])
def get_courses():
    with Session(engine) as session:
        return session.exec(select(Course)).all()


@app.get("/courses/{course_id}", response_model=list[LessonPublic])
def get_lessons(course_id: int):
    with Session(engine) as session:
        return session.exec(select(Lesson).where(Lesson.course_id == course_id)).all()


@app.get("/lessons/{lesson_id}", response_model=LessonPublic)
def get_lesson(lesson_id: int):
    with Session(engine) as session:
        lesson = session.get(Lesson, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")
        return lesson


@app.post("/courses/{course_id}/enroll")
def enroll_course(course_id: int, user_id: int):
    with Session(engine) as session:
        course = session.get(Course, course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        existing = session.exec(
            select(UserCourse).where(
                UserCourse.user_id == user_id,
                UserCourse.course_id == course_id,
            )
        ).first()
        if existing:
            return {"message": "Already enrolled"}

        user_course = UserCourse.model_validate({"user_id": user_id, "course_id": course_id})
        session.add(user_course)
        session.commit()
        return {"message": "Enrolled successfully"}


@app.post("/lessons/{lesson_id}/watched")
def mark_lesson_watched(lesson_id: int, user_id: int):
    with Session(engine) as session:
        lesson = session.get(Lesson, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        existing_lesson_progress = session.exec(
            select(UserLesson).where(
                UserLesson.user_id == user_id,
                UserLesson.lesson_id == lesson_id,
            )
        ).first()

        if existing_lesson_progress:
            existing_lesson_progress.watched = True
            existing_lesson_progress.completed_at = datetime.now()
            session.add(existing_lesson_progress)
        else:
            lesson_data = UserLessonCreate(
                user_id=user_id,
                lesson_id=lesson_id,
                watched=True,
                completed_at=datetime.now(),
            )
            user_lesson = UserLesson.model_validate(lesson_data)
            session.add(user_lesson)

        course_size = len(session.exec(select(Lesson).where(Lesson.course_id == lesson.course_id)).all())
        watched_size = len(
            session.exec(
                select(UserLesson)
                .join(Lesson, UserLesson.lesson_id == Lesson.id)
                .where(
                    UserLesson.user_id == user_id,
                    UserLesson.watched == True,
                    Lesson.course_id == lesson.course_id,
                )
            ).all()
        )

        user_course = session.exec(
            select(UserCourse).where(
                UserCourse.user_id == user_id,
                UserCourse.course_id == lesson.course_id,
            )
        ).first()

        if user_course:
            user_course.completed = course_size > 0 and course_size == watched_size
            user_course.percent_complete = (watched_size / course_size) * 100 if course_size > 0 else 0.0
            session.add(user_course)

        session.commit()
        return {"message": "Lesson marked as watched"}


@app.get("/profile/{user_id}", response_model=UserPublic)
def get_user(user_id: int):
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        return user


@app.get("/profile/{user_id}/progress", response_model=list[UserCoursePublic])
def get_course_progress(user_id: int):
    with Session(engine) as session:
        return session.exec(select(UserCourse).where(UserCourse.user_id == user_id)).all()


@app.get("/profile/{user_id}/progress/{course_id}", response_model=list[UserLessonPublic])
def get_lesson_progress(user_id: int, course_id: int):
    with Session(engine) as session:
        return session.exec(
            select(UserLesson)
            .join(Lesson, UserLesson.lesson_id == Lesson.id)
            .where(
                UserLesson.user_id == user_id,
                Lesson.course_id == course_id,
            )
        ).all()


@app.get("/profile/{user_id}/recommendations", response_model=list[str])
def get_recommendations(user_id: int):
    with Session(engine) as session:
        enrolled = session.exec(select(UserCourse).where(UserCourse.user_id == user_id)).all()
        enrolled_ids = {item.course_id for item in enrolled}
        all_courses = session.exec(select(Course)).all()
        picks = [course.title for course in all_courses if course.id not in enrolled_ids][:5]
        return picks


@app.get("/admin/users", response_model=list[UserPublic])
def admin_get_users():
    with Session(engine) as session:
        return session.exec(select(User)).all()


@app.patch("/admin/users/{user_id}", response_model=UserPublic)
def admin_update_user(user_id: int, payload: UserUpdate):
    with Session(engine) as session:
        user = session.get(User, user_id)
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(user, key, value)

        session.add(user)
        session.commit()
        session.refresh(user)
        return user


@app.get("/admin/users/{user_id}/course-progress", response_model=list[UserCoursePublic])
def admin_get_user_course_progress(user_id: int):
    with Session(engine) as session:
        return session.exec(select(UserCourse).where(UserCourse.user_id == user_id)).all()


@app.get("/admin/users/{user_id}/lesson-progress", response_model=list[UserLessonPublic])
def admin_get_user_lesson_progress(user_id: int, course_id: int | None = Query(default=None)):
    with Session(engine) as session:
        query = select(UserLesson).where(UserLesson.user_id == user_id)
        if course_id is not None:
            query = query.join(Lesson, UserLesson.lesson_id == Lesson.id).where(Lesson.course_id == course_id)
        return session.exec(query).all()


@app.patch("/admin/user-courses/{record_id}", response_model=UserCoursePublic)
def admin_update_user_course_progress(record_id: int, payload: UserCourseUpdate):
    with Session(engine) as session:
        record = session.get(UserCourse, record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Course progress record not found")

        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(record, key, value)

        session.add(record)
        session.commit()
        session.refresh(record)
        return record


@app.patch("/admin/user-lessons/{record_id}", response_model=UserLessonPublic)
def admin_update_user_lesson_progress(record_id: int, payload: UserLessonUpdate):
    with Session(engine) as session:
        record = session.get(UserLesson, record_id)
        if not record:
            raise HTTPException(status_code=404, detail="Lesson progress record not found")

        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(record, key, value)

        session.add(record)
        session.commit()
        session.refresh(record)
        return record


@app.post("/admin/courses", response_model=CoursePublic)
def admin_create_course(payload: CourseCreate):
    with Session(engine) as session:
        course = Course.model_validate(payload)
        session.add(course)
        session.commit()
        session.refresh(course)
        return course


@app.patch("/admin/courses/{course_id}", response_model=CoursePublic)
def admin_update_course(course_id: int, payload: CourseUpdate):
    with Session(engine) as session:
        course = session.get(Course, course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(course, key, value)

        session.add(course)
        session.commit()
        session.refresh(course)
        return course


@app.delete("/admin/courses/{course_id}")
def admin_delete_course(course_id: int):
    with Session(engine) as session:
        course = session.get(Course, course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        lessons = session.exec(select(Lesson).where(Lesson.course_id == course_id)).all()
        for lesson in lessons:
            session.delete(lesson)

        session.delete(course)
        session.commit()
        return {"message": "Course deleted"}


@app.post("/admin/lessons", response_model=LessonPublic)
def admin_create_lesson(payload: LessonCreate):
    with Session(engine) as session:
        course = session.get(Course, payload.course_id)
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        lesson = Lesson.model_validate(payload)
        session.add(lesson)
        session.commit()
        session.refresh(lesson)
        return lesson


@app.patch("/admin/lessons/{lesson_id}", response_model=LessonPublic)
def admin_update_lesson(lesson_id: int, payload: LessonUpdate):
    with Session(engine) as session:
        lesson = session.get(Lesson, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        data = payload.model_dump(exclude_unset=True)
        for key, value in data.items():
            setattr(lesson, key, value)

        session.add(lesson)
        session.commit()
        session.refresh(lesson)
        return lesson


@app.delete("/admin/lessons/{lesson_id}")
def admin_delete_lesson(lesson_id: int):
    with Session(engine) as session:
        lesson = session.get(Lesson, lesson_id)
        if not lesson:
            raise HTTPException(status_code=404, detail="Lesson not found")

        session.delete(lesson)
        session.commit()
        return {"message": "Lesson deleted"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
