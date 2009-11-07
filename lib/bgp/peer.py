#!/usr/bin/env python
# encoding: utf-8
"""
peer.py

Created by Thomas Mangin on 2009-08-25.
Copyright (c) 2009 Exa Networks. All rights reserved.
"""

import time

from bgp.structure.message    import Failure
from bgp.message.open         import Open
from bgp.message.update       import Update
from bgp.message.keepalive    import KeepAlive
from bgp.message.notification import Notification, SendNotification

from bgp.protocol import Protocol,Network
from bgp.display import Display


# Present a File like interface to socket.socket

class Peer (Display):
	debug_timers = False		# debug hold/keepalive timers
	debug_trace = True			# debug traceback on unexpected exception
	
	def __init__ (self,neighbor,supervisor):
		Display.__init__(self,neighbor.peer_address,neighbor.peer_as)
		self.supervisor = supervisor
		self.neighbor = neighbor
		self.running = False
		self.restart = True
		self.bgp = None
		self._loop = None
		

	def stop (self):
		self.running = False

	def shutdown (self):
		self.running = False
		self.restart = False
	
	def run (self):
		if self._loop:
			try:
				self._loop.next()
			except StopIteration:
				self._loop = None
		elif self.restart:
			self.running = True
			self._loop = self._run()
		else:
			self.bgp.close()
			self.supervisor.unschedule(self)
	
	def _run (self):
		try:
			self.bgp = Protocol(self.neighbor)
			self.bgp.connect()
		
			o = self.bgp.new_open()
			self.log('-> %s' % o)
			yield

			o = self.bgp.read_open()
			self.log('<- %s' % o)
			yield

			message = self.bgp.new_keepalive(force=True)
			self.log('-> KEEPALIVE')
			yield

			message = self.bgp.read_keepalive()
			self.log('<- KEEPALIVE')

			a = self.bgp.new_announce()
			self.logIf(a,'-> %s' % a)

			while self.running:
				c = self.bgp.check_keepalive()
				self.logIf(self.debug_timers,'Receive Timer %d second(s) left' % c)

				c,k = self.bgp.new_keepalive()
				self.logIf(k,'-> KEEPALIVE')
				self.logIf(self.debug_timers,'Sending Timer %d second(s) left' % c)

				message = self.bgp.read_message()
				self.logIf(message.TYPE == KeepAlive.TYPE,'<- KEEPALIVE')
				self.logIf(message.TYPE == Update.TYPE,'<- UPDATE')

				u = self.bgp.new_update()
				self.logIf(u,'-> %s' % u)

				yield 
			# User closing the connection
			raise SendNotification(6,0)
		except SendNotification,e:
			self.log('Sending Notification (%d,%d) [%s]  %s' % (e.code,e.subcode,str(e),e.data))
			try:
				self.bgp.new_notification(e)
				self.bgp.close()
			except Failure:
				pass
			return
		except Notification, e:
			self.log('Received Notification (%d,%d) from peer %s' % (e.code,e.subcode,str(e)))
			self.bgp.close()
			return
		except Failure, e:
			self.log(str(e))
			self.bgp.close()
			return
		except Exception, e:
			self.log('UNHANDLED EXCEPTION')
			if self.debug_trace:
				import sys
				import traceback
				traceback.print_exc(file=sys.stdout)
			else:
				self.log(str(e))
			if self.bgp: self.bgp.close()
			return
