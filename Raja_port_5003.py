from hashlib import sha256
import json, datetime, re
from uuid import uuid4, uuid5, NAMESPACE_DNS
from flask import Flask, request, jsonify
import requests
from urllib.parse import urlparse
import sys


# HERE new_block is at like <__main__.Block object at 0x000001E20C6A0760>(so,we use new_block.)
# i have not ASIC or GPU so, i also take timesatamp as an argument
class Block:
    def __init__(self, index, unspent_transaction, prev_hash, timestamp,miner,merkel_root):
        self.index = index
        self.unspent_transaction = unspent_transaction
        transaction_volume = 0
        fee = 0
        for i in range(0, len(self.unspent_transaction)):
            transaction_volume += float(re.findall("[+]?\d*\.\d*|\d+", self.unspent_transaction[i]['ammount'])[0])
            fee += float(re.findall("[+]?\d*\.\d*|\d+", self.unspent_transaction[i]['fee'])[0])
        self.Fee_Reward = format(fee, '.10f') + " RYC"
        self.Transaction_Volume = f'{transaction_volume} RYC'
        self.Number_of_Transaction = len(self.unspent_transaction)
        self.prev_hash = prev_hash
        self.Merkel_root=merkel_root
        self.timestamp = timestamp
        self.block_reward = "12.50000000 RYC"
        self.miner = miner

    def compute_hash(self):
        return sha256(json.dumps(self.__dict__, sort_keys=True).encode()).hexdigest()


class Blockchain:
    def __init__(self):
        self.unspent_transaction = []
        self.chain = []
        self.create_genesis_block()
        self.nodes = set()

    def create_genesis_block(self):
        self.add_transaction(sender='raja', receiver='rajat', ammount='1200 RYC', fee='0.000001244 RYC')
        self.add_transaction(sender=str(uuid4()).replace('-', ''), receiver="Arpit", ammount="12.500000000 RYC",
                             fee="0.00000 RYC")
        for i in range(0, len(self.unspent_transaction)):
            self.unspent_transaction[i]['transaction_id'] = str(uuid5(NAMESPACE_DNS, json.dumps(self.unspent_transaction[i], sort_keys=True))).replace('-', '')
        Merkel_root=self.merkel_root(self.unspent_transaction)
        genesis_block = Block(0, self.unspent_transaction, '0' * 64, str(datetime.datetime.now()),'Arpit',Merkel_root)
        block_hash = self.proof_of_work(genesis_block)
        genesis_block.hash = block_hash
        genesis_block.Size = f'{sys.getsizeof(genesis_block.__dict__)}bytes'
        self.chain.append(genesis_block.__dict__)
        self.unspent_transaction = []
    def proof_of_work(self, block):
        block.nonce = 0
        check_proof = False
        while check_proof is False:
            hash_operation = block.compute_hash()
            if hash_operation.startswith('0000'):
                check_proof = True
            else:
                block.nonce += 1
        return hash_operation

    @property
    def previous_block(self):
        return self.chain[-1]

    def add_transaction(self, sender, receiver, ammount, fee):
        self.unspent_transaction.append({'sender':sender,'receiver':receiver,'ammount': ammount, 'fee': fee})

    def mine_block(self):
        if self.unspent_transaction:
            self.add_transaction(sender=str(uuid4()).replace('-', ''), receiver="Arpit", ammount="12.500000000RYC",
                                 fee="0.00000RYC")
            for i in range(0, len(self.unspent_transaction)):
                self.unspent_transaction[i]['transaction_id'] = str(uuid5(NAMESPACE_DNS, json.dumps(self.unspent_transaction[i], sort_keys=True))).replace('-', '')
            Merkel_root=self.merkel_root(self.unspent_transaction)
            prev_block = self.previous_block
            # Here previous block now convted into dictionary form that's why we use ['index']
            index = prev_block['index']
            prev_hash = prev_block['hash']
            new_block = Block(index + 1, self.unspent_transaction, prev_hash, str(datetime.datetime.now()),'Arpit',Merkel_root)
            Block_hash = self.proof_of_work(new_block)
            block = self.add_block(new_block, Block_hash)
            self.unspent_transaction = []
            return block
        else:
            return False
    def merkel_root(self,transaction_list):
        hash_list = []
        if len(transaction_list) == 1:
            return transaction_list[0]
        for i in range(0, len(transaction_list) - 1, 2):
            hash_list.append(sha256((json.dumps(transaction_list[i]) +json.dumps(transaction_list[i + 1])).encode()).hexdigest())
        if len(transaction_list) % 2 == 1:
            hash_list.append(sha256((json.dumps(transaction_list[-1]) +json.dumps( transaction_list[-1])).encode()).hexdigest())
        return self.merkel_root(hash_list)
    def add_block(self, new_block, Block_hash):
        hash_of_previous_block = self.previous_block['hash']
        if hash_of_previous_block != new_block.prev_hash:
            print("hash ka ratta")
            return False
        if self.valid_proof(new_block, Block_hash):
            new_block.hash = Block_hash
            new_block.Size = f'{sys.getsizeof(new_block.__dict__)}bytes'
            self.chain.append(new_block.__dict__)
        return new_block

    def valid_proof(self, new_block, Block_hash):
        current_hash = new_block.compute_hash()
        if current_hash.startswith('0000') and current_hash == Block_hash:
            return True
        else:
            print("proof b shi nhi h ")
            return False

    def add_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def is_valid_chain(self, chain):
        block_index = 1
        prev_block = chain[0]
        while block_index < len(chain):
            previous_block = Block(prev_block['index'], prev_block['unspent_transaction'], prev_block['prev_hash'],
                                   prev_block['timestamp'],prev_block['miner'],prev_block['Merkel_root'])
            previous_block.nonce = prev_block['nonce']
            previous_block.hash = prev_block['hash']
            current_block = chain[block_index]
            if previous_block.hash != current_block['prev_hash']:
                return False
            block_hash = previous_block.hash
            delattr(previous_block, "hash")
            if not self.valid_proof(previous_block, block_hash):
                print("Kuch to gadbad h ")
                return False
            block_index += 1
            previous_block = current_block
        return True

    def consensus(self):
        max_length = len(self.chain)
        longest_chain = None
        for node in self.nodes:
            response = requests.get(f'http://{node}/get_chain')
            if response.status_code == 200:
                chain = response.json()['chain']
                connect_node_length = response.json()['length']
                if connect_node_length > max_length and self.is_valid_chain(chain):
                    max_length = connect_node_length
                    longest_chain = chain
        if longest_chain:
            self.chain = longest_chain
            return True
        return False

    def announce_new_block(self, block):
        for node in self.nodes:
            requests.post(f'http://{node}/veriy_and_add_block', json=block.__dict__)


