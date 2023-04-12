# Distributed under MIT License
# Copyright (c) 2021 Remi BERTHOLET
# pylint:disable=consider-using-f-string
""" Get the wan ip address """
import random
import time
import uasyncio
import wifi.wifi
import server.stream
import server.httprequest
import server.server
import server.notifier
import tools.logger
import tools.strings
import tools.tasking

class WanIp:
	""" Class to get the wan ip address """
	config = None
	last_sync = 0
	wan_ip = None
	forced = [False]

	@staticmethod
	async def request(host, port, path):
		""" Asynchronous request to ip server """
		result = None
		try:
			streamio = None
			reader,writer = await uasyncio.open_connection(tools.strings.tostrings(host), port)
			streamio = server.stream.Stream(reader, writer)
			req = server.httprequest.HttpRequest(None)
			req.set_path(tools.strings.tobytes(path))
			req.set_header(b"HOST",tools.strings.tobytes(host))
			req.set_method(b"GET")
			req.set_header(b"Accept"         ,b"text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8")
			req.set_header(b"User-Agent"     ,b"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.3 Safari/605.1.15")
			req.set_header(b"Accept-Language",b"fr-FR,fr;q=0.9")
			req.set_header(b"Connection"     ,b"keep-alive")
			await req.send(streamio)
			response = server.httprequest.HttpResponse(streamio)
			await response.receive(streamio)
			if response.status == b"200":
				result = response.get_content().strip()

		except Exception as err:
			tools.logger.syslog(err)
		finally:
			if streamio:
				await streamio.close()
		return result

	@staticmethod
	def init():
		""" Initialisation task """
		if WanIp.config is None:
			WanIp.config = server.server.ServerConfig()
			WanIp.config.load_create()
		else:
			WanIp.config.refresh()

	@staticmethod
	async def synchronize():
		""" Get the wan ip address with asynchronous method """
		hosts =[
			("alma.ch"              ,"/myip.cgi"),
			("api.infoip.io"        ,"/ip"),
			("api.ipify.org"        ,"/"),
			("checkip.amazonaws.com","/"),
			("l2.io"                ,"/ip"),
			("whatismyip.akamai.com","/")
		]
		host, path = hosts[random.randrange(0,len(hosts))]
		resp = await WanIp.request(host,80,path)
		if resp:
			return resp.decode("utf-8")
		else:
			tools.logger.syslog("Cannot get wan ip with '%s'"%host)
			return None

	@staticmethod
	async def task():
		""" Asynchronous task to refresh periodically the wan ip """
		WanIp.init()
		polling = 13

		# If wanip synchronization enabled
		if WanIp.config.wanip:
			# If the wan is present
			if wifi.wifi.Wifi.is_wan_available():
				if WanIp.last_sync + 86413 < time.time() or WanIp.last_sync == 0:
					# Get wan ip
					new_wan_ip = await WanIp.synchronize()

					# If wan ip get
					if new_wan_ip is not None:
						# If wan ip must be notified
						if WanIp.wan_ip != new_wan_ip:
							server.notifier.Notifier.daily_notify()
						WanIp.wan_ip = new_wan_ip
						wifi.wifi.Wifi.wan_connected()
					else:
						wifi.wifi.Wifi.wan_disconnected()
		else:
			polling = 59

		await uasyncio.sleep(polling)

	@staticmethod
	def start():
		""" Start wanip synchronisation task """
		tools.tasking.Tasks.create_monitor(WanIp.task)
