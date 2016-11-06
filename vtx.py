# -*- coding: utf-8 -*-

import json
import urllib2
import logging
import time
import os
import pygame

BASE_URL = 'http://192.168.2.112'
MONITOR_URL = BASE_URL + '/api/v1/monitor/'
HEADERS = {'User-Agent': 'vtx publisher'}

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("vtx")

screen = None
logo = None
font =  None
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
    logger.info("Framebuffer size: %d x %d", size[0], size[1])
    global screen
    screen = pygame.display.set_mode(size, pygame.FULLSCREEN)
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

    num = min(len(data.get("data")), 11)
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


def main():
    while True:
        data = get_monitor()
        draw_table(data)
        time.sleep(1)

if __name__ == "__main__":
    main()
