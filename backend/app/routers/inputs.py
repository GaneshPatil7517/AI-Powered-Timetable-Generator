from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app import models, schemas

router = APIRouter()

# DB Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------
# Division APIs
# -------------------------

@router.post("/divisions")
def add_division(division: schemas.DivisionCreate, db: Session = Depends(get_db)):
    new_division = models.Division(**division.dict())
    db.add(new_division)
    db.commit()
    return {"message": "Division added successfully"}

@router.get("/divisions")
def get_divisions(db: Session = Depends(get_db)):
    return db.query(models.Division).all()

@router.delete("/divisions/{division_id}")
def delete_division(division_id: int, db: Session = Depends(get_db)):
    division = db.query(models.Division).filter(models.Division.id == division_id).first()
    if division:
        db.delete(division)
        db.commit()
    return {"message": "Division deleted successfully"}

# -------------------------
# Teacher APIs
# -------------------------

@router.post("/teachers")
def add_teacher(teacher: schemas.TeacherCreate, db: Session = Depends(get_db)):
    new_teacher = models.Teacher(**teacher.dict())
    db.add(new_teacher)
    db.commit()
    return {"message": "Teacher added successfully"}

@router.get("/teachers")
def get_teachers(db: Session = Depends(get_db)):
    return db.query(models.Teacher).all()

@router.delete("/teachers/{teacher_id}")
def delete_teacher(teacher_id: int, db: Session = Depends(get_db)):
    teacher = db.query(models.Teacher).filter(models.Teacher.id == teacher_id).first()
    if teacher:
        db.delete(teacher)
        db.commit()
    return {"message": "Teacher deleted successfully"}

# -------------------------
# Subject APIs
# -------------------------

@router.post("/subjects")
def add_subject(subject: schemas.SubjectCreate, db: Session = Depends(get_db)):
    new_subject = models.Subject(**subject.dict())
    db.add(new_subject)
    db.commit()
    return {"message": "Subject added successfully"}

@router.get("/subjects")
def get_subjects(db: Session = Depends(get_db)):
    return db.query(models.Subject).all()

@router.delete("/subjects/{subject_id}")
def delete_subject(subject_id: int, db: Session = Depends(get_db)):
    subject = db.query(models.Subject).filter(models.Subject.id == subject_id).first()
    if subject:
        db.delete(subject)
        db.commit()
    return {"message": "Subject deleted successfully"}

# -------------------------
# Subject ↔ Teacher Mapping
# -------------------------

@router.post("/subject-teachers")
def assign_teacher(
    mapping: schemas.SubjectTeacherCreate,
    db: Session = Depends(get_db)
):
    new_mapping = models.SubjectTeacher(**mapping.dict())
    db.add(new_mapping)
    db.commit()
    return {"message": "Teacher assigned to subject successfully"}

# -------------------------
# Timetable Configuration
# -------------------------

@router.post("/config")
def add_config(config: schemas.TimetableConfigCreate, db: Session = Depends(get_db)):
    new_config = models.TimetableConfig(**config.dict())
    db.add(new_config)
    db.commit()
    return {"message": "Timetable configuration saved"}
