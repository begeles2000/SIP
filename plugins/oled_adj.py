#!/usr/bin/env python
# This plugin sends data to I2C for OLED 128x32 char with Adafruit_SSD1306.
# This plugin required python Adafruit_SSD1306 library


from threading import Thread, Lock
from random import randint
import json
import time
import sys
import traceback

import web
import gv  # Get access to ospi's settings
from urls import urls  # Get access to sip's URLs
from ospi import template_render
from webpages import ProtectedPage
from helpers import uptime, get_ip, get_cpu_temp, get_rpi_revision
from blinker import signal

"""Import libraries for oled screen"""
import Adafruit_SSD1306
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
import Adafruit_GPIO as GPIO
import RPi.GPIO

# Add a new url to open the data entry page.
urls.extend(['/oled', 'plugins.oled_adj.settings',
             '/oledj', 'plugins.oled_adj.settings_json',
             '/oleda', 'plugins.oled_adj.update'])

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['OLED Settings', '/oled'])

################################################################################
# Main function loop:                                                          #
################################################################################

class OLEDSender(Thread):
    def __init__(self):
        Thread.__init__(self)
        self.daemon = True
        self.start()
        self.status = ''
        self.alarm_mode = False
        self.schedule_mode = False
        self._display = ['name']
        self._sleep_time = 0
        self._lcd = Lock()   

    def _lcd_print(self, report, txt=None):
        self._lcd.acquire()
        """Print messages to OLED 128x32"""
        dataoled = get_oled_options()
                
        #define RST pin
        adr = dataoled['adress']
        #configure display settings
        disp = Adafruit_SSD1306.SSD1306_128_32(rst=int(adr),gpio=GPIO.get_platform_gpio(mode=RPi.GPIO.BOARD))
                
        disp.begin()
        disp.clear()
        disp.display()
        width = disp.width
        height = disp.height
        image = Image.new('1', (width, height))
        draw = ImageDraw.Draw(image)
        draw.rectangle((0,0,width,height), outline=0, fill=0)
        padding = -2
        top = padding
        bottom = height-padding
        x = 0
        font = ImageFont.load_default()
        
        if report == 'name':            
            draw.rectangle((0,0,width,height), outline=0, fill=0)
            draw.text((x, top), "Name: ", font=font, fill=255)
            draw.text((x, top+8), str(gv.sd['name']),  font=font, fill=255)
            draw.text((x, top+16), "Irrigation syst.", font=font, fill=255)
            disp.image(image)
            disp.display()           
            self.add_status('SIP. / Irrigation syst.')
        elif report == 'd_sw_version':
            draw.rectangle((0,0,width,height), outline=0, fill=0)
            draw.text((x, top), "Software SIP: ", font=font, fill=255)
            draw.text((x, top+8), str(gv.ver_date),  font=font, fill=255)
            draw.text((x, top+16), "", font=font, fill=255)
            disp.image(image)
            disp.display()
            self.add_status('Software SIP: / ' + gv.ver_date)
        elif report == 'd_ip':            
            ip = get_ip()
            draw.rectangle((0,0,width,height), outline=0, fill=0)
            draw.text((x, top), "My IP is: ", font=font, fill=255)
            draw.text((x, top+8), str(ip),  font=font, fill=255)
            draw.text((x, top+16), "", font=font, fill=255)
            disp.image(image)
            disp.display()
            self.add_status('My IP is: / ' + str(ip))
        elif report == 'd_port':
            draw.rectangle((0,0,width,height), outline=0, fill=0)
            draw.text((x, top), "Port IP: ", font=font, fill=255)
            draw.text((x, top+8), str(gv.sd['htp']),  font=font, fill=255)
            draw.text((x, top+16), "", font=font, fill=255)
            disp.image(image)
            disp.display()           
            self.add_status('Port IP: / {}'.format(gv.sd['htp']))
        elif report == 'd_cpu_temp':
            temp = get_cpu_temp(gv.sd['tu']) + ' ' + gv.sd['tu']
            draw.rectangle((0,0,width,height), outline=0, fill=0)
            draw.text((x, top), "CPU temperature: ", font=font, fill=255)
            draw.text((x, top+8), str(temp),  font=font, fill=255)
            draw.text((x, top+16), "", font=font, fill=255)
            disp.image(image)
            disp.display()            
            self.add_status('CPU temperature: / ' + temp)
        elif report == 'd_date_time':
            da = time.strftime('%d.%m.%Y', time.gmtime(gv.now))
            ti = time.strftime('%H:%M:%S', time.gmtime(gv.now))
            
            draw.rectangle((0,0,width,height), outline=0, fill=0)
            draw.text((x, top), "Date Time: ", font=font, fill=255)
            draw.text((x, top+8), str(da),  font=font, fill=255)
            draw.text((x, top+16), str(ti), font=font, fill=255)
            disp.image(image)
            disp.display()
            self.add_status(da + ' ' + ti)
        elif report == 'd_uptime':
            up = uptime()
            draw.rectangle((0,0,width,height), outline=0, fill=0)
            draw.text((x, top), "System run Time: ", font=font, fill=255)
            draw.text((x, top+8), str(up),  font=font, fill=255)
            draw.text((x, top+16), "", font=font, fill=255)
            disp.image(image)
            disp.display()
            self.add_status('System run time: / ' + up)
        elif report == 'd_rain_sensor':
            if gv.sd['rs']:
                rain_sensor = "Active"
            else:
                rain_sensor = "Inactive"
            draw.rectangle((0,0,width,height), outline=0, fill=0)
            draw.text((x, top), "Rain sensor: ", font=font, fill=255)
            draw.text((x, top+8), str(rain_sensor),  font=font, fill=255)
            draw.text((x, top+16), "", font=font, fill=255)
            disp.image(image)
            disp.display()
            self.add_status('Rain sensor: / ' + rain_sensor)
        elif report == 'd_running_stations':  # Report running Stations
            if gv.pon is None:
                prg = 'Idle'
            elif gv.pon == 98:  # something is running
                prg = 'Run-once'
            elif gv.pon == 99:
                prg = 'Manual Mode'
            else:
                prg = "Prog: {}".format(gv.pon)

            s = ""
            if prg != "Idle":
                # Get Running Stations from gv.ps
                for i in range(len(gv.ps)):
                    p, d = gv.ps[i]
                    if p != 0:
                        s += "S{} ".format(str(i+1))
            draw.rectangle((0,0,width,height), outline=0, fill=0)
            draw.text((x, top), "Running Stations: ", font=font, fill=255)
            draw.text((x, top+8), str(prg),  font=font, fill=255)
            draw.text((x, top+16), str(s), font=font, fill=255)
            disp.image(image)
            disp.display()
        elif report == 'd_alarm_signal':  # ALARM!!!!
            draw.rectangle((0,0,width,height), outline=0, fill=0)
            draw.text((x, top), "ALARM!: ", font=font, fill=255)
            draw.text((x, top+8), str(txt),  font=font, fill=255)
            draw.text((x, top+16), "", font=font, fill=255)
            disp.image(image)
            disp.display()
        elif report == 'd_stat_schedule_signal':  # A program has been scheduled
            draw.rectangle((0,0,width,height), outline=0, fill=0)
            draw.text((x, top), "New program: ", font=font, fill=255)
            draw.text((x, top+8), "Running",  font=font, fill=255)
            draw.text((x, top+16), "...", font=font, fill=255)
            disp.image(image)
            disp.display()           
            self.add_status('New Program Running / ')
        self._lcd.release()

    def add_status(self, msg):
        if self.status:
            self.status += '\n' + msg
        else:
            self.status = msg
        print msg

    def update(self):
        oled_opts = get_oled_options()
        self._display = ['name']
        for key in oled_opts.keys() :
            if key.startswith('d_') and oled_opts[key] == 'on':
                self._display.append(key)
        self._sleep_time = 0

    def _sleep(self, secs):
        self._sleep_time = secs
        while self._sleep_time > 0:
            time.sleep(1)
            self._sleep_time -= 1

    def alarm(self, name,  **kw):
        dataoled = get_oled_options()
        if dataoled['use_oled'] != 'off' and not self.alarm_mode:  # if LCD plugin is enabled
            self.alarm_mode = True
        self._lcd_print('d_alarm_signal', txt=kw['txt'])

    def notify_station_scheduled(self, name,  **kw):
        dataoled = get_oled_options()
        if dataoled['use_oled'] != 'off' and not self.schedule_mode:  # if LCD plugin is enabled
            self.schedule_mode = True
            self._lcd_print('d_stat_schedule_signal')

    def run(self):
        time.sleep(randint(3, 10))  # Sleep some time to prevent printing before startup information
        print "OLED plugin is active"
        
        self.update()
        text_shift = 0
        while True:
            try:
                dataoled = get_oled_options()                          # load data from file
                if dataoled['use_oled'] != 'off':                      # if LCD plugin is enabled
                    if text_shift >= len(self._display):
                        text_shift = 0
                        self.status = ''
                    if self.alarm_mode:
                        self._sleep(20)
                        self.alarm_mode = False
                    elif self.schedule_mode:
                        self._sleep(5)
                        self.schedule_mode = True
                        self._lcd_print('d_running_stations')
                        self._sleep(5)
                    else:
                        self._lcd_print(self._display[text_shift])
                        text_shift += 1  # Increment text_shift value
                self._sleep(4)

            except Exception:
                exc_type, exc_value, exc_traceback = sys.exc_info()
                err_string = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
                self.add_status('OLED plugin encountered error: ' + err_string)
                self._sleep(60)


