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
    '/doors', 'plugins.door.semiOpen',
	'/dooru', 'plugins.door.update']) 

# Add this plugin to the home page plugins menu
gv.plugin_menu.append(['Door control', '/door'])

# Add this to the signal plugin
def notify_door_actuated(status, **kw):
    print "Door actuated. Actual status {}".format(status)

door_actuated = signal('door_actuated')
door_actuated.connect(notify_door_actuated)

def report_door_actuated(status):
    """
    Send blinker signal indicating that the door has been actuated.
    Include the door status as data.
    """
    door_actuated.send(status)

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
            'o_semi': 'on',
            'o_sens': 'off',
            'sens_t': 'NO',
            'active': 'low',
            'last':   '0',
            'status':'closed'
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
        print 'Door control plugin only supported on pi.'
except:
  print 'Door control: GPIO pins not set'
  pass


#### setup GPIO pins as output and either high or low ####
#### setup also GPIO inputs and either NO or NC       ####
def init_pins():
    global pi
    try:
        for i in range(len(relay_pins)):
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
                pi.set_mode(sensor_pin[0], pigpio.INPUT)
            else:                
                GPIO.setup(sensor_pin[0], GPIO.IN, pull_up_down=GPIO.PUD_UP) 
         
    except:
        pass


init_pins();

"""Read sensor status and save it"""
def update_sensor():
    print (GPIO.input(sensor_pin[0]))
    if params['o_sens'] == 'on':
        if params['sens_t'] == 'NO':
            if GPIO.input(sensor_pin[0]):
                params['status'] = "OPEN";
            else:
                params['status'] = "CLOSE";
        else:
            if GPIO.input(sensor_pin[0]):
                params['status'] = "CLOSE";
            else:
                params['status'] = "OPEN";


################################################################################
# Web pages:                                                                   #
################################################################################

class settings(ProtectedPage):
    """Load an html page for entering relay board adjustments"""

    def GET(self):
        with open('./data/door.json', 'r') as f:  # Read the settings from file
            params = json.load(f)
        return template_render.door(params)


class update(ProtectedPage):
    """Save user input to door.json file"""

    def GET(self):
        qdict = web.input()
        changed = False        
        if params['enabled'] != str(qdict['enabled']):           
           params['enabled'] = str(qdict['enabled'])
           changed = True             
        if params['o_full'] != str(qdict['o_full']): # if the open full field has changed update the params           
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
        if params['last'] != str(qdict['last']):  # if type of relays has changed, update the params           
           params['last'] = str(qdict['last'])           
           changed = True
        
        if changed:
           init_pins();
           with open('./data/door.json', 'w') as f:  # write the settings to file
              json.dump(params, f)
        raise web.seeother('/')
      
class fullOpen(ProtectedPage):
    ##Actuates the full open relay
    
    def GET(self):
        GPIO.output(relay_pins[0], GPIO.LOW)
        time.sleep(1)
        GPIO.output(relay_pins[0], GPIO.HIGH)        
        update_sensor()
        report_door_actuated(params['status'])
        params['last'] =  time.asctime( time.localtime(time.time()) )
        with open('./data/door.json', 'w') as f:  # write the settings to file
              json.dump(params, f) 
        raise web.seeother('/door')

class semiOpen(ProtectedPage):
    ##Actuates the full open relay
    
    def GET(self):
        GPIO.output(relay_pins[1], GPIO.LOW)
        time.sleep(1)
        GPIO.output(relay_pins[1], GPIO.HIGH)
        time.sleep(1)
        update_sensor()
        report_door_actuated(params['status'])
        params['last'] =  time.asctime( time.localtime(time.time()) )
        with open('./data/door.json', 'w') as f:  # write the settings to file
              json.dump(params, f)             
        raise web.seeother('/door')
       