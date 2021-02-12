from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister
from qiskit.quantum_info import Statevector
import math

# randomStringGen
# Make random strings of length string_length
# @param string_length: length of the random string to be generated
# @return: the generated random string
def randomStringGen(string_length):
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
