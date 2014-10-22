import sys, time
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
		self.data = [0, 0, 0, 0]
		self.cnt = 0
		self.codeword = 0
		self.prev = 0
		self.base_freq = 170.8
		self.step_freq = 0.0125

	def crc(self):
		return CRC.calcWord((self.data[0] << 32) | (self.data[1] << 16) | (self.data[2]), 48) == self.data[3] >> 1

def shift(var, bit):
	var = (var << 1) & 0xFFFF
	if bit:
		var += 1

	return var

def mpt1327_decode(bit, m):
	m.prev = shift(m.prev, m.data[0] & 0x8000 == 0x8000)
	for i in range(3):
		m.data[i] = shift(m.data[i], m.data[i+1] & 0x8000 == 0x8000)

	m.data[3] = shift(m.data[3], bit);
	m.cnt += 1

	if m.codeword == 0:
		if m.data[3] == MPT_SYNC and m.crc():
			#print "CW0: %X, %X, %X, %X" % (m.data[0], m.data[1], m.data[2], m.data[3])
			#print "SYS: 0x%X" % (m.data[0] & 0x7FFF)
			sys.stdout.flush()
			m.codeword = 1
			m.cnt = 0

	if m.codeword == 1:
		if m.cnt == 64 and m.crc():
			#print "Prev: %X" % (m.prev)
			#print "CW1: %X, %X, %X, %X" % (m.data[0], m.data[1], m.data[2], m.data[3])
			cat = (m.data[1] >> 7) & 0x7
			type = (m.data[1] >> 5) & 0x3
			func = (m.data[1] >> 2) & 0x7

			if cat == 0:
				if type == 0:
					pass
					#sys.stdout.write('ALOHA ')
					#print "ALOHA %d" % ((m.data[1] & 0x3) << 2 | (m.data[2] >> 14))
				elif type == 1:
					sys.stdout.write('ACK')
					sys.stdout.write(acks[func])

					prefix = (m.data[0] & 0x7F00) >> 8
					ident1 = (m.data[0] << 5 | m.data[1] >> 11) & 0x1FFF

					print ' Prefix: 0x%x Ident1: 0x%x' % (prefix, ident1)
				elif type == 2:
					if func == 1:
						print "MAINT %d" % ((m.data[1] & 0x3) << 8 | (m.data[2] >> 8))
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
			
			if m.data[1] & 1<<10 == 0:
				channel_num = (m.data[1] << 1 | m.data[2] >> 15) & 0x3FF
				print "GTC Channel %d - %.4fMHz (%s)" % (channel_num, m.base_freq + (channel_num * m.step_freq), 'data' if (m.data[1] & 0x200) else 'voice')

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
