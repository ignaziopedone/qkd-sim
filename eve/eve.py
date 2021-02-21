from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister, execute, BasicAer
from qiskit.quantum_info import Statevector
from flask import Flask, request, Response
import logging
import requests
import yaml
import pickle
from trng import randomStringGen
import numpy as np
import re


app = Flask(__name__)

pref_file = open("/usr/src/app/src/configEve.yaml", 'r')
prefs = yaml.safe_load(pref_file)

interceptAndResend = prefs['attack']['interceptAndResend']
manInTheMiddle = prefs['attack']['manInTheMiddle']

abPatterns = [
		re.compile('00$'), # search for the '..00' output (Alice obtained -1 and Bob obtained -1)
		re.compile('01$'), # search for the '..01' output
		re.compile('10$'), # search for the '..10' output (Alice obtained -1 and Bob obtained 1)
		re.compile('11$')  # search for the '..11' output
]


# chsh_corr
# Calculates CHSH correlation value
# @param circuits: circuits used for the measurements
# @param result: measurement results
# @param aliceMeasurementChoices: Alice's basis table
# @param bobMeasurementChoices: Bob's basis table
# @param abPatterns: patterns count in results
# @return: correlation value
def chsh_corr(circuits, result, aliceMeasurementChoices, bobMeasurementChoices, abPatterns):
	# lists with the counts of measurement results
	# each element represents the number of (-1,-1), (-1,1), (1,-1) and (1,1) results respectively
	countA1B1 = [0, 0, 0, 0] # XW observable
	countA1B3 = [0, 0, 0, 0] # XV observable
	countA3B1 = [0, 0, 0, 0] # ZW observable
	countA3B3 = [0, 0, 0, 0] # ZV observable

	for i in range(len(result)):
		res = result[i]

		# if the spins of the qubits of the i-th singlet were projected onto the a_1/b_1 directions
		if (aliceMeasurementChoices[i] == 1 and bobMeasurementChoices[i] == 1):
			for j in range(4):
				if abPatterns[j].search(res):
					countA1B1[j] += 1

		if (aliceMeasurementChoices[i] == 1 and bobMeasurementChoices[i] == 3):
			for j in range(4):
				if abPatterns[j].search(res):
					countA1B3[j] += 1

		if (aliceMeasurementChoices[i] == 3 and bobMeasurementChoices[i] == 1):
			for j in range(4):
				if abPatterns[j].search(res):
					countA3B1[j] += 1

		# if the spins of the qubits of the i-th singlet were projected onto the a_3/b_3 directions
		if (aliceMeasurementChoices[i] == 3 and bobMeasurementChoices[i] == 3):
			for j in range(4):
				if abPatterns[j].search(res):
					countA3B3[j] += 1

	# number of the results obtained from the measurements in a particular basis
	total11 = sum(countA1B1)
	total13 = sum(countA1B3)
	total31 = sum(countA3B1)
	total33 = sum(countA3B3)

	# expectation values of XW, XV, ZW and ZV observables (2)
	expect11 = 0
	if total11 != 0:
		expect11 = (countA1B1[0] - countA1B1[1] - countA1B1[2] + countA1B1[3])/total11 # -1/sqrt(2)
	expect13 = 0
	if total13 != 0:
		expect13 = (countA1B3[0] - countA1B3[1] - countA1B3[2] + countA1B3[3])/total13 # 1/sqrt(2)
	expect31 = 0
	if total31 != 0:
		expect31 = (countA3B1[0] - countA3B1[1] - countA3B1[2] + countA3B1[3])/total31 # -1/sqrt(2)
	expect33 = 0
	if total33 != 0:
		expect33 = (countA3B3[0] - countA3B3[1] - countA3B3[2] + countA3B3[3])/total33 # -1/sqrt(2)

	corr = expect11 - expect13 + expect31 + expect33 # calculate the CHSC correlation value (3)

	return corr




