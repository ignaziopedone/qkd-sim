# E91 singlet source
This folder contains the source code to generate entangled qubits. It represents a source of entangled photons. It has been separed from the rest of the code in order to allow easy modification if source modeling (noice introduction, different sources characterization and so forth) needs to be performed.

Right now it just creates simulated entangled qubits when requested.


## Workflow
singletSource.py is basically composed by two elements: a flask interface where singlet requests may be performed and a dedicated thread that is in charge of actually perform singlets generation.

The idea is that the dedicated thread starts to generate singlets up to a specific number in order for the siglets to be already available when requested.
If more singlets than available are required, the web interface can trigger generation of other singlets by using a flag. In any case, when web interface uses the already generated singlets to fullfil a request, it signals the thread that new singlets need to be generated so that they will be ready before another request occurs. This is done in the hope to save time by avoiding to generate singlets when requested.
If thread is generating singlet and a new request arrives it may happen that the request can be fullfilled with the already generated singlets, even if thread has not reached the predefined number for generation. In such a case web interface can prevent other singlets generation by activating a flag that stops the thread.
Flags are used to synchronize the access to the shared resource, represented by the singlets, between the web interface and the thread. Web interface will always have the priority in accessing resource since it can stop generation from the thread on its needs.

## Interface
Singlets can be requested using the following endpoint:
```sh
 GET http://172.15.0.7:4000/getQbits?number=x
```

This call returns a list of Statevector containing entangled qubits pairs.
