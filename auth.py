import logging
import bcrypt
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String
import jwt
import os
import time

SECRET_KEY = os.environ['SECRET_KEY']
db_user = os.environ['DB_USER']
db_password = os.environ['DB_PASSWORD']
db_name = os.environ['DB_NAME']
db_host = os.environ['DB_HOST']

engine = create_engine(f'mysql://{db_user}:{db_password}@{db_host}/{db_name}')
metadata = MetaData()

users = Table('users', metadata,
              Column('id', Integer, primary_key=True),
              Column('username', String(80), unique=True, nullable=False),
              Column('password', String(80), nullable=False))

token_rev = Table('token_revoked', metadata,
                  Column('id', Integer, primary_key=True),
                  Column('token', String(255), unique=True,nullable=False))

metadata.create_all(engine)

def is_valid_password(password):
    return len(password) >= 8

def logout(token):
    conn = engine.connect()
    query = token_rev.insert().values(token=token)
    conn.execute(query)
    conn.commit()
    conn.close()
    return {"success": True, "message": "token revocato!"}


def login(username, password):
    conn = engine.connect()
    query = users.select().where(users.c.username == username)
    result = conn.execute(query)
    user = result.fetchone()
    conn.close()

    if user:
        #logging.error(f"errore: {user}")
        hashed_password = user[2]
        if bcrypt.checkpw(password.encode('utf-8'), hashed_password.encode('utf-8')):
            logging.error(f'{user}')
            token = createToken(username)
            return {"success": True, "message": "Login riuscito", "token": token}
    else:
        return {"success": False, "message": "Credenziali non valide. Riprova."}

def register(username, password):
    if not is_valid_password(password):
        return {"success": False, "message": "La password deve essere lunga almeno 8 caratteri."}

    hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

    conn = engine.connect()
    query = users.select().where(users.c.username == username)
    result = conn.execute(query)
    existing_user = result.fetchone()
    logging.error(f'{existing_user}')

    if existing_user:
        conn.close()
        return {"success": False, "message": "Questo username è già stato utilizzato. Scegli un altro username."}

    query = users.insert().values(username=username, password=hashed_password)
    # Creazione token
    token = createToken(username)
    try:
        conn.execute(query)
        conn.commit()
        conn.close()
        return {"success": True, "message": "Registrazione riuscita", "token":token}
    except Exception as e:
        conn.close()
        return {"success": False, "message": f"Errore durante l'inserimento dell'utente: {str(e)}"}
def createToken(username):
    t_data = {"username": f"{username}", "expirationTime": time.time() + 3600*2}
    token = jwt.encode(payload=t_data, key=SECRET_KEY, algorithm="HS256")
    return token
