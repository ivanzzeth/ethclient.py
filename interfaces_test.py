import unittest
import queue
from web3 import Web3
from solcx import compile_source

from interfaces import Contract


class TestInterfaces(unittest.TestCase):
    compiled_sol = None
    web3: Web3
    greeter: Contract

    def setup(self):
        self.compiled_sol = compile_source(
            '''
            pragma solidity >0.5.0;

            contract Greeter {
                string public greeting;

                event GreetingUpdated1(string _greeting);
                event GreetingUpdated2(string _greeting);
                event GreetingUpdated3(string _greeting);
                constructor() public {
                    greeting = 'Hello';
                }

                function setGreeting(string memory _greeting) public {
                    greeting = _greeting;
                    emit GreetingUpdated1(_greeting);
                    emit GreetingUpdated2(_greeting);
                    emit GreetingUpdated3(_greeting);
                }

                function greet() view public returns (string memory) {
                    return greeting;
                }
            }
            '''
        )

        contract_id, contract_interface = self.compiled_sol.popitem()
        abi = contract_interface['abi']
        bytecode = contract_interface['bin']
        self.web3 = Web3(Web3.EthereumTesterProvider())
        greeter_factory = self.web3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = greeter_factory.constructor().transact()
        tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        greeter = self.web3.eth.contract(
            address=tx_receipt.contractAddress,
            abi=abi
        )

        self.greeter = Contract(greeter)

    def test_interfaces(self):
        self.setup()
        print('addr1: ', self.web3.eth.accounts[0])
        print('addr2: ', self.web3.eth.accounts[1])
        print('greet: ', self.greeter.functions.greet())
        res = self.greeter.functions.setGreeting('hello', **{
            'from': self.web3.eth.accounts[1]
        })
        print('tx: ', self.web3.eth.get_transaction(res.tx_hash))
        for event in res.events:
            print('set event: ', event)
        self.greeter.shutdown(wait=True)
