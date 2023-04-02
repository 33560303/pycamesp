# Distributed under MIT License
# Copyright (c) 2021 Remi BERTHOLET
""" Allows automatic component start without editing python scripts.
This searches for __startup__.py files in lib directory and runs the 'startup' function """
from tools import logger, filesystem, tasking

starter_kwargs = None
class Starter:
	""" Automatic component start without editing python script """
	@staticmethod
	async def task(**kwargs):
		""" Starter of components """
		global starter_kwargs
		directories,filenames = await filesystem.ascandir("lib","__startup__.py",True)
		for startup in filenames:
			startup = startup.replace("lib/","")
			startup = startup.replace(".py","")
			startup = startup.replace("/",".")

			try:
				# pylint:disable=consider-using-f-string
				exec("import %s"%startup)
				starter_kwargs = kwargs
				exec("%s.startup(**starter_kwargs)"%startup)
				starter_kwargs = None
				logger.syslog("Start component %s"%startup[:-12])
			except Exception as err:
				logger.syslog(err)

	@staticmethod
	def start(**kwargs):
		""" Start module started """
		tasking.Tasks.create_task(Starter.task(**kwargs))