app = Flask(__name__)
blockchain = Blockchain()

@app.route('/get_chain', methods=['GET'])
def get_chain():
    response = {'chain': blockchain.chain,
                'length': len(blockchain.chain)}
    return jsonify(response), 200


@app.route('/mine_block', methods=['GET'])
def mine_block():
    blockchain.consensus()
    block = blockchain.mine_block()
    if not block:
        response = {'message': 'Please put some transaction'}
    else:
        response = {'message': 'congrats you just mined the block',
                    'block': block.__dict__, }
        blockchain.announce_new_block(block)
    return jsonify(response), 200


@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    transaction_json = request.get_json()
    transaction_keys = ['sender', 'receiver', 'ammount', 'fee']
    for key in transaction_keys:
        if key not in transaction_json:
            response = {'message': 'please provide right name of sender ,receiver and ammount in json file'}
            return jsonify(response), 400
    length = len(blockchain.unspent_transaction)
    limit = 20
    if length < limit:
        blockchain.add_transaction(transaction_json['sender'], transaction_json['receiver'],
                                   transaction_json['ammount'], transaction_json['fee'])
        index = blockchain.previous_block['index'] + 1
        response = {'message': f'This Transaction will be added into {index} block'}
    else:
        response = {'message': 'Please mine these 20 transaction,then after you will allow to add transation',
                    'unspent_transaction': blockchain.unspent_transaction}
    return jsonify(response), 201


@app.route('/pending_transaction', methods=['GET'])
def pending_transaction():
    if blockchain.unspent_transaction:
        resp = {'pending_Transaction': blockchain.unspent_transaction}
    else:
        resp = {'message': 'No pending  transaction in this blockchain'}
    return jsonify(resp), 200


@app.route('/connect_node', methods=['POST'])
def connect_node():
    nodes_json = request.get_json()
    nodes = nodes_json.get('nodes')
    if nodes is None:
        return "No node available to connect", 400
    for address in nodes:
        blockchain.add_node(address)
    response = {'message': "All nodes are now connected in  the Ray_coin blockchain now contain following node",
                'nodes': list(blockchain.nodes)}
    return jsonify(response), 201


@app.route('/veriy_and_add_block', methods=['POST'])
def veriy_and_add_block():
    block_data = request.json
    block = Block(block_data['index'], block_data['unspent_transaction'], block_data['prev_hash'],
                  block_data['timestamp'],block_data['miner'],block_data['Merkel_root'])
    block.nonce = block_data['nonce']
    block_hash = block_data['hash']
    block_added = blockchain.add_block(block, block_hash)
    compute_merkle_root=blockchain.merkel_root(block_data['unspent_transaction'])
    if (compute_merkle_root==block_data['Merkel_root'] and block_added):
        response = {'message': 'block added to the chain'}
    else:
        response = {'message': 'The block was discarded by the node'}
    return jsonify(response), 201


@app.route('/consensus', methods=['GET'])
def consensus():
    if blockchain.consensus():
        response = {'messaage': "The node have different chain ,so it was replaced by longest chain",
                    'new_chain': blockchain.chain}
    else:
        response = {'message': "All good The chain is the largest one",
                    }
    return jsonify(response), 200


app.run(host='0.0.0.0', port=5003)
