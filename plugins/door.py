#!/usr/bin/env python

from blinker import signal
import web, json, time
import gv  # Get access to SIP's settings, gv = global variables
from urls import urls  # Get access to SIP's URLs
from sip import template_render
from webpages import ProtectedPage

# Load the Raspberry Pi GPIO (General Purpose Input Output) library
try:
    if gv.use_pigpio:
        import pigpio
        pi = pigpio.pi()
    else:
        import RPi.GPIO as GPIO
        pi = 0
except IOError:
    pass

# Add a new url to open the data entry page.
urls.extend(['/door', 'plugins.door.settings',
 	'/doorf', 'plugins.door.fullOpen',
	'/dooru', 'plugins.door.update']) 

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['Door controll', '/door'])

params = {}

# Read in the parameters for this plugin from it's JSON file
def load_params():
    global params
    try:
        with open('./data/door.json', 'r') as f:  # Read the settings from file
            params = json.load(f)
    except IOError: #  If file does not exist create file with defaults.
        params = {
            'enabled': 'off',
            'o_full': 'on',
            'o_semi': 'off',
            'o_sens': 'off',
            'sens_t': 'NO',
            'active': 'low'
        }
        with open('./data/door.json', 'w') as f:
            json.dump(params, f)
    return params

load_params()

if params['enabled'] == 'on':
    gv.use_gpio_pins = False  # Signal SIP to not use GPIO pins

#### define the GPIO pins that will be used ####
try:
    if gv.platform == 'pi': # If this will run on Raspberry Pi:
        if not gv.use_pigpio:
            GPIO.setmode(GPIO.BOARD) #IO channels are identified by header connector pin numbers. Pin numbers are 
        relay_pins = [38,40]
        sensor_pin = [19]
        for i in range(len(relay_pins)):
            try:
                relay_pins[i] = gv.pin_map[relay_pins[i]]
            except:
                relay_pins[i] = 0
    else:
        print 'Door controll plugin only supported on pi.'
except:
  print 'Door controll: GPIO pins not set'
  pass


#### setup GPIO pins as output and either high or low ####
#### setup also GPIO inputs and either NO or NC       ####
def init_pins():
  global pi

  try:
    for i in range(params['relays']):
        if gv.use_pigpio:
            pi.set_mode(relay_pins[i], pigpio.OUTPUT)
        else:
            GPIO.setup(relay_pins[i], GPIO.OUT)
        if params['active'] == 'low':
            if gv.use_pigpio:
                pi.write(relay_pins[i],1)
            else:
                GPIO.output(relay_pins[i], GPIO.HIGH)
        else:
            if gv.use_pigpio:
                pi.write(relay_pins[i],0)
            else:
                GPIO.output(relay_pins[i], GPIO.LOW)
        time.sleep(0.1)
    #if sensor is enabled    
    if params['o_sens'] == 'on':
        if gv.use_pigpio:
            pi.set_mode(sensor_pin, pigpio.INPUT)
        else:
            if params['sens_t'] == 'NO':
                GPIO.setup(sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN) 
            else:
                GPIO.setup(sensor_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
  except:
    pass

#### change outputs when blinker signal received ####
def on_zone_change(arg): #  arg is just a necessary placeholder.
    """ Switch relays when core program signals a change in zone state."""

    global pi

    with gv.output_srvals_lock:
        for i in range(params['relays']):
            try:
                if gv.output_srvals[i]:  # if station is set to on
                    if params['active'] == 'low':  # if the relay type is active low, set the output low
                        if gv.use_pigpio:
                            pi.write(relay_pins[i],0)
                        else:
                            GPIO.output(relay_pins[i], GPIO.LOW)
                    else:  # otherwise set it high
                        if gv.use_pigpio:
                            pi.write(relay_pins[i],1)
                        else:
                            GPIO.output(relay_pins[i], GPIO.HIGH)
#                     print 'relay switched on', i + 1, "pin", relay_pins[i]  #  for testing #############
                else:  # station is set to off
                    if params['active'] == 'low':  # if the relay type is active low, set the output high
                        if gv.use_pigpio:
                            pi.write(relay_pins[i],1)
                        else:
                            GPIO.output(relay_pins[i], GPIO.HIGH)
                    else:  # otherwise set it low
                        if gv.use_pigpio:
                            pi.write(relay_pins[i],0)
                        else:
                            GPIO.output(relay_pins[i], GPIO.LOW)
#                     print 'relay switched off', i + 1, "pin", relay_pins[i]  #  for testing ############
            except Exception, e:
                print "Problem switching relays", e, relay_pins[i]
                pass

init_pins();


################################################################################
# Web pages:                                                                   #
################################################################################

class settings(ProtectedPage):
    """Load an html page for entering relay board adjustments"""

    def GET(self):
        with open('./data/door.json', 'r') as f:  # Read the settings from file
            params = json.load(f)
        return template_render.door(params)


# class settings_json(ProtectedPage):
#     """Returns plugin settings in JSON format"""
# 
#     def GET(self):
#         web.header('Access-Control-Allow-Origin', '*')
#         web.header('Content-Type', 'application/json')
#         return json.dumps(params)


class update(ProtectedPage):
    """Save user input to door.json file"""

    def GET(self):
        qdict = web.input()
        changed = False
        if params['enabled'] != str(qdict['enabled']):
           params['enabled'] = str(qdict['enabled'])
           changed = True             
        if params['o_full'] != str(qdict['o_full']):  # if the open full field has changed update the params
           params['o_full'] = str(qdict['o_full'])
           changed = True
        if params['o_semi'] != str(qdict['o_semi']):  # if the open SEMI field has changed update the params
           params['o_semi'] = str(qdict['o_semi'])
           changed = True
        if params['o_sens'] != str(qdict['o_sens']):  # if the sensor active field has changed update the params
           params['o_sens'] = str(qdict['o_sens'])
           changed = True
        if params['sens_t'] != str(qdict['sens_t']):  # if the sensor type field has changed update the params
           params['sens_t'] = str(qdict['sens_t'])
           changed = True
        if params['active'] != str(qdict['active']):  # if type of relays has changed, update the params
           params['active'] = str(qdict['active'])           
           changed = True
        if changed:
           init_pins();
           with open('./data/door.json', 'w') as f:  # write the settings to file
              json.dump(params, f)
        raise web.seeother('/')
      
class fullOpen(ProtectedPage):
    ##Actuates the full open relay"
    GPIO.output(sensor_pin, GPIO.HIGH)
    sleep(1)
    GPIO.output(sensor_pin, GPIO.LOW)
    def GET(self):
        with open('./data/door.json', 'r') as f:  # Read the settings from file
            params = json.load(f)
        
         raise web.seeother('/door')