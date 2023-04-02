# Distributed under MIT License
# Copyright (c) 2021 Remi BERTHOLET
# pylint:disable=consider-using-f-string
""" Periodic task, wifi management, get wan_ip, synchronize time """
import gc
import uasyncio
from server.user import User
from server.server import ServerConfig
import wifi
from tools import lang,tasking,watchdog,info,system,support,topic,filesystem

class Periodic:
	""" Class to manage periodic task """
	server_config = None

	@staticmethod
	def init():
		""" Constructor """
		if Periodic.server_config is None:
			Periodic.server_config = ServerConfig()
			Periodic.server_config.load_create()
			Periodic.last_success_notification = None
			Periodic.current_time = 0
			watchdog.WatchDog.start(watchdog.SHORT_WATCH_DOG)
		else:
			Periodic.server_config.refresh()

	@staticmethod
	async def check_login():
		""" Inform that login detected """
		# Get login state
		login =  User.get_login_state()

		# If login detected
		if login is not None:
			from server.notifier import Notifier
			if login:
				if Periodic.last_success_notification is None:
					notif = True
					Periodic.last_success_notification = Periodic.current_time
				elif Periodic.last_success_notification + 5*60 < Periodic.current_time:
					Periodic.last_success_notification = Periodic.current_time
					notif = True
				else:
					notif = False
				if notif:
					Notifier.notify(topic=topic.login, value=topic.value_success, message=lang.login_success_detected, display=False, enabled=Periodic.server_config.notify)
			else:
				Notifier.notify    (topic=topic.login, value=topic.value_failed,  message=lang.login_failed_detected,  display=False, enabled=Periodic.server_config.notify)

	@staticmethod
	async def task(**kwargs):
		""" Periodic task method """
		Periodic.init()
		if support.battery():
			from tools import battery

		polling_id = 0

		watchdog.WatchDog.start(watchdog.SHORT_WATCH_DOG)
		while True:
			# Reload server config if changed
			if polling_id % 5 == 0:
				# Manage login user
				await Periodic.check_login()

				Periodic.server_config.refresh()

			# Manage server
			if wifi.Wifi.is_lan_connected():
				tasking.Tasks.start_server()

			# Reset brownout counter if wifi connected
			if wifi.Wifi.is_wan_connected():
				if support.battery():
					battery.Battery.reset_brownout()

			# Periodic garbage to avoid memory fragmentation
			if polling_id % 7 == 0:
				gc.collect()
				if filesystem.ismicropython():
					# pylint:disable=no-member
					gc.threshold(gc.mem_free() // 5 + gc.mem_alloc())

			# Check if any problems have occurred and if a reboot is needed
			if polling_id % 3607 == 0:
				if info.get_issues_counter() > 15:
					system.reboot("Reboot required, %d problems detected"%info.get_issues_counter())

			# Reset watch dog
			watchdog.WatchDog.feed()
			await uasyncio.sleep(1)
			polling_id += 1
			Periodic.current_time += 1

	@staticmethod
	def start():
		""" Start periodic treatment """
		tasking.Tasks.create_monitor(Periodic.task)
