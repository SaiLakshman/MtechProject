import getpass
import bigchaindb_driver
import bigchaindb
import json
from bigchaindb.common.transaction import TransactionLink
from AssetMetadata import Metadata
from exceptions import IncorrectPasswordError
from crypto_utils import generate_key_from_password, Base58Encoder, generate_storage_hash_from_password, generate_keypair,verify_storage_hash_from_password, encrypt, decrypt
#from dh import DiffieHellman
#from binascii import hexlify # For debug output

class User(object):
    '''
    classdocs
    '''
    def __init__(self, username = None, password = None, private_key = None, public_key = None, symmetric_keys = None):
        '''
        Constructor
        '''
        self.username = username
        self.password = password 
        self.private_key = private_key
        self.public_key = public_key
        #self.diffiehellman= DiffieHellman()
        self.symmetric_keys = symmetric_keys or {}
        self.bigchaindb_driver = bigchaindb_driver.BigchainDB()
        self.bigchain = bigchaindb.Bigchain()
    
    @property
    def username(self):
        return self.__username
    
    @username.setter
    def username(self, username):
        self.__username = username
    
    @property
    def password(self):
        '''
        self.password is a tuple containing both the password storage hash and the salt used to generate
        the password storage hash
        '''
        return self.__password
 
    @password.setter
    def password(self, value):
        self.__password = value
 
    @property
    def private_key(self):
        return self.__private_key

    @private_key.setter
    def private_key(self, value):
        self.__private_key = value

    @property
    def public_key(self):
        return self.__public_key
 
    @public_key.setter
    def public_key(self, value):
        self.__public_key = value

    @property
    def symmetric_keys(self):
        '''
        symmetric_keys contains the symmetric key generated from the password as well as the
        salt used to generate it
        
        For now we just have a single symmetric key stored which can be later expanded to store
        multiple ones depending upon the type of data
        
        Also, in the future we can consider generating a master key from the password which can be
        used to generate further keys for actual encryption 
        '''
        return self.__symmetric_keys
    
    @symmetric_keys.setter
    def symmetric_keys(self, value):
        self.__symmetric_keys = value

    @property
    def bigchaindb_driver(self):
        return self.__bigchaindb_driver
    
    @bigchaindb_driver.setter
    def bigchaindb_driver(self, value):
        self.__bigchaindb_driver = value
    
    @property
    def bigchain(self):
        return self.__bigchain
    
    @bigchain.setter
    def bigchain(self, value):
        self.__bigchain = value
    
    def __str__(self):
        return "username: " + self.username + "\npublic_key: " + self.public_key
        
    def to_dict(self):
        '''
        This is the JSON serializable dict encoding for User object. 
        We also convert self.password (both storage_hash and password) from bytes to str to make
        them JSON serializable. 
        '''
        d = {}
        d['username'] = self.username
        d['password'] = (self.password[0].decode(), self.password[1].decode())
        d['private_key'] = self.private_key
        d['public_key'] = self.public_key
        d['symmetric_keys'] = (self.symmetric_keys[0].decode(), self.symmetric_keys[1].decode()) 
        return d
    
    def from_dict(self, d):
        if not isinstance(d,dict):
            raise ValueError
        if not 'username' in d:
            raise AttributeError('username not in provided dict')
        if not 'password' in d:
            raise AttributeError('password not in provided dict')
        if not 'private_key' in d:
            raise AttributeError('private_key not in provided dict')
        if not 'public_key' in d:
            raise AttributeError('public_key not in provided dict')
        if not 'symmetric_keys' in d:
            raise AttributeError('symmetric_keys not in provided dict')
        self.username = d['username']
        self.password = d['password']
        self.password = (self.password[0].encode(), self.password[1].encode())
        self.private_key = d['private_key']
        self.public_key = d['public_key']
        self.symmetric_keys = d['symmetric_keys']
   
    def set_with_username_password(self, username, password):
        self.username = username
        
        # TODO: this has to be the storage hash from crypto_utils
        self.password = generate_storage_hash_from_password(password)
        
        # TODO: the private key has to be generated from the password through crypto_utils
        self.private_key, self.public_key = generate_keypair()
        self.symmetric_keys = generate_key_from_password(password)
    
    def _check_password(self, password):
        verify_storage_hash_from_password(
                                self.password[0], password, self.password[1])
        
    def get_input(self):
        '''
        To get input for the new user from the cli
        We take as input the username and the password and then call self.set_with_username_password
        which generates the public/private keypair randomly.  
        The new user can then be added to the wallet using the add_user method of Wallet object.
        '''
        username = input('Enter the new user name: ')
        while True:
            try:
                password = getpass.getpass('Enter new password: ')
                if password == getpass.getpass('Repeat the new password: '):
                    self.set_with_username_password(username, password)
                    break;
                else:
                    raise IncorrectPasswordError('password mismatch. please try again...')
            except IncorrectPasswordError as e:
                print(e)
                continue
    
    def display_all_assets(self):
        decision= input("Do u want to Decrypt the asset: ")
        if decision.lower() == 'yes':
           print(self.symmetric_keys[0])
           key= input("Enter the decrypt key: ")
           for tx in self.get_all_txns():
              print('\n')
              print(tx['operation'])
              print("Asset ID: ",tx['id'])
              if tx['operation'] == 'CREATE':
                 data = tx['asset']['data']['encrypted']
                 print(decrypt(key,data))
              elif tx['operation'] == 'TRANSFER':
                 print(self.get_asset_by_id(tx['asset']['id']))
                 #print(tx['id'])
        else:
          for tx in self.get_all_txns():
             print('\n')
             print(tx['operation'])
             if tx['operation'] == 'CREATE':
                data = tx['asset']['data']['encrypted']
                print(data)
             elif tx['operation'] == 'TRANSFER':
                 #print(self.get_asset_by_id(tx['asset']['id']))
                print(tx['asset']['id'])
    
    def get_all_txns(self):
        '''
        To get all the transactions created by this user.
        '''
        for tx_lnk in self.get_owned_ids():
            yield self.bigchaindb_driver.transactions.retrieve(tx_lnk.txid)
    
    def get_owned_ids(self):
        '''
        Returns a list of TransactionLink objects that contain the txid and the cid that are
        owned by the public key associated with this user
        '''
        return self.bigchain.get_owned_ids(self.public_key)

    def get_asset_by_id(self, id, decrypt = False):
        '''
        To fetch the given asset. 
        '''
        if not decrypt:
            return self.bigchain.get_asset_by_id(id)
    
    def get_status_txn(self,tx_id):
        if self.bigchaindb_driver.transactions.status(tx_id).get('status') == 'valid':
           print('Valid')
        else:
           print('Not Valid')

    def retrieve_txn(self, tx_id):
        return self.bigchaindb_driver.transactions.retrieve(tx_id)
    
    def remove_none_elements_from_list(self,list):
        return [e for e in list if e is not None]
    
    def create_asset(self, asset= None, allowed_keys= None, description='',use_encryption= None):
        '''
        To create a new data asset for the calling user i.e self.
        
        The created asset will be readable by the public keys in the list of allowed_keys.
        If allowed keys is not specified, only self.public_key will be able to view the asset. 
        
        Parameters:
            asset:         
                a dict object describing the asset (this will be assigned a new 
                 asset id by BigchainDB)
            allowed_keys: 
                a list of public keys that are allowed to view the asset
                Note: the public key of self will be added to the allowed_keys if not specified
            description:
                a description of the asset
            encrypt:
                flag set to enable encryption of the asset being stored, else is stored in plaintext
        
        Returns:
            a (asset_id, txn_id) pair where
                asset_id: id of the asset created
                txn_id: id of the transaction in which the asset has been recorded
        '''
        print("Before, ",asset,type(asset))
        print("In create asset: ")
        if allowed_keys:
            if not isinstance(allowed_keys, list):
                allowed_keys = [allowed_keys]
            for k in allowed_keys:
                if isinstance(k, bytes):
                    k = k.decode()
                if not isinstance(k, str):
                    raise ValueError('the keys in allowed_keys must be bytes or str object')
            if not self.public_key in allowed_keys:
                allowed_keys.append(self.public_key)
        
        else:
            allowed_keys = [self.public_key]
       
        if use_encryption:
           print("In Encryption..")
           if isinstance(asset, dict):
               print("In dict format")
               asset = json.dumps(asset)
           asset = {'encrypted':encrypt(self.symmetric_keys[0], asset)}
           print("asset in E: ", asset)           
        else:
           print("Without encryption: ")
           if isinstance(asset,dict):
              print("In dict format")
              asset= json.dumps(asset)
              print("asset in WOE", asset)
           asset={'hash': asset}
        asset_payload = {'data':asset}
        print("Final ",asset_payload)
        metadata= Metadata(allowed_keys= allowed_keys,data= description,type= Metadata.CREATE).to_dict()
        print("Metadata: ", metadata)
        tx = self.bigchaindb_driver.transactions.prepare(
            operation='CREATE', signers=self.public_key,asset=asset_payload, metadata=metadata)
        
        signed_tx = self.bigchaindb_driver.transactions.fulfill(tx, private_keys=self.__private_key)
        
        sent_tx = self.bigchaindb_driver.transactions.send(signed_tx)
        if not sent_tx == signed_tx:
            raise ValueError('Sent transaction differs from signed txn')
        return (tx['id'])
    
    def retrieve_asset(self, asset_id):
        '''
        Retrieve data is a request to retrieve data contained in the asset specified by asset_id or all the data of the public_key.
        There is no guarantee that such requests will be granted. Provided the request is granted
        PrivAd will fetch the requested data and serve to the user.
        The data could however be encrypted and the user should obtain the symmetric key
        necessary to decrypt the data. 
        '''
        asset_id= input("Enter the asset_id: ")
        retrieve_asset= self.bigchaindb_driver.transactions.retrieve(asset_id)
        print(retrieve_asset)
        secret= retrieve_asset['asset']['data']['hash']
        print(secret)
        key= decrypt(self.private_key,secret)
        print(key)
