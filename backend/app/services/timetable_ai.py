import random
from collections import defaultdict
from sqlalchemy.orm import Session

from app.models import Subject, TimetableConfig, Division, SubjectTeacher, Room, TeacherAvailability
from app.services.slot_generator import generate_weekly_slots
from app.services.constraints import (
    extract_lecture_slots,
    expand_subjects,
    enforce_nep_policies,
    violates_weekly_hours,
    get_consecutive_slots
)
from app.services.genetic_algorithm import (
    create_chromosome,
    fitness,
    crossover,
    mutate,
    local_search,
    create_next_generation
)


def generate_ai_timetable(db: Session):
    """
    Generate an optimized timetable using genetic algorithm with:
    - Teacher availability constraints
    - Room allocation
    - Consecutive lab handling
    - Workload balancing
    """
    config = db.query(TimetableConfig).order_by(TimetableConfig.id.desc()).first()
    subjects = db.query(Subject).all()
    divisions = db.query(Division).all()
    mappings = db.query(SubjectTeacher).all()
    rooms = db.query(Room).filter(Room.is_available == True).all()
    
    if not config or not subjects or not divisions:
        return {"timetable": [], "error": "Missing configuration, subjects, or divisions"}

    subjects = enforce_nep_policies(subjects)

    # Build subjects map with teacher assignments
    subject_teacher_map = defaultdict(list)
    for m in mappings:
        subject_teacher_map[m.subject_id].append(m.teacher_id)

    subjects_map = {}
    for s in subjects:
        subjects_map[s.name] = {
            "category": s.category,
            "hours": s.weekly_hours,
            "is_lab": s.is_lab,
            "teachers": subject_teacher_map.get(s.id, []),
            "preferred_room_id": s.preferred_room_id,
            "requires_lab": s.requires_lab
        }

    # Get teacher availability
    teacher_availability = {}
    avail_records = db.query(TeacherAvailability).all()
    for a in avail_records:
        key = (a.teacher_id, a.day)
        teacher_availability[key] = a.is_available

    # Generate slots
    weekly_slots = generate_weekly_slots(
        config.working_days,
        config.start_time,
        config.end_time,
        config.break_count,
        config.break_duration
    )

    lecture_slots = extract_lecture_slots(weekly_slots)
    consecutive_slots = get_consecutive_slots(lecture_slots)

    # Create expanded slots (per division)
    expanded_slots = []
    for division in divisions:
        for slot in lecture_slots:
            expanded_slots.append({
                "division": division.name,
                "day": slot["day"],
                "time": slot["time"]
            })

    slot_count = len(expanded_slots)

    # Expand subjects to units
    subject_units = expand_subjects(subjects, divisions)
    random.shuffle(subject_units)
    subject_units = subject_units[:slot_count]

    # Create initial population
    population_size = 20
    population = [
        create_chromosome(subject_units, slot_count)
        for _ in range(population_size)
    ]

    # Genetic algorithm parameters
    generations = 60
    mutation_rate = 0.15

    # Evolution loop
    for gen in range(generations):
        # Filter invalid chromosomes
        valid_population = [c for c in population if not violates_weekly_hours(c, subjects_map)]
        
        if not valid_population:
            # Recreate population if all invalid
            population = [
                create_chromosome(subject_units, slot_count)
                for _ in range(population_size)
            ]
            continue
        
        # Create next generation
        population = create_next_generation(
            valid_population, 
            subjects_map, 
            expanded_slots,
            mutation_rate=mutation_rate,
            elite_size=3
        )
        
        # Adaptive mutation rate
        if gen > 30:
            mutation_rate = 0.1
        if gen > 50:
            mutation_rate = 0.05

    # Get best solution
    best = max(population, key=lambda c: fitness(
        c, subjects_map, expanded_slots, consecutive_slots, teacher_availability
    ))
    
    # Apply local search for refinement
    best = local_search(best, subjects_map, expanded_slots, max_iterations=20)

    # Build result structure
    division_day_map = defaultdict(lambda: defaultdict(list))
    room_allocations = defaultdict(list)

    for slot, gene in zip(expanded_slots, best):
        division = slot["division"]
        day = slot["day"]
        time = slot["time"]

        if gene is None:
            division_day_map[division][day].append({
                "time": time,
                "subject": "FREE",
                "type": "Free",
                "room": None,
                "teachers": []
            })
            continue

        gene_division, subject_name, is_lab = gene if len(gene) > 2 else (*gene, False)
        
        if gene_division != division:
            division_day_map[division][day].append({
                "time": time,
                "subject": "FREE",
                "type": "Free",
                "room": None,
                "teachers": []
            })
            continue

        subject = next((s for s in subjects if s.name == subject_name), None)
        subject_info = subjects_map.get(subject_name, {})
        teachers = subject_info.get("teachers", [])
        
        # Allocate room
        room_id = None
        room_name = None
        if rooms:
            if subject and subject.preferred_room_id:
                room_id = subject.preferred_room_id
            else:
                # Find suitable room
                room_type = "Lab" if is_lab else "Lecture"
                suitable_rooms = [r for r in rooms if r.room_type == room_type]
                if suitable_rooms:
                    # Check availability
                    for room in suitable_rooms:
                        room_key = (room.id, day, time)
                        if room_key not in room_allocations:
                            room_id = room.id
                            break
            
            if room_id:
                room_allocations[(room_id, day, time)].append(division)
                room = next((r for r in rooms if r.id == room_id), None)
                room_name = room.name if room else None

        division_day_map[division][day].append({
            "time": time,
            "subject": subject_name,
            "type": "Lab" if is_lab else "Theory",
            "room": room_name,
            "teachers": teachers
        })

    # Build result in frontend-friendly format
    result = []
    for division, days in division_day_map.items():
        result.append({
            "division": division,
            "days": [
                {
                    "day": day,
                    "slots": sorted(slots, key=lambda s: s["time"])
                }
                for day, slots in days.items()
            ]
        })

    # Calculate statistics
    fitness_score = fitness(best, subjects_map, expanded_slots, consecutive_slots, teacher_availability)
    
    return {
        "timetable": result,
        "statistics": {
            "fitness_score": fitness_score,
            "total_slots": slot_count,
            "generations": generations
        }
    }
