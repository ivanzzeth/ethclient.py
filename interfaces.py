import queue
from typing import *

from eth_typing import (
    Address,
    BlockNumber,
    ChecksumAddress,
    HexStr,
)

from web3 import Web3

from web3.types import (
    ABI,
    ABIEvent,
    ABIFunction,
    BlockIdentifier,
    EventData,
    FunctionIdentifier,
    LogReceipt,
    TxParams,
    TxReceipt,
)

from web3.contract import (
    Contract as Web3Contract,
    ContractEvent as Web3ContractEvent,
    ContractEvents as Web3ContractEvents,
    ContractFunction as Web3ContractFunction,
)

from web3.logs import (
    DISCARD,
    IGNORE,
    STRICT,
    WARN,
    EventLogErrorFlags,
)

from web3.datastructures import AttributeDict

import nonce


class ExecutionResult:
    tx_hash: str
    return_value: Any
    events: Iterable[EventData]
    error: Union[str, None]

    def __init__(self, tx_hash: str, return_value: Any, events: Iterable[EventData], error: Union[str, None]):
        self.tx_hash = tx_hash
        self.return_value = return_value
        self.events = events
        self.error = error

    def __str__(self):
        return {
            'return_value': self.return_value,
            'events': self.events,
            'error': self.error,
        }.__str__()


class ContractFunction:
    nonce_manager: nonce.Manager
    web3_func: Web3ContractFunction
    events: Web3ContractEvents

    def __init__(self, nm: nonce.Manager, events: Web3ContractEvents,
                 web3_func: Web3ContractFunction) -> None:
        self.nonce_manager = nm
        self.events = events
        self.web3_func = web3_func

    def __call__(self, *args: Any, **kwargs: Any) -> ExecutionResult:
        """

        :param args: the function args of smart contract
        :param kwargs: the transaction params
        :return:
        """
        web3_func = self.web3_func.__call__(*args, **{})

        block_number = self.web3_func.web3.eth.block_number

        tx = kwargs
        tx_hash: str = ""
        events: List = []
        error = None

        if web3_func.abi['stateMutability'] not in {'pure', 'view'}:
            receipt_out_queue = queue.Queue(maxsize=1)
            tx = web3_func.buildTransaction(tx)
            self.nonce_manager.submit_tx(tx, '', receipt_out_queue)
            (tx_hash, receipt) = receipt_out_queue.get()
            for event in self.events:
                try:
                    events.extend(event().processReceipt(receipt, EventLogErrorFlags.Discard))
                except:
                    pass

            events.sort(key=lambda x: x['logIndex'], reverse=False)
            block_number = receipt['blockNumber']

        # calling `call` function without 'data' field in transaction params.
        call_tx_params = dict(tx)
        if 'data' in call_tx_params:
            del call_tx_params['data']

        return_value = web3_func.call(transaction=call_tx_params, block_identifier=block_number)

        # TODO: error message
        return ExecutionResult(tx_hash, return_value, events, error)


class ContractFunctions(AttributeDict):
    def __init__(self, d: Dict[str, ContractFunction]):
        super(ContractFunctions, self).__init__(d)


class Contract:
    web3Contract: Web3Contract
    functions: ContractFunctions
    manager: nonce.Manager

    def __init__(self, contract: Web3Contract):
        self.web3Contract = contract
        self.manager = nonce.Manager(contract.web3)

        # load functions
        func_dict = {}
        for func_name in contract.functions:
            f = contract.functions.__getattribute__(func_name)
            func_dict[func_name] = ContractFunction(
                self.manager,
                self.web3Contract.events,
                f)
        self.functions = ContractFunctions(func_dict)

    def shutdown(self, wait=False):
        self.manager.shutdown(wait=wait)
