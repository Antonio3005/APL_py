import time
from flask import Flask, request
import auth
import threading
import notifier
import logging

app = Flask(__name__)

def send_email():
    while(True):
        notifier.send_notify()
        time.sleep(3600)


@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    response = auth.login(username,password)
    return response

@app.route('/logout', methods=['POST'])
def logout():
    data = request.headers.get('Authorization')
    if not data:
        return {"success": False, "message": "Header Authorization mancante"}

    # Controlla se l'intestazione "Authorization" è nel formato corretto (Bearer)
    header_parts = data.split(" ")
    if len(header_parts) != 2 and header_parts[0] != 'Bearer':
        return {"success": False,"message": "Formato Authorization non valido"}

    # Ottieni il token dalla seconda parte dell'intestazione
    try:
        token = header_parts[1]
        response = auth.logout(token)
    except Exception as e:
        return {"success": False, "message": "Token non presente"}

    return response

@app.route('/register',methods=['POST'])
def register():
    data = request.json
    username = data.get("username")
    password = data.get("password")
    response = auth.register(username,password)
    return response

bg_thread = threading.Thread(target=send_email)
bg_thread.daemon = True  # Termina il thread quando l'app si ferma
bg_thread.start()

if __name__ == '__main__':
    app.run()
