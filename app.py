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
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 MB

socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode="threading"
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

os.makedirs(
    UPLOAD_FOLDER,
    exist_ok=True
)


# =========================================
# DATABASE CONNECTION
# =========================================

def get_db():

    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row

    return conn


# =========================================
# DATABASE INITIALIZATION / MIGRATION
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
            timestamp TEXT NOT NULL,
            content_type TEXT NOT NULL DEFAULT 'text',
            file_name TEXT,
            file_url TEXT,
            file_size INTEGER,
            file_type TEXT,
            is_deleted INTEGER NOT NULL DEFAULT 0,
            is_edited INTEGER NOT NULL DEFAULT 0
        )
        """
    )

    # Check existing columns
    columns = {
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(messages)"
        ).fetchall()
    }

    # Migrate old databases
    migrations = {

        "content_type":
            "ALTER TABLE messages ADD COLUMN "
            "content_type TEXT NOT NULL DEFAULT 'text'",

        "file_name":
            "ALTER TABLE messages ADD COLUMN file_name TEXT",

        "file_url":
            "ALTER TABLE messages ADD COLUMN file_url TEXT",

        "file_size":
            "ALTER TABLE messages ADD COLUMN file_size INTEGER",

        "file_type":
            "ALTER TABLE messages ADD COLUMN file_type TEXT",

        "is_deleted":
            "ALTER TABLE messages ADD COLUMN "
            "is_deleted INTEGER NOT NULL DEFAULT 0",

        "is_edited":
            "ALTER TABLE messages ADD COLUMN "
            "is_edited INTEGER NOT NULL DEFAULT 0"
    }

    for column, sql in migrations.items():

        if column not in columns:
            conn.execute(sql)

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
    timestamp,
    content_type="text",
    file_name=None,
    file_url=None,
    file_size=None,
    file_type=None
):

    conn = get_db()

    cursor = conn.execute(
        """
        INSERT INTO messages
        (
            message_type,
            sender,
            receiver,
            message,
            timestamp,
            content_type,
            file_name,
            file_url,
            file_size,
            file_type
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            message_type,
            sender,
            receiver,
            message,
            timestamp,
            content_type,
            file_name,
            file_url,
            file_size,
            file_type
        )
    )

    message_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return message_id


# =========================================
# CONVERT DATABASE ROW TO MESSAGE
# =========================================

def row_to_message(row):

    return {
        "id": row["id"],
        "type": row["message_type"],
        "username": row["sender"],
        "receiver": row["receiver"],
        "message": row["message"],
        "time": row["timestamp"],
        "content_type": row["content_type"],
        "file_name": row["file_name"],
        "file_url": row["file_url"],
        "file_size": row["file_size"],
        "file_type": row["file_type"],
        "is_deleted": bool(row["is_deleted"]),
        "is_edited": bool(row["is_edited"])
    }


# =========================================
# GET PUBLIC MESSAGE HISTORY
# =========================================

def get_public_messages():

    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            id,
            message_type,
            sender,
            receiver,
            message,
            timestamp,
            content_type,
            file_name,
            file_url,
            file_size,
            file_type,
            is_deleted,
            is_edited
        FROM messages
        WHERE message_type = 'public'
        ORDER BY id ASC
        """
    ).fetchall()

    conn.close()

    return [
        row_to_message(row)
        for row in rows
    ]


# =========================================
# GET PRIVATE MESSAGE HISTORY
# =========================================

def get_private_messages(
    username1,
    username2
):

    conn = get_db()

    rows = conn.execute(
        """
        SELECT
            id,
            message_type,
            sender,
            receiver,
            message,
            timestamp,
            content_type,
            file_name,
            file_url,
            file_size,
            file_type,
            is_deleted,
            is_edited
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

    return [
        row_to_message(row)
        for row in rows
    ]


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

    if "file" not in request.files:

        return jsonify({
            "success": False,
            "error": "No file was provided."
        }), 400

    file = request.files["file"]

    if not file or file.filename == "":

        return jsonify({
            "success": False,
            "error": "No file was selected."
        }), 400

    original_filename = file.filename

    safe_filename = secure_filename(
        original_filename
    )

    if not safe_filename:

        return jsonify({
            "success": False,
            "error": "Invalid file name."
        }), 400

    unique_filename = (
        f"{uuid.uuid4().hex}_{safe_filename}"
    )

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        unique_filename
    )

    try:

        file.save(file_path)

        file_size = os.path.getsize(
            file_path
        )

    except Exception as error:

        if os.path.exists(file_path):
            os.remove(file_path)

        return jsonify({
            "success": False,
            "error": f"Could not save file: {error}"
        }), 500

    return jsonify({
        "success": True,
        "file_name": original_filename,
        "stored_name": unique_filename,
        "file_size": file_size,
        "file_type": (
            file.mimetype
            or "application/octet-stream"
        ),
        "file_url": (
            f"/uploads/{unique_filename}"
        )
    })


# =========================================
# FILE SIZE ERROR
# =========================================

