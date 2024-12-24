# ethclient.py
Make calling smart contract like a common function.

## Requirements

Python 3.8+

## Get started

Install `ethclient`

```bash
pip install ethclient
```

Usage:

```python
from ethclient import Contract
greeter = web3.eth.contract(
    address=contract_address,
    abi=abi
)

greeter = Contract(greeter)
```

## Local Development

Create a new virtual environment:
```bash
python -m venv myenv
```

To activate this environment, use:
```bash
source ./myenv/bin/activate
```

Install dependencies:
```bash
pip install -r requirements.txt
```