# LAN Chat — Web Version

A simple real-time web-based chat application that runs on localhost and can be accessed by devices on the same LAN/Wi-Fi.

## Stack
- HTML, CSS, JavaScript
- Python + Flask
- Flask-SocketIO / WebSocket
- No database yet (SQLite can be added later)

## Features
- Browser chat UI
- Real-time messages
- Multiple users
- Online-user list
- Join/leave notifications
- Timestamps
- Responsive design
- Localhost and LAN access

## Run

1. Check Python:
```bash
python --version
```

2. Create and activate a virtual environment (recommended):
```bash
python -m venv venv
venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Start:
```bash
python app.py
```

5. Open:
```text
http://127.0.0.1:5000
```

## Test on the same computer
Open several browser tabs and join with different usernames.

## Test on another device
Connect both devices to the same Wi-Fi. On Windows run:
```cmd
ipconfig
```
Find the server PC's IPv4 address, for example `192.168.1.10`.

On the second device open:
```text
http://192.168.1.10:5000
```

The server listens on `0.0.0.0`, so it accepts LAN connections. If Windows Firewall blocks access, allow Python on the private network.

## Architecture

```text
Browser 1 ─┐
Browser 2 ─┼── WebSocket ──> Python Flask Server
Browser 3 ─┘
```

The browser loads the page over HTTP. Socket.IO then maintains a real-time connection for chat messages.

## Networking concepts
- IP address: identifies the host on the network
- Port 5000: identifies the application
- Client: browser connecting to the server
- Server: Python process handling users
- WebSocket: persistent two-way communication
- LAN: local network such as Wi-Fi

## Future upgrades
- SQLite chat history
- Authentication
- Private messages
- File transfer
- End-to-end encryption
- Typing indicators
- Read receipts

## Resume description
**LAN Chat — Python, Flask, WebSocket, HTML, CSS, JavaScript**

Developed a real-time browser-based LAN chat application using Python Flask and WebSocket communication, supporting multiple concurrent users, online-user tracking, timestamps, and local-network access through a responsive HTML/CSS interface.
