import sys
import requests
import time
import validators

def main():
	# request 100 keys without eavesdropper
	'''
	x = requests.post('http://172.15.0.6:4000/attacks?interceptAndResend=0')
	error_count = 0
	count = 0
	good_count = 0
	for i in range(100):
		print("requesting key ", count)
		x = requests.post('http://172.15.0.4:4000/startKeyExchange', data = repr({'destination' : 'http://172.15.0.5:4000', 'length' : 128, 'protocol' : 'BB84'}))
		aliceKey = x.content
		aliceStatus = x.status_code
		x = requests.post('http://172.15.0.5:4000/startKeyExchange', data = repr({'destination' : 'http://172.15.0.4:4000', 'length' : 128, 'protocol' : 'BB84'}))
		bobStatus = x.status_code
		bobKey = x.content
		if aliceStatus == 200 and bobStatus == 200:
			count += 1
			if eval(aliceKey)[1] == True:
				good_count += 1
			else:
				error_count += 1
	print("Number of keys requested:", count, "number of correctly exchanged keys:", good_count, "number of errors:", error_count)
	'''

	# request 100 keys with eavesdropper
	x = requests.post('http://172.15.0.6:4000/attacks?interceptAndResend=1')
	error_count = 0
	count = 0
	good_count = 0
	qber = {}
	for i in range(100):
		print("requesting key ", count)
		x = requests.post('http://172.15.0.4:4000/startKeyExchange', data = repr({'destination' : 'http://172.15.0.5:4000', 'length' : 128, 'protocol' : 'BB84'}))
		aliceKey = x.content
		aliceStatus = x.status_code
		x = requests.post('http://172.15.0.5:4000/startKeyExchange', data = repr({'destination' : 'http://172.15.0.4:4000', 'length' : 128, 'protocol' : 'BB84'}))
		bobStatus = x.status_code
		bobKey = x.content
		aliceKey = eval(aliceKey)
		if aliceStatus == 200 and bobStatus == 200:
			count += 1
			if aliceKey[1] == True:
				error_count += 1
			else:
				q = str(aliceKey[2])
				if qber.get(q) is None:
					qber[q] = 1
				else:
					qber[q] = qber[q] + 1
	print("numebr of keys requested:", count, "number of error:", error_count)
	print("qber occurrencies:")
	print(qber)


if __name__ == "__main__":
	main()