#        u= User()
 #       asset= u.retrieve_shared_secret()
        #hash= asset["Hash"]
        #tx = self.bigchaindb_driver.transactions.retrieve(asset_id)
        #encrypted_asset = tx['asset']['data']['encrypted']
        #decrypt_key= retrieve_shared_secret(self)
        #return decrypt(decrypt_key, encrypted_asset)

    def update_asset(self,asset_id= None, allowed_keys= None, pubkey_updated_user= None):
        '''
        To update the asset given by asset_id by the calling user i.e. self
        Parameters:
           asset_id: An Id of the asset which has to be updated or changed.
           allowed_keys: A list of public keys that are allowed to view or modify the asset.
           pubkey_updated_user: Public Key of the updated user to add into the allowed_keys list.
        returns asset_id: modified assets id.
        '''
        print("In update access: ")
        u= User()
        retrieve_tx= self.retrieve_txn(asset_id)
        allowed_keys= retrieve_tx['metadata']['allowed_keys']
        allowed_keys.append(pubkey_updated_user)
        description= ''
        metadata= Metadata(allowed_keys= allowed_keys,data= description,type= Metadata.CHANGE).to_dict()
        retrieve_asset= self.bigchaindb_driver.transactions.retrieve(asset_id)
        asset= retrieve_asset['asset']['data']['encrypted']
        de_asset= decrypt(self.symmetric_keys[0],asset)
        de_asset= str(de_asset)[2:-1]
        updated_asset_id= self.create_asset(de_asset,allowed_keys,description=description,use_encryption=True)
        print(updated_asset_id)
        self.generate_shared_secret(self,pubkey_updated_user)
        return (updated_asset_id)
    
    def modify_asset(self,asset_id= None, public_key= None):
        print("In modify asset")
        retrieve_tx= self.retrieve_txn(asset_id)
        allowed_keys= retrieve_tx['metadata']['allowed_keys']
        retrieve_asset= self.bigchaindb_driver.transactions.retrieve(asset_id)
        asset= retrieve_asset['asset']['data']['encrypted']
        decrypt_key= input("Enter the decrypt key: ")
        de_asset= decrypt(decrypt_key,asset)
        print("Before: ",de_asset)
        de_asset= str(de_asset)[2:-1]
        print("after: ",de_asset)
        print("Original Asset: ", de_asset)
        print(type(de_asset))
        json_de_asset= json.loads(de_asset)
        print(type(json_de_asset))
        print("Type the notes here. Ctrl-D to save it.")
        contents = []
        while True:
           try:
              line = input()
           except EOFError:
              break
           contents.append(line)
        de_asset_str= ','.join(contents)
        json_de_asset['Modification done by: '+self.public_key + ' is ']= de_asset_str
        modified_asset= json.dumps(json_de_asset)
        print(type(modified_asset))
        print(modified_asset)
        description= "Asset is modified by "+ self.public_key+ " "
        modified_asset_id= self.create_asset(modified_asset,allowed_keys,description=description,use_encryption=True)
        return modified_asset_id

    def generate_shared_secret(self,user1,user2= None):
        print("In shared secret..")
        if not isinstance(user1, User):
           raise ValueError('expected a User class object for sharing keys')
        key= user1.symmetric_keys[0]
        if isinstance(key,bytes):
           key= user1.symmetric_keys[0].decode()
        print(key)
        hash1= encrypt(user2,key)
        print(hash1)
        asset= dict()
        asset= hash1
        fiasset= json.dumps(asset)
        allowed_keys=[user1.public_key,user2]
        asset_id= self.create_asset(fiasset,allowed_keys,description="Asset Sharing Key ",use_encryption=False)
        print(asset_id)
        return asset_id
        
 
    def retrieve_shared_secret(self):
        asset_id= input("Enter the asset_id: ")
        retrieve_asset= self.bigchaindb_driver.transactions.retrieve(asset_id)
        print(retrieve_asset)
        encrypted_asset = retrieve_asset['asset']['data']['Hash']
        print("Enc_asset : ",encrypted_asset)
        key= decrypt(self.private_key,encrypted_asset)
        #key= key.encode()
        print(key)
