from pathlib import Path

from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

from config import Config
from sqlalchemy import inspect
from database import configure_sqlalchemy, init_db, remove_sqlalchemy_session
from routes.auth import auth_bp
from routes.account import account_bp
from routes.admin import admin_bp
from routes.creators import creators_bp
from routes.projects import projects_bp
from routes.reports import reports_bp
from routes.socials import socials_bp


def create_app(config_class=Config):
    frontend_dist = Path(__file__).resolve().parent.parent / "dist"
    app = Flask(__name__, static_folder=str(frontend_dist / "assets"), static_url_path="/assets")
    app.config.from_object(config_class)
    configure_sqlalchemy(app.config)
    CORS(app, origins=[app.config["FRONTEND_ORIGIN"]], supports_credentials=True)
    # Production schemas are created by Alembic, never implicitly at startup.
    if app.config["APP_ENV"] != "production":
        with app.app_context():
            init_db(app.config)
    app.logger.info("Database configured using %s.", (app.config.get("DATABASE_URL") or "development SQLite fallback").split(":", 1)[0])

    @app.teardown_appcontext
    def cleanup_sqlalchemy(_error=None):
        remove_sqlalchemy_session()

    app.register_blueprint(auth_bp)
    app.register_blueprint(account_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(creators_bp)
    app.register_blueprint(socials_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(reports_bp)

    @app.get("/api/health")
    def health():
        return jsonify({"status": "ok", "service": "upnext-backend"})

    @app.get("/api/db-info")
    def db_info():
        if not app.config.get("EXPOSE_DB_INFO", False):
            return jsonify({"error": "Not found."}), 404
        from database import _engine
        return jsonify({"tables": sorted(inspect(_engine).get_table_names())})

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(400)
    def bad_request(_error):
        return jsonify({"error": "Bad request."}), 400

    @app.errorhandler(401)
    def unauthorized(_error):
        return jsonify({"error": "Authentication required."}), 401

    @app.errorhandler(403)
    def forbidden(_error):
        return jsonify({"error": "Forbidden."}), 403

    @app.errorhandler(409)
    def conflict(_error):
        return jsonify({"error": "Conflict."}), 409

    @app.errorhandler(429)
    def rate_limited(_error):
        return jsonify({"error": "Too many requests. Please try again shortly."}), 429

    @app.errorhandler(500)
    def server_error(_error):
        return jsonify({"error": "Internal server error."}), 500

    @app.route("/", defaults={"path": ""})
    @app.route("/<path:path>")
    def frontend(path):
        if path == "api" or path.startswith("api/"):
            return jsonify({"error": "Not found."}), 404
        requested = frontend_dist / path
        if path and requested.is_file():
            return send_from_directory(frontend_dist, path)
        if (frontend_dist / "index.html").is_file():
            return send_from_directory(frontend_dist, "index.html")
        return jsonify({"error": "Frontend build not found."}), 404

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False))
