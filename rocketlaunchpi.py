#!/usr/bin/env python
# RocketLaunchPi - Next Launch from Planet Earth 
#
# Note that actual launch time is approximate due 
# to last minute mission changes! 
#
# Uses LCD 20x4 I2C code from 
# https://gist.github.com/DenisFromHR/cc863375a6e19dce359d
# 
# Expects LCD I2C on 0x27 address
#
# Optional Audio
#
# Usage via cron: 
# Avoids running at same time as earthquakepi and during night
# $ crontab -e
# 5,20,35,50 08-22 * * * sudo python /home/pi/RocketLaunchPi/rocketlaunchpi.py >/home/pi/RocketLaunchPi/rocket.log 2>&1
#
#
# Version 1.0 2016.07.26 - Initial
#
# License: GPLv3, see: www.gnu.org/licenses/gpl-3.0.html
#


import subprocess
import os
import urllib2
import json
from datetime import datetime
from datetime import timedelta
import time
import calendar
import atexit
import socket
import sys
import re
import traceback

import RPi_I2C_driver

############ USER VARIABLES
DEBUG    = 0       # Debug 0 off, 1 on
LOG      = 1       # Log Launch data for past 15 min
AUDIO    = 1       # Sound 0 off, 1 on
VOLUME   = 80      # Sound volume 0-100% (if supported)
## OTHER SETTINGS
WAV = "/home/pi/RocketLaunchPi/NASAcountdown.wav"  # Path to Sound file
DISPLAY  = 0       # 0 Turn off LCD at exit, 1 Leave LCD on after exit
PAUSE    = 60      # Display Launch data for X seconds
########### END OF USER VARIABLES



## METHODS BELOW

def blink(lcd): # Blink the LCD
    for i in range(0,3,1):
        lcd.backlight(1)
        time.sleep(0.3)
        lcd.backlight(0)
        time.sleep(0.3)
    lcd.backlight(1)

def volume(val): # Set Volume for Launch
    vol = int(val)
    cmd = "sudo amixer -q sset PCM,0 "+str(vol)+"%"
    if DEBUG:
	print(cmd)
    os.system(cmd)
    return

def sound(val): # Play a sound
    time.sleep(1)
    cmd = "/usr/bin/aplay -q "+str(val)
    if DEBUG:
	print(cmd)
    os.system(cmd)
    #proc = subprocess.call(['/usr/bin/aplay', WAV], stderr=subprocess.PIPE)
    return


def exit():
    """
    Exit handler, which clears all custom chars and shuts down the display.
    """
    try:
	if not DISPLAY:
            lcd = RPi_I2C_driver.lcd()
            lcd.backlight(0)
        if DEBUG:
            print "exit()"
    except:
        # avoids ugly KeyboardInterrupt trace on console...
        pass


#####


#####
# MAIN HERE
if __name__ == '__main__':
    atexit.register(exit)

    lcd = RPi_I2C_driver.lcd()
    if DEBUG:
        lcd.backlight(1)
        lcd.lcd_clear()
        lcd.lcd_display_string('RocketLaunchPi',1)
        lcd.lcd_display_string('DEBUG ON',2)
        lcd.lcd_display_string('All Times are LOCAL',3)
	print "DEBUG MODE"
        print "STARTUP"
	if AUDIO:
	    volume(VOLUME)
	    sound(WAV)
        PAUSE = 10
    
    # Find the next Launch
    URL = "https://launchlibrary.net/1.2/launch?next=1&mode=verbose"

    if LOG:
	print URL

    # Call LaunchLibrary API. timeout in seconds 
    try:
        tmout = 15
        #socket.setdefaulttimeout(tmout)
        response = urllib2.urlopen(URL, timeout=tmout)
        data = json.load(response)   
        if DEBUG:
            print "--------------"
            print data
            print "--------------"
    except:
	print "timeout waiting for LaunchLibrary API response"
    
    # Status of launch
    status_arr = [ 'n/a', 'GREEN', 'RED', 'SUCCESS', 'FAILED']

    cnt = 0
    # DESIGNED FOR MULTIPLE LAUNCHES, BUT ONLY FIRST IS BEING GATHERED
    for launch in data['launches']:
        if LOG:
            print launch['id']
            print launch['name']
            print launch['isonet']
            print launch['location']['pads'][0]['name']
            print launch['location']['name']
            print launch['rocket']['name']
            print "--------------"

        try:
            id    = launch['id']
            title = launch['name']
            isotm = launch['isonet']
            loc   = launch['location']['name']
            rocket= launch['rocket']['name']
            status= launch['status']

	    # Format to fit screen
	    loc = loc[:24]
	    rocket = rocket[:24]
	    status = "STATUS: "+status_arr[int(status)]
    
	    # GET CURRENT UTC TIME
    	    utcnow = datetime.utcnow()
    	    utcnow_15 = utcnow - timedelta(minutes = 15)

	    # CONVERT LAUNCH TIME TO UTC AND LOCALTIME
	    # Note that actual launch time is approximate! 
	    unixsec = calendar.timegm(time.strptime(isotm.replace('Z', 'GMT'), '%Y%m%dT%H%M%S%Z'))
            utctime = datetime.utcfromtimestamp(unixsec)
            loctime = datetime.fromtimestamp(unixsec).strftime('%Y-%m-%d %H:%M:%S')

	    if DEBUG:
		print "utctime:"+str(utctime)
		print "loctime:"+str(loctime)
		print "status:"+str(status)
    
	    # LCD 20 x 4 DISPLAY
            lcd.lcd_clear()
	    blink(lcd)
	    lcd.lcd_display_string(rocket,1)
	    lcd.lcd_display_string(loc,2)
	    lcd.lcd_display_string(loctime,3)
	    lcd.lcd_display_string(status,4)
    	
	    # Sound Effect
	    # Note that the launch sound is only approximate to actual 
	    # launch (+-15 minutes or more if last minute hold/scrub)
	    if AUDIO:
		if utcnow_15 <= utctime <= utcnow:
	            volume(VOLUME)
                    sound(WAV)

	    cnt = cnt + 1
	    time.sleep(PAUSE)

        except NameError:
            print "No launches scheduled."
            if DEBUG:
                print(traceback.format_exc())
            print(traceback.format_exc()) # TEMPY

        except Exception as e:
            print "Unexpected error:", sys.exc_info()[0]
            if DEBUG:
                print(traceback.format_exc())

    # END FOR LOOP

    if (cnt == 0):
        lcd.backlight(DISPLAY)
        lcd.lcd_clear()
        lcd.lcd_display_string('RocketLaunchPi',1)
        lcd.lcd_display_string('No Launches scheduled!',2)
	time.sleep(PAUSE)
	if LOG:
	    print "No launches scheduled"
	
    if DEBUG:
        print "END OF RUN"

