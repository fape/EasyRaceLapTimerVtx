# -*- coding: utf-8 -*-

import sys
import json
import urllib2
import logging
import time
import os
import pygame
import argparse
import socket
import paho.mqtt.client as mqtt

BASE_URL = 'http://192.168.2.112'
UPD_IP = ''
MQTT_HOST = '192.168.2.112'
MQTT_TOPIC = 'erlt/monitor'
MONITOR_URL = BASE_URL + '/api/v1/monitor/'
HEADERS = {'User-Agent': 'vtx publisher'}

logging.basicConfig(level=logging.DEBUG, stream=sys.stdout)
logger = logging.getLogger("vtx")


args = None
screen = None
logo = None
font = None
font2 = None


def get_json(url):
    try:
        request = urllib2.Request(url, headers=HEADERS)
        response = urllib2.urlopen(request)
        return json.load(response, response.info().getparam('charset'))
    except urllib2.HTTPError as e:
        logger.error("HTTP Error: %s, %s", e.code, url)
    except urllib2.URLError as e:
        logger.error("URL Error %s, %s", e.reason, url)
    except ValueError as e:
            logger.error("Json Decode Error: %s", e.message)
    except Exception as e:
        logger.error("Unexpected exception: %s", e.message)
    return None


def get_monitor():
    logger.debug("get monitor")
    return get_json(MONITOR_URL)


def init_window():
    pygame.init()
    logger.info("init window")
    global screen
    screen = pygame.display.set_mode((615, 512))
    logger.info("window size: %d x %d", screen.get_width(), screen.get_height())
    # Clear the screen to start
    screen.fill((0, 0, 0))
    # Initialise font support
    pygame.font.init()
    # Render the screen
    pygame.display.flip()


def init_framebuffer():
    "Ininitializes a new pygame screen using the framebuffer"
    # Based on "Python GUI in Linux frame buffer"
    # http://www.karoltomala.com/blog/?p=679
    disp_no = os.getenv("DISPLAY")
    if disp_no:
        print "I'm running under X display = {0}".format(disp_no)

    # Check which frame buffer drivers are available
    # Start with fbcon since directfb hangs with composite output
    drivers = ['fbcon', 'directfb', 'svgalib']
    found = False
    for driver in drivers:
        # Make sure that SDL_VIDEODRIVER is set
        if not os.getenv('SDL_VIDEODRIVER'):
            os.putenv('SDL_VIDEODRIVER', driver)
        try:
            pygame.display.init()
        except pygame.error:
            print 'Driver: {0} failed.'.format(driver)
            continue
        found = True
        break

    if not found:
        raise Exception('No suitable video driver found!')

    size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
    global screen
    screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
    logger.info("Framebuffer size: %d x %d", screen.get_width(), screen.get_height())
    # Clear the screen to start
    screen.fill((0, 0, 0))
    # Initialise font support
    pygame.font.init()
    # Hide mouse
    pygame.mouse.set_visible(False)
    # Render the screen
    pygame.display.update()


def draw_table(data):
    if not screen:
        if args.window:
            init_window()
        else:
            init_framebuffer()
    # Clear the screen to start
    screen.fill((0, 0, 0))
    # Render the Easy race lap timer to bottom center
    global logo
    if not logo:
        logo = pygame.image.load('easy_race_lap_timer_logo-2.png').convert_alpha()

    global font
    if not font:
        font = pygame.font.SysFont("sans", 49)
        logger.info("font: %s", pygame.font.get_default_font())  # freesansbold.ttf
    global font2
    if not font2:
        font2 = pygame.font.SysFont("sans", 37)

    # Get a font and use it render some text on a Surface.
    #font = pygame.font.Font(None, 70)
    # font2 = pygame.font.Font(None, 45)

    session = data.get("session")
    text = font.render(session.get("title"), True, (255, 255, 255))  # White text

    logger.debug("text height %s", text.get_height())
    screen.blit(logo, (0, (text.get_height()/2 - logo.get_height()/2)))
    # Blit the racename to left corner
    screen.blit(text, (((screen.get_width() - logo.get_width() - 5 )/2 - text.get_width()/2 + logo.get_width() + 5 ), 0))

    num = min(len(data.get("data")), 11)+1
    test = font2.render("M", True, (255, 255, 255))

    space = max(round((((screen.get_height()-text.get_height())-num * test.get_height())/num+2)), 0)
    #space = 0
    logger.debug("space %s", space);

    idx = 0
    text_h = text.get_height() + space;

    for item in data.get("data"):
        rank = item.get("position")
        pilot = item.get("pilot").get("name")
        fastest_lap = format_lap_time(item.get("fastest_lap").get("lap_time"))
        last_lap = format_lap_time(item.get("last_lap").get("lap_time"))
        avg_lap = format_lap_time(item.get("avg_lap_time"))
        lap_count = item.get("lap_count")

        line = "%s %s %s %s %s %s" % (rank, pilot, last_lap, fastest_lap, avg_lap, lap_count)
        text = font2.render(line, True, (249, 178, 51) if (idx % 2 == 0) else (255, 255, 255))
        idx += 1
        logger.debug("line %s, text_h %s, height %s", line, text_h, text.get_height())

        if text_h + text.get_height() <= screen.get_height():
            screen.blit(text, (0, text_h))
            text_h += text.get_height()+ space
        else:
            break

    # Render the screen
    pygame.display.update()


def format_lap_time(time):
    return "%ss" % round(time/1000., 4)


def mqtt_on_connect(client, userdata, flags, rc):
    logger.debug("Connected with result code %s", rc)
    client.subscribe(MQTT_TOPIC)


def mqtt_on_message(client, userdata, msg):
    data = json.loads(msg.payload)
    draw_table(data)


def draw_mqtt():
    logger.debug("mqtt draw")

    client = mqtt.Client()
    client.on_connect = mqtt_on_connect
    client.on_message = mqtt_on_message

    client.connect(MQTT_HOST, 1883, 60)
    init_framebuffer()
    client.loop_forever()


def draw_udp():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind((UPD_IP, 33333))

    init_framebuffer()

    while True:
        rawdata, addr = s.recvfrom(65535)
        logger.debug("address %s", addr)
        data = json.loads(rawdata)
        draw_table(data)


def draw_polling():
    while True:
        data = get_monitor()
        draw_table(data)
        time.sleep(1)


def draw_file():
    data = json.load(args.file)
    draw_table(data)

    if args.window:
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit();
                    exit()
    else:
        time.sleep(10)


def main():
    logger.debug(args)
    if not args:
        logger.error("no args")
    if args.mqtt:
        logger.info("use mqtt")
        draw_mqtt()
    elif args.udp:
        logger.info("use udp")
        draw_udp()
    elif args.file:
        logger.info("use file")
        draw_file()
    else:
        logger.info("use polling")
        draw_polling()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='vtx publisher')
    parser.add_argument('-m', '--mqtt', action='store_true')
    parser.add_argument('-u', '--udp', action='store_true')
    parser.add_argument('-f', '--file', type=argparse.FileType('r'))
    parser.add_argument('-w', '--window', action='store_true')

    args = parser.parse_args()

    main()
