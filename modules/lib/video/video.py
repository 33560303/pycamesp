# Distributed under MIT License
# Copyright (c) 2021 Remi BERTHOLET
""" Class to manage the camera of the ESP32CAM.
This requires the modified firmware.
I added in the firmware the possibility of detecting movements,
as well as a lot of adjustment on the camera, not available on the other firmware that manages the esp32cam.
"""
# pylint: disable=multiple-statements
import time
import uasyncio
from tools import info,system,jsonconfig,logger
if info.iscamera():
	import camera

class CameraConfig(jsonconfig.JsonConfig):
	""" Class that collects the camera rendering configuration """
	def __init__(self):
		""" Constructor """
		jsonconfig.JsonConfig.__init__(self)
		self.activated  = True
		self.framesize  = b"640x480"
		self.pixformat  = b"JPEG"
		self.quality    = 25
		self.brightness = 0
		self.contrast   = 0
		self.saturation = 0
		self.hmirror    = False
		self.vflip      = False
		self.flash_level = 0

class Motion:
	""" Class motion detection returned by the detect function """
	def __init__(self, motion):
		""" Constructor with motion object_ """
		self.motion = motion

	def deinit (self):
		""" Destructor """
		self.motion.deinit()

	def extract(self):
		""" Extract the full content of motion """
		return self.motion.extract()

	def compare(self, other):
		""" Compare image to detect motion """
		return self.motion.compare(other.motion)

	def configure(self, param):
		""" Configure the motion detection """
		self.motion.configure(param)

	def get_image(self):
		""" Return the jpeg buffer of motion """
		return self.motion.get_image()

class Reservation:
	""" Manage the camera reservation """
	def __init__(self):
		""" Constructor """
		self.identifier = None
		self.count = 0
		self.lock = uasyncio.Lock()
		self.suspended = 0

	async def reserve(self, object_, timeout=0, suspension=None):
		""" Wait the ressource and reserve """
		result = False
		# Wait
		while True:
			result = await self.acquire(object_, suspension)
			if result:
				break
			timeout -= 1
			if timeout <= 0:
				break
			await uasyncio.sleep_ms(1000)
		return result

	async def acquire(self, object_, suspension=None):
		""" Reserve the camera, is used to stream the output of the camera
		to the web page. It stop the motion detection during this phase """
		result = False
		await self.lock.acquire()
		identifier = id(object_)
		try:
			# If not reserved
			if self.identifier is None:
				# If suspension not required
				if suspension is None:
					# If previous suspension ended
					if self.suspended <= 0:
						# Reserve
						self.identifier = identifier
						self.count = 1
						self.suspended = 0
						result = True
					else:
						# Decrease suspension counter
						self.suspended -= 1
				else:
					# Reserve
					self.identifier = identifier
					self.count = 1
					self.suspended = suspension
					result = True
			# If already reserved by the current object_
			elif self.identifier == identifier:
				# Increase reservation counter
				self.count += 1
				self.suspended = suspension
				result = True
		finally:
			self.lock.release()
		return result

	async def unreserve(self, object_):
		""" Unreserve the camera """
		result = False
		await self.lock.acquire()
		identifier = id(object_)
		try:
			if self.identifier == identifier:
				if self.count <= 1:
					self.count = 0
					self.identifier = None
				else:
					self.count -= 1
				result = True
		finally:
			self.lock.release()
		return result

