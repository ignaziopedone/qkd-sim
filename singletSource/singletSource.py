# importing Qiskit
from qiskit import QuantumCircuit, ClassicalRegister, QuantumRegister
from qiskit.quantum_info import Statevector

from flask import Flask, request

from threading import Thread
import logging

ready = False
stop = False
singlets = []
app = Flask(__name__)

numberOfSinglets = 1024


class singletGenerator(Thread):
	def __init__(self):
		Thread.__init__(self)

	def run(self):
		global ready
		global singlets
		global stop

		# circuit for singlet generation
		qre = QuantumRegister(2, name='qre')
		cre = ClassicalRegister(2, name='cre')
		singlet = QuantumCircuit(qre, cre, name='Alice')
		singlet.x(qre[0])
		singlet.x(qre[1])
		singlet.h(qre[0])
		singlet.cx(qre[0],qre[1])

		while(True):
			if ready == False:
				# generate singlets
				for i in range(numberOfSinglets):
					sve = Statevector.from_label('00')
					entangledBits = sve.evolve(singlet)
					singlets.append(entangledBits)
					if stop:
						break

				# signal that singlet generation is complete
				ready = True


@app.route('/getQbits', methods=['GET'])
def getQbits():
	global ready
	global singlets
	global stop

	size = request.args.get('number')
	if size == None:
		return "Error: number of singlets to be returned must be specified", 400
	size = int(size)
	# make sure enough singlet are generated
	while len(singlets) < size:
		ready = False
		while not ready:
			# wait for the singlet to be created
			if len(singlets) >= size:
				# singlets are enough now. stop generation
				stop = True
		# trigger other singlets generation
		stop = False
	ready = False

	# prepare data to return
	data = repr(singlets[:size])
	# clean singlets list and trigger another generation
	singlets = []
	stop = False
	ready = False
	return data




if __name__ == "__main__":
	# launch qubits generator thread
	sg = singletGenerator()
	sg.start()
	app.logger.setLevel(logging.INFO)
	app.run(host='0.0.0.0', port=4000)
	sg.join()
