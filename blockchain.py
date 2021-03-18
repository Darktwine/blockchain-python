import binascii
# from cryptography.hazmat.primitives import serialization as crypto_serialization
# from cryptography.hazmat.primitives.asymmetric import rsa
# from cryptography.hazmat.backends import default_backend as crypto_default_backend
import Cryptodome
import Cryptodome.Random
from Cryptodome.PublicKey import RSA
from Cryptodome.Cipher import Salsa20
import hashlib
import json
from urllib.parse import urlparse
from uuid import uuid4
import requests
from flask import Flask, jsonify, request


class Blockchain:
    def __init__(self):
        self.chain = []
        self.transaction = []
        self.new_block(previous_hash='0')
        self.nodes = set()

        # rsa encryption (testing wrong location)
        #self.private_key = RSA.generate(1024, random_gen)
        #self.public_key = self.private_key.public_key()

    # check if rsa encryption is working
    """
    def set_key(self):
        key = rsa.generate_private_key(
            backend=crypto_default_backend(),
            public_exponent=65537,
            key_size=2048
        )
        private_key = key.private_bytes(crypto_serialization.Encoding.PEM,
                                        crypto_serialization.PrivateFormat.PKCS8,
                                        crypto_serialization.NoEncryption())
        public_key = key.public_key().public_bytes(crypto_serialization.Encoding.OpenSSH,
                                                   crypto_serialization.PublicFormat.OpenSSH)
        self.public_key = public_key
        self.private_key = private_key
        
        print('public\n')
        print(binascii.hexlify(self.public_key.exportKey(format='DER')).decode('ascii'))
        print('private\n')
        print(binascii.hexlify(self.private_key.exportKey(format='DER')).decode('ascii'))
    """

    # add nodes
    def create_nodes(self, address):
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid')

    # proof of work testing (sends transactions to each node in network) c
    def proof(self, book_key):
        network = self.nodes
        for node in network:
            if node != book_key:
                requests.post(f'http://{node}/add_transaction', data={
                    "sender_key": self.transaction[0]['sender_key'],
                    "receiver_key": self.transaction[0]['receiver_key'],
                    "book_key": self.transaction[0]['book_key']
                })
                response = requests.get(f'http://{node}/add_block')

    # consensus testing (adding longest chain)
    def consensus(self):
        self.proof(self.transaction[0]['book_key'])
        network = self.nodes
        check_chain = None
        length_chain = len(self.chain)
        for node in network:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']
                if length > length_chain and self.validate_chain(chain):
                    length_chain = length
                    check_chain = chain
        if check_chain:
            self.chain = check_chain
            return True
        return False

    # creating a new block
    def new_block(self, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'transaction': self.transaction,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }
        self.transaction = []
        self.chain.append(block)
        return block

    # creating new transactions
    def new_transaction(self, sender_key, receiver_key, book_key):
        # testing
        #key = b'self.private_key'
        #cipher = Salsa20.new(key)
        self.transaction.append({
            'sender_key': sender_key,
            'receiver_key': receiver_key,
            'book_key': book_key
        })
        return self.last_block['index'] + 1

    # checks if chain is valid
    def validate_chain(self, chain):
        previous_block = chain[0]
        counter = 1
        while counter < len(chain):
            current_block = chain[counter]
            previous_hash = self.hash(previous_block)
            if current_block['previous_hash'] != previous_hash:
                return False
            previous_block = current_block
            counter = counter + 1
        return True

    # hash the block
    @staticmethod
    def hash(block):
        block_hash = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_hash).hexdigest()

    # gets last block from chain
    @property
    def last_block(self):
        return self.chain[-1]


app = Flask(__name__)
node_identifier = str(uuid4()).replace('-', '')
blockchain = Blockchain()

# remove later
# blockchain.set_key()


# create block
@app.route('/add_block', methods=['GET'])
def add_block():
    last_block = blockchain.last_block
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(previous_hash)
    response = {
        'message': "new block",
        'index': block['index'],
        'transaction': block['transaction'],
        'previous_hash': block['previous_hash']
    }
    return jsonify(response), 200


# create transaction
@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    values = request.get_json()
    required = ['sender_key', 'receiver_key', 'book_key']
    if not all(keys in values for keys in required):
        return 'Missing keys', 400
    # testing
    #apple = nodes
    #key = b'apple'
    # encryptor = Salsa20.new(key)
    index = blockchain.new_transaction((values['sender_key']),
                                       (values['receiver_key']),
                                       (values['book_key']))
    response = {'message': f' New transaction for block {index} and transaction {len(blockchain.transaction)} '}
    return jsonify(response), 201


# returns chain
@app.route('/get_chain', methods=['GET'])
def get_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain)
    }
    return jsonify(response), 200


# add new nodes
@app.route('/new_nodes', methods=['POST'])
def new_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return "Error", 400
    for node in nodes:
        blockchain.create_nodes(node)
    response = {
        'message': "Node created",
        'total_nodes': list(blockchain.nodes)
    }
    return jsonify(response), 201


@app.route('/check_consensus', methods=['GET'])
def check_consensus():
    good = blockchain.consensus()
    if good:
        response = {
            'message': 'New chain',
            'chain': blockchain.chain
        }
    else:
        response = {
            'message': 'Consensus failed',
            'chain': blockchain.chain
        }
    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=5000, type=int, help='port to listen to')
    args = parser.parse_args()
    port = args.port
    app.run(host='127.0.0.1', port=port)
