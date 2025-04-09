import sys
import os
import logging
from flask import Flask, redirect

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create a simple Flask app that redirects to our FastAPI app
app = Flask(__name__)

@app.route('/')
def index():
    # Redirect to the FastAPI app running on port 8000
    return redirect('/static/modern-ui.html')

@app.route('/<path:path>')
def proxy(path):
    # Serve static files
    if path.startswith('static/'):
        return app.send_static_file(path[7:])
    # Otherwise redirect to the main page
    return redirect('/static/modern-ui.html')

# Add static folder
app.static_folder = 'nexus-ai-addon/nexus/static'

# This is used by Gunicorn to find the Flask app
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)