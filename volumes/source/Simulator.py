# importing Qiskit
from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister, execute, BasicAer
from qiskit.quantum_info import Statevector

# Import basic plotting tools
from qiskit.tools.visualization import plot_histogram

# import utility modules
import math
import numpy as np
from flask import Flask, request, Response
import requests
import pickle
import sys
import multiprocessing
from multiprocessing import Process
import logging
import pyspx.shake256_128f as sphincs
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from trng import randomStringGen
import time
import mysql.connector
import hvac
import yaml
from QKD import QKD
import time
import base64

# global variables
alice_key = []
alice_table = []
temp_alice_key = ''
key_length = 0
app = Flask(__name__)
server = None
serverPort = 4000

pref_file = open("config/configS.yaml", 'r')
prefs = yaml.safe_load(pref_file)

chunk = prefs['simulator']['chunk_size'] # increasing chunk may lead to Memory Error
authenticationMethod = prefs['simulator']['authentication']
correlationThreshold = int(prefs['simulator']['chsh_threshold'])


# utility function - timeout parameter is expressed in milliseconds
# convert epoch time to milliseconds
current_time = lambda: int(round(time.time() * 1000))

# convert the array of bits into an array of bytes as per QKD specifications (bit 0 is the first bit of the octect - ETSI GS QKD 004 v1.1.1 (2010-12), page 9, table 1)
def convertToBytes(key, key_length):
	# convert list of bit in list of bytes
	byteskey = []
	for octect in range(int(key_length/8)):
		i = 7
		num = 0
		for bit in key[(8*octect):(8*(octect+1))]:
			num = (int(bit) << i) | num
			i = i - 1
		byteskey.append(num)
	# convert list to bytearray
	byteskey = bytearray(byteskey)
	return byteskey


# MODULE INTERFACE


# generateQubits
# generates a random string and encodes it in a statevector
# @return: the statevector, the basis table used to measure the qubits and the measurement results
def generateQubits():
	# Creating registers with n qubits
	qr = QuantumRegister(chunk, name='qr')
	cr = ClassicalRegister(chunk, name='cr')

	# Quantum circuit for alice state
	alice = QuantumCircuit(qr, cr, name='Alice')

	# Generate a random number in the range of available qubits [0,65536))
	temp_alice_key = randomStringGen(chunk)
	#app.logger.info("key: ", temp_alice_key)

		
	# Switch randomly about half qubits to diagonal basis
	alice_table = np.array([])
	for index in range(len(qr)):
		if 0.5 < int(randomStringGen(1)):
			# change to diagonal basis
			alice.h(qr[index])
			alice_table = np.append(alice_table, 'X')
		else:
			# stay in computational basis
			alice_table = np.append(alice_table, 'Z')

	# Reverse basis table
	alice_table = alice_table[::-1]

	# Generate a statevector initialised with the random generated string
	sve = Statevector.from_label(temp_alice_key)
	# Evolve stetavector in generated circuit
	qubits = sve.evolve(alice)

	# return quantum circuit, basis table and temporary key
	return qubits, alice_table, temp_alice_key


def getPresharedKey(keyID = None):
	db = mysql.connector.connect(host=str(prefs['internal_db']['host']), user=str(prefs['internal_db']['user']), passwd=str(prefs['internal_db']['passwd']), database=str(prefs['internal_db']['database']), autocommit=True)
	cursor = db.cursor(buffered=True)
	if keyID is None:
		cursor.execute("SELECT * FROM " + str(prefs['preshared_key']['table']))
		result = cursor.fetchone()
		if result is None:
			app.logger.error("No preshared key found. Unable to authenticate messages.")
			return None, False
		keyID = str(result[0])
		TTL = int(result[1])
	else:
		cursor.execute("SELECT * FROM " + str(prefs['preshared_key']['table']) + " WHERE keyID = '%s'" % keyID)
		result = cursor.fetchone()
		if result is None:
			app.logger.error("No preshared key found. Unable to authenticate messages.")
			return None, False
		TTL = int(result[1])
	# get the key from vault
	client = hvac.Client(url='http://' + prefs['vault']['host'])
	client.token = prefs['vault']['token']
	response = client.secrets.kv.read_secret_version(path=prefs['preshared_key']['preshared_path'])
	keys = response['data']['data']['keys']
	key = keys[str(keyID)]
	TTL = TTL - 1
	if TTL == 0:
		# this is the last time we can use this key. Remove it from storage
		keys.pop(keyID)
		# remove this key from storage
		client.secrets.kv.v2.create_or_update_secret(path=prefs['preshared_key']['preshared_path'], secret=dict(keys=keys),)
		cursor.execute("DELETE FROM " + str(prefs['preshared_key']['table']) + " WHERE keyID = '%s'" % keyID)
	else:
		# update TTL count
		cursor.execute("UPDATE " + str(prefs['preshared_key']['table']) + " SET TTL = %d WHERE keyID = '%s'" % (TTL, keyID))
	return key, keyID, TTL



