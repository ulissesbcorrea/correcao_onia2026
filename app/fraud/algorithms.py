"""Fraud detection algorithms for ONIA exam data."""

from app.extensions import db
from app.models import Student, School, Answer, Justification, FraudFlag
from app.upload.image_service import find_student_images
from rapidfuzz import fuzz


def detect_identical_answers_same_school(batch_id):
    """Detect students from the same school with identical answers."""
    new_flags = 0

    # Get all students from this batch
    students = Student.query.filter_by(import_batch_id=batch_id).all()
    schools_map = {}
    for s in students:
        schools_map.setdefault(s.school_id, []).append(s)

    for school_id, school_students in schools_map.items():
        if len(school_students) < 2:
            continue

        for i in range(len(school_students)):
            for j in range(i + 1, len(school_students)):
                s1 = school_students[i]
                s2 = school_students[j]

                # Get answers for both students
                answers1 = {a.question_number: a.selected_option for a in s1.answers}
                answers2 = {a.question_number: a.selected_option for a in s2.answers}

                if not answers1 or not answers2:
                    continue

                # Count matching answers
                all_questions = set(list(answers1.keys()) + list(answers2.keys()))
                if not all_questions:
                    continue

                matches = 0
                for q in all_questions:
                    if answers1.get(q) == answers2.get(q) and answers1.get(q) is not None:
                        matches += 1

                total = len(all_questions)
                if total == 0:
                    continue

                similarity = matches / total

                level = None
                reason = None
                if similarity >= 1.0:
                    level = "high"
                    reason = f"Respostas 100% idênticas ({matches}/{total}) na mesma escola"
                elif similarity >= 0.8:
                    level = "medium"
                    reason = f"Respostas {similarity*100:.0f}% similares ({matches}/{total}) na mesma escola"

                if level:
                    # Check if flag already exists for this pair
                    existing = FraudFlag.query.filter_by(
                        student_id=s1.id,
                        related_student_id=s2.id,
                        algorithm_name="identical_answers",
                    ).first()
                    if not existing:
                        flag = FraudFlag(
                            student_id=s1.id,
                            related_student_id=s2.id,
                            source="algorithmic",
                            level=level,
                            reason=reason,
                            algorithm_name="identical_answers",
                        )
                        db.session.add(flag)

                        s1.is_flagged = True
                        if not s1.flag_level or (level == "high" and s1.flag_level != "high"):
                            s1.flag_level = level

                        new_flags += 1

    db.session.commit()
    return {"algorithm": "identical_answers_same_school", "new_flags": new_flags}


def detect_similar_justifications(batch_id):
    """Detect students with identical justification photo hashes in same school."""
    new_flags = 0

    students = Student.query.filter_by(import_batch_id=batch_id).all()
    schools_map = {}
    for s in students:
        schools_map.setdefault(s.school_id, []).append(s)

    for school_id, school_students in schools_map.items():
        if len(school_students) < 2:
            continue

        for i in range(len(school_students)):
            for j in range(i + 1, len(school_students)):
                s1 = school_students[i]
                s2 = school_students[j]

                just1 = s1.justifications[0] if s1.justifications else None
                just2 = s2.justifications[0] if s2.justifications else None

                if not just1 or not just2:
                    continue
                if not just1.photo_hash or not just2.photo_hash:
                    continue

                if just1.photo_hash == just2.photo_hash:
                    existing = FraudFlag.query.filter_by(
                        student_id=s1.id,
                        related_student_id=s2.id,
                        algorithm_name="identical_justification",
                    ).first()
                    if not existing:
                        flag = FraudFlag(
                            student_id=s1.id,
                            related_student_id=s2.id,
                            source="algorithmic",
                            level="critical",
                            reason="Justificativas idênticas (mesmo hash de foto) na mesma escola",
                            algorithm_name="identical_justification",
                        )
                        db.session.add(flag)

                        s1.is_flagged = True
                        s1.flag_level = "critical"

                        new_flags += 1

    db.session.commit()
    return {"algorithm": "similar_justifications", "new_flags": new_flags}


def detect_no_justification(batch_id):
    """Mark students without justifications as rejected."""
    count = 0
    students = Student.query.filter_by(
        import_batch_id=batch_id, status="pending"
    ).all()

    for s in students:
        if not s.justifications:
            s.status = "rejected"
            count += 1

    db.session.commit()
    return {"algorithm": "no_justification", "rejected": count}


def run_all_fraud_detection(batch_id, skip_no_justification=True):
    """Run all fraud detection algorithms."""
    results = {}
    if not skip_no_justification:
        results["no_justification"] = detect_no_justification(batch_id)
    results["identical_answers"] = detect_identical_answers_same_school(batch_id)
    results["identical_justifications"] = detect_similar_justifications(batch_id)
    results["ocr_similarity"] = detect_ocr_text_similarity(batch_id)
    return results


def detect_ocr_text_similarity(batch_id):
    """Compare OCR-extracted text from justifications of same-school students."""
    from app.fraud.ocr import extract_text

    new_flags = 0
    students = Student.query.filter_by(import_batch_id=batch_id).all()
    schools_map = {}
    for s in students:
        schools_map.setdefault(s.school_id, []).append(s)

    for school_id, school_students in schools_map.items():
        if len(school_students) < 2:
            continue

        # Pre-extract texts for efficiency
        student_texts = {}
        for s in school_students:
            images = find_student_images(s.xlsx_id, s.name)
            paths = [img["path"] for img in images]
            if paths:
                text = extract_text(paths[0])  # answer_sheet usually
                if text and len(text) > 20:
                    student_texts[s.id] = text

        for i in range(len(school_students)):
            for j in range(i + 1, len(school_students)):
                s1 = school_students[i]
                s2 = school_students[j]
                t1 = student_texts.get(s1.id)
                t2 = student_texts.get(s2.id)
                if not t1 or not t2:
                    continue

                similarity = fuzz.ratio(t1, t2) / 100.0

                level = None
                reason = None
                if similarity >= 0.90:
                    level = "critical"
                    reason = f"Textos OCR {similarity*100:.0f}% idênticos na mesma escola"
                elif similarity >= 0.75:
                    level = "high"
                    reason = f"Textos OCR {similarity*100:.0f}% similares na mesma escola"

                if level:
                    existing = FraudFlag.query.filter_by(
                        student_id=s1.id,
                        related_student_id=s2.id,
                        algorithm_name="ocr_similarity",
                    ).first()
                    if not existing:
                        flag = FraudFlag(
                            student_id=s1.id,
                            related_student_id=s2.id,
                            source="algorithmic",
                            level=level,
                            reason=reason,
                            algorithm_name="ocr_similarity",
                        )
                        db.session.add(flag)
                        s1.is_flagged = True
                        if not s1.flag_level or level == "critical":
                            s1.flag_level = level
                        new_flags += 1

    db.session.commit()
    return {"algorithm": "ocr_similarity", "new_flags": new_flags}