@app.route('/sendRegister', methods=['POST'])
def forwardQubits():
	qubits = pickle.loads(request.data)
	destination = request.args.get('destination')
	if destination is None:
		# error - this should not happen
		return "Bad request", 400
	req = destination + '/sendRegister'
	keyLen = request.args.get('keyLen')
	if keyLen is not None:
		req = req + '?keyLen=' + keyLen

	# Do attacks on quantum channel here
	if interceptAndResend:
		chunk = qubits[0].num_qubits
		eveTable = np.array([])
		eveMeasurements = []
		for i in range(len(qubits)):
			# generate a quantum circuit random basis for measurements
			qr = QuantumRegister(chunk, name='qr')
			cr = ClassicalRegister(chunk, name='cr')
			circuit = QuantumCircuit(qr, cr, name='qcircuit')

			basisChoice = randomStringGen(chunk)
			# randomly chose basis for measurement
			table = np.array([])
			for index, bit in enumerate(basisChoice): 
				if 0.5 < int(bit):
					circuit.h(qr[index])
					table = np.append(table, 'X')
				else:
					table = np.append(table, 'Z')

			# Reverse table
			table = table[::-1]
			eveTable = np.append(eveTable, table)
			eveMeasurements.append(qubits[i].evolve(circuit))

		# replace data to be forwarded
		qubits = eveMeasurements

	# forward request and related reply
	x = requests.post(req, data = pickle.dumps(qubits))
	return x.content, x.status_code


@app.route('/compareBasis', methods=['POST'])
def compareBasis():
	destination = request.args.get('destination')
	if destination is None:
		# error - this should not happen
		return "Bad request", 400
	
	res = eval(request.data)
	if len(res) == 2:
		# sphincs+
		basis_table = res[0]
		table_sign = res[1]
		forward = [basis_table, table_sign]
	else:
		# aesgcm
		basis_table = res[0]
		keyID = res[1]
		nonce = res[2]
		forward = [basis_table, keyID, nonce]

	# Do attacks on classical channel here
	if manInTheMiddle:
		pass

	# forward request and related reply
	x = requests.post(destination + '/compareBasis', data = repr(forward))
	return x.content, x.status_code


@app.route('/verifyKey', methods=['POST'])
def verifyKey():
	destination = request.args.get('destination')
	if destination is None:
		# error - this should not happen
		return "Bad request", 400
	req = eval(request.data)
	if len(req) == 4:
		# sphincs+
		subkey = req[0]
		key_sign = req[1]
		picked = req[2]
		pick_sign = req[3]
		forward = [subkey, key_sign, picked, pick_sign]
	else:
		# aesgcm
		keyID = req[0]
		chypherVK = req[1]
		nonceVK = req[2]
		chypherP = req[3]
		nonceP = req[4]
		forward = [keyID, chypherVK, nonceVK, chypherP, nonceP] 

	# Do attacks on classical channel here
	if manInTheMiddle:
		pass

	# forward request and related reply
	x = requests.post(destination + '/verifyKey', data = repr(forward))
	return x.content, x.status_code


@app.route('/attacks', methods=['POST'])
def toggleAttack():
	global interceptAndResend
	global manInTheMiddle

	intAndRes = request.args.get('interceptAndResend')
	if intAndRes is not None:
		interceptAndResend = int(intAndRes)
	mitm =  request.args.get('manInTheMiddle')
	if mitm is not None:
		manInTheMiddle = int(mitm)
	resp = Response("OK")
	resp.headers['Access-Control-Allow-Origin'] = '*'
	return resp


