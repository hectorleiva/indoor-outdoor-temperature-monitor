#!/usr/bin/env python3
# Get temperature from sensor and temperature from OpenWeather and display it on the MatrixPortal

import board
import terminalio
import time
import busio
import adafruit_bme680

from adafruit_matrixportal.matrixportal import MatrixPortal

try:
    from secrets import secrets
    LATITUDE = secrets['latitude']
    LONGITUDE = secrets['longitude']
    SEALEVEL = secrets['sealevel']
    OPENWEATHER_TOKEN = secrets['openweather_token']
    OPENWEATHER_UNITS = secrets['openweather_units']

    # To determine time using the Adafruit Time Service
    TIMEZONE = secrets['timezone']
    AIO_USERNAME = secrets['aio_username']
    AIO_KEY = secrets['aio_key']
except ImportError:
    print("WiFi secrets, Openweather API Tokens, and Latitude/Longitude values are kept in secrets.py, please add them!")
    raise

# --- Display setup ---
matrixportal = MatrixPortal(
    status_neopixel=board.NEOPIXEL,
    bit_depth=4
)

# Create a static label
# "IN" - index 0
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(2, 4),
    text_scale=1
)

# "OUT" - index 1
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(35, 4),
    text_scale=1
)

# "F" for degrees for INDOORS - index 2
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(26, 16),
    text_scale=1
)

# "F" for degrees for OUTDOORS - index 3
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(59, 16),
    text_scale=1
)

# Dynamic labels
# Temperature INDOORS - index 4
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(2, 18),
    text_scale=2
)

# Temperature OUTDOORS - index 5
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=(35, 18),
    text_scale=2
)

