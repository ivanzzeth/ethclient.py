import unittest
import queue
from web3 import Web3

import nonce


class TestNonceManager(unittest.TestCase):
    web3: Web3

    def setup(self):
        self.web3 = Web3(Web3.EthereumTesterProvider())

    def test_manager(self):
        self.setup()
        manager = nonce.Manager(self.web3, 0)
        tx = {
            'from': self.web3.eth.accounts[0],
            'to': self.web3.eth.accounts[1],
            'value': 1
        }
        print('tx: ', tx)
        receipt_out_queue = queue.Queue(maxsize=1)

        manager.submit_tx(tx, '', receipt_out_queue)
        (tx_hash, receipt) = receipt_out_queue.get()
        print('hash: ', tx_hash)
        print('receipt: ', receipt)
        manager.shutdown(wait=True)