class Camera:
	""" Singleton class to manage the camera """
	reservation = Reservation()
	opened = False
	lock = uasyncio.Lock()
	modified = [False]
	success = [0]
	failed  = [0]
	newFailed = [0]
	config = None

	@staticmethod
	def gpio_config(pwdn = 32,
		reset= -1,
		xclk =  0,
		siod = 26,
		sioc = 27,
		d7   = 35,
		d6   = 34,
		d5   = 39,
		d4   = 36,
		d3   = 21,
		d2   = 19,
		d1   = 18,
		d0   =  5,
		vsync= 25,
		href = 23,
		pclk = 22,
		freq_hz=20000000,
		ledc_timer=0,
		ledc_channel=0,
		pixel_format=3,
		frame_size=13,
		jpeg_quality=12,
		fb_count=1,
		flash_led=4):
		""" Configure the structure for camera initialization. It must be done before the first call of Camera.open.
			The defaults values are for ESP32CAM.
			- pwdn           : GPIO pin for camera power down line
			- reset          : GPIO pin for camera reset line
			- xclk           : GPIO pin for camera XCLK line
			- siod           : GPIO pin for camera SDA line
			- sioc           : GPIO pin for camera SCL line
			- d7             : GPIO pin for camera D7 line
			- d6             : GPIO pin for camera D6 line
			- d5             : GPIO pin for camera D5 line
			- d4             : GPIO pin for camera D4 line
			- d3             : GPIO pin for camera D3 line
			- d2             : GPIO pin for camera D2 line
			- d1             : GPIO pin for camera D1 line
			- d0             : GPIO pin for camera D0 line
			- vsync          : GPIO pin for camera VSYNC line
			- href           : GPIO pin for camera HREF line
			- pclk           : GPIO pin for camera PCLK line
			- freq_hz        : Frequency of XCLK signal, in Hz. Either 20KHz or 10KHz for OV2640 double FPS (Experimental)
			- ledc_timer     : LEDC timer to be used for generating XCLK
			- ledc_channel   : LEDC channel to be used for generating XCLK
			- pixel_format   : Format of the pixel data: PIXFORMAT_ + YUV422|GRAYSCALE|RGB565|JPEG
			- frame_size     : Size of the output image: FRAMESIZE_ + QVGA|CIF|VGA|SVGA|XGA|SXGA|UXGA
			- jpeg_quality   : Quality of JPEG output. 0-63 lower means higher quality
			- fb_count       : Number of frame buffers to be allocated. If more than one, then each frame will be acquired (double speed)
			- flash_led      : GPIO pin for flash led or 0 to disable """
		Camera.get_config()
		if Camera.is_activated():
			camera.configure(
				pwdn=pwdn,
				reset=reset,
				xclk=xclk,
				siod=siod,
				sioc=sioc,
				d7=d7,
				d6=d6,
				d5=d5,
				d4=d4,
				d3=d3,
				d2=d2,
				d1=d1,
				d0=d0,
				vsync=vsync,
				href=href,
				pclk=pclk,
				freq_hz=freq_hz,
				ledc_timer=ledc_timer,
				ledc_channel=ledc_channel,
				pixel_format=pixel_format,
				frame_size=frame_size,
				jpeg_quality=jpeg_quality,
				fb_count=fb_count,
				flash_led=flash_led)

	@staticmethod
	def open():
		""" Open the camera """
		Camera.get_config()
		if Camera.is_activated():
			result = True
			if Camera.opened is False:
				for i in range(10):
					res = camera.init()
					if res is False:
						# print("Camera not initialized")
						camera.deinit()
						time.sleep(0.5)
					else:
						break
				else:
					result = False

				if result:
					# Photo on 800x600, motion detection / 8 (100x75), each square detection 8x8 (12.5 x 9.375)
					Camera.opened = True
		else:
			result = False
		return result

	@staticmethod
	def get_stat():
		""" Statistic """
		return Camera.success[0], Camera.failed[0]

	@staticmethod
	def reset_stat():
		""" Reset statistic """
		Camera.success[0] = 0
		Camera.failed [0] = 0
		Camera.newFailed[0] = 0

	@staticmethod
	def close():
		""" Close the camera """
		if Camera.opened is True:
			camera.deinit()
			Camera.opened = False

	@staticmethod
	def is_opened():
		""" Indicates if the camera opened """
		return Camera.opened

	@staticmethod
	def capture():
		""" Capture an image on the camera """
		return Camera.retry(camera.capture)

	@staticmethod
	def motion():
		""" Get the motion informations.
		This contains a jpeg image, with matrices of the different color RGB """
		return Camera.retry(camera.motion)

	@staticmethod
	def flash(level=0):
		""" Start or stop the flash """
		camera.flash(level)

	@staticmethod
	def retry(callback):
		""" Retry camera action and manage error """
		result = None
		if Camera.opened:
			retry = 10
			while 1:
				if retry <= 0:
					system.reboot("Reboot forced after camera problem")
				try:
					result = callback()
					Camera.success[0] += 1
					break
				except ValueError:
					Camera.failed[0] += 1
					Camera.newFailed[0] += 1
					if retry <= 3:
						logger.syslog("Failed to get image %d retry before reset"%retry)
					retry -= 1
					time.sleep(0.5)
			total = Camera.success[0] + Camera.failed[0]
			STAT_CAMERA=5000
			if (total % STAT_CAMERA) == 0:
				if Camera.success[0] != 0:
					newFailed = 100.-((Camera.newFailed[0]*100)/STAT_CAMERA)
					failed    = 100.-((Camera.failed[0]*100)/total)
				else:
					newFailed = 0.
					failed    = 0.
				logger.syslog("Camera stat : last %-3.1f%%, total %-3.1f%% success on %d"%(newFailed, failed, total))
				Camera.newFailed[0] = 0
		return result

	@staticmethod
	async def reserve(object_, timeout=0, suspension=None):
		""" Reserve the camera, is used to stream the output of the camera
		to the web page. It stop the motion detection during this phase """
		return await Camera.reservation.reserve(object_, timeout, suspension)

	@staticmethod
	async def unreserve(object_):
		""" Unreserve the camera """
		return await Camera.reservation.unreserve(object_)

	@staticmethod
	def is_modified():
		""" Indicates that the camera configuration has been changed """
		return Camera.modified[0]

	@staticmethod
	def clear_modified():
		""" Reset the indicator of configuration modification """
		Camera.modified[0] = False

	@staticmethod
	def framesize(resolution):
		""" Configure the frame size """
		val = None
		Camera.modified[0] = True
		if resolution == b"UXGA"  or resolution == b"1600x1200" :val = camera.FRAMESIZE_UXGA
		if resolution == b"SXGA"  or resolution == b"1280x1024" :val = camera.FRAMESIZE_SXGA
		if resolution == b"XGA"   or resolution == b"1024x768"  :val = camera.FRAMESIZE_XGA
		if resolution == b"SVGA"  or resolution == b"800x600"   :val = camera.FRAMESIZE_SVGA
		if resolution == b"VGA"   or resolution == b"640x480"   :val = camera.FRAMESIZE_VGA
		if resolution == b"CIF"   or resolution == b"400x296"   :val = camera.FRAMESIZE_CIF
		if resolution == b"QVGA"  or resolution == b"320x240"   :val = camera.FRAMESIZE_QVGA
		if resolution == b"HQVGA" or resolution == b"240x176"   :val = camera.FRAMESIZE_HQVGA
		if resolution == b"QQVGA" or resolution == b"160x120"   :val = camera.FRAMESIZE_QQVGA
		if Camera.opened and val is not None:
			# print("Framesize %s"%strings.tostrings(resolution))
			camera.framesize(val)
		# else:
			# print("Framesize not set")

	@staticmethod
	def pixformat(format_):
		""" Change the format of image """
		Camera.modified[0] = True
		val = None
		if format_ == b"RGB565"    : val=camera.PIXFORMAT_RGB565
		if format_ == b"YUV422"    : val=camera.PIXFORMAT_YUV422
		if format_ == b"GRAYSCALE" : val=camera.PIXFORMAT_GRAYSCALE
		if format_ == b"JPEG"      : val=camera.PIXFORMAT_JPEG
		if format_ == b"RGB888"    : val=camera.PIXFORMAT_RGB888
		if format_ == b"RAW"       : val=camera.PIXFORMAT_RAW
		if format_ == b"RGB444"    : val=camera.PIXFORMAT_RGB444
		if format_ == b"RGB555"    : val=camera.PIXFORMAT_RGB555
		if Camera.opened and val is not None:
			# print("Pixformat %s"%strings.tostrings(format_))
			camera.pixformat(val)
		# else:
			# print("Pixformat not set")

	@staticmethod
	def quality(val=None, modified=True):
		""" Configure the compression """
		Camera.modified[0] = modified
		if Camera.opened:
			# print("Quality %d"%val)
			return camera.quality(val)
		return None

	@staticmethod
	def brightness(val=None):
		""" Change the brightness """
		Camera.modified[0] = True
		if Camera.opened:
			# print("Brightness %d"%val)
			return camera.brightness(val)
		return None

	@staticmethod
	def contrast(val=None):
		""" Change the contrast """
		Camera.modified[0] = True
		if Camera.opened:
			# print("Contrast %d"%val)
			return camera.contrast(val)
		return None

	@staticmethod
	def saturation(val=None):
		""" Change the saturation """
		Camera.modified[0] = True
		if Camera.opened:
			# print("Saturation %d"%val)
			return camera.saturation(val)
		return None

	@staticmethod
	def sharpness(val=None):
		""" Change the sharpness """
		Camera.modified[0] = True
		if Camera.opened:
			# print("Sharpness %d"%val)
			return camera.sharpness(val)
		return None

	@staticmethod
	def hmirror(val=None):
		""" Set horizontal mirroring """
		Camera.modified[0] = True
		if Camera.opened:
			# print("Hmirror %d"%val)
			return camera.hmirror(val)
		return None

	@staticmethod
	def vflip(val=None):
		""" Set the vertical flip """
		Camera.modified[0] = True
		if Camera.opened:
			# print("Vflip %d"%val)
			return camera.vflip(val)
		return None

	@staticmethod
	def configure(config):
		""" Configure the camera """
		if Camera.opened:
			Camera.pixformat (config.pixformat)
			Camera.framesize (config.framesize)
			Camera.quality   (config.quality)
			Camera.brightness(config.brightness)
			Camera.contrast  (config.contrast)
			Camera.saturation(config.saturation)
			Camera.hmirror   (config.hmirror)
			Camera.vflip     (config.vflip)
			Camera.flash     (config.flash_level)

	@staticmethod
	def get_config():
		""" Reload configuration if it changed """
		if Camera.config is None:
			Camera.config = CameraConfig()
			if Camera.config.load() is False:
				Camera.config.save()
		else:
			if Camera.config.is_changed():
				Camera.config.load()
		return Camera.config

	@staticmethod
	def is_activated():
		""" Indicates if the camera is configured to be activated """
		if Camera.config is None:
			Camera.get_config()
		if Camera.config is not None:
			return Camera.config.activated
		else:
			return False
