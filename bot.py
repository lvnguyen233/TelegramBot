import telebot
from uber_rides.session import Session
from uber_rides.client import UberRidesClient
import requests
import json


# Google Places API
search_key = "AIzaSyDtl_8f-gc1uITSV3QWIlCUsK7fFRBlZJs"

# Uber
uber_svtoken = "oE9QMeV2R1o9zcBceOJ6cuD-TeQ5x-riTAGwAxou"
session = Session(server_token=uber_svtoken)
client = UberRidesClient(session)



class User:
    def __init__(self):
        self.ip             = ""
        self.current_lat    = -1
        self.current_lng    = -1
        self.query          = ""
        self.dest_lat       = -1
        self.dest_lng       = -1
        self.dest_addr      = ""
        self.num_seat       = -1
        self.U_price_range  = ""
        self.L_price_range  = ""
        self.uber_ETA       = -1
        self.lyft_ETA       = -1



    # Search dest location and address using Google's Places API
    def search_dest(self):
        url = "https://maps.googleapis.com/maps/api/place/textsearch/json?"
        current_location = "{},{}".format(self.current_lat, self.current_lng)
        params = { "query": self.query, "key": search_key, "location" : current_location, "radius": 10000}
        get_info = requests.get(url, params=params).json()

        # need an if case here

        # Grab the 1st item
        self.dest_lat = get_info["results"][0]["geometry"]["location"]["lat"]
        self.dest_lng = get_info["results"][0]["geometry"]["location"]["lng"]
        self.dest_addr = get_info["results"][0]["formatted_address"]

    def get_uber_info(self):
        # Get price info from Uber
        response_price = client.get_price_estimates(start_latitude=self.current_lat, start_longitude=self.current_lng,
                                            end_latitude=self.dest_lat, end_longitude=self.dest_lng)
        estimate_price = response_price.json.get("prices")

        # Get ETA info from Uber
        headers = {"Authorization": "Token {}".format(uber_svtoken)}
        params = {"start_latitude": self.current_lat, "start_longitude": self.current_lng}
        url = "https://api.uber.com/v1.2/estimates/time?"
        estimate_time = requests.get(url, headers=headers, params=params).json()["times"]

        num_seat = self.num_seat
        if (num_seat <= 2):
            self.uber_ETA = estimate_time[0]["estimate"] / 60
            self.U_price_range = estimate_price[0]["estimate"]





# Telegram Bot
telegram_token = "338308635:AAFqrqtKH1xgRC5LncS3UPuGUgxVLRlzjkk"
bot_URL = "https://api.telegram.org/bot{}/".format(telegram_token)

user_dict = {}
bot = telebot.TeleBot(telegram_token)

# Start conversation
@bot.message_handler(commands=['start'])
def get_started(message):
    markup = telebot.types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True)
    itembtn1 = telebot.types.KeyboardButton("Yes", request_location=True)
    itembtn2 = telebot.types.KeyboardButton("No I don't want to")
    markup.add(itembtn1, itembtn2)
    msg = bot.send_message(message.chat.id, "What's up homie! Can you send me your current location?", reply_markup=markup)
    bot.register_next_step_handler(msg, process_current_location)


# Get user's current location
def process_current_location(message):
    if (message.location != None):
        lat = message.location.latitude
        lng = message.location.longitude
        user = User()
        user_dict[message.chat.id] = user
        user.current_lat = lat
        user.current_lng = lng
        msg = bot.send_message(message.chat.id, "Cool! So where are you heading?")
        bot.register_next_step_handler(msg, process_destination)

    else:
        bot.send_message(message.chat.id, "Sorry we can't help you without your location")



# Query user's destination
def process_destination(message):
    try:
        response = message.text
        user = user_dict[message.chat.id]
        user.query = response
        user.search_dest()
        markup = telebot.types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True)
        itembtn1 = telebot.types.KeyboardButton("Yes")
        itembtn2 = telebot.types.KeyboardButton("No")
        markup.add(itembtn1, itembtn2)
        msg = bot.send_message(message.chat.id, "Is this the address?\n{}".format(user.dest_addr), reply_markup=markup)
        bot.register_next_step_handler(msg, number_people)
    except Exception as e:
        msg = bot.send_message(message.chat.id, "oooops! please try again")
        bot.register_next_step_handler(msg, process_destination)



def number_people(message):
    response = message.text
    if (response == "Yes"):
        markup = telebot.types.ReplyKeyboardMarkup(row_width=1, one_time_keyboard=True)
        itembtn1 = telebot.types.KeyboardButton("1")
        itembtn2 = telebot.types.KeyboardButton("2")
        itembtn3 = telebot.types.KeyboardButton("3 to 4")
        itembtn4 = telebot.types.KeyboardButton("More than 4")
        markup.add(itembtn1, itembtn2, itembtn3, itembtn4)
        msg = bot.send_message(message.chat.id, "How many seats do you need?", reply_markup=markup)
        bot.register_next_step_handler(msg, process_order)

    else:
        msg = bot.send_message(message.chat.id, "Hmmm.. Can you retype your destination?")
        bot.register_next_step_handler(msg, process_destination)


def process_order(message):
    response = message.text
    user = user_dict[message.chat.id]
    user.num_seat = int(response)
    user.get_uber_info()
    msg = bot.send_message(message.chat.id, "Uber:  ETA {} minutes - Price range {}".format(user.uber_ETA, user.U_price_range))




bot.polling()
