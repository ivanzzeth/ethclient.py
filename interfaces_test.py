import unittest
from web3 import Web3
from solcx import compile_source

from interfaces import Contract


class TestInterfaces(unittest.TestCase):
    compiled_sol = None
    web3: Web3
    greeter: Contract

    def setup(self):
        from solcx import install_solc, set_solc_version
        solc_version = 'v0.6.1'
        install_solc(solc_version)
        set_solc_version(solc_version)

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

        # add middleware for reconnection
        # self.web3.middleware_onion.add(http_retry_request_middleware, 'http_retry_request_middleware')
        # self.web3.middleware_onion.inject(ReconnectMiddleware, 'reconnect_middleware', 0)

        greeter_factory = self.web3.eth.contract(abi=abi, bytecode=bytecode)
        tx_hash = greeter_factory.constructor().transact()
        tx_receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash)
        greeter = self.web3.eth.contract(
            address=tx_receipt.contractAddress,
            abi=abi
        )

        self.greeter = Contract(greeter)

    def set_greeting(self, greeting: str, default_greeting='Hello'):
        self.assertEqual(self.greeter.functions.greet().return_value, default_greeting,
                         'unexpected default greet string')

        res = self.greeter.functions.setGreeting(greeting, **{
            'from': self.web3.eth.accounts[1],
            # 'gas': 88888,
            # 'gasPrice': 875000001,
            'value': 0,
        })
        if res.error is not None:
            print()
        self.assertTrue(res.error is None, 'execution err: {}'.format(res))
        print('tx: ', self.web3.eth.get_transaction(res.tx_hash))
        for event in res.events:
            print('set event: ', event)
        self.assertTrue(len(res.events) == 3, 'unexpected events length')
        print('set_greeting_res: ', res)

        greeting_res = self.greeter.functions.greet()
        print('greeting_res: ', greeting_res)
        # greet:  {'return_value': 'Hello', 'events': [], 'error': None}

        # waiting for transaction receipt
        self.web3.eth.wait_for_transaction_receipt(res.tx_hash)
        print('greeting: ', greeting_res.return_value)
        # greeting:  hello

        self.assertEqual(greeting_res.return_value, greeting, 'setGreeting failed')

    def test_interfaces(self):
        try:
            self.setup()
            print('addr1: ', self.web3.eth.accounts[0])
            print('addr2: ', self.web3.eth.accounts[1])

            self.set_greeting('hello')

            self.set_greeting('hello2', 'hello')
        finally:
            self.greeter.shutdown(wait=True)

