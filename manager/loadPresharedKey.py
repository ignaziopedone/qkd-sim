import mysql.connector
import hvac
from trng import randomStringGen
import uuid


db = mysql.connector.connect(host='172.15.0.2', user='root', passwd='dummypassword', database='simulatorDB', autocommit=True)
cursor = db.cursor()

# generate 32 byte keys
keys = {}
for i in range(50):
	keyID = str(uuid.uuid4())
	keys[keyID] = randomStringGen(32)

# clean previous storage
client = hvac.Client(url='http://172.15.0.3:8200')
client.token = 's.qSYNEKbCQVlGEO9QG4IOmwkd'

client.secrets.kv.delete_metadata_and_all_versions('alicePresharedSimKeys')
client.secrets.kv.delete_metadata_and_all_versions('bobPresharedSimKeys')
cursor.execute("DELETE FROM aliceSim_pre_keys")
cursor.execute("DELETE FROM bobSim_pre_keys")

# save keys in vault
client.secrets.kv.v2.create_or_update_secret(path='alicePresharedSimKeys', secret=dict(keys=keys),)
client.secrets.kv.v2.create_or_update_secret(path='bobPresharedSimKeys', secret=dict(keys=keys),)

# save keys references in DB
IDs = list(keys.keys())
for keyID in IDs:
	cursor.execute("INSERT INTO aliceSim_pre_keys (keyID, TTL) VALUES ('%s', 20)" % (keyID))
	cursor.execute("INSERT INTO bobSim_pre_keys (keyID, TTL) VALUES ('%s', 20)" % (keyID))


