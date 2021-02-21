# qkd-simulator

qkd-simulator can be used to simulate quantum key exchange between two instances. This implementation leans on different docker that need to be run before it start. The simulator itself runs on two different docker containers representing the two instances that try to exchange the keys.

Docker-compose can be used to simultaneously run all needed docker container and to statically assign them IP addresses so that they can know where to find each others. This configuration can be seen in docker-compose.yaml file. Here the following IP addresses are assigned:
- Mysql DB: http://172.15.0.2
- Vault: http://172.15.0.3:8200
- Alice simulator instance: http://172.15.0.4:4000
- Bob simulator instance: http://172.15.0.5:4000
- Eve simulator instance: http://172.15.0.6:4000

Alice and Bob communicate through Eve that owns both classical and quantum channel. Hence if Alice wants to send a key to Bob, she will send the key to Eve that will then forward the key to Bob. This allows to design attacks or other configuration in Eve docker without interfering with implemented QKD protocol. Source code for Eve can be found in `eve` folder.

Alice and Bob share the same source code. The only difference between them is some setting regarding public and private keys to authenticate messages on the classical channel or a different mysql table where internal data are saved. These settings have been specified in a configuration file named `configS.yaml`. Even if Alice and Bob share the same source code, they need to have a different configuration file. This problem has been fixed by specified different `volumes` in docker-compose for the two instances. Hence, if you want to change Alice configuration file you will need to modify file `volumes/alice/configS.yaml`. If, instead, you want to modify Bob configuration file you will need to modify file `volumes/bob/configS.yaml`. Docker-compose will map those file to folder `config/configS.yaml` in docker containers, allowing both Alice and Bob to share the same code with different configuration files. Please note that if you need to change a setting for both Alice and Bob you will need to manually update both of those files.

In order to start all docker containers needed for this implementation, open a terminal into this folder and run the commands:
```sh
docker-compose build
docker-compose up
```

After docker containers have been setup, it is needed to unseal vault docker (that is sealed by default at startup). If you didn't changed `volumes` folder in this repository (with the exception of configuration files), vault is already initialised and can be unseal by issuing the following command from a terminal:
```sh
export VAULT_ADDR='http://172.15.0.3:8200'
vault operator unseal 62cbf8b7c181822c774d95d6ae5bd29d8f97f642f30cdcb6cc511869447131dcf8
vault operator unseal d818f6a40a94882d78feb4fbf84f89e2b29a5ef6e45d3b3beae4dfc08a06351d63
```
Please note that vault must be installed on your system in order to issue the above commands without throwing errors.

If you want to use AES-GCM as authentication method you need to add preshared key in storage of both instances of simulator. In order to do that, after unsealing vault, you can launch the program `loadPresharedKey.py`.

Once storage is configured you can start interacting with simulator.

## Test
### Script test
A simple script has been written in order to simply interact with simulator containers. The script is inside manager folder. It comes in the form of a docker container that will provide a python3 environment already configured with all python modules needed to run the script.
Besides the test script, manager container has in charge the unseal of vault storage and the load of preshared keys to be used with AES-GCM authentication. These operation are performed in background as soon as the conatiner starts.

Once container is running you can connect to its shell with the following command:
```sh
docker-compose exec manager sh
```

From the docker's shell you can start test by issuing the command:
```sh
python src/simulatorManager.py
```
The program will run in a continuous `while(True)` loop until `Exit` option is selected and allows to perform the following operations:

- Start a new key exchange. This option can be selected by pressing `1` and `Enter` in the menu. The program automatically connects to Alice container (http://172.15.0.4:4000) and allows to select the destination you want to reach (if you press `Enter` when the program queries the destination, it will use the default Bob address). After destination has been selected it queries for the length of the key and the protocol you want to use (currently only BB84 and E91 are the available choices). The program will output the result of the key exchange procedure and the time elapsed to fulfill the request.

- Change simulator settings. This option allows to select the length of the chunks the key will be splitted into (it is not possible to manage too many qubits at the same time for memory reasons, hence the key will be splitted in chunks) and the authentication method to be used in public channel.

- Change Eve's settings. This option can be used to configure implemented attacks over classical or quantum channel. After having selected this option, follow the instruction of the program to select the setting you prefer.

For BB84, when launching a key exchange without changing settings the default settings used are:
- key length: 128 bits
- chunk size: 9 bits
- public channel authentication: sphincs+
- attack on public channel: None
- attack on quantum channel: None

### Web server test
A web server is available to give a better user experience when starting key exchange or change settings on the simulator or channel. User interface is pretty intuitive and does not need explanations.

In order to access web server test, after launching all docker containers using docker compose, open a web browser and type the following address:
```sh
http://172.15.0.8:4000
```


## Notes
Simulator uses statevector to manipulate and send quantum bits over flask interface. When a register is applied to a statevector, you must consider the statevector flipped: if a statevector is initialised as `'0011'` the instruction `circuit.h(qr[0])` will apply an Hadamard gate to the last qubit (1), not the first one (0)!. For this reason, when constructing basis table by randomly select basis for measurement, basis table is flipped in order to reflect the actual qubit that is measured.
