#!/usr/bin/env python
# encoding: utf-8
"""
asn.py

Created by Thomas Mangin on 2010-01-15.
Copyright (c) 2010 Exa Networks. All rights reserved.
"""


from struct import pack

# =================================================================== ASN

class ASN (int):
	def asn4 (self):
		return self > pow(2,16)

	def pack (self,asn4):
		if asn4:
			return pack('!L',self)
		return pack('!H',self)

	def __len__ (self):
		return self.length

AS_TRANS = ASN(23456)
