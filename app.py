from flask import (
    Flask,
    render_template,
    request,
    jsonify,
    send_from_directory
)

from flask_socketio import SocketIO, emit
from datetime import datetime
from werkzeug.utils import secure_filename

import sqlite3
import os
import uuid


# =========================================
# FLASK CONFIGURATION
# =========================================

app = Flask(__name__)

app.config["SECRET_KEY"] = "lan-chat-secret-key"

# Maximum file upload size = 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

socketio = SocketIO(
    app,
    cors_allowed_origins="*"
)


# =========================================
# DATABASE CONFIGURATION
# =========================================

BASE_DIR = os.path.dirname(
    os.path.abspath(__file__)
)

DATABASE = os.path.join(
    BASE_DIR,
    "chat.db"
)


# =========================================
# FILE UPLOAD CONFIGURATION
# =========================================

UPLOAD_FOLDER = os.path.join(
    BASE_DIR,
    "uploads"
)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER


# Create uploads folder if it doesn't exist
os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# =========================================
# DATABASE CONNECTION
# =========================================

def get_db():

    conn = sqlite3.connect(
        DATABASE
    )

    conn.row_factory = sqlite3.Row

    return conn


# =========================================
# INITIALIZE DATABASE
# =========================================

def init_db():

    conn = get_db()

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_type TEXT NOT NULL,
            sender TEXT NOT NULL,
            receiver TEXT,
            message TEXT NOT NULL,
            timestamp TEXT NOT NULL
        )
        """
    )

    conn.commit()

    conn.close()


# =========================================
# SAVE MESSAGE
# =========================================

def save_message(
    message_type,
    sender,
    receiver,
    message,
    timestamp
):

    conn = get_db()

    conn.execute(
        """
        INSERT INTO messages
        (
            message_type,
            sender,
            receiver,
            message,
            timestamp
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            message_type,
            sender,
            receiver,
            message,
            timestamp
        )
    )

    conn.commit()

    conn.close()


# =========================================
# GET PUBLIC HISTORY
# =========================================

def get_public_messages():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            message_type,
            sender,
            receiver,
            message,
            timestamp
        FROM messages
        WHERE message_type = 'public'
        ORDER BY id ASC
        """
    ).fetchall()

    conn.close()

    history = []

    for row in rows:

        history.append(
            {
                "type": row["message_type"],
                "username": row["sender"],
                "receiver": row["receiver"],
                "message": row["message"],
                "time": row["timestamp"]
            }
        )

    return history


# =========================================
# GET PRIVATE HISTORY
# =========================================

def get_private_messages(
    username1,
    username2
):

    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            message_type,
            sender,
            receiver,
            message,
            timestamp
        FROM messages
        WHERE message_type = 'private'
        AND (
            (sender = ? AND receiver = ?)
            OR
            (sender = ? AND receiver = ?)
        )
        ORDER BY id ASC
        """,
        (
            username1,
            username2,
            username2,
            username1
        )
    ).fetchall()

    conn.close()

    history = []

    for row in rows:

        history.append(
            {
                "type": row["message_type"],
                "username": row["sender"],
                "receiver": row["receiver"],
                "message": row["message"],
                "time": row["timestamp"]
            }
        )

    return history


# =========================================
# CONNECTED USERS
# =========================================

# socket ID -> username

users = {}


# =========================================
# HOME PAGE
# =========================================

@app.route("/")
def index():

    return render_template(
        "index.html"
    )


# =========================================
# FILE UPLOAD
# =========================================

@app.route(
    "/upload",
    methods=["POST"]
)
def upload_file():

    # Check whether a file was provided
    if "file" not in request.files:

        return jsonify(
            {
                "success": False,
                "error": "No file was provided."
            }
        ), 400


    file = request.files["file"]


    # Check empty filename
    if file.filename == "":

        return jsonify(
            {
                "success": False,
                "error": "No file was selected."
            }
        ), 400


    # Make filename safe
    original_filename = file.filename

    safe_filename = secure_filename(
        original_filename
    )


    # Make sure filename is still valid
    if not safe_filename:

        return jsonify(
            {
                "success": False,
                "error": "Invalid file name."
            }
        ), 400


    # Create unique filename
    unique_filename = (
        str(uuid.uuid4())
        + "_"
        + safe_filename
    )


    # Complete file path
    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        unique_filename
    )


    # Save file
    file.save(file_path)


    # Get file size
    file_size = os.path.getsize(
        file_path
    )


    # Return file information
    return jsonify(
        {
            "success": True,
            "file_name": original_filename,
            "stored_name": unique_filename,
            "file_size": file_size,
            "file_type": file.content_type,
            "file_url": (
                "/uploads/"
                + unique_filename
            )
        }
    )


