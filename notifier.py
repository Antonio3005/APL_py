import logging
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String
import smtplib,os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import requests
import json
from datetime import datetime, timedelta


db_user = os.environ['DB_USER']
db_password = os.environ['DB_PASSWORD']
db_name = os.environ['DB_NAME']
db_host = os.environ['DB_HOST']
api_key = os.environ['API_KEY']
mail_username = os.environ['MAIL_USERNAME']
mail_password = os.environ['MAIL_PASSWORD']

engine = create_engine(f'mysql://{db_user}:{db_password}@{db_host}/{db_name}')
metadata = MetaData()

fav = Table('favourites', metadata,
          Column('id', Integer, primary_key=True),
            Column('user', String(80), unique=True, nullable=False),
            Column('city_from', String(255), unique=True, nullable=False),
            Column('city_to', String(255), unique=True, nullable=False),
            Column('date_from', String(255), unique=True, nullable=False),
            Column('return_from', String(255), unique=True, nullable=False),
            Column('price', String(255), unique=True, nullable=False))

metadata.create_all(engine)

def get_iata(city):
    try:
        url = 'https://api.tequila.kiwi.com/locations/query'
        headers = {
            'accept': 'application/json',
            'apikey': api_key
        }

        params = {
            'term': city,
            'locale': 'it-IT',
            'location_types': 'city',
            'limit': 10,
            'active_only': True
        }

        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 200:
            # Analizza la risposta JSON
            try:
                data = response.json()
                # Assicurati che l'array "locations" sia presente e non vuoto
                if "locations" in data and data["locations"]:
                    # Estrai il valore associato alla chiave "code"
                    iata = data["locations"][0]["code"]
                    print(iata)
                else:
                    print("Array 'locations' vuoto o assente nella risposta dell'API.")
            except json.JSONDecodeError:
                print("Errore nella decodifica della risposta JSON.")

        else:
            # Se la richiesta non è andata a buon fine, stampa il codice di stato
            print(f"Errore nella richiesta. Codice di stato: {response.status_code}")

        return iata
    except Exception as e:
        print(f"Errore durante l'ottenimento di IATA per la città {city}: {e}")
        return None

def get_flights(iata_from, iata_to, date_from, date_to, return_from, return_to, price_from, price_to):
    try:
        url = 'https://api.tequila.kiwi.com/v2/search'
        headers = {
            'accept': 'application/json',
            'apikey': api_key
        }

        params = {
            'fly_from': iata_from,
            'fly_to': iata_to,
            'date_from': date_from,
            'date_to': date_to,
            'return_from': return_from,
            'return_to': return_to,
            'adults': 1,
            'adult_hand_bag': 1,
            'partner_market': 'it',
            'price_from': price_from,
            'price_to': price_to,
            'vehicle_type': 'aircraft',
            'sort': 'price',
            'limit': 2,
            'locale': 'it'
        }

        # Make the API request
        response = requests.get(url, params=params, headers=headers)

        if response.status_code == 200:
            data = response.json()
        else:
            print(f"Error: {response.status_code}, {response.text}")

        return data
    except Exception as e:
        print(f"Errore durante l'ottenimento dei voli: {e}")
        return None


#def check_flights(flight):


def send_notify():
    conn = engine.connect()
    query = fav.select()
    result = conn.execute(query)
    favs = result.fetchall()
    conn.close()

    logging.error("sono qui")

    if not favs:
        return "Non ci sono rotte preferite!"

    for f in favs:
        logging.error(f)

        iata_from = get_iata(f[2])
        iata_to = get_iata(f[3])

        date_to = calc_date(f[4])
        return_to = calc_date(f[5])

        price_min="1"

        data = get_flights(iata_from,iata_to,f[4],date_to,f[5],return_to,price_min,f[6])
        #logging.error(f"voli: {data}")
        if data is not None:
            logging.error(data['data'])
            if data['data'] == []:
                data['user']=f[1]
                check_flights(data)
                logging.error("sono qui")
            else :
                for d in data['data']:
                    d['user'] = f[1]
                    logging.error(f"Valore di data: {type(d)}")

                #serialized_data = d.decode('utf-8')

                    check_flights(d)



def calc_date(d):
    date = datetime.strptime(d, "%d/%m/%Y")
    new_date = date + timedelta(days=2)
    new_date = new_date.strftime("%d/%m/%Y")
    return new_date

def formatta_date(d):
    data_dt = datetime.strptime(d, "%Y-%m-%dT%H:%M:%S.%fZ")
    data_formattata = data_dt.strftime("%d/%m/%Y")
    return data_formattata