class Simulator(QKD):
	def exchangeKey(self, key_length, destination='http://localhost:4000', protocol='bb84', timeout=0):
		if protocol == 'e91':
			# check if a key is already present
			client = hvac.Client(url='http://' + prefs['vault']['host'])
			client.token = prefs['vault']['token']
			db = mysql.connector.connect(host=str(prefs['internal_db']['host']), user=str(prefs['internal_db']['user']), passwd=str(prefs['internal_db']['passwd']), database=str(prefs['internal_db']['database']), autocommit=True)
			cursor = db.cursor(buffered=True)
			cursor.execute("SELECT * FROM " + str(prefs['simulator']['table']) + " WHERE requestIP = 'E91'")
			result = cursor.fetchone()
			if result is not None:
				# key already exchanged
				response = client.secrets.kv.read_secret_version(path='e91Key')
				key = response['data']['data']['key']
				# delete key once returned
				client.secrets.kv.delete_metadata_and_all_versions('e91Key')
				cursor.execute("DELETE FROM " + str(prefs['simulator']['table']) + " WHERE `requestIP` = 'E91'")
				return key, True, 0

			x = requests.post('http://' + prefs['eve']['ip_addr'] + '/startE91exchange?destination=' + destination, data=repr(key_length))
			if x.status_code == 200:
				response = client.secrets.kv.read_secret_version(path='e91Key')
				key = response['data']['data']['key']
				# delete key once returned
				client.secrets.kv.delete_metadata_and_all_versions('e91Key')
				cursor.execute("DELETE FROM " + str(prefs['simulator']['table']) + " WHERE `requestIP` = 'E91'")
				return key, True, 0
			return None, False, 0
		# bb84
		else:
			# delay the start of the exchange of a random number of seconds (between 0 and 8)
			randNo = randomStringGen(3)
			# convert bit string into bytes
			randNo = int(randNo, 2)
			time.sleep(randNo)

			app.logger.info('Starting key exchange. Desired key length: %s' % str(key_length))
			# 1/3 of the key needs to be exchanged in order to verify key
			# that part of the key cannot be used anymore after key verification
			# generate 1/3 more than key_length that will then be exchanged
			# in this way final key length will be as equals as key_length
			key_length = int(key_length)
			includingVerifyLen = round(key_length + (key_length / 3))
			# add a 15% of the total length
			generateLength = includingVerifyLen + round(includingVerifyLen * 15 / 100)
			# multiply generatedLength by two since qubits will be discarded with a probability of 50%
			generateLength = generateLength * 2

			# check if a key has already been exchanged with desired destination
			destAddr = str(prefs['eve']['ip_addr']).split(':')[0]
			db = mysql.connector.connect(host=str(prefs['internal_db']['host']), user=str(prefs['internal_db']['user']), passwd=str(prefs['internal_db']['passwd']), database=str(prefs['internal_db']['database']), autocommit=True)
			cursor = db.cursor()
			# use a lock to access database to avoid concurrency access
			cursor.execute("LOCK TABLES " + str(prefs['simulator']['table']) + " WRITE")
			try:
				cursor.execute("SELECT * FROM " + str(prefs['simulator']['table']) + " WHERE requestIP = '%s'" % (destAddr))
				result = cursor.fetchone()
				if result is not None:
					# a key with this id has already been requested from server side
					# wait until the whole key is received
					# release lock during wait
					cursor.execute("UNLOCK TABLES")
					start_time = current_time()
					while bool(result[1]) is not True:
						cursor.execute("SELECT * FROM " + str(prefs['simulator']['table']) + " WHERE requestIP = '%s'" % (destAddr))
						result = cursor.fetchone()
						if current_time() > start_time + timeout:
							# timeout elapsed - clean requests list
							cursor.execute("DELETE FROM " + str(prefs['simulator']['table']) + " WHERE `requestIP` = '%s'" % (destAddr))

							return None, 4, 0
					# now key exchange is complete
					verified = result[3]
					if verified == 0:
						verified = False
					else:
						verified = True
					# key is saved in vault
					client = hvac.Client(url='http://' + prefs['vault']['host'])
					client.token = prefs['vault']['token']
					response = client.secrets.kv.read_secret_version(path='currentKey')
					key = response['data']['data']['key']
					# delete key once returned
					client.secrets.kv.delete_metadata_and_all_versions('currentKey')
					# once key has been exchange, delete its data from this module
					cursor.execute("LOCK TABLES " + str(prefs['simulator']['table']) + " WRITE")
					cursor.execute("DELETE FROM " + str(prefs['simulator']['table']) + " WHERE `requestIP` = '%s'" % (destAddr))
					cursor.execute("UNLOCK TABLES")
					return key, verified, 1
				else:
					# start key exchange - save information
					cursor.execute("INSERT INTO " + str(prefs['simulator']['table']) + " (requestIP, complete, exchangedKey, verified) VALUES ('%s', False, NULL, False)" % (destAddr))
				# release lock
				cursor.execute("UNLOCK TABLES")
			except Exception as e:
				# error occurred - clean requests list
				cursor.execute("DELETE FROM " + str(prefs['simulator']['table']) + " WHERE `requestIP` = '%s'" % (destAddr))
				# always release lock before quit
				cursor.execute("UNLOCK TABLES")
				raise(e)

			# start a new key exchange
			# generate state vectors
			qubit_vectors = []
			alice_table = np.array([])
			alice_key = ''
			start = time.time()
			for i in range(math.ceil(generateLength/chunk)):
				qubits, alice_table_part, temp_alice_key = generateQubits()
				qubit_vectors.append(qubits)
				alice_table = np.append(alice_table, alice_table_part)
				alice_key = alice_key + temp_alice_key
			end = time.time()
			app.logger.info("Qubits generation time: " + str(end - start))

			# send quantum bits
			start = time.time()
			x = requests.post('http://' + prefs['eve']['ip_addr'] + '/sendRegister?keyLen=' + str(key_length) + '&destination=' + destination, data = pickle.dumps(qubit_vectors))
			if x.status_code != 200:
				# error - return
				#cursor.execute("DELETE FROM " + str(prefs['simulator']['table']) + " WHERE `requestIP` = '%s'" % (destAddr))
				return None, False, 0
			end = time.time()
			app.logger.info("/sendRegister time: " + str(end - start))

			if authenticationMethod == 'aesgcm':
				start = time.time()
				# select key
				key, keyID, TTL = getPresharedKey()
				if key is None:
					# no key available, return an error
					cursor.execute("DELETE FROM " + str(prefs['simulator']['table']) + " WHERE `requestIP` = '%s'" % (destAddr))
					return None, False, 0
				aesgcm = AESGCM(bytes(key, 'utf-8'))
				# select nonce
				nonce = randomStringGen(12)
				cypherTable = aesgcm.encrypt(bytes(nonce, 'utf-8'), alice_table.tobytes(), None)
				end = time.time()
				app.logger.info("aes-gcm signature time: " + str(end - start))
				# compare basis table
				reqData = [cypherTable, keyID, nonce]
				start = time.time()
				y = requests.post('http://' + prefs['eve']['ip_addr'] + '/compareBasis?destination=' + destination, data = repr(reqData))
				if y.status_code != 200:
					# error - return
					cursor.execute("DELETE FROM " + str(prefs['simulator']['table']) + " WHERE `requestIP` = '%s'" % (destAddr))
					return None, False, 0
				end = time.time()
				app.logger.info("/compareBasis time: " + str(end - start))
				rep = eval(y.content)
				cypherRep = rep[0]
				nonceRep = rep[1]
				start = time.time()
				bob_table = aesgcm.decrypt(bytes(nonceRep, 'utf-8'), cypherRep, None)
				end = time.time()
				app.logger.info("aes-gcm decrypt time: " + str(end - start))
				# convert bytes back to numpy array
				bob_table = np.frombuffer(bob_table, dtype=alice_table.dtype)
			# default to sphincs
			else:
				# sign alice_table before sending it
				start = time.time()
				aliceSign = sphincs.sign(alice_table.tobytes(), eval(prefs['auth_key']['privateKey']))
				end = time.time()
				app.logger.info("sphincs+ signature time: " + str(end - start))
				# compare basis table
				start = time.time()
				y = requests.post('http://' + prefs['eve']['ip_addr'] + '/compareBasis?destination=' + destination, data = repr([pickle.dumps(alice_table), aliceSign]))
				if y.status_code != 200:
					# error - return
					cursor.execute("DELETE FROM " + str(prefs['simulator']['table']) + " WHERE `requestIP` = '%s'" % (destAddr))
					return None, False, 0
				end = time.time()
				app.logger.info("/compareBasis time: " + str(end - start))

				rep = eval(y.content)
				bob_table = pickle.loads(rep[0])
				tableSign = rep[1]
				# check that table was actually sent from Bob
				start = time.time()
				if not sphincs.verify(bob_table.tobytes(), tableSign, eval(prefs['auth_key']['peerPublicKey'])):
					app.logger.error("Table comparison failed due to wrong signature!")
					cursor.execute("DELETE FROM " + str(prefs['simulator']['table']) + " WHERE `requestIP` = '%s'" % (destAddr))
					return None, False, 0
				end = time.time()
				app.logger.info("sphincs+ verify time: " + str(end - start))

			keep = []
			discard = []
			for qubit, basis in enumerate(zip(alice_table, bob_table)):
				if basis[0] == basis[1]:
					#print("Same choice for qubit: {}, basis: {}" .format(qubit, basis[0]))
					keep.append(qubit)
				else:
					#print("Different choice for qubit: {}, Alice has {}, Bob has {}" .format(qubit, basis[0], basis[1]))
					discard.append(qubit)

			#print('Percentage of qubits to be discarded according to table comparison: ', len(keep)/chunk)
			alice_key = [alice_key[qubit] for qubit in keep]

			# randomly select bit to be used for key verification
			picked, verifyingKey = [], []
			i = 0
			# we need to generate a random number between 0 and includingVerifyLen
			# randomStringGen generates a string of bit - calculate how many bit we need to get a consistent top value
			bits = 0
			temp = includingVerifyLen
			while temp > 0:
				temp = temp >> 1
				bits += 1
			while i < includingVerifyLen - key_length:
				# generate a valid random number (in range 0 - key_length + includingVerifyLen and not already used)
				while True:
					randNo = randomStringGen(bits)
					# convert bit string into bytes
					randNo = int(randNo, 2)
					if randNo >= includingVerifyLen:
						# not a valid number
						continue
					if randNo in picked:
						# number already used
						continue
					# number is valid - exit from this inner loop
					break
				# add randNo to list of picked
				picked.append(randNo)
				i += 1

			# remove used bits from the key
			for i in sorted(picked, reverse=True):
				verifyingKey.append(int(alice_key[i]))
				del alice_key[i]

			# make sure key length is exactly equals to key_length
			alice_key = alice_key[:key_length]

			app.logger.info("Key exchange completed - new key: %s" % alice_key)
			app.logger.info("key len: %s" % str(len(alice_key)))

			# delete info once key exchange is complete
			try:
				cursor.execute("LOCK TABLES " + str(prefs['simulator']['table']) + " WRITE")
				cursor.execute("DELETE FROM " + str(prefs['simulator']['table']) + " WHERE `requestIP` = '%s'" % (destAddr))
				cursor.execute("UNLOCK TABLES")
			except Exception as e:
				# always release lock before quit
				cursor.execute("UNLOCK TABLES")
				raise(e)

			if authenticationMethod == 'aesgcm':
				# we need to take another key
				key, keyID, TTL = getPresharedKey()
				if key is None:
					# no key available, return an error
					return None, False, 0
				aesgcm = AESGCM(bytes(key, 'utf-8'))
				# select nonce
				nonceVK = randomStringGen(12)
				nonceP = randomStringGen(12)
				cypherVK = aesgcm.encrypt(bytes(nonceVK, 'utf-8'), bytes(repr(verifyingKey), 'utf-8'), None)
				cypherP = aesgcm.encrypt(bytes(nonceP, 'utf-8'), bytes(repr(picked), 'utf-8'), None)
				x = requests.post('http://' + prefs['eve']['ip_addr'] + '/verifyKey?destination=' + destination, data = repr([keyID, cypherVK, nonceVK, cypherP, nonceP]))
				if x.status_code != 200:
					app.logger.error("Server error occurred %s" % x.status_code)
					return alice_key, False, 0
				# get Bob's reply
				rep = eval(x.content)
				cypherRep = rep[0]
				nonce = rep[1]
				bobKey = aesgcm.decrypt(bytes(nonce, 'utf-8'), cypherRep, None)
				bobKey = eval(bobKey)

			# default to sphincs
			else:
				# sign data with our private key
				keySign = sphincs.sign(bytes(verifyingKey), eval(prefs['auth_key']['privateKey']))
				picked = np.array(picked)
				pickSign = sphincs.sign(picked.tobytes(), eval(prefs['auth_key']['privateKey']))
				# send data and signature to verify key exchange
				x = requests.post('http://' + prefs['eve']['ip_addr'] + '/verifyKey?destination=' + destination, data = repr([verifyingKey, keySign, pickle.dumps(picked), pickSign]))
				if x.status_code != 200:
					app.logger.error("Server error occurred %s" % x.status_code)
					return alice_key, False, 0

				# get Bob's reply
				rep = eval(x.content)
				bobKey = rep[0]
				bobKeySign = rep[1]

				# verify Bob's signature
				if not sphincs.verify(bytes(bobKey), bobKeySign, eval(prefs['auth_key']['peerPublicKey'])):
					app.logger.error("Key verification failed due to wrong signature!")
					return alice_key, false, 0

			# check that Alice and Bob have the same key
			acc = 0
			for bit in zip(verifyingKey, bobKey):
				if bit[0] == bit[1]:
					acc += 1

			app.logger.info('\nPercentage of similarity between the keys: %s' % str(acc/len(verifyingKey)))
			qber = 1 - (acc/len(verifyingKey))

			if (acc//len(verifyingKey) == 1):
				return alice_key, True, qber
				app.logger.info("\nKey exchange has been successfull")
			else:
				app.logger.error("\nKey exchange has been tampered! Check for eavesdropper or try again")
				return alice_key, False, qber


	def begin(self, port = 4000):
		global server
		global serverPort

		serverPort = port
		# configure logger
		# file logging
		fh = logging.FileHandler('simulator.log')
		formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
		fh.setFormatter(formatter)
		app.logger.addHandler(fh)
		app.logger.setLevel(logging.DEBUG)

		# start server
		app.logger.info('Starting server')
		server = Process(target=run)
		server.start()

	def end(self):
		app.logger.info('Killing threads')
		server.terminate()
		server.join()
		app.logger.info('Correctly quit application')



def run():
	fh = logging.FileHandler('simulator.log')
	formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	fh.setFormatter(formatter)
	app.logger.addHandler(fh)
	app.logger.setLevel(logging.DEBUG)
	app.run(host='0.0.0.0', port=serverPort)


# WEB INTERFACE



@app.route('/sendRegister', methods=['POST'])
def getQuantumKey():
	global temp_alice_key
	global alice_key
	global alice_table
	global key_length

	requestIP = request.remote_addr
	# retrieve information about this destination if any
	db = mysql.connector.connect(host=str(prefs['internal_db']['host']), user=str(prefs['internal_db']['user']), passwd=str(prefs['internal_db']['passwd']), database=str(prefs['internal_db']['database']), autocommit=True)
	cursor = db.cursor()
	# use a lock to access database to avoid concurrency access
	cursor.execute("LOCK TABLES " + str(prefs['simulator']['table']) + " WRITE")
	try:
		cursor.execute("SELECT * FROM " + str(prefs['simulator']['table']) + " WHERE requestIP = '%s'" % requestIP)
		result = cursor.fetchone()
		if result is not None:
			# an exchange for this key is already in progress, return an error
			# release db lock
			cursor.execute("UNLOCK TABLES")
			return "Error", 400
		else:
			# a new key exchange can be started
			# insert information
			cursor.execute("INSERT INTO " + str(prefs['simulator']['table']) + " (requestIP, complete, exchangedKey, verified) VALUES ('%s', False, NULL, False)" % (requestIP))
		# release db lock
		cursor.execute("UNLOCK TABLES")
	except Exception as e:
		# always release lock before quit
		cursor.execute("UNLOCK TABLES")
		raise(e)
	# new key requested - reset all variables
	alice_table = np.array([])
	alice_key = []
	temp_alice_key = ''
	# get key length
	key_length = int(request.args.get('keyLen'))
	app.logger.info('New key exchange requested from client. Desired key length %s' % str(key_length))
	
	qubits_vectors = pickle.loads(request.data)

	chunk = qubits_vectors[0].num_qubits

	for i in range(len(qubits_vectors)):
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
		alice_table = np.append(alice_table, table)
		qubits = qubits_vectors[i].evolve(circuit)
		# Measure statevector
		meas = qubits.measure()
		temp_alice_key += meas[0]

	return "OK"

@app.route('/compareBasis', methods=['POST'])
def compareBasis():
	global alice_key
	global alice_table

	res = eval(request.data)

	if authenticationMethod == 'aesgcm':
		cypher_table = res[0]
		keyID = res[1]
		nonce = res[2]
		# get key and TTL
		key, keyID, TTL = getPresharedKey(keyID)
		if key is None:
			return "Error: unable to get required preshared key.", 400
		aesgcm = AESGCM(bytes(key, 'utf-8'))
		bob_table = aesgcm.decrypt(bytes(nonce, 'utf-8'), cypher_table, None)
		# convert bytes back to numpy array
		bob_table = np.frombuffer(bob_table, dtype=alice_table.dtype)
		
	else:
		bob_table = pickle.loads(res[0])
		tableSign = res[1]

		# check that table was actually sent from Bob
		if not sphincs.verify(bob_table.tobytes(), tableSign, eval(prefs['auth_key']['peerPublicKey'])):
			app.logger.error("Table comparison failed due to wrong signature!")
			return "Unauthorized", 401

	keep = []
	discard = []
	for qubit, basis in enumerate(zip(bob_table, alice_table)):
		if basis[0] == basis[1]:
			#print("Same choice for qubit: {}, basis: {}" .format(qubit, basis[0])) 
			keep.append(qubit)
		else:
			#print("Different choice for qubit: {}, Alice has {}, Bob has {}" .format(qubit, basis[0], basis[1]))
			discard.append(qubit)

	#print('Percentage of qubits to be discarded according to table comparison: ', len(keep)/chunk)

	# get new key
	alice_key += [temp_alice_key[qubit] for qubit in keep]

	if authenticationMethod == 'aesgcm':
		nonce = randomStringGen(12)
		cypherTable = aesgcm.encrypt(bytes(nonce, 'utf-8'), alice_table.tobytes(), None)
		return repr([cypherTable, nonce])
	else:
		# prepare reply
		reply = alice_table
		# sign reply to let Bob trust us
		repSign = sphincs.sign(alice_table.tobytes(), eval(prefs['auth_key']['privateKey']))
		# reset alice_table for next comparisons
		alice_table = np.array([])

		return repr([pickle.dumps(reply), repSign])

@app.route('/verifyKey', methods=['POST'])
def verifyKey():
	global alice_key

	# key exchange completed
	req = eval(request.data)

	# verify key
	if authenticationMethod == 'aesgcm':
		keyID = req[0]
		chypherVK = req[1]
		nonceVK = req[2]
		chypherP = req[3]
		nonceP = req[4]
		# get key and TTL
		key, keyID, TTL = getPresharedKey(keyID)
		if key is None:
			return "Error: unable to get required preshared key.", 400
		aesgcm = AESGCM(bytes(key, 'utf-8'))
		bobKey = aesgcm.decrypt(bytes(nonceVK, 'utf-8'), chypherVK, None)
		picked = aesgcm.decrypt(bytes(nonceP, 'utf-8'), chypherP, None)
		bobKey = eval(bobKey)
		picked = eval(picked)
	# default to sphincs
	else:
		bobKey = req[0]
		keySign = req[1]
		picked = pickle.loads(req[2])
		pickSign = req[3]

		# check that message actually comes from Bob
		if not sphincs.verify(bytes(bobKey), keySign, eval(prefs['auth_key']['peerPublicKey'])):
			app.logger.error("Key verification failed due to wrong signature!")
			return "Unauthorized", 401
		if not sphincs.verify(picked.tobytes(), pickSign, eval(prefs['auth_key']['peerPublicKey'])):
			app.logger.error("Key verification failed due to wrong signature!")
			return "Unauthorized", 401

	# get part of the key to be used during key verification
	verifyingKey = []
	# add picked bit to verifyingKey and remove them from the key
	for i in sorted(picked, reverse=True):
		verifyingKey.append(int(alice_key[i]))
		del alice_key[i]

	# make sure key length is exactly equals to key_length
	alice_key = alice_key[:key_length]
	app.logger.info("New Alice's key: %s" % alice_key)
	app.logger.info("key len: %s" % str(len(alice_key)))

	# check that Alice and Bob have the same key
	acc = 0
	for bit in zip(verifyingKey, bobKey):
		if bit[0] == bit[1]:
			acc += 1

	app.logger.info('\nPercentage of similarity between the keys: %s' % str(acc/len(verifyingKey)))

	if (acc//len(verifyingKey) == 1):
		verified = True
		app.logger.info("\nKey exchange has been successfull")
	else:
		verified = False
		app.logger.error("\nKey exchange has been tampered! Check for eavesdropper or try again")

	# save key
	db = mysql.connector.connect(host=str(prefs['internal_db']['host']), user=str(prefs['internal_db']['user']), passwd=str(prefs['internal_db']['passwd']), database=str(prefs['internal_db']['database']), autocommit=True)
	cursor = db.cursor()
	# use a lock to access database to avoid concurrency access
	cursor.execute("LOCK TABLES " + str(prefs['simulator']['table']) + " WRITE")
	try:
		# save key in vault
		client = hvac.Client(url='http://' + prefs['vault']['host'])
		client.token = prefs['vault']['token']
		client.secrets.kv.v2.create_or_update_secret(path='currentKey', secret=dict(key=alice_key),)
		cursor.execute('UPDATE ' + str(prefs["simulator"]["table"]) + ' SET complete = True, verified = %d WHERE requestIP = "%s"' % (verified, request.remote_addr))

		cursor.execute("UNLOCK TABLES")
	except Exception as e:
		# error occurred - clean requests list
		cursor.execute("DELETE FROM " + str(prefs['simulator']['table']) + " WHERE `requestIP` = '%s'" % (request.remote_addr))

		# always release lock before quit
		cursor.execute("UNLOCK TABLES")
		raise(e)

	if authenticationMethod == 'aesgcm':
		nonce = randomStringGen(12)
		cypherVKey = aesgcm.encrypt(bytes(nonce, 'utf-8'), bytes(repr(verifyingKey), 'utf-8'), None)
		return repr([cypherVKey, nonce])
	# default to sphincs
	else:
		# prepare our reply - sign this key part
		keySignature = sphincs.sign(bytes(verifyingKey), eval(prefs['auth_key']['privateKey']))

	return repr([verifyingKey, keySignature])



@app.route('/getBasis', methods=['GET'])
def getBasis():
	length = request.args.get('length')
	if length is None:
		# error - this should not happen
		return "Bad request", 400
	length = int(length)
	i = 0
	basisTable = []
	while i < length:
		randNo = randomStringGen(2)
		# convert string into bytes
		randNo = int(randNo, 2)
		# we need a number in range 1 to 3 - skip 0
		if randNo > 0:
			basisTable.append(randNo)
			i = i + 1
	return repr(basisTable)


@app.route('/setKey', methods=['POST'])
def setKey():
	data = eval(request.data)
	recvKey = data[0]
	chsh = data[1]
	if chsh > correlationThreshold:
		# key was tampered, discard it
		return "Discarded"

	# save key in vault
	client = hvac.Client(url='http://' + prefs['vault']['host'])
	client.token = prefs['vault']['token']
	client.secrets.kv.v2.create_or_update_secret(path='e91Key', secret=dict(key=recvKey),)
	db = mysql.connector.connect(host=str(prefs['internal_db']['host']), user=str(prefs['internal_db']['user']), passwd=str(prefs['internal_db']['passwd']), database=str(prefs['internal_db']['database']), autocommit=True)
	cursor = db.cursor()
	cursor.execute("INSERT INTO " + str(prefs['simulator']['table']) + " (requestIP) VALUES ('E91')")
	return "OK"


@app.route('/startKeyExchange', methods=['POST'])
def keyExchange():
	try:
		data = eval(request.data)
		destination = data.get('destination')
		if destination is None:
			return "Error: a destination must be specified in body request", 400
		key_length = data.get('length')
		if key_length is None:
			key_length = prefs['simulator']['def_key_len']
		key_length = int(key_length)
		protocol = data.get('protocol')
		if protocol is None:
			protocol = prefs['simulator']['protocol']
		exchanger = Simulator()
		key, verified, qber = exchanger.exchangeKey(key_length, destination, protocol)
		if key != None:
			# convert key into array of bytes first and base64 then
			key = convertToBytes(key, key_length)
			key = base64.b64encode(key)
		resp = Response(repr([key, verified, qber]))
		resp.headers['Access-Control-Allow-Origin'] = '*'
		return resp
	except Exception as e:
		app.logger.error(e)
		return "Server error", 503

@app.route('/settings', methods=['POST'])
def settings():
	global chunk
	global authenticationMethod

	data = eval(request.data)
	changed = False
	try:
		chunk = data['chunk']
		changed = True
	except:
		pass
	try:
		authenticationMethod = data['auth']
		changed = True
	except:
		pass
	if changed:
		resp = Response("OK")
		resp.headers['Access-Control-Allow-Origin'] = '*'
		return resp
	return "Not found", 404

def main():
	# configure logger
	# file logging
	fh = logging.FileHandler('simulator.log')
	formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
	fh.setFormatter(formatter)
	app.logger.addHandler(fh)
	app.logger.setLevel(logging.DEBUG)

	# start server
	app.logger.info('Starting server')
	server = Process(target=run)
	server.start()

	while True:
		app.logger.info('Waiting for commands')
		userCmd = input("waiting for user commands:\n")
		app.logger.info("processing command: %s" % userCmd)
		if "exchange key" in userCmd:
			# check if key length is specified
			try:
				data = userCmd.split(" ")
				key_length = int(data[2])
			except:
				key_length = prefs['simulator']['def_key_len']
			alice_key, verified = exchangeKey(key_length)
		elif "quit" == userCmd:
			# exit
			break
		else:
			print("cmd not found")
			app.logger.warning('Unrecognized command: %s' % userCmd)

	app.logger.info('Killing threads')
	server.terminate()
	p.terminate()
	server.join()
	p.join()
	app.logger.info('Correctly quit application')

if __name__ == "__main__":
	main()
