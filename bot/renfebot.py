import os
import json
from textwrap import dedent

import telebot
from credentials import get_token
from utils import sanitize_station_input, export_input

TOKEN = get_token()
bot = telebot.TeleBot(TOKEN)
searching = False

@bot.message_handler(commands=['start'])
def send_welcome(message: telebot.types.Message):
	bot.send_message(message.chat.id, dedent(f"Hola {message.from_user.first_name}. "\
						"Bienvenido a tu bot de Renfe. Te ayudaré a encontrar "\
						"billetes de tren para tus viajes. Para empezar, escribe "\
						"/ayuda para ver los comandos disponibles."))

@bot.message_handler(commands=['ayuda'])
def send_help(message: telebot.types.Message):
	bot.send_message(message.chat.id, dedent("""\
		/ayuda - Muestra los comandos disponibles
		/buscar - Busca billetes de tren
		/reintentar - Vuelve a buscar billetes con los parámetros de la última búsqueda
		/debug - Muestra información de depuración del último log
		"""))

@bot.message_handler(commands=['reintentar'])
def send_retry(message: telebot.types.Message):
	try:
		with open('resources/last_input.json', 'r') as f:
			user_params = json.load(f)
			f.close()
		search_trains(message, user_params)
	except FileNotFoundError:
		bot.send_message(message.chat.id, "No hay ninguna búsqueda anterior")

@bot.message_handler(commands=['debug'])
def send_debug(message: telebot.types.Message):
	logs = os.listdir("logs")
	user_logs = []
	for log in logs:
		if message.from_user.username in log:
			user_logs.append(log)
	if len(user_logs) == 0:
		bot.send_message(message.chat.id, "No hay logs disponibles")
	else:
		bot.send_message(message.chat.id, dedent("""\
			Envía este documento a los desarrolladores para que puedan ayudarte:
		"""))
		user_logs.sort(reverse=True)
		bot.send_document(message.chat.id, open(f"logs/{user_logs[0]}", "rb"))

@bot.message_handler(commands=['cancelar'])
def send_cancel(message: telebot.types.Message):
	global searching
	if searching:
		searching = False
		bot.send_message(message.chat.id, "Búsqueda cancelada")
	else:
		bot.send_message(message.chat.id, "No hay ninguna búsqueda en curso")

@bot.message_handler(commands=['buscar'])
def start(message: telebot.types.Message):
	if searching:
		bot.send_message(message.chat.id, "Ya hay una búsqueda en curso, por favor espera o utiliza /cancelar para cancelarla")
		return
	user_params = {}
	bot.send_message(message.chat.id, "🚉 ¿Desde qué estación sales?")
	bot.register_next_step_handler(message, get_origin_station, user_params)

def get_origin_station(message: telebot.types.Message, user_params):
	station = sanitize_station_input(message.text)
	if station is None:
		bot.send_message(message.chat.id, dedent("No he entendido a qué estación te refieres,\
		   por favor introdúcela como aparece en la web de Renfe"))
		bot.register_next_step_handler(message, get_origin_station, user_params)
	user_params["origin_station"] = station
	bot.send_message(message.chat.id, "🚉 ¿A qué estación vas?")
	bot.register_next_step_handler(message, get_destination_station, user_params)

def get_destination_station(message: telebot.types.Message, user_params):
	station = sanitize_station_input(message.text)
	if station is None:
		bot.send_message(message.chat.id, dedent("No he entendido a qué estación te refieres,\
		   por favor introdúcela como aparece en la web de Renfe"))
		bot.register_next_step_handler(message, get_destination_station, user_params)
	user_params["destination_station"] = station
	bot.send_message(message.chat.id, "📅 ¿Cuándo sales? (dd-mm-aaaa)")
	bot.register_next_step_handler(message, get_departure_date, user_params)

def get_departure_date(message: telebot.types.Message, user_params):
	user_params["departure_date"] = message.text
	bot.send_message(message.chat.id, "🔙 ¿Necesitas billete de vuelta? (S/N)")
	bot.register_next_step_handler(message, get_return, user_params)

def get_return(message: telebot.types.Message, user_params):
	if message.text == "S" or message.text == "s":
		user_params["return"] = True
		bot.send_message(message.chat.id, "📅 ¿Cuándo vuelves? (dd-mm-aaaa)")
		bot.register_next_step_handler(message, get_return_date, user_params)
	else:
		user_params["return"] = False
		bot.send_message(message.chat.id, "¿Quieres filtrar los resultados? (S/N)")
		bot.register_next_step_handler(message, get_filter, user_params)

def get_return_date(message: telebot.types.Message, user_params):
	user_params["return_date"] = message.text
	bot.send_message(message.chat.id, "¿Quieres filtrar los resultados? (S/N)")
	bot.register_next_step_handler(message, get_filter, user_params)

def get_filter(message: telebot.types.Message, user_params):
	if message.text == "S" or message.text == "s":
		bot.send_message(message.chat.id, "💵 ¿Precio máximo? (introduce 0 si no quieres filtrar por precio)")
		bot.register_next_step_handler(message, get_max_price, user_params)
	else:
		search_trains(message, user_params)

def get_max_price(message: telebot.types.Message, user_params):
	user_params["max_price"] = message.text
	bot.send_message(message.chat.id, "⏳ ¿Duración máxima del trayecto? (introduce 0 si no quieres filtrar por duración)")
	bot.register_next_step_handler(message, get_max_duration, user_params)

def get_max_duration(message: telebot.types.Message, user_params):
	user_params["max_duration"] = message.text
	bot.send_message(message.chat.id, "🕒 ¿A partir de qué hora quieres salir? (hh:mm)")
	bot.register_next_step_handler(message, get_ida_earliest, user_params)

def get_ida_earliest(message: telebot.types.Message, user_params):
	user_params["ida_earliest"] = message.text
	bot.send_message(message.chat.id, "🕒 ¿Y cómo muy tarde? (hh:mm)")
	bot.register_next_step_handler(message, get_ida_latest, user_params)

def get_ida_latest(message: telebot.types.Message, user_params):
	user_params["ida_latest"] = message.text
	if user_params["return"]:
		bot.send_message(message.chat.id, "🕒 ¿A partir de qué hora quieres volver? (hh:mm)")
		bot.register_next_step_handler(message, get_vuelta_earliest, user_params)
	else:
		search_trains(message, user_params)

def get_vuelta_earliest(message: telebot.types.Message, user_params):
	user_params["vuelta_earliest"] = message.text
	bot.send_message(message.chat.id, "🕒 ¿Y cómo muy tarde? (hh:mm)")
	bot.register_next_step_handler(message, get_vuelta_latest, user_params)

def get_vuelta_latest(message: telebot.types.Message, user_params):
	user_params["vuelta_latest"] = message.text
	search_trains(message, user_params)

def search_trains(message: telebot.types.Message, user_params):
	global searching
	searching = True
	bot.send_message(message.chat.id, "🔎 Buscando billetes...")
	export_input(user_params)
	for key, value in user_params.items():
		print(f"{key}: {value}")

	# finish search
	searching = False

bot.polling()