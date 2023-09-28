from app import app


@app.route("/")
def index():
    message = f"""Hello from Flask"""
    return message
