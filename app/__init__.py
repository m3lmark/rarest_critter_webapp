from flask import Flask

app = Flask(__name__)

from app.routes import bp as main_bp
app.register_blueprint(main_bp)