@app.route('/startE91exchange', methods=['POST'])
def startE91exchange():
	destination = request.args.get('destination')
	if destination is None:
		# error - this should not happen
		return "Bad request", 400
	source = request.remote_addr
	length = int(request.data)


	qr = QuantumRegister(2, name="qr")
	cr = ClassicalRegister(2, name="cr")
	# measure the spin projection of qubit onto X basis
	measure1 = QuantumCircuit(qr, cr, name='measure1')
	measure1.h(qr[0])

	# measure the spin projection of qubit onto W basis
	measure2 = QuantumCircuit(qr, cr, name='measure2')
	measure2.s(qr[0])
	measure2.h(qr[0])
	measure2.t(qr[0])
	measure2.h(qr[0])

	# measure the spin projection of qubit onto Z basis
	measure3 = QuantumCircuit(qr, cr, name='measure3')

	# measure the spin projection of qubit onto V basis
	measure4 = QuantumCircuit(qr, cr, name='measure4')
	measure4.s(qr[1])
	measure4.h(qr[1])
	measure4.tdg(qr[1])
	measure4.h(qr[1])

	meas_circuits1 = [measure1, measure2, measure3]
	meas_circuits2 = [measure2, measure3, measure4]

	current_len = 0
	aliceKey = []
	bobKey = []
	circuits = []
	result = []
	aliceBasis = []
	bobBasis = []

	while current_len < length:
		singletSize = (length - current_len) * 3

		# require singlets
		x = requests.get(prefs['destinations']['entangledSource'] + '/getQbits?number=' + str(singletSize))
		if x.status_code != 200:
			return "Error during singlet generation", 500
		singlets = eval(x.content)
		# request basis table to Alice and Bob
		x = requests.get('http://' + str(source) + ':' + str(prefs['destinations']['sourcePort']) + '/getBasis?length=' + str(singletSize))
		if x.status_code != 200:
			return "Error retrieving basis table", 500
		newAliceBasis = eval(x.content)
		x = requests.get(destination + '/getBasis?length=' + str(singletSize))
		if x.status_code != 200:
			return "Error retrieving basis table", 500
		newBobBasis = eval(x.content)

		for i in range(singletSize):
			singlet = singlets[i]
			# compose circuit depending by the basis chosen by Alice and Bob
			circuit = meas_circuits1[newAliceBasis[i] - 1] + meas_circuits2[newBobBasis[i] - 1]
			circuits.append(circuit)
			# measure singlet with the just created circuit
			meas = singlet.evolve(circuit)
			res = meas.measure()[0]
			result.append(res)

			if abPatterns[0].search(res): # check if the key is '..00' (if the measurement results are -1,-1)
				aliceResult = -1
				bobResult = -1
			if abPatterns[1].search(res):
				aliceResult = 1
				bobResult = -1
			if abPatterns[2].search(res): # check if the key is '..10' (if the measurement results are -1,1)
				aliceResult = -1
				bobResult = 1
			if abPatterns[3].search(res):
				aliceResult = 1
				bobResult = 1

			if (newAliceBasis[i] == 2 and newBobBasis[i] == 1) or (newAliceBasis[i] == 3 and newBobBasis[i] == 2):
				# record the multiplied by -1 i-th result obtained Bob as the bit of the secret key k'
				bobResult = - bobResult
				# convert 1, -1 values into 1, 0
				if aliceResult == -1:
					aliceResult = 0
				if bobResult == -1:
					bobResult = 0
				
				# record the i-th result obtained by Alice as the bit of the secret key k
				aliceKey.append(aliceResult)
				bobKey.append(bobResult)

		aliceBasis.extend(newAliceBasis)
		bobBasis.extend(newBobBasis)
		current_len = len(aliceKey)

	chsh = chsh_corr(circuits, result, aliceBasis, bobBasis, abPatterns) # CHSH correlation value
	# make sure keys have the correct length
	aliceKey = aliceKey[:length]
	bobKey = bobKey[:length]
	x = requests.post('http://' + str(source) + ':' + str(prefs['destinations']['sourcePort']) + '/setKey', data = repr([aliceKey, chsh]))
	if x.status_code == 200:
		x = requests.post(destination + '/setKey', data = repr([bobKey, chsh]))
		if x.status_code == 200:
			return "OK"
	return "Error", 500


def main():
	app.logger.setLevel(logging.INFO)
	app.run(host='0.0.0.0', port=4000)

if __name__ == "__main__":
	main()
