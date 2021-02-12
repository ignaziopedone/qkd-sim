import sys
import requests
import time
import validators

def main():
	# run forever (or until the stop command)
	while(True):
		choice = input("\nPlease insert command:\n 1) Start key exchange\n 2) Change simulator settings\n 3) Change Eve's settings\n 4) Exit\n[1-4]: ")
		if choice is None or choice == '':
			continue
		choice = eval(choice)
		if type(choice) is not int or choice not in range(1,5):
			print("Error: please select a valid command by inserting relative number (1-4)")
			continue
		if choice == 1:
			destination = input("Insert destination (press enter for default Bob address: http://172.15.0.5:4000):\n")
			if destination == '':
				destination = 'http://172.15.0.5:4000'
			else:
				if validators.url(destination) is not True:
					print("Error: selected destination (%s) is not a valid URL" % destination)
					continue
			length = eval(input("Insert key length (bits number):\n"))
			if type(length) is not int:
				print("Error: key length must be an integer")
				continue
			prot = input("Select protocol:\n 1) BB84\n 2) E91\n[1-2]: ")
			prot = eval(prot)
			if type(prot) is not int or prot not in range(1,3):
				print("Error: please select a valid protocol by inserting relative number (1-2)")
				continue
			protocol = 'bb84'
			if prot == 2:
				protocol = 'e91'

			print("Starting key exchange of length %d, with destination %s, using protocol %s." % (length, destination, protocol))
			start = time.time()
			x = requests.post('http://172.15.0.4:4000/startKeyExchange', data = repr({'destination' : destination, 'length' : length, 'protocol' : protocol}))
			end = time.time()
			aliceKey = x.content
			aliceStatus = x.status_code
			print("Request completed with status code:", aliceStatus, "\nKey:", aliceKey, "\nElapsed time: ", end - start)
			print("\nRetrieving the same key from destination...")
			x = requests.post(destination + '/startKeyExchange', data = repr({'destination' : 'http://172.15.0.4:4000', 'length' : length, 'protocol' : protocol}))
			bobStatus = x.status_code
			bobKey = x.content
			if aliceStatus == 200 and bobStatus == 200:
				aliceKey = eval(aliceKey)[0]
				bobKey = eval(bobKey)[0]
				if aliceKey != None and bobKey != None:
					print("Key length: " + str(len(aliceKey)))
					equals = True
					for i in range(len(aliceKey)):
						if aliceKey[i] != bobKey[i]:
							equals = False
					if equals:
						print("The two keys are the same")
					else:
						print("The two keys differs")
			print("Done")

		elif choice == 2:
			choice = eval(input("Select setting you want to change:\n 1) chunk length\n 2) authentication method\n[1-2]: "))
			auth = 'sphincs+'
			if type(choice) is not int or choice not in range(1,3):
				print("Error: invalid choice")
				continue
			if choice == 1:
				chunk = eval(input("Insert statevector length (bits number) (values greather than 20 lead to memory error):\n"))
				if type(chunk) is not int:
					print("Error: length must be an integer")
					continue

				x = requests.post('http://172.15.0.4:4000/settings', data = repr({'chunk': chunk}))
				print("Request completed with status code:", x.status_code, "\nMessage:", x.content)
			elif choice == 2:
				authentication = eval(input("Select public channel authentication method:\n 1) Sphincs+\n 2) AES-GCM\n[1-2]: "))
				auth = 'sphincs+'
				if type(authentication) is not int or authentication not in range(1,3):
					print("Error: invalid choice")
					continue
				if authentication == 2:
					auth = 'aesgcm'
				print("changing setting in Alice simulator...")
				x = requests.post('http://172.15.0.4:4000/settings', data = repr({'auth': auth}))
				print("Request completed with status code:", x.status_code, "\nMessage:", x.content)
				print("changing setting in Bob simulator...")
				x = requests.post('http://172.15.0.5:4000/settings', data = repr({'auth': auth}))
				print("Request completed with status code:", x.status_code, "\nMessage:", x.content)
			continue
		elif choice == 3:
			destination = input("Insert Eve's IP address (press enter for default Eve address: http://172.15.0.6:4000):\n")
			if destination == '':
				destination = 'http://172.15.0.6:4000' 
			setting = input("\nPlease select setting you want to change:\n 1) Enable intercept and resend attack\n 2) Disable intercept and resend attack\n 3) Enable man in the middle attack \n 4) Disable man in the middle attack\n[1-4]: ")
			setting = eval(setting)
			if type(setting) is not int or setting < 1 or setting > 4:
				print("Error: selected value must be in range (1-4)")
				continue
			if setting == 1:
				x = requests.post(destination + '/attacks?interceptAndResend=1')
			elif setting == 2:
				x = requests.post(destination + '/attacks?interceptAndResend=0')
			elif setting == 3:
				x = requests.post(destination + '/attacks?manInTheMiddle=1')
			elif setting == 3:
				x = requests.post(destination + '/attacks?manInTheMiddle=0')	
			print("Request completet with status code:", x.status_code, "\nMessage:", x.content)

		elif choice == 4:
			print("Bye")
			break



if __name__ == "__main__":
	main()