checker = OLEDSender()
alarm = signal('alarm_toggled')
alarm.connect(checker.alarm)
program_started = signal('stations_scheduled')
program_started.connect(checker.notify_station_scheduled)
################################################################################
# Helper functions:                                                            #
################################################################################


def get_oled_options():
    """Returns the data form file."""
    dataoled = {
        'use_oled': 'off',
        'adress': '24',
        'd_sw_version': 'on',
        'd_ip': 'on',
        'd_port': 'on',
        'd_cpu_temp': 'on',
        'd_date_time': 'on',
        'd_uptime': 'on',
        'd_rain_sensor': 'on',
        'd_running_stations': 'on',
        'status': checker.status
    }
    try:
        with open('./data/oled_adj.json', 'r') as f:  # Read the settings from file
            file_data = json.load(f)
        for key, value in file_data.iteritems():
            if key in dataoled:
                dataoled[key] = value
    except Exception:
        pass

    return dataoled

################################################################################
# Web pages:                                                                   #
################################################################################


class settings(ProtectedPage):
    """Load an html page for entering lcd adjustments."""

    def GET(self):
        return template_render.oled_adj(get_oled_options())


class settings_json(ProtectedPage):
    """Returns plugin settings in JSON format."""

    def GET(self):
        web.header('Access-Control-Allow-Origin', '*')
        web.header('Content-Type', 'application/json')
        return json.dumps(get_oled_options())


class update(ProtectedPage):
    """Save user input to oled_adj.json file."""

    def GET(self):
        qdict = web.input()
        dataoled = {
            'use_oled': 'off',
            'adress': '24',
            'd_sw_version': 'on',
            'd_ip': 'on',
            'd_port': 'on',
            'd_cpu_temp': 'on',
            'd_date_time': 'on',
            'd_uptime': 'on',
            'd_rain_sensor': 'on',
            'd_running_stations': 'on',
            'status': checker.status
        }
        for k in dataoled.keys():
            if qdict.has_key(k):
                dataoled[k] = qdict[k]
            else:
                dataoled[k] = 'off'

        with open('./data/oled_adj.json', 'w') as f:  # write the settings to file
            json.dump(dataoled, f)
        checker.update()
        raise web.seeother('/')
