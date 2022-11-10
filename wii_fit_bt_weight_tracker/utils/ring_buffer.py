import numpy


# From https://github.com/irq0/wiiscale/blob/master/scale.py
class RingBuffer:
	def __init__(self, length):
		self.length = length
		self.filled = False
		self.index = 0
		self.data = None
		self.reset()

	def extend(self, x):
		x_index = (self.index + numpy.arange(x.size)) % self.data.size
		self.data[x_index] = x
		self.index = x_index[-1] + 1

		if not self.filled and self.index == (self.length-1):
			self.filled = True

	def append(self, x):
		x_index = (self.index + 1) % self.data.size
		self.data[x_index] = x
		self.index = x_index

		if not self.filled and self.index == (self.length-1):
			self.filled = True

	def get(self):
		idx = (self.index + numpy.arange(self.data.size)) % self.data.size
		return self.data[idx]

	def reset(self):
		self.data = numpy.zeros(self.length, dtype=numpy.int)
		self.index = 0