# =========================================
# SERVE UPLOADED FILES
# =========================================

@app.route(
    "/uploads/<filename>"
)
def uploaded_file(filename):

    return send_from_directory(
        app.config["UPLOAD_FOLDER"],
        filename,
        as_attachment=True
    )


# =========================================
# USER JOIN
# =========================================

@socketio.on("join")
def handle_join(username):

    username = (
        username.strip()[:20]
        or "Guest"
    )

    users[request.sid] = username

    emit(
        "system_message",
        {
            "message":
                f"{username} joined the chat.",
            "time":
                now()
        },
        broadcast=True
    )

    emit(
        "user_list",
        list(users.values()),
        broadcast=True
    )


# =========================================
# PUBLIC HISTORY REQUEST
# =========================================

@socketio.on("get_public_history")
def handle_public_history():

    history = get_public_messages()

    emit(
        "message_history",
        {
            "conversation": "public",
            "messages": history
        },
        to=request.sid
    )


# =========================================
# PRIVATE HISTORY REQUEST
# =========================================

@socketio.on("get_private_history")
def handle_private_history(data):

    current_user = users.get(
        request.sid
    )

    if not current_user:
        return


    other_user = str(
        data.get(
            "username",
            ""
        )
    ).strip()


    if not other_user:
        return


    history = get_private_messages(
        current_user,
        other_user
    )


    emit(
        "message_history",
        {
            "conversation": other_user,
            "messages": history
        },
        to=request.sid
    )


# =========================================
# SEND MESSAGE
# =========================================

@socketio.on("send_message")
def handle_message(data):

    sender = users.get(
        request.sid,
        "Guest"
    )

    message = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    receiver = data.get(
        "receiver"
    )


    # Don't send empty messages
    if not message:
        return


    # Limit message length
    message = message[:1000]


    # =====================================
    # PRIVATE MESSAGE
    # =====================================

    if receiver:

        # Find receiver socket ID
        target_sid = next(
            (
                sid
                for sid, username
                in users.items()
                if username == receiver
            ),
            None
        )


        # Receiver exists
        if target_sid:

            current_time = now()

            payload = {
                "type":
                    "private",

                "username":
                    sender,

                "receiver":
                    receiver,

                "message":
                    message,

                "time":
                    current_time
            }


            # Save private message
            save_message(
                message_type="private",
                sender=sender,
                receiver=receiver,
                message=message,
                timestamp=current_time
            )


            # Send to receiver
            socketio.emit(
                "new_message",
                payload,
                to=target_sid
            )


            # Send copy to sender
            socketio.emit(
                "new_message",
                payload,
                to=request.sid
            )


        else:

            emit(
                "chat_error",
                {
                    "message":
                        f"{receiver} is no longer online."
                }
            )


    # =====================================
    # PUBLIC MESSAGE
    # =====================================

    else:

        current_time = now()

        payload = {
            "type":
                "public",

            "username":
                sender,

            "receiver":
                None,

            "message":
                message,

            "time":
                current_time
        }


        # Save public message
        save_message(
            message_type="public",
            sender=sender,
            receiver=None,
            message=message,
            timestamp=current_time
        )


        # Send to everyone
        emit(
            "new_message",
            payload,
            broadcast=True
        )


# =========================================
# USER DISCONNECT
# =========================================

@socketio.on("disconnect")
def handle_disconnect():

    username = users.pop(
        request.sid,
        None
    )


    if username:

        emit(
            "system_message",
            {
                "message":
                    f"{username} left the chat.",
                "time":
                    now()
            },
            broadcast=True
        )


        emit(
            "user_list",
            list(users.values()),
            broadcast=True
        )


# =========================================
# CURRENT TIME
# =========================================

def now():

    return datetime.now().strftime(
        "%H:%M"
    )


# =========================================
# START SERVER
# =========================================

if __name__ == "__main__":

    # Create database/table if needed
    init_db()


    print(
        "Local:   http://127.0.0.1:5000"
    )


    print(
        "Network: http://<YOUR-LAN-IP>:5000"
    )


    socketio.run(
        app,
        host="0.0.0.0",
        port=5000,
        debug=True
    )