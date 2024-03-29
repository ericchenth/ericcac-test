#!/usr/bin/env python
# encoding: utf-8
"""
network.py

Created by Thomas Mangin on 2009-09-06.
Copyright (c) 2009-2011 Exa Networks. All rights reserved.
"""

import os
import struct
import time
import socket
import select

from bgp.utils import hexa,trace
from bgp.structure.address import AFI
from bgp.message import Failure

from bgp.log import Logger
logger = Logger()

class Connection (object):
	def __init__ (self,peer,local,md5,ttl):
		self.last_read = 0
		self.last_write = 0
		self.peer = peer

		logger.wire("Opening connection to %s" % self.peer)

		if peer.afi != local.afi:
			raise Failure('The local IP and peer IP must be of the same family (both IPv4 or both IPv6)')

		try:
			if peer.afi == AFI.ipv4:
				self._io = socket.socket(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP)
			if peer.afi == AFI.ipv6:
				self._io = socket.socket(socket.AF_INET6, socket.SOCK_STREAM, socket.IPPROTO_TCP)
			try:
				self._io.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
			except AttributeError:
				pass
			try:
				self._io.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
			except AttributeError:
				pass
			self._io.settimeout(1)
			if peer.afi == AFI.ipv4:
				self._io.bind((local.ip,0))
			if peer.afi == AFI.ipv6:
				self._io.bind((local.ip,0,0,0))
		except socket.error,e:
			self.close()
			raise Failure('could not bind to local ip %s - %s' % (local.ip,str(e)))

		if md5:
			try:
				TCP_MD5SIG = 14
				TCP_MD5SIG_MAXKEYLEN = 80
				SS_PADSIZE = 120
				
				n_addr = socket.inet_aton(peer.ip)
				n_port = socket.htons(179)
				tcp_md5sig = 'HH4s%dx2xH4x%ds' % (SS_PADSIZE, TCP_MD5SIG_MAXKEYLEN)
				md5sig = struct.pack(tcp_md5sig, socket.AF_INET, n_port, n_addr, len(md5), md5)
				self._io.setsockopt(socket.IPPROTO_TCP, TCP_MD5SIG, md5sig)
			except socket.error,e:
				self.close()
				raise Failure('This OS does not support TCP_MD5SIG, you can not use MD5 : %s' % str(e))

		# None (ttl-security unset) or zero (maximum TTL) is the same thing
		if ttl:
			try:
				self._io.setsockopt(socket.IPPROTO_IP,socket.IP_TTL, 20)
			except socket.error,e:
				self.close()
				raise Failure('This OS does not support IP_TTL (ttl-security), you can not use MD5 : %s' % str(e))

		try:
			if peer.afi == AFI.ipv4:
				self._io.connect((peer.ip,179))
			if peer.afi == AFI.ipv6:
				self._io.connect((peer.ip,179,0,0))
			self._io.setblocking(0)
		except socket.error, e:
			self.close()
			raise Failure('could not connect to peer (if you use MD5, check your passwords): %s' % str(e))

	def pending (self):
		r,_,_ = select.select([self._io,],[],[],0)
		if r: return True
		return False

	# File like interface

	def read (self,number):
		if number == 0: return ''
		try:
			r = self._io.recv(number)
			self.last_read = time.time()
			logger.wire("%15s RECV %s" % (self.peer,hexa(r)))
			return r
		except socket.timeout,e:
			self.close()
			logger.wire("%15s %s" % (self.peer,trace()))
			raise Failure('timeout attempting to read data from the network:  %s ' % str(e))
		except socket.error,e:
			self.close()
			logger.wire("%15s %s" % (self.peer,trace()))
			raise Failure('problem attempting to read data from the network:  %s ' % str(e))

	def write (self,data):
		try:
			logger.wire("%15s SENT %s" % (self.peer,hexa(data)))
			r = self._io.send(data)
			self.last_write = time.time()
			return r
		except socket.error, e:
			# Broken pipe, we ignore as we want to make sure if there is data to read before failing
			if getattr(e,'errno',None) != 32:
				self.close()
				logger.wire("%15s %s" % (self.peer,trace()))
				raise Failure('problem attempting to write data to the network: %s' % str(e))

	def close (self):
		try:
			logger.wire("Closing connection to %s" % self.peer)
			self._io.close()
		except socket.error:
			pass

