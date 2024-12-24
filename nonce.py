import queue
import logging

from web3 import Web3
from web3.types import TxParams

from thread import ThreadManager, QUEUE_EXIT_SIGNAL

CONFIRM_TIMEOUT = 1000 * 30


class Manager:
    def __init__(self, w3: Web3, queue_size: int = 0):
        """

        :param queue_size: If queue_size is <= 0, queue size is infinite.
        """
        self.task_queue = queue.Queue(maxsize=queue_size)
        self.receipt_queue = queue.Queue(maxsize=queue_size)

        self._task_thread_manager = ThreadManager(self.task_queue, max_workers=1)
        self._check_thread_manager = ThreadManager(self.receipt_queue, max_workers=1)

        self.web3: Web3 = w3
        self._nonce_dict = {}

        # TODO:
        self._worker()
        self._confirm_receipt()

    def _worker(self):
        def schedule():
            while not self._task_thread_manager.has_shutdown():
                try:
                    item = self.task_queue.get()
                    if item is QUEUE_EXIT_SIGNAL:
                        self.task_queue.put(item)
                        print('exit tx schedule task...')
                        break
                    # TODO: remove private_key
                    (tx, receipt_out_queue) = item

                    gas = self.web3.eth.estimate_gas(tx)
                    self.web3.eth.call(tx)
                    gas_price = self.web3.eth.gas_price
                    addr = tx['from']
                    nonce = self.get_nonce(addr)

                    # fill tx
                    tx = dict(tx)
                    tx['nonce'] = nonce

                    # send transaction
                    tx_hash = self.web3.eth.send_transaction(tx)
                    self.receipt_queue.put((tx_hash, receipt_out_queue))
                    logging.info('put to receipt queue, tx {}'.format(tx_hash.hex()))

                    self.increase_nonce(addr)

                    # TODO: double confirm that the transaction execution is successful

                except Exception as e:
                    print('submit tx exception: {}'.format(e))
                    pass

        self._task_thread_manager.submit(schedule)

    def _confirm_receipt(self):
        def confirm():
            while not self._check_thread_manager.has_shutdown():
                try:
                    item = self.receipt_queue.get()
                    if item is QUEUE_EXIT_SIGNAL:
                        self.task_queue.put(item)
                        break
                    (tx_hash, receipt_out_queue) = item
                    receipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=CONFIRM_TIMEOUT)
                    if receipt['status'] == 0:
                        logging.warning('transaction {} execution err'.format(tx_hash.hex()))
                    if receipt_out_queue is not False:
                        receipt_out_queue.put((tx_hash, receipt))
                except Exception as e:
                    logging.error('confirm thread got exception: {}'.format(e))
                    raise e

        self._check_thread_manager.submit(confirm)

    def submit_tx(self, tx: TxParams, receipt_out_queue: queue.Queue = None):
        self.task_queue.put((tx, receipt_out_queue))

    def shutdown(self, wait: False):
        self._task_thread_manager.shutdown(wait)
        self._check_thread_manager.shutdown(wait)

    def get_nonce(self, account: str, block_identifier='latest') -> int:
        if (account in self._nonce_dict) is False:
            self._nonce_dict[account] = self.web3.eth.get_transaction_count(account, block_identifier)
        logging.info('nonce: {}'.format(self._nonce_dict[account]))
        return self._nonce_dict[account]

    def increase_nonce(self, account: str):
        self._nonce_dict[account] += 1
