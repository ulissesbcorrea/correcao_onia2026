from flask import Flask, jsonify, render_template, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity
from config import config_map
from app.extensions import db, migrate, jwt


def create_app(config_name=None):
    if config_name is None:
        config_name = "default"

    flask_app = Flask(__name__)
    flask_app.config.from_object(config_map.get(config_name, config_map["default"]))

    db.init_app(flask_app)
    migrate.init_app(flask_app, db)
    jwt.init_app(flask_app)

    # Import route modules FIRST so @bp.route decorators execute before registration
    import app.auth.routes  # noqa
    import app.upload.routes  # noqa
    import app.fraud.routes  # noqa
    import app.review.routes  # noqa
    import app.distribution.routes  # noqa
    import app.dashboard.routes  # noqa

    from app.auth import auth_bp
    from app.upload import upload_bp
    from app.fraud import fraud_bp
    from app.review import review_bp
    from app.distribution import distribution_bp
    from app.dashboard import dashboard_bp

    flask_app.register_blueprint(auth_bp, url_prefix="/api/auth")
    flask_app.register_blueprint(upload_bp, url_prefix="/api/upload")
    flask_app.register_blueprint(fraud_bp, url_prefix="/api/fraud")
    flask_app.register_blueprint(review_bp, url_prefix="/api/review")
    flask_app.register_blueprint(distribution_bp, url_prefix="/api/distribution")
    flask_app.register_blueprint(dashboard_bp, url_prefix="/api/dashboard")

    from app.models import Evaluator

    @flask_app.route("/")
    @flask_app.route("/dashboard")
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

    @flask_app.route("/login")
    def login_page():
        return render_template("login.html")

    @flask_app.route("/logout")
    def logout():
        return redirect(url_for("login_page"))

    @flask_app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request"}), 400

    @flask_app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"error": "Unauthorized"}), 401

    @flask_app.errorhandler(403)
    def forbidden(error):
        return jsonify({"error": "Forbidden"}), 403

    @flask_app.errorhandler(404)
    def not_found(error):
        return jsonify({"error": "Not found"}), 404

    @flask_app.errorhandler(500)
    def internal_error(error):
        return jsonify({"error": "Internal server error"}), 500

    return flask_app
