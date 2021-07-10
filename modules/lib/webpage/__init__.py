# Distributed under MIT License
# Copyright (c) 2021 Remi BERTHOLET
""" All web pages defined here """
from tools.useful import log, iscamera
from webpage.passwordpage import *
from webpage.mainpage import *
from webpage.changepasswordpage import *
from webpage.infopage import *
from webpage.pushoverpage import *
from webpage.serverpage import *
from webpage.wifipage import *
if iscamera():
	from webpage.motionpage import *
	from webpage.streamingpage import *
	from webpage.camerapage import *
	from webpage.historicpage import *
	from webpage.zonemaskingpage import *
from webpage.presencepage import *
from webpage.batterypage import *
from webpage.systempage import *