# ERROR Display - index 6
matrixportal.add_text(
    text_font=terminalio.FONT,
    text_position=((matrixportal.graphics.display.width // 5),
                   (matrixportal.graphics.display.height // 3) + 1),
    text_scale=1
)

matrixportal.set_text("IN", 0)
matrixportal.set_text("OUT", 1)
matrixportal.set_text("F" if OPENWEATHER_UNITS is "imperial" else "C", 2)
matrixportal.set_text("F" if OPENWEATHER_UNITS is "imperial" else "C", 3)


def sensor_data_stringified(bme680, units):
    if units is "imperial":
        temperature = "%0.0f" % ((bme680.temperature * 1.8) + 32)
    else:
        temperature = "%0.0f" % bme680.temperature

    # pressure = "%0.1fhPa" % bme680.pressure
    # gas = "{}%".format(bme680.gas)
    return temperature


def callWeatherAPI(token, lat, lng, units):
    DATA_SOURCE = 'https://api.openweathermap.org/data/2.5/onecall?units={}&lat={}&lon={}&appid={}&exclude=minutely,hourly,daily,alerts'.format(
        units,
        lat,
        lng,
        token
    )

    print(DATA_SOURCE)

    current_value = matrixportal.network.fetch_data(
        DATA_SOURCE, json_path=['current'])
    return current_value[0]  # this returns the weather data as an object


def callTimeService():
    TIME_URL = "https://io.adafruit.com/api/v2/%s/integrations/time/strftime?x-aio-key=%s" % (
        AIO_USERNAME, AIO_KEY)
    # See https://apidock.com/ruby/DateTime/strftime for full options
    TIME_URL += "&fmt=%25s"  # return date time data in UNIX timestamp
    response = matrixportal.network.fetch_data(TIME_URL)
    return int(response)


def convertRGBArrayToHexString(colorRGBObj):
    hexString = '#'
    for colorVal in colorRGBObj:
        hexString += '{:X}'.format(colorVal)
    return hexString


def fromToColorConverter(fromColorRGBArray, toColorRGBArray, stepVal):
    newColorObj = {}

    for index, fromColorVal in enumerate(fromColorRGBArray):
        if (fromColorVal == toColorRGBArray[index]):
            newColorObj[index] = toColorRGBArray[index]
        elif (fromColorVal < toColorRGBArray[index] and (fromColorVal + stepVal) >= toColorRGBArray[index]):
            newColorObj[index] = toColorRGBArray[index]  # destination reached
        elif fromColorVal < toColorRGBArray[index]:
            newColorObj[index] = fromColorVal + stepVal
        else:
            newColorObj[index] = fromColorVal - stepVal

    print("newColorObj: ", newColorObj)
    print("toColorRGBArray: ", toColorRGBArray)
    return (newColorObj[0], newColorObj[1], newColorObj[2])


DAYTIME_COLORS = {
    "HOT": (212, 28, 15),
    "NEUTRAL": (255, 255, 255),
    "COLD": (3, 78, 255)
}

NIGHTIME_COLORS = {
    "HOT": (21, 2, 1),
    "NEUTRAL": (25, 25, 25),
    "COLD": (0, 7, 25)
}

# Start with the colors being dim
CURRENT_COLORS = {
    "HOT": (0, 0, 0),
    "NEUTRAL": (0, 0, 0),
    "COLD": (0, 0, 0)
}


def determineColorsForDisplay(weather_data, indoor_temp: str, units: str, unix_timestamp: int):
    outdoor_temp = int(weather_data['temp'])
    indoor_temp = int(indoor_temp)

    SHOULD_DIM_DISPLAY = unix_timestamp > weather_data[
        'sunset'] or unix_timestamp < weather_data['sunrise']

    # if (SHOULD_DIM_DISPLAY):
    #     HOT_COLOR = '#150201'        # 9 shades darker than 'd41c0f'
    #     NEUTRAL_COLOR = '#191919'    # 9 shades darker than 'ffffff'
    #     COLD_COLOR = '#000719'       # 9 shades darker than '034eff'
    # else:
    #     HOT_COLOR = '#d41c0f'
    #     NEUTRAL_COLOR = '#ffffff'
    #     COLD_COLOR = '#034eff'

    outdoor_display_assignments = [1, 3, 5]
    indoor_display_assignments = [0, 2, 4]

    while (SHOULD_DIM_DISPLAY and
           CURRENT_COLORS["HOT"] != NIGHTIME_COLORS["HOT"] and
           CURRENT_COLORS["NEUTRAL"] != NIGHTIME_COLORS["NEUTRAL"] and
           CURRENT_COLORS["COLD"] != NIGHTIME_COLORS["COLD"]
           ):
        CURRENT_COLORS["HOT"] = fromToColorConverter(
            CURRENT_COLORS["HOT"], NIGHTIME_COLORS["HOT"], 2)
        CURRENT_COLORS["NEUTRAL"] = fromToColorConverter(
            CURRENT_COLORS["NEUTRAL"], NIGHTIME_COLORS["NEUTRAL"], 2)
        CURRENT_COLORS["COLD"] = fromToColorConverter(
            CURRENT_COLORS["COLD"], NIGHTIME_COLORS["COLD"], 2)

        print("CURRENT_COLORS within loop: ", CURRENT_COLORS)
        print("NIGHTTIME_COLORS: ", NIGHTIME_COLORS)

        if units is "imperial":
            for i in outdoor_display_assignments:
                if outdoor_temp > 89:
                    matrixportal.set_text_color(
                        convertRGBArrayToHexString(CURRENT_COLORS["HOT"]), i)
                elif outdoor_temp < 35:
                    matrixportal.set_text_color(
                        convertRGBArrayToHexString(CURRENT_COLORS["COLD"]), i)
                else:
                    matrixportal.set_text_color(
                        convertRGBArrayToHexString(CURRENT_COLORS["NEUTRAL"]), i)
            for i in indoor_display_assignments:
                if indoor_temp > 83:
                    matrixportal.set_text_color(
                        convertRGBArrayToHexString(CURRENT_COLORS["HOT"]), i)
                elif indoor_temp < 50:
                    matrixportal.set_text_color(
                        convertRGBArrayToHexString(CURRENT_COLORS["COLD"]), i)
                else:
                    matrixportal.set_text_color(
                        convertRGBArrayToHexString(CURRENT_COLORS["NEUTRAL"]), i)
        else:
            for i in outdoor_display_assignments:
                if outdoor_temp > 31:
                    matrixportal.set_text_color(
                        convertRGBArrayToHexString(CURRENT_COLORS["HOT"]), i)
                elif outdoor_temp < 2:
                    matrixportal.set_text_color(
                        convertRGBArrayToHexString(CURRENT_COLORS["COLD"]), i)
                else:
                    matrixportal.set_text_color(
                        convertRGBArrayToHexString(CURRENT_COLORS["NEUTRAL"]), i)
            for i in indoor_display_assignments:
                if indoor_temp > 26:
                    matrixportal.set_text_color(
                        convertRGBArrayToHexString(CURRENT_COLORS["HOT"]), i)
                elif indoor_temp < -2:
                    matrixportal.set_text_color(
                        convertRGBArrayToHexString(CURRENT_COLORS["COLD"]), i)
                else:
                    matrixportal.set_text_color(
                        convertRGBArrayToHexString(CURRENT_COLORS["NEUTRAL"]), i)

        time.sleep(2)

    print("outside the loop and setting the colors: ", CURRENT_COLORS)
    if units is "imperial":
        for i in outdoor_display_assignments:
            if outdoor_temp > 89:
                matrixportal.set_text_color(
                    convertRGBArrayToHexString(CURRENT_COLORS["HOT"]), i)
            elif outdoor_temp < 35:
                matrixportal.set_text_color(
                    convertRGBArrayToHexString(CURRENT_COLORS["COLD"]), i)
            else:
                matrixportal.set_text_color(
                    convertRGBArrayToHexString(CURRENT_COLORS["NEUTRAL"]), i)
        for i in indoor_display_assignments:
            if indoor_temp > 83:
                matrixportal.set_text_color(
                    convertRGBArrayToHexString(CURRENT_COLORS["HOT"]), i)
            elif indoor_temp < 50:
                matrixportal.set_text_color(
                    convertRGBArrayToHexString(CURRENT_COLORS["COLD"]), i)
            else:
                matrixportal.set_text_color(
                    convertRGBArrayToHexString(CURRENT_COLORS["NEUTRAL"]), i)
    else:
        for i in outdoor_display_assignments:
            if outdoor_temp > 31:
                matrixportal.set_text_color(
                    convertRGBArrayToHexString(CURRENT_COLORS["HOT"]), i)
            elif outdoor_temp < 2:
                matrixportal.set_text_color(
                    convertRGBArrayToHexString(CURRENT_COLORS["COLD"]), i)
            else:
                matrixportal.set_text_color(
                    convertRGBArrayToHexString(CURRENT_COLORS["NEUTRAL"]), i)
        for i in indoor_display_assignments:
            if indoor_temp > 26:
                matrixportal.set_text_color(
                    convertRGBArrayToHexString(CURRENT_COLORS["HOT"]), i)
            elif indoor_temp < -2:
                matrixportal.set_text_color(
                    convertRGBArrayToHexString(CURRENT_COLORS["COLD"]), i)
            else:
                matrixportal.set_text_color(
                    convertRGBArrayToHexString(CURRENT_COLORS["NEUTRAL"]), i)


def writeTemperatureValuesToDisplay(outdoor_temp: str, indoor_temp: str):
    matrixportal.set_text(indoor_temp, 4)
    matrixportal.set_text(outdoor_temp, 5)


def writeErrorOnDisplay(error: str):
    print(error)
    matrixportal.set_text(error, 6)
    matrixportal.set_text_color('#d41c0f', 6)


# Global Values
outdoor_temp_object = {"temp": 0, "sunset": 0, "sunrise": 0}
indoor_temp = ''
NEXT_OUTDOOR_TEMP_SYNC = 0
UNIX_TIMESTAMP_FROM_TIME_SERVICE = 0

# Set-up Indoor Temperature Sensor
i2c = busio.I2C(board.SCL, board.SDA)
bme680 = adafruit_bme680.Adafruit_BME680_I2C(i2c)
bme680.sea_level_pressure = SEALEVEL

# Initialized values
writeTemperatureValuesToDisplay('la', 'Ho')  # ¿Hola, como estas?

while True:
    NOW = time.time()  # Current epoch time in seconds, UTC

    # if NOW > NEXT_OUTDOOR_TEMP_SYNC:
    #     NEXT_OUTDOOR_TEMP_SYNC = NOW + (60 * 60)  # Network call every hour

    #     try:
    #         UNIX_TIMESTAMP_FROM_TIME_SERVICE = callTimeService()
    #     except Exception as e:
    #         print('callTimeService Error: ', e)
    #         writeErrorOnDisplay('timeSer')

    #     try:
    #         outdoor_temp_object = callWeatherAPI(
    #             OPENWEATHER_TOKEN, LATITUDE, LONGITUDE, OPENWEATHER_UNITS)
    #     except Exception as e:
    #         print('openApi Error: ', e)
    #         writeErrorOnDisplay('openApi')

    UNIX_TIMESTAMP_FROM_TIME_SERVICE = 1665281210
    outdoor_temp_object = {'dt': 1665281222, 'sunrise': 1665226788, 'visibility': 10000, 'weather': [{'id': 801, 'icon': '02n', 'main': 'Clouds', 'description': 'few clouds'}],
                           'pressure': 1021, 'humidity': 60, 'clouds': 20, 'wind_deg': 330, 'wind_speed': 6.91, 'temp': 48.9, 'dew_point': 35.65, 'feels_like': 45.91, 'sunset': 1665268053, 'uvi': 0}

    print("timestamp: ", UNIX_TIMESTAMP_FROM_TIME_SERVICE)
    print("outdoor_temp_object: ", outdoor_temp_object)

    indoor_temp = sensor_data_stringified(bme680, OPENWEATHER_UNITS)

    writeTemperatureValuesToDisplay(
        str(int(outdoor_temp_object['temp'])), indoor_temp)

    determineColorsForDisplay(outdoor_temp_object, indoor_temp,
                              OPENWEATHER_UNITS, UNIX_TIMESTAMP_FROM_TIME_SERVICE)

    time.sleep(60 * 5)  # wait 5 minutes
