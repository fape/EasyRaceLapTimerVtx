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

BASE_URL = 'http://localhost'
UPD_IP = ''
MQTT_HOST = '192.168.2.112'
MQTT_TOPIC = 'erlt/monitor'
MONITOR_URL = BASE_URL + '/api/v1/monitor/'
HEADERS = {'User-Agent': 'vtx publisher'}

logger = None


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
    screen = pygame.display.set_mode((658, 540))
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
        logger.debug("I'm running under X display = %", disp_no)

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
        except pygame.error as e:
            logger.error("Driver: %s failed: %s", driver, e)
            continue
        logger.info("Driver found: %s", driver)
        found = True
        break

    if not found:
        raise Exception('No suitable video driver found!')

    size = (pygame.display.Info().current_w, pygame.display.Info().current_h)
    global screen
    screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
    logger.info("FrameBuffer size: %d x %d", screen.get_width(), screen.get_height())
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
        font2 = pygame.font.SysFont("sans", 40)

    # pygame.draw.rect(screen, (255, 0, 0), (0, 0, screen.get_width(), screen.get_height()), 1)

    # Get a font and use it render some text on a Surface.
    # font = pygame.font.Font(None, 70)
    # font2 = pygame.font.Font(None, 45)

    session = data.get("session")
    text = font.render(session.get("title"), True, (255, 255, 255))  # White text

    logger.debug("text height %s", text.get_height())
    screen.blit(logo, (0, (text.get_height()/2 - logo.get_height()/2)))
    # Blit the racename to left corner
    screen.blit(text, (((screen.get_width() - logo.get_width() - 5 )/2 - text.get_width()/2 + logo.get_width() + 5 ), 0))

    num = min(len(data.get("data")), 11)+1

    h_space = max(round((((screen.get_height()-text.get_height())-num * font2.get_height())/num+2)), 0)
    # space = 0
    logger.debug("h_space %s", h_space)

    idx = 0
    text_h = text.get_height() + h_space

    table = {}
    max_sizes = {}

    for item in data.get("data"):
        even = idx % 2 == 0
        idx += 1
        rank = item.get("position")
        rank_txt = render_table_text(rank, even)
        pilot = item.get("pilot").get("name")
        pilot_txt = render_table_text(pilot, even)
        fastest_lap = item.get("fastest_lap").get("lap_time")
        fastest_lap_txt = render_table_text(format_lap_time(fastest_lap), even)
        last_lap = item.get("last_lap").get("lap_time")
        last_lap_txt = render_table_text(format_lap_time(last_lap), even)
        avg_lap = item.get("avg_lap_time")
        avg_lap_txt = render_table_text(format_lap_time(avg_lap), even)
        # lap_count = item.get("lap_count")
        # lap_count_txt = render_table_text(lap_count, even)

        table[pilot] = {"position": idx, "rank": rank, "rank_txt": rank_txt, "pilot": pilot, "pilot_txt": pilot_txt,
                        "fastest_lap": fastest_lap, "fastest_lap_txt": fastest_lap_txt, "last_lap": last_lap,
                        "last_lap_txt": last_lap_txt, "avg_lap": avg_lap, "avg_lap_txt": avg_lap_txt,
                        # "lap_count": lap_count, "lap_count_txt": lap_count_txt
                        }

        calc_max_width(max_sizes, "rank_txt", rank_txt)
        calc_max_width(max_sizes, "pilot_txt", pilot_txt)
        calc_max_width(max_sizes, "fastest_lap_txt", fastest_lap_txt)
        calc_max_width(max_sizes, "last_lap_txt", last_lap_txt)
        calc_max_width(max_sizes, "avg_lap_txt", avg_lap_txt)
        # calc_max_width(max_sizes, "lap_count_txt", lap_count_txt)

    test_txt = font2.render(" ", True, (255, 255, 255))
    w_space = max(round((screen.get_width() - sum(max_sizes.itervalues()))/5), test_txt.get_width())
    w_space_start = round(w_space/2)
    logger.debug("w_space %s" % w_space)

    for item in table.itervalues():
        pos = item["position"]
        rank_txt = item["rank_txt"]
        pilot_txt = item["pilot_txt"]
        last_lap_txt = item["last_lap_txt"]
        fastest_lap_txt = item["fastest_lap_txt"]
        avg_lap_txt = item["avg_lap_txt"]
        draw_height = text_h + (pos-1)*(font2.get_height() + h_space)
        if draw_height + font2.get_height() <= screen.get_height():
            screen.blit(rank_txt, (max_sizes["rank_txt"] - rank_txt.get_width()+ w_space_start, draw_height))
            screen.blit(pilot_txt, (max_sizes["rank_txt"] + w_space + w_space_start, draw_height))
            screen.blit(last_lap_txt, (max_sizes["rank_txt"] + max_sizes["pilot_txt"] + w_space * 2 + w_space_start,
                                       draw_height))
            screen.blit(fastest_lap_txt, (max_sizes["rank_txt"] + max_sizes["pilot_txt"] + max_sizes["last_lap_txt"]
                        + w_space * 3 + w_space_start, draw_height))
            screen.blit(avg_lap_txt, (max_sizes["rank_txt"] + max_sizes["pilot_txt"] + max_sizes["last_lap_txt"]
                        + max_sizes["fastest_lap_txt"] + w_space * 4 + w_space_start, draw_height))

    del table
    logger.debug(max_sizes)
    # Render the screen
    pygame.display.update()


def calc_max_width(sizes, key, text):
    sizes[key] = max(sizes.get(key, 0), text.get_width())


def render_table_text(text, even):
    return font2.render("%s" % text, True, (249, 178, 51) if even else (255, 255, 255))


def format_lap_time(lap_time):
    return "%ss" % round(lap_time/1000., 2)


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

    while True:
        raw_data, address = s.recvfrom(65535)
        logger.debug("address %s", address)
        data = json.loads(raw_data)
        draw_table(data)
        process_window_event()


def draw_polling():
    while True:
        data = get_monitor()
        draw_table(data)
        process_window_event()
        time.sleep(1)


def draw_file():
    data = json.load(args.file)
    draw_table(data)

    if args.window:
        while True:
            process_window_event()
    else:
        time.sleep(100)


def process_window_event():
    if args.window:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()


def init_logging(args):
    level = getattr(logging, args.log.upper(), None)
    if not isinstance(level, int):
        raise ValueError('Invalid log level: %s' % args.log)
    logging.basicConfig(level=level, stream=sys.stdout)
    global logger
    logger = logging.getLogger("vtx")


def main():
    init_logging(args)
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
    parser.add_argument('-l', '--log', choices=['critical', 'error', 'warning', 'info', 'debug'], default='info')

    args = parser.parse_args()

    main()
