import telebot
from uber_rides.session import Session
from uber_rides.client import UberRidesClient
import requests
import json
import emoji

# Google Places API
search_key = "AIzaSyDtl_8f-gc1uITSV3QWIlCUsK7fFRBlZJs"

# Uber
uber_svtoken = "oE9QMeV2R1o9zcBceOJ6cuD-TeQ5x-riTAGwAxou"
session = Session(server_token=uber_svtoken)
client = UberRidesClient(session)

# Lyft
lyft_clientToken = "gAAAAABZG6IA4Grs4Qm0YYWUcGNHhL6pblpPVFlUTio5MOb8_-w1cBPrV1xgBV7YgQH2HM2g7kg6MY043akfI1Talqxcv9pZNXQgJqLQ3fGp0Y-5NU14yUMFi7Iz0SiTcUDuso-ScAiEUOpku9VD23pAUNQpD3db6tQC62PqI3yLxK_YMd1MvcA="



class User:
    def __init__(self):
        self.ip             = ""
        self.current_lat    = -1
        self.current_lng    = -1
        self.query          = ""
        self.dest_lat       = -1
        self.dest_lng       = -1
        self.dest_addr      = ""
        self.dest_title     = ""
        self.num_seat       = -1




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
        self.dest_title = get_info["results"][0]["name"]

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

        uber_dict = {}

        uber_dict["UberPool_ETA"] = estimate_time[0]["estimate"] / 60
        uber_dict["UberPool_Price"] = estimate_price[0]["estimate"]
        uber_dict["UberX_ETA"] = estimate_time[1]["estimate"] / 60
        uber_dict["UberX_Price"] = estimate_price[1]["estimate"]
        uber_dict["UberXL_ETA"] = estimate_time[2]["estimate"] / 60
        uber_dict["UberXL_Price"] = estimate_price[2]["estimate"]

        return uber_dict

    def get_lyft_info(self):
        lyft_dict = {}

        headers = {"Authorization": "Bearer {}".format(lyft_clientToken)}
        params_ETA = {"lat": self.current_lat, "lng": self.current_lng}
        url_ETA = "https://api.lyft.com/v1/eta?"
        estimate_time = requests.get(url_ETA, headers=headers, params=params_ETA).json()["eta_estimates"]

        lyft_dict["LyftLine_ETA"] = estimate_time[0]["eta_seconds"] / 60
        lyft_dict["Lyft_ETA"] = estimate_time[1]["eta_seconds"] / 60
        lyft_dict["LyftPlus_ETA"] = estimate_time[2]["eta_seconds"] / 60

        params_price = {"start_lat": self.current_lat, "start_lng": self.current_lng,
                        "end_lat": self.dest_lat, "end_lng": self.dest_lng}
        url_price = "https://api.lyft.com/v1/cost?"
        estimate_price = requests.get(url_price, headers=headers, params=params_price).json()["cost_estimates"]
        lyft_dict["LyftLine_Price"] = "${}-{}".format(estimate_price[1]["estimated_cost_cents_min"]/100, estimate_price[1]["estimated_cost_cents_max"]/100)
        lyft_dict["Lyft_Price"] = "${}-{}".format(estimate_price[2]["estimated_cost_cents_min"]/100, estimate_price[2]["estimated_cost_cents_max"]/100)
        lyft_dict["LyftPlus_Price"] = "${}-{}".format(estimate_price[0]["estimated_cost_cents_min"]/100, estimate_price[0]["estimated_cost_cents_max"]/100)

        return lyft_dict

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
    msg = bot.send_message(message.chat.id, "Can you send me your current location?", reply_markup=markup)
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
        bot.send_message(message.chat.id, "Is this the address?")
        msg = bot.send_venue(message.chat.id, user.dest_lat, user.dest_lng,
                            user.dest_title, user.dest_addr, reply_markup=markup)
        bot.register_next_step_handler(msg, process_order)
    except Exception as e:
        msg = bot.send_message(message.chat.id, "oooops! please try again")
        bot.register_next_step_handler(msg, process_destination)


def process_order(message):
    response = message.text
    if (response == "Yes"):
        user = user_dict[message.chat.id]
        uber_info = user.get_uber_info()
        uber_emoji = emoji.emojize(":black_medium_square:")
        uberPool_info = uber_emoji + "<b>Uber {}</b>\nArrives in {} minutes\nPrice range from {}".format("Pool", uber_info["UberPool_ETA"], uber_info["UberPool_Price"])
        uberX_info = uber_emoji + "<b>Uber {}</b>\nArrives in {} minutes\nPrice range from {}".format("X", uber_info["UberX_ETA"], uber_info["UberX_Price"])


        lyft_info = user.get_lyft_info()
        lyft_emoji = emoji.emojize(":red_circle:")
        lyftLine_info = lyft_emoji + " <b>Lyft {}</b>\nArrives in {} minutes\nPrice range from {}".format("Line", lyft_info["LyftLine_ETA"], lyft_info["LyftLine_Price"])
        LYFT_INFO = lyft_emoji + " <b>Lyft</b>\nArrives in {} minutes\nPrice range from {}".format(lyft_info["Lyft_ETA"], lyft_info["Lyft_Price"])
        msg = bot.send_message(message.chat.id, uberPool_info + "\n\n" + uberX_info + "\n\n" + lyftLine_info + "\n\n" + LYFT_INFO, parse_mode="HTML")

    else:
        msg = bot.send_message(message.chat.id, "Hmmm... Can you retype your destination?")
        bot.register_next_step_handler(msg, process_destination)



bot.polling()
