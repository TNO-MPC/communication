# TNO MPC Lab - Communication

The TNO MPC lab consists of generic software components, procedures, and functionalities developed and maintained on a regular basis to facilitate and aid in the development of MPC solutions. The lab is a cross-project initiative allowing us to integrate and reuse previously developed MPC functionalities to boost the development of new protocols and solutions.

The package tno.mpc.communication is part of the TNO Python Toolbox.

*Limitations in (end-)use: the content of this repository may solely be used for applications that comply with international export control laws.*  
*This implementation of cryptographic software has not been audited. Use at your own risk.*

## Documentation

Documentation of the tno.mpc.communication package can be found [here](https://docs.mpc.tno.nl/communication/3.1.0).

## Install

Easily install the tno.mpc.communication package using pip:
```console
$ python -m pip install tno.mpc.communication
```

If you wish to run the tests you can use:
```console
$ python -m pip install 'tno.mpc.communication[tests]'
```

## Usage

The communication module uses `async` functions for sending and receiving. If you are familiar
with the async module, you can skip to the `Pools` section.

### Async explanation
When `async` functions are called, they return what is called a *coroutine*.
This is a special kind of object, because it is basically a promise that the code will be run and
a result will be given when the coroutine is given to a so-called *event loop*.
For example, see the following

```python
import asyncio

async def add(a: int, b: int) -> int:
    return a + b

def main():
    a,b = 1, 2
    coroutine_object = add(a, b) # This is now a coroutine object of type Awaitable[int]
    event_loop = asyncio.get_event_loop() # This is the event loop that will run the coroutine
    result = event_loop.run_until_complete(coroutine_object) # This call starts the coroutine in the event loop
    print(result) # this prints 3

if __name__ == "__main__":
    main()
```

As you can see from the example, the async methods are defined using `async def`, which tells python
that it should return a coroutine. We saw how we can call an async function from a regular function
using the event loop. *Note that you should never redefine the event loop and always retrieve the
event loop as done in the example* (unless you know what you are doing). We can also call async
functions from other async functions using the `await` statement, as is shown in the following example.

```python
import asyncio

async def add_four_numbers(first: int, second: int, third: int, fourth: int) -> int:
    first_second = await add(first, second) # This is blocking, so the function will wait until this is done
    third_fourth_coroutine = add(third, fourth) # This is non-blocking, so the code will continue while the add(third,fourth) code starts running
    # we can do some other stuff here
    print("I am a print statement")
    third_fourth = await third_fourth_coroutine # we wait until the add(third,fourth) is done
    result = await add(first_second, third_fourth)
    # here it is important to use await for the result, because then an integer is produced and given
    # to the return statement instead of a coroutine
    return result

async def add(a: int, b: int) -> int:
    return a + b

def main():
    a, b, c, d = 1, 2, 3, 4
    coroutine_object = add_four_numbers(a, b, c, d) # This is now a coroutine object of type Awaitable[int]
    event_loop = asyncio.get_event_loop() # This is the event loop that will run the coroutine
    result = event_loop.run_until_complete(coroutine_object) # This call starts the coroutine in the event loop
    print(result) # this prints 10

if __name__ == "__main__":
    main()
```

Note that the type of the `coroutine_object` in the `main` function is an `Awaitable[int]`.
This refers to the fact that the result can be awaited (inside an `async` function) and will return an integer once that is done.

### Pools
A `Pool` represents a network. A Pool contains a server, which listens for incoming messages from
other parties in the network, and clients for each other party in the network. These clients are
called upon when we want to send or receive messages.

It is also possible to use and initialize the pool without taking care of the event loop 
yourself, in that case the template below can be ignored and the examples can be used as one 
would regularly do. (An event loop is however still needed when using the `await` keyword or 
when calling an `async` function.)

### Template
Below you can find a template for using `Pool`. Alternatively, you could create the pool in the
`main` logic and give it as a parameter to the `async_main` function.

```python
import asyncio

from tno.mpc.communication import Pool

async def async_main():
    pool = Pool()
    # ...

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main())
```

### Pool initialization

The following logic works both in regular fuctions and `async` functions.
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
- (nested) lists/tuples/dictionaries/numpy arrays containing any of the above. Combinations of these as well.

Under the hood [`ormsgpack`](https://pypi.org/project/ormsgpack) is used, additional options can be activated using the `option` parameter (see, https://github.com/aviramha/ormsgpack#option).

Messages can be sent both synchronously and asynchronously.
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

### Custom serialization logic
It is also possible to define serialization logic in custom classes and load the logic into the commmunication module. An example is given below. We elaborate on the requirements for such classes after the example.

```python
class SomeClass:
    
    def serialize(self, **kwargs: Any) -> Dict[str, Any]:
        # serialization logic that returns a dictionary

    @staticmethod
    def deserialize(obj: Dict[str, Any], **kwargs: Any) -> 'SomeClass':
        # deserialization logic that turns the dictionary produced
        # by serialize back into an object of type SomeClass
```

The class needs to contain a `serialize` method and a `deserialize` method. The type annotation is necessary and validated by the 
communication module.
Next to this, the `**kwargs` argument is also necessary to allow for nested (de)serialization that 
makes use of additional optional keyword arguments. It is not necessary to use any of these optional keyword 
arguments. If one does not make use of the `**kwargs` and also does not make a call to a subsequent 
`Serialization.serialize()` or `Serialization.deserialize()`, it is advised to write 
`**_kwargs: Any` instead of `**kwargs: Any`.



To add this logic to the communication module, you have to run the following command at the start of your script. The `check_annotiations` parameter determines whether
the type hints of the serialization code and the presence of a `**kwargs` parameter are checked. 
You should only change this to False *if you are exactly sure of what you are doing*.

```python
from tno.mpc.communication import Serialization

if __name__ == "__main__":
   Serialization.set_serialization_logic(SomeClass, check_annotations=True)
```


