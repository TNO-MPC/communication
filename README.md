# TNO MPC Lab - Communication

The TNO MPC lab consists of generic software components, procedures, and functionalities developed and maintained on a regular basis to facilitate and aid in the development of MPC solutions. The lab is a cross-project initiative allowing us to integrate and reuse previously developed MPC functionalities to boost the development of new protocols and solutions.

The package tno.mpc.communication is part of the TNO Python Toolbox.

*Remark: This cryptography software may not be used in applications that violate international export control legislations.*

## Documentation

Documentation of the tno.mpc.communication package can be found [here](https://docs.mpc.tno.nl/communication/1.0.4).

## Install

Easily install the tno.mpc.communication package using pip:
```console
$ python -m pip install tno.mpc.communication
```

## Usage

Make sure that the initialization and the usage of the pool occurs in the same event loop.

### Template
```python
import asyncio

from tno.mpc.communication import Pool

async def main():
    pool = Pool()
    # ...

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
```

### Pool initialization

#### Without SSL (do not use in production)
```python
from tno.mpc.communication import Pool

pool = Pool()
pool.add_http_server() # default port=80
pool.add_http_client("Client 1", "192.168.0.101") # default port=80
pool.add_http_client("Client 2", "192.168.0.102", port=1234)
```

#### With SSL
```python
from tno.mpc.communication import Pool

pool = Pool(key="path/to/keyfile", cert="path/to/certfile", ca_cert="path/to/cafile")
pool.add_http_server() # default port=443
pool.add_http_client("Client 1", "192.168.0.101") # default port=443
pool.add_http_client("Client 2", "192.168.0.102", port=1234)
```

#### Adding clients
HTTP clients are identified by an address. The address can be an IP address, but hostnames are also supported. For example, when communicating between two docker containers on the same network, the address that is provided to `pool.add_http_client` can either be the IP address of the client container or the name of the client container.

### Sending, receiving messages 
The library supports sending the following objects through the send and receive methods:
- strings
- byte strings
- integers
- floats 
- (nested) lists/dictionaries/numpy arrays containing any of the above. Combinations of these as well.

It is now also possible to define serialization logic in custom classes and load the logic into the commmunication module.
The class has to have the following two methods. The type annotation is necessary for the communication module to validate the serialization logic.

```python
class SomeClass:
    
    def serialize(self) -> dict:
        # serialization logic that returns a dictionary

    @staticmethod
    def deserialize(dictionary) -> 'SomeClass':
        # deserialization logic that turns the dictionary produced
        # by serialize back into an object of type SomeClass
```

To add this logic to the communication module, you have to run the following command at the start of your script. The `check_annotiations` parameter determines whether
the type hints of the serialization code are checked. You should only change this to False *if you are exactly sure of what you're doing*.

```python
from tno.mpc.communication import communication

if __name__=="__main__":
    communication.Communication.set_serialization_logic(SomeClass, check_annotations=True)
```

Messages can be send both synchronously and asynchronously.
If you do not know which one to use, use the synchronous methods with `await`.

```python
# Client 0
await pool.send("Client 1", "Hello!") # Synchronous send message (blocking)
pool.asend("Client 1", "Hello!")      # Asynchronous send message (non-blocking, schedule send task)

# Client 1
res = await pool.recv("Client 0") # Receive message synchronously (blocking)
res = pool.arecv("Client 0")      # Receive message asynchronously (non-blocking, returns Future if message did not arrive yet)
```

### Custom message IDs
```python
# Client 0
await pool.send("Client 1", "Hello!", "Message ID 1")

# Client 1
res = await pool.recv("Client 0", "Message ID 1")
```
