File in this folder have been used to retrieve useful data about simuations.
- test.py requests 100 keys with BB84 protocol of 128 bits with an eavesdropper enabled in the channel (the same test can be performed without eavesdropper by commenting out related portion of file). It collects qber values for each key exchange and prints the resulting array.

- graph.py plots the qber values occurrency with the corresponding gaussian representing the probability distribution. Assing your qber array to x variable at the beginning of the file and lauch the script to get the result.
