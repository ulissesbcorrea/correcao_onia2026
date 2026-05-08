from flask import request, jsonify, render_template, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from app.dashboard import dashboard_bp
from app.auth.decorators import evaluator_required, admin_required
from app.extensions import db
from app.models import Student, Review, FraudFlag, ApprovalCounter, School, Evaluator
from app.utils.pagination import paginate_query


@dashboard_bp.route("/summary", methods=["GET"])
@evaluator_required
def dashboard_summary_api():
    total = Student.query.count()
    approved = Student.query.filter_by(status="approved").count()
    rejected = Student.query.filter_by(status="rejected").count()
    pending = Student.query.filter_by(status="pending").count()
    flagged = Student.query.filter_by(is_flagged=True).count()
    schools_count = School.query.count()
    evaluators_count = Evaluator.query.filter_by(is_active=True).count()
    counter = db.session.get(ApprovalCounter, 1)

    return jsonify({
        "total_students": total,
        "approved": approved,
        "rejected": rejected,
        "pending": pending,
        "flagged": flagged,
        "schools": schools_count,
        "evaluators": evaluators_count,
        "approval_goal": counter.to_dict() if counter else None,
    })


@dashboard_bp.route("/submissions", methods=["GET"])
@evaluator_required
def submission_list_api():
    query = Student.query.join(School)

    status = request.args.get("status")
    if status:
        query = query.filter(Student.status == status)

    school = request.args.get("school")
    if school:
        query = query.filter(School.name.ilike(f"%{school}%"))

    polo = request.args.get("polo")
    if polo:
        query = query.filter(School.polo.ilike(f"%{polo}%"))

    has_fraud = request.args.get("has_fraud")
    if has_fraud is not None:
        query = query.filter(Student.is_flagged == (has_fraud.lower() == "true"))

    search = request.args.get("search")
    if search:
        query = query.filter(Student.name.ilike(f"%{search}%"))

    sort_by = request.args.get("sort_by", "name")
    order = request.args.get("order", "asc")

    sort_map = {
        "name": Student.name,
        "score": Student.score,
        "school": School.name,
        "polo": School.polo,
        "status": Student.status,
    }
    sort_col = sort_map.get(sort_by, Student.name)
    if order == "desc":
        query = query.order_by(sort_col.desc(), Student.name.asc())
    else:
        query = query.order_by(sort_col.asc(), Student.name.asc())

    result = paginate_query(query)
    items = []
    for s in result["items"]:
        d = s.to_dict()
        d["polo"] = s.school.polo if s.school else None
        items.append(d)
    result["items"] = items
    return jsonify(result)


@dashboard_bp.route("/counter", methods=["GET"])
@evaluator_required
def approval_counter_api():
    counter = db.session.get(ApprovalCounter, 1)
    if not counter:
        counter = ApprovalCounter(id=1, count=0, goal=200)
        db.session.add(counter)
        db.session.commit()
    return jsonify(counter.to_dict())


@dashboard_bp.route("/polos", methods=["GET"])
@evaluator_required
def list_polos():
    polos = db.session.query(School.polo).filter(School.polo.isnot(None), School.polo != "").distinct().order_by(School.polo).all()
    return jsonify({"polos": [p[0] for p in polos]})


# HTML page routes

@dashboard_bp.route("", methods=["GET"])
@dashboard_bp.route("/", methods=["GET"])
@jwt_required(optional=True)
def dashboard_page():
    user_id = get_jwt_identity()
    if not user_id:
        return redirect(url_for("login_page"))
    user = db.session.get(Evaluator, int(user_id))
    if not user:
        return redirect(url_for("login_page"))
    if user.role == "admin":
        return render_template("admin/dashboard.html", session={"user": user.to_dict()})
    return render_template("evaluator/assignments.html", session={"user": user.to_dict()})


@dashboard_bp.route("/login")
def login_page():
    return render_template("login.html")
