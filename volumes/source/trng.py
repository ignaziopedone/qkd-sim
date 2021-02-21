import yaml
import math


pref_file = open("config/configS.yaml", 'r')
prefs = yaml.safe_load(pref_file)

if prefs['rng']['rand'] == 'trng':
	# true random number generator uses quantum
	from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister
	from qiskit.quantum_info import Statevector
else:
	# pseudo random number generator uses random
	import random

# randomStringGen
# Make random strings of length string_length
# @param string_length: length of the random string to be generated
# @return: the generated random string
def randomStringGen(string_length):
	if prefs['rng']['rand'] == 'trng':
		#output variables used to access quantum computer results at the end of the function
		output = ''
		n = string_length
		temp_n = 10
		temp_output = ''
		for i in range(math.ceil(n/temp_n)):
			#initialize quantum registers for circuit
			q = QuantumRegister(temp_n, name='q')
			c = ClassicalRegister(temp_n, name='c')
			rs = QuantumCircuit(q, c, name='rs')
			rs.h(range(temp_n))

			label = '0' * temp_n

			#execute circuit and extract 0s and 1s from key
			sve = Statevector.from_label(label)
			res = sve.evolve(rs)
			temp_output = res.measure()[0]
			output += temp_output

		#return output clipped to size of desired string length
		return output[:n]
	else:
		return ''.join(str(random.randint(0,1)) for i in range(string_length))