@app.errorhandler(413)
def file_too_large(error):

    return jsonify({
        "success": False,
        "error":
            "File is too large. "
            "Maximum allowed size is 10 MB."
    }), 413


# =========================================
# SERVE UPLOADED FILES
# =========================================

@app.route(
    "/uploads/<path:filename>"
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
        str(username).strip()[:20]
        or "Guest"
    )

    users[request.sid] = username

    emit(
        "system_message",
        {
            "message":
                f"{username} joined the chat.",
            "time": now()
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
# SEND TEXT MESSAGE
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

    if not message:
        return

    message = message[:1000]

    # =====================================
    # PRIVATE MESSAGE
    # =====================================

    if receiver:

        receiver = str(
            receiver
        ).strip()

        target_sid = next(
            (
                sid
                for sid, username
                in users.items()
                if username == receiver
            ),
            None
        )

        if target_sid:

            current_time = now()

            message_id = save_message(
                message_type="private",
                sender=sender,
                receiver=receiver,
                message=message,
                timestamp=current_time,
                content_type="text"
            )

            payload = {
                "id": message_id,
                "type": "private",
                "username": sender,
                "receiver": receiver,
                "message": message,
                "time": current_time,
                "content_type": "text",
                "file_name": None,
                "file_url": None,
                "file_size": None,
                "file_type": None,
                "is_deleted": False,
                "is_edited": False
            }

            socketio.emit(
                "new_message",
                payload,
                to=target_sid
            )

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

        message_id = save_message(
            message_type="public",
            sender=sender,
            receiver=None,
            message=message,
            timestamp=current_time,
            content_type="text"
        )

        payload = {
            "id": message_id,
            "type": "public",
            "username": sender,
            "receiver": None,
            "message": message,
            "time": current_time,
            "content_type": "text",
            "file_name": None,
            "file_url": None,
            "file_size": None,
            "file_type": None,
            "is_deleted": False,
            "is_edited": False
        }

        emit(
            "new_message",
            payload,
            broadcast=True
        )


# =========================================
# SEND FILE MESSAGE
# =========================================

@socketio.on("send_file")
def handle_file_message(data):

    sender = users.get(
        request.sid
    )

    if not sender:
        return

    receiver = data.get(
        "receiver"
    )

    file_name = str(
        data.get(
            "file_name",
            ""
        )
    ).strip()

    stored_name = str(
        data.get(
            "stored_name",
            ""
        )
    ).strip()

    file_size = data.get(
        "file_size"
    )

    file_type = str(
        data.get(
            "file_type",
            "application/octet-stream"
        )
    )

    # Never trust a path from the browser
    safe_stored_name = os.path.basename(
        stored_name
    )

    if (
        not file_name
        or not safe_stored_name
        or safe_stored_name != stored_name
    ):

        emit(
            "chat_error",
            {
                "message":
                    "Invalid file information."
            }
        )
        return

    file_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        safe_stored_name
    )

    if not os.path.isfile(file_path):

        emit(
            "chat_error",
            {
                "message":
                    "Uploaded file could not be found."
            }
        )
        return

    file_url = (
        f"/uploads/{safe_stored_name}"
    )

    try:

        file_size = int(file_size)

    except (TypeError, ValueError):

        file_size = os.path.getsize(
            file_path
        )

    # =====================================
    # PRIVATE FILE
    # =====================================

    if receiver:

        receiver = str(
            receiver
        ).strip()

        target_sid = next(
            (
                sid
                for sid, username
                in users.items()
                if username == receiver
            ),
            None
        )

        if not target_sid:

            emit(
                "chat_error",
                {
                    "message":
                        f"{receiver} is no longer online."
                }
            )
            return

        current_time = now()

        message_id = save_message(
            message_type="private",
            sender=sender,
            receiver=receiver,
            message=file_name,
            timestamp=current_time,
            content_type="file",
            file_name=file_name,
            file_url=file_url,
            file_size=file_size,
            file_type=file_type
        )

        payload = {
            "id": message_id,
            "type": "private",
            "username": sender,
            "receiver": receiver,
            "message": file_name,
            "time": current_time,
            "content_type": "file",
            "file_name": file_name,
            "file_url": file_url,
            "file_size": file_size,
            "file_type": file_type,
            "is_deleted": False,
            "is_edited": False
        }

        socketio.emit(
            "new_message",
            payload,
            to=target_sid
        )

        socketio.emit(
            "new_message",
            payload,
            to=request.sid
        )

    # =====================================
    # PUBLIC FILE
    # =====================================

    else:

        current_time = now()

        message_id = save_message(
            message_type="public",
            sender=sender,
            receiver=None,
            message=file_name,
            timestamp=current_time,
            content_type="file",
            file_name=file_name,
            file_url=file_url,
            file_size=file_size,
            file_type=file_type
        )

        payload = {
            "id": message_id,
            "type": "public",
            "username": sender,
            "receiver": None,
            "message": file_name,
            "time": current_time,
            "content_type": "file",
            "file_name": file_name,
            "file_url": file_url,
            "file_size": file_size,
            "file_type": file_type,
            "is_deleted": False,
            "is_edited": False
        }

        emit(
            "new_message",
            payload,
            broadcast=True
        )


# =========================================
# DELETE / UNSEND MESSAGE
# =========================================

@socketio.on("delete_message")
def handle_delete_message(data):

    sender = users.get(
        request.sid
    )

    if not sender:
        return

    try:

        message_id = int(
            data.get("id")
        )

    except (TypeError, ValueError):

        emit(
            "chat_error",
            {
                "message":
                    "Invalid message ID."
            }
        )
        return

    conn = get_db()

    row = conn.execute(
        """
        SELECT
            id,
            message_type,
            sender,
            receiver,
            content_type,
            file_url,
            is_deleted
        FROM messages
        WHERE id = ?
        """,
        (message_id,)
    ).fetchone()

    if not row:

        conn.close()

        emit(
            "chat_error",
            {
                "message":
                    "Message could not be found."
            }
        )
        return

    # Only sender can delete
    if row["sender"] != sender:

        conn.close()

        emit(
            "chat_error",
            {
                "message":
                    "You can only delete your own messages."
            }
        )
        return

    if row["is_deleted"]:

        conn.close()
        return

    # Soft delete
    conn.execute(
        """
        UPDATE messages
        SET
            message = ?,
            is_deleted = 1,
            file_url = NULL
        WHERE id = ?
        """,
        (
            "This message was deleted.",
            message_id
        )
    )

    conn.commit()
    conn.close()

    # Delete associated uploaded file
    file_url = row["file_url"]

    if file_url:

        stored_name = os.path.basename(
            file_url
        )

        file_path = os.path.join(
            app.config["UPLOAD_FOLDER"],
            stored_name
        )

        if os.path.isfile(file_path):

            try:
                os.remove(file_path)
            except OSError:
                pass

    payload = {
        "id": message_id,
        "message": "This message was deleted.",
        "is_deleted": True
    }

    # Public message
    if row["message_type"] == "public":

        socketio.emit(
            "message_deleted",
            payload
        )

    # Private message
    else:

        target_sid = next(
            (
                sid
                for sid, username
                in users.items()
                if username == row["receiver"]
            ),
            None
        )

        if target_sid:

            socketio.emit(
                "message_deleted",
                payload,
                to=target_sid
            )

        socketio.emit(
            "message_deleted",
            payload,
            to=request.sid
        )


# =========================================
# EDIT MESSAGE
# =========================================

@socketio.on("edit_message")
def handle_edit_message(data):

    sender = users.get(
        request.sid
    )

    if not sender:
        return

    try:

        message_id = int(
            data.get("id")
        )

    except (TypeError, ValueError):

        emit(
            "chat_error",
            {
                "message":
                    "Invalid message ID."
            }
        )
        return

    new_message = str(
        data.get(
            "message",
            ""
        )
    ).strip()

    if not new_message:

        emit(
            "chat_error",
            {
                "message":
                    "Edited message cannot be empty."
            }
        )
        return

    new_message = new_message[:1000]

    conn = get_db()

    row = conn.execute(
        """
        SELECT
            id,
            message_type,
            sender,
            receiver,
            content_type,
            is_deleted
        FROM messages
        WHERE id = ?
        """,
        (message_id,)
    ).fetchone()

    if not row:

        conn.close()

        emit(
            "chat_error",
            {
                "message":
                    "Message could not be found."
            }
        )
        return

    # Only sender can edit
    if row["sender"] != sender:

        conn.close()

        emit(
            "chat_error",
            {
                "message":
                    "You can only edit your own messages."
            }
        )
        return

    # Deleted messages cannot be edited
    if row["is_deleted"]:

        conn.close()

        emit(
            "chat_error",
            {
                "message":
                    "Deleted messages cannot be edited."
            }
        )
        return

    # Only text messages can be edited
    if row["content_type"] != "text":

        conn.close()

        emit(
            "chat_error",
            {
                "message":
                    "Only text messages can be edited."
            }
        )
        return

    conn.execute(
        """
        UPDATE messages
        SET
            message = ?,
            is_edited = 1
        WHERE id = ?
        """,
        (
            new_message,
            message_id
        )
    )

    conn.commit()
    conn.close()

    payload = {
        "id": message_id,
        "message": new_message,
        "is_edited": True
    }

    # Public message
    if row["message_type"] == "public":

        socketio.emit(
            "message_edited",
            payload
        )

    # Private message
    else:

        target_sid = next(
            (
                sid
                for sid, username
                in users.items()
                if username == row["receiver"]
            ),
            None
        )

        if target_sid:

            socketio.emit(
                "message_edited",
                payload,
                to=target_sid
            )

        socketio.emit(
            "message_edited",
            payload,
            to=request.sid
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
                "time": now()
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
# INITIALIZE DATABASE
# =========================================

init_db()


# =========================================
# START SERVER
# =========================================

if __name__ == "__main__":

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