def check_flights(flight_data):
    try:
        if(flight_data['data']==[]):
            body = (f"Per oggi niente offerte")

        else:

            logging.error(f"process_flight_dats : {flight_data}")
            max_price = float(flight_data['price'])  # Converti il prezzo in un numero a virgola mobile
            logging.error(max_price)
            conn = engine.connect()
            query = fav.select().where(
                (fav.c.user == flight_data['user']) &
                (fav.c.city_from == flight_data['route'][0]['cityFrom']) &
                (fav.c.city_to == flight_data['route'][0]['cityTo']) &
                (fav.c.date_from == formatta_date(flight_data['route'][0]['local_departure'])) &
                (fav.c.return_from == formatta_date(flight_data['route'][1]['local_departure']))
            )
            result = conn.execute(query)
            favs = result.fetchall()

            logging.error(f"{favs}")

            if favs:
                for f in favs:
                    if float(f.price) > max_price:
                        logging.error(f"Prezzo {f.price} maggiore o uguale a {max_price}")
                        body = (f"Ci sono nuove offerte di volo disponibili per le tue richieste: \n"
                                "Andata:\n"
                                f"Citta di partenza {flight_data['route'][0]['cityFrom']}\n"
                                f"Aeroporto di partenza {flight_data['route'][0]['flyFrom']}\n"
                                f"Aeroporto di arrivo {flight_data['route'][0]['flyTo']}\n"
                                f"Citta di arrivo {flight_data['route'][0]['cityTo']}\n"
                                f"Data di partenza {flight_data['route'][0]['local_departure']}\n"
                                "Ritorno:\n"
                                f"Citta di partenza {flight_data['route'][1]['cityFrom']}\n"
                                f"Aeroporto di partenza {flight_data['route'][1]['flyFrom']}\n"
                                f"Aeroporto di arrivo {flight_data['route'][1]['flyTo']}\n"
                                f"Citta di arrivo {flight_data['route'][1]['cityTo']}\n"
                                f"Data di ritorno {flight_data['route'][1]['local_departure']}\n"
                                f"Prezzo {flight_data['price']}\n")
                    else:
                        logging.error("Per oggi niente offerte")
                        logging.error(f"Volo al prezzo di {max_price}")
                        body = (f"Per oggi niente offerte")

            else:
                body = (f"Ci sono nuove offerte di volo disponibili per le tue richieste: \n"
                        "Andata:\n"
                        f"Citta di partenza {flight_data['route'][0]['cityFrom']}\n"
                        f"Aeroporto di partenza {flight_data['route'][0]['flyFrom']}\n"
                        f"Aeroporto di arrivo {flight_data['route'][0]['flyTo']}\n"
                        f"Citta di arrivo {flight_data['route'][0]['cityTo']}\n"
                        f"Data di partenza {flight_data['route'][0]['local_departure']}\n"
                        "Ritorno:\n"
                        f"Citta di partenza {flight_data['route'][1]['cityFrom']}\n"
                        f"Aeroporto di partenza {flight_data['route'][1]['flyFrom']}\n"
                        f"Aeroporto di arrivo {flight_data['route'][1]['flyTo']}\n"
                        f"Citta di arrivo {flight_data['route'][1]['cityTo']}\n"
                        f"Data di ritorno {flight_data['route'][1]['local_departure']}\n"
                        f"Prezzo {flight_data['price']}\n")

        # Esegui il commit delle modifiche al database

        to_email = flight_data['user']
        subject = 'Nuove offerte di volo disponibili!'
        send_notification_email(to_email, subject, body)
    except Exception as e:
        return logging.error(f'Errore durante l\'elaborazione dei dati di volo: {e}')

def send_notification_email(to_email, subject, body):
    try:
        # Configurare i dettagli del server SMTP
        smtp_server = 'smtp.libero.it'
        smtp_port = 465
        smtp_username = mail_username
        smtp_password = mail_password

        # Creare un oggetto del messaggio
        msg = MIMEMultipart()
        msg['From'] = mail_username
        msg['To'] = to_email
        msg['Subject'] = subject

        logging.error(f"IL BODY È : {body}")

        # Aggiungere il corpo del messaggio
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        # Inizializzare la connessione SMTP
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
            server.login(smtp_username, smtp_password)
            server.sendmail(msg['From'], msg['To'], msg.as_string())


        logging.error("Email inviata con successo!")
        return 'Email inviata con successo!'
    except Exception as e:
        logging.error(f'Errore durante l\'invio dell\'email: {e}')
        return 'Errore durante l\'invio dell\'email: ' + str(e)

