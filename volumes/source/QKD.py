import abc

class QKD(abc.ABC):
	@abc.abstractmethod
	def begin(self, serverPort):
		pass

	@abc.abstractmethod
	def exchangeKey(self, key_length, key_id, destination, timeout, eve):
		pass

	@abc.abstractmethod
	def end(self):
		pass
