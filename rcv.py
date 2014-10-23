import sys, time
from bitstring import BitArray
from CrcMoose import CrcAlgorithm

MPT_SYNC = 0xC4D7
MPT_SYNT = 0x3B28

CRC = CrcAlgorithm(15, 0x6815, xorMask=0x1)

acks = [
	' General',
	'I Intermediate',
	'Q Call queued',
	'X Message rejected',
	'V Called unit unavailable',
	'E ** EMERGENCY CALL**',
	'T Try on given address',
	'B Call back or negative'
]

class mpt1327_state:
	def __init__(self):
		self.data = BitArray(uint=0, length=64)
		self.cnt = 0
		self.codeword = 0
		self.prev = 0
		self.base_freq = 170.8
		self.step_freq = 0.0125

	def crc(self):
		data, checksum = self.data.unpack('uint:48, uint:15')
		return CRC.calcWord(data, 48) == checksum and self.data.count(1) % 2 == 0 # Even parity

def mpt1327_decode(bit, m):
	m.data <<= 1
	m.data[63] = bit

	m.cnt += 1

	address_codeword, information_field, parity = m.data.unpack('bool, bits:47, uint')

	if m.codeword == 0:
		sysid, ccs, preamble = information_field.unpack('uint:15, uint:16, uint:16')
		if parity == MPT_SYNC and m.crc():
			#print "CW0: %X, %X, %X, %X" % (m.data[0], m.data[1], m.data[2], m.data[3])
			print "SYS: 0x%X" % sysid
			sys.stdout.flush()
			m.codeword = 1
			m.cnt = 0

	if m.codeword == 1:
		if m.cnt == 64:
			if m.crc():
				#print "Prev: %X" % (m.prev)
				#print "CW1: %X, %X, %X, %X" % (m.data[0], m.data[1], m.data[2], m.data[3])
				parameters, general, cat, type, func, sub_parameters = information_field.unpack('bits:20, bool, uint:3, uint:2, uint:3, bits')
				cat = (m.data[1] >> 7) & 0x7
				type = (m.data[1] >> 5) & 0x3
				func = (m.data[1] >> 2) & 0x7

				if cat == 0:
					if type == 0:
						pass
						#sys.stdout.write('ALOHA ')
						print "ALOHA %d" % ((m.data[1] & 0x3) << 2 | (m.data[2] >> 14))
					elif type == 1:
						sys.stdout.write('ACK')
						sys.stdout.write(acks[func])

						prefix, ident1 = parameters.unpack('uint:7, uint:13')

						print ' Prefix: 0x%x Ident1: 0x%x' % (prefix, ident1)
					elif type == 2:
						if func == 1:
							print "MAINT %d" % sub_parameters.unpack('uint')
						print 'REQ / AHOY'
					elif type == 3:
						#print 'MISC'
						if func == 1:
							print 'Call maintenance message - MAINT'
						elif func == 3:
							print 'Move to control channel - MOVE'
						elif func == 4:
							# TODO: MISC BCAST
							#print "SYSDEF: %d" % ((m.data[0] & 0x7C00) >> 10)
							pass
						else:
							print "CAT: %d TYPE: %d FUNC: %d" % (cat, type, func)
				elif cat == 1:
					if type == 0:
						print 'Single address message'
					elif type == 1:
						print 'Short data message'
				else:
					print "CAT: %d TYPE: %d FUNC: %d" % (cat, type, func)

				if not general:
					pfix, ident1, general, data, channel_num, ident2, aloha_num = information_field.unpack('uint:7, uint:13, bool, bool, uint:10, uint:13, uint:2')
					print "GTC Channel %d - %.4fMHz (%s)" % (channel_num, m.base_freq + (channel_num * m.step_freq), 'data' if (data) else 'voice')

			m.codeword = 0
			m.cnt = 0

	return m

state = mpt1327_state()
f = open(sys.argv[1], 'r', 0)
while True:
	c = f.read(1)
	if c is None:
		time.sleep(0)
		break
	bit = (c == '\1')
	state = mpt1327_decode(bit, state)
print
