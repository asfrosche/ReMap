import os
import logging
from flask import Flask, render_template, send_from_directory
from bot import user_locations, start_bot
import threading
from common import create_map

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "default-secret-key")

@app.route('/')
def show_map():
    try:
        if not user_locations:
            return render_template('map.html', user_locations={})

        # Create the map and get country users data
        map_obj, country_users = create_map(user_locations)

        # Get the HTML representation of the map
        map_html = map_obj._repr_html_()

        return render_template(
            'map.html',
            user_locations=user_locations,
            map_html=map_html
        )
    except Exception as e:
        logger.error(f"Error showing map: {str(e)}")
        return "Error generating map. Please try again later.", 500

@app.route('/static/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

def run_flask():
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)

if __name__ == '__main__':
    # Start the Discord bot in a separate thread
    bot_thread = threading.Thread(target=start_bot)
    bot_thread.start()

    # Start Flask server
    run_flask()