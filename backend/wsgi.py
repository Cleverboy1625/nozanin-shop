import os
import sys

from a2wsgi import ASGIMiddleware

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main import app

application = ASGIMiddleware(app)