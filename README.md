# TNO MPC Lab - Communication

The TNO MPC lab consists of generic software components, procedures, and
functionalities developed and maintained on a regular basis to facilitate and
aid in the development of MPC solutions. The lab is a cross-project initiative
allowing us to integrate and reuse previously developed MPC functionalities to
boost the development of new protocols and solutions.

The package tno.mpc.communication is part of the TNO Python Toolbox.

_Limitations in (end-)use: the content of this repository may solely be used for
applications that comply with international export control laws._  
_This implementation of cryptographic software has not been audited. Use at your
own risk._

## Documentation

Documentation of the tno.mpc.communication package can be found
[here](https://docs.mpc.tno.nl/communication/4.5.0).

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

The communication module uses `async` functions for sending and receiving. If
you are familiar with the async module, you can skip to the `Pools` section.

### Async explanation

When `async` functions are called, they return what is called a _coroutine_.
This is a special kind of object, because it is basically a promise that the
code will be run and a result will be given when the coroutine is given to a
so-called _event loop_. For example, see the following

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

As you can see from the example, the async methods are defined using
`async def`, which tells python that it should return a coroutine. We saw how we
can call an async function from a regular function using the event loop. _Note
that you should never redefine the event loop and always retrieve the event loop
as done in the example_ (unless you know what you are doing). We can also call
async functions from other async functions using the `await` statement, as is
shown in the following example.

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

Note that the type of the `coroutine_object` in the `main` function is an
`Awaitable[int]`. This refers to the fact that the result can be awaited (inside
an `async` function) and will return an integer once that is done.

### Pools

A `Pool` represents a network. A Pool contains a server, which listens for
incoming messages from other parties in the network, and clients for each other
party in the network. These clients are called upon when we want to send or
receive messages.

It is also possible to use and initialize the pool without taking care of the
event loop yourself, in that case the template below can be ignored and the
examples can be used as one would regularly do. (An event loop is however still
needed when using the `await` keyword or when calling an `async` function.)

### Template

Below you can find a template for using `Pool`. Alternatively, you could create
the pool in the `main` logic and give it as a parameter to the `async_main`
function.

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

The following logic works both in regular functions and `async` functions.

#### Without SSL/TLS (do not use in production)

The following snippet will start a HTTP server and define its clients. Clients
are configured on both the sending and the receiving side. The sending side
needs to know who to send a message to. The receiving side needs to know who it
receives a message from for further handling.

By default the `Pool` object uses the origin IP and port to identify the client.
However, a more secure and robust identification through SSL/TLS certificates is
also supported and described in section
[With SSL/TLS (SSL/TLS certificate as client identifier)](#with-ssltls-ssltls-certificate-as-client-identifier).

```python
from tno.mpc.communication import Pool

pool = Pool()
pool.add_http_server() # default port=80
pool.add_http_client("Client 1", "192.168.0.101") # default port=80
pool.add_http_client("Client 2", "192.168.0.102", port=1234)
```

#### With SSL/TLS

A more secure connection can be achieved by using SSL/TLS. A `Pool` object can
be initialized with paths to key, certificate and CA certificate files that are
passed as arguments to a
[`ssl.SSLContext`](https://docs.python.org/3/library/ssl.html#ssl.SSLContext)
object. More information on the expected files can be found in the
`Pool.__init__` docstring and the
[`ssl` documentation](https://docs.python.org/3/library/ssl.html#certificates).

```python
from tno.mpc.communication import Pool

pool = Pool(key="path/to/keyfile", cert="path/to/certfile", ca_cert="path/to/cafile")
pool.add_http_server() # default port=443
pool.add_http_client("Client 1", "192.168.0.101") # default port=443
pool.add_http_client("Client 2", "192.168.0.102", port=1234)
```

We do not pose constraints on the certificates that you use in the protocol.
However, your organisation most likely poses minimal security requirements on
the certificates used. As such we do not advocate a method for generating
certificates but rather suggest to contact your system administrator for
obtaining certificates.

#### With SSL/TLS (SSL/TLS certificate as client identifier)

This approach does not use the origin of a message (HTTP request) as identifier
of a party, but rather the SSL/TLS certificate of that party. This requires a
priori exchange of the certificates, but is more robust to more complex (docker)
network stacks, proxies, port forwarding, load balancers, IP spoofing, etc.

More specifically, we assume that a certificate has a unique combination of
issuer Common Name and S/N and use these components to create a HTTP client
identifier. Our assumption is based on the fact that we trust the issuer (TSL
assumption) and that the issuer is supposed to hand out end-user certificates
with different serial numbers.

```python
from tno.mpc.communication import Pool

pool = Pool(key="path/to/own/keyfile", cert="path/to/own/certfile", ca_cert="path/to/cafile")
pool.add_http_server() # default port=443
pool.add_http_client("Client 1", "192.168.0.101", port=1234, cert="path/to/client/certfile")
```

Additional dependencies are required in order to load and compare certificates.
These can be installed by installing this package with the `tls` extra, e.g.
`pip install tno.mpc.communication[tls]`.

#### Adding clients

HTTP clients are identified by an address. The address can be an IP address, but
hostnames are also supported. For example, when communicating between two docker
containers on the same network, the address that is provided to
`pool.add_http_client` can either be the IP address of the client container or
the name of the client container.

### Sending, receiving messages

The library supports sending the following objects through the send and receive
methods:

- strings
- byte strings
- integers
- floats
- enum (partially, see [Serializing `Enum`](#serializing-enum))
- (nested) lists/tuples/dictionaries/numpy arrays containing any of the above.
  Combinations of these as well.

Under the hood [`ormsgpack`](https://pypi.org/project/ormsgpack) is used,
additional options can be activated using the `option` parameter (see,
https://github.com/aviramha/ormsgpack#option).

Messages can be sent both synchronously and asynchronously. If you do not know
which one to use, use the synchronous methods with `await`.

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

It is also possible to define serialization logic in custom classes and load the
logic into the commmunication module. An example is given below. We elaborate on
the requirements for such classes after the example.

```python
class SomeClass:

    def serialize(self, **kwargs: Any) -> Dict[str, Any]:
        # serialization logic that returns a dictionary

    @staticmethod
    def deserialize(obj: Dict[str, Any], **kwargs: Any) -> 'SomeClass':
        # deserialization logic that turns the dictionary produced
        # by serialize back into an object of type SomeClass
```

The class needs to contain a `serialize` method and a `deserialize` method. The
type annotation is necessary and validated by the communication module. Next to
this, the `**kwargs` argument is also necessary to allow for nested
(de)serialization that makes use of additional optional keyword arguments. It is
not necessary to use any of these optional keyword arguments. If one does not
make use of the `**kwargs` and also does not make a call to a subsequent
`Serialization.serialize()` or `Serialization.deserialize()`, it is advised to
write `**_kwargs: Any` instead of `**kwargs: Any`.

To add this logic to the communication module, you have to run the following
command at the start of your script. The `check_annotiations` parameter
determines whether the type hints of the serialization code and the presence of
a `**kwargs` parameter are checked. You should only change this to False _if you
are exactly sure of what you are doing_.

```python
from tno.mpc.communication import Serialization

if __name__ == "__main__":
   Serialization.set_serialization_logic(SomeClass, check_annotations=True)
```

### Serializing `Enum`

The `Serialization` module can serialize an `Enum` member; however, only the
value is serialized. The simplest way to work around this limitation is to
convert the deserialized object into an `Enum` member:

```python
from enum import Enum, auto


class TestEnum(Enum):
    A = auto()
    B = auto()

enum_obj = TestEnum.B

# Client 0
await pool.send("Client 1", enum_obj)

# Client 1
res = await pool.recv("Client 0")  # 2 <class 'int'>
enum_res = TestEnum(res)  # TestEnum.B <enum 'TestEnum'>
```

## Example code

Below is a very minimal example of how to use the library. It consists of two
instances, Alice and Bob, who greet each other. Here, Alice runs on localhost
and uses port 61001 for sending/receiving. Bob also runs on localhost, but uses
port 61002.

`alice.py`

```python
import asyncio

from tno.mpc.communication import Pool


async def async_main():
    # Create the pool for Alice.
    # Alice listens on port 61001 and adds Bob as client.
    pool = Pool()
    pool.add_http_server(addr="127.0.0.1", port=61001)
    pool.add_http_client("Bob", addr="127.0.0.1", port=61002)

    # Alice sends a message to Bob and waits for a reply.
    # She prints the reply and shuts down the pool
    await pool.send("Bob", "Hello Bob! This is Alice speaking.")
    reply = await pool.recv("Bob")
    print(reply)
    await pool.shutdown()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main())
```

`bob.py`

```python
import asyncio

from tno.mpc.communication import Pool


async def async_main():
    # Create the pool for Bob.
    # Bob listens on port 61002 and adds Alice as client.
    pool = Pool()
    pool.add_http_server(addr="127.0.0.1", port=61002)
    pool.add_http_client("Alice", addr="127.0.0.1", port=61001)

    # Bob waits for a message from Alice and prints it.
    # He replies and shuts down his pool instance.
    message = await pool.recv("Alice")
    print(message)
    await pool.send("Alice", "Hello back to you, Alice!")
    await pool.shutdown()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(async_main())
```

To run this example, run each of the files in a separate terminal window. Note
that if `alice.py` is started prior to `bob.py`, it will throw a
`ClientConnectorError`. Namely, Alice tries to send a message to port 61002,
which has not been opened by Bob yet. After starting `bob.py`, the error
disappears.

The outputs in the two terminals will be something similar to the following:

```bash
>>> python alice.py
2022-07-07 09:36:20,220 - tno.mpc.communication.httphandlers - INFO - Serving on 127.0.0.1:61001
2022-07-07 09:36:20,230 - tno.mpc.communication.httphandlers - INFO - Received message from 127.0.0.1:61002
Hello back to you, Bob!
2022-07-07 09:36:20,232 - tno.mpc.communication.httphandlers - INFO - HTTPServer: Shutting down server task
2022-07-07 09:36:20,232 - tno.mpc.communication.httphandlers - INFO - Server 127.0.0.1:61001 shutdown
```

```bash
>>> python bob.py
2022-07-07 09:36:16,915 - tno.mpc.communication.httphandlers - INFO - Serving on 127.0.0.1:61002
2022-07-07 09:36:20,223 - tno.mpc.communication.httphandlers - INFO - Received message from 127.0.0.1:61001
Hello Bob! This is Alice speaking.
2022-07-07 09:36:20,232 - tno.mpc.communication.httphandlers - INFO - HTTPServer: Shutting down server task
2022-07-07 09:36:20,256 - tno.mpc.communication.httphandlers - INFO - Server 127.0.0.1:61002 shutdown
```
