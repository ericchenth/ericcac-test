#!/usr/bin/env python
# encoding: utf-8
"""
attributes.py

Created by Thomas Mangin on 2009-11-05.
Copyright (c) 2009 Exa Networks. All rights reserved.
"""

import socket

from bgp.utils import *
from bgp.structure.address import AFI,SAFI
from bgp.structure.ip import to_IP,Inet
from bgp.message.update.attribute import AttributeID,Flag,Attribute

# =================================================================== NextHop (3)

def to_NextHop (ip):
	return NextHop(to_IP(ip))

class NextHop (Attribute):
	ID = AttributeID.NEXT_HOP
	FLAG = Flag.TRANSITIVE
	MULTIPLE = False

	# Take an IP as value
	def __init__ (self,value):
		Attribute.__init__(self,value)

	def pack (self):
		return self._attribute(self.attribute.pack())

	def __len__ (self):
		return len(self.attribute.pack())

	def __str__ (self):
		return str(self.attribute)
