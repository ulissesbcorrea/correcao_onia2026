from flask import jsonify


def register_error_handlers(flask_app):
    @flask_app.errorhandler(400)
    def bad_request(error):
        return jsonify({"error": "Bad request", "message": str(error)}), 400

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
