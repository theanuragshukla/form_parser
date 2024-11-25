from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import uuid
from fields import do_the_thing, IN_PROGRESS
import json

app = Flask(__name__)
CORS(app, origins="*")

UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True) 


@app.route("/")
def index():
    return "Hello, World!"

@app.route("/upload", methods=["POST"])
def upload_file():
    try:
        if "file" not in request.files:
            return jsonify({"status": False, "data": None, "error": "No file part in the request"}), 400

        file = request.files["file"]

        if file.filename == "":
            return jsonify({"status": False, "data": None, "error": "No file selected"}), 400

        if not file.filename.lower().endswith(".pdf"):
            return jsonify({"status": False, "data": None, "error": "Only PDF files are allowed"}), 400

        uid = str(uuid.uuid4())

        file_path = os.path.join(UPLOAD_FOLDER, f"{uid}.pdf")
        file.save(file_path)
        do_the_thing(file_path)

        return jsonify({"status": True, "data": {"uid": uid}, "error": None}), 200

    except Exception as e:
        return jsonify({"status": False, "data": None, "error": str(e)}), 500


@app.route("/get-output/<uid>", methods=["GET"])
def analyze(uid):
    while(uid in IN_PROGRESS):
        pass
    with open(f"uploads/{uid}_out.json", "r") as f:
        data = json.load(f)
        return jsonify({"status": True, "data": data, "error": None}), 200

@app.route("/uploads/<uid>")
def read_pdf(uid):
    if('.' in uid):
        return send_from_directory(UPLOAD_FOLDER, f'{uid}')
    return send_from_directory(UPLOAD_FOLDER, f'{uid}.pdf')




if __name__ == "__main__":
    app.run(debug=True)

