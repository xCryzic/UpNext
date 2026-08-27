from flask import Flask, jsonify
from flask_cors import CORS

from config import Config
from database import get_db, init_db
from routes.auth import auth_bp
from routes.creators import creators_bp
from routes.projects import projects_bp
from routes.reports import reports_bp
from routes.socials import socials_bp


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    CORS(app, origins=[app.config["FRONTEND_ORIGIN"]], supports_credentials=True)
    with app.app_context():
        init_db()

    app.register_blueprint(auth_bp)
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
        connection = get_db()
        try:
            tables = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall()
            return jsonify({"tables": [row["name"] for row in tables]})
        finally:
            connection.close()

    @app.errorhandler(404)
    def not_found(_error):
        return jsonify({"error": "Not found."}), 404

    @app.errorhandler(500)
    def server_error(_error):
        return jsonify({"error": "Internal server error."}), 500

    return app


app = create_app()


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=app.config.get("DEBUG", False))
