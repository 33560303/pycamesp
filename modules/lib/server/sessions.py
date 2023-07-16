# Distributed under Pycameresp License
# Copyright (c) 2023 Remi BERTHOLET
""" Class used to store http connection sessions, it is useful if you define
an user and password, on your site """
import time
import tools.encryption
import tools.strings
import tools.date

class Sessions:
	""" Class manage an http sessions """
	sessions = []

	@staticmethod
	def create(duration, remember_me=False):
		""" Create new session """
		session = tools.encryption.gethash(tools.date.date_to_bytes())
		if remember_me == b"1":
			duration = 86400*365
		Sessions.sessions.append((session, time.time() + duration))
		return session

	@staticmethod
	def check(session):
		""" Check if the session not expired """
		result = False
		if session is not None:
			for sessionId, expiration in Sessions.sessions:
				if sessionId == session:
					result = True
					break
		Sessions.purge()
		return result

	@staticmethod
	def purge():
		""" Purge older sessions (only expired) """
		current_time = time.time()
		for sessionId, expiration in Sessions.sessions:
			if expiration < current_time:
				Sessions.sessions.remove((sessionId, expiration))

	@staticmethod
	def remove(sessionIdRemove):
		""" Remove session """
		for sessionId, expiration in Sessions.sessions:
			if sessionId == sessionIdRemove:
				Sessions.sessions.remove((sessionId, expiration))
