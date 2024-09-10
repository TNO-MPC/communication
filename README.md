# TNO PET Lab - secure Multi-Party Computation (MPC) - Communication

Generic communication module for pool-based communication intended for
use in the Multi-Party Computation modules of the PET Lab.

### PET Lab

The TNO PET Lab consists of generic software components, procedures, and functionalities developed and maintained on a regular basis to facilitate and aid in the development of PET solutions. The lab is a cross-project initiative allowing us to integrate and reuse previously developed PET functionalities to boost the development of new protocols and solutions.

The package `tno.mpc.communication` is part of the [TNO Python Toolbox](https://github.com/TNO-PET).

_Limitations in (end-)use: the content of this software package may solely be used for applications that comply with international export control laws._  
_This implementation of cryptographic software has not been audited. Use at your own risk._

## Documentation

Documentation of the `tno.mpc.communication` package can be found
[here](https://docs.pet.tno.nl/mpc/communication/4.11.2).

## Install

Easily install the `tno.mpc.communication` package using `pip`:

```console
$ python -m pip install tno.mpc.communication
```

_Note:_ If you are cloning the repository and wish to edit the source code, be
sure to install the package in editable mode:

```console
$ python -m pip install -e 'tno.mpc.communication'
```

If you wish to run the tests you can use:

```console
$ python -m pip install 'tno.mpc.communication[tests]'
```

Note: The package specifies several optional dependency groups:

- `bitarray`: Adds support for sending `bitarray` types
- `gmpy`: Adds support for sending various `gmpy2` types
- `numpy`: Adds support for sending `numpy` types
- `pandas`: Adds support for sending `pandas` types
- `tests`: Includes all optional libraries required to run the full test suite
- `tls`: Required if SSL is needed
- `torch`: Adds support for sending `torch` types through [`safetensors`](https://huggingface.co/docs/safetensors/index), thereby avoiding `pickle`. Deserialized tensors are stored in CPU memory (the [`pytorch` docs](https://pytorch.org/docs/stable/generated/torch.Tensor.cuda.html#torch.Tensor.cuda) explain how to store a copy in CUDA memory).

See [sending, receiving messages](#sending-receiving-messages) for more
information on the supported third party types.
Optional dependencies can be installed by specifying their names in brackets
after the package name, e.g. when using `pip install`, use `pip install
tno.mpc.communication[extra1,extra2]` to install the groups `extra1` and
`extra2`.

## Usage

The communication module uses `async` functions for sending and receiving. If you are familiar
with the async module, you can skip to the `Pools` section.

### Async explanation

When `async` functions are called, they return what is called a _coroutine_.
This is a special kind of object, because it is basically a promise that the code will be run and
a result will be given once the code has been ran.

Async methods are defined using `async def`, which tells
python that it should return a coroutine. `asyncio.run` can run the coroutine, but should only be
called from the top-level. The advertised approach to use coroutines is as follows:

```python
import asyncio

async def add(a: int, b: int) -> int:
    return a + b

async def main():
    a, b = 1, 2
    result = await add(a, b)  # result is set once the coroutine add(a, b) has finished. other code may run in the meantime.
    print(result)  # this prints 3

if __name__ == "__main__":
    asyncio.run(main())
```

Here, the `main` function _awaits_ the result of the coroutine. As a consequence, the `main`
function itself is a coroutine. We let `asyncio` do the heavy lifting by calling it from the
top-level.

### Pools

A `Pool` represents a network. A Pool contains a server, which listens for incoming messages from
other parties in the network, and clients for each other party in the network. These clients are
called upon when we want to send or receive messages.

It is also possible to use and initialize the pool without taking care of the event loop
yourself, in that case the template below can be ignored and the examples can be used as one
would regularly do. (An event loop is however still needed when using the `await` keyword or
when calling an `async` function.)

### Template

Below you can find a template for using `Pool`.

```python
import asyncio

from tno.mpc.communication import Pool

async def async_main():
    pool = Pool()
    # ...

if __name__ == "__main__":
    asyncio.run(async_main())
```

### Pool initialization

The following logic works both in regular functions and `async` functions.

#### Without SSL/TLS (do not use in production)

The following snippet will start a HTTP server and define its clients. Clients are configured on both the sending and the receiving side. The sending side needs to know who to send a message to. The receiving side needs to know who it receives a message from for further handling.

By default the `Pool` object uses the origin IP and port to identify the client. However, a more secure and robust identification through SSL/TLS certificates is also supported and described in section [With SSL/TLS (SSL/TLS certificate as client identifier)](#with-ssltls-ssltls-certificate-as-client-identifier).

```python
from tno.mpc.communication import Pool

pool = Pool()
pool.add_http_server() # default port=80
pool.add_http_client("Client 1", "192.168.0.101") # default port=80
pool.add_http_client("Client 2", "192.168.0.102", port=1234)
```

#### With SSL/TLS

A more secure connection can be achieved by using SSL/TLS. A `Pool` object can be initialized with paths to key, certificate and CA certificate files that are passed as arguments to a [`ssl.SSLContext`](https://docs.python.org/3/library/ssl.html#ssl.SSLContext) object. More information on the expected files can be found in the `Pool.__init__` docstring and the [`ssl` documentation](https://docs.python.org/3/library/ssl.html#certificates).

```python
from tno.mpc.communication import Pool

pool = Pool(key="path/to/keyfile", cert="path/to/certfile", ca_cert="path/to/cafile")
pool.add_http_server() # default port=443
pool.add_http_client("Client 1", "192.168.0.101") # default port=443
pool.add_http_client("Client 2", "192.168.0.102", port=1234)
```

We do not pose constraints on the certificates that you use in the protocol. However, your organisation most likely poses minimal security requirements on the certificates used. As such we do not advocate a method for generating certificates but rather suggest to contact your system administrator for obtaining certificates.

#### With SSL/TLS (SSL/TLS certificate as client identifier)

This approach does not use the origin of a message (HTTP request) as identifier of a party, but rather the SSL/TLS certificate of that party. This requires a priori exchange of the certificates, but is more robust to more complex (docker) network stacks, proxies, port forwarding, load balancers, IP spoofing, etc.

More specifically, we assume that a certificate has a unique combination of issuer Common Name and S/N and use these components to create a HTTP client identifier. Our assumption is based on the fact that we trust the issuer (TSL assumption) and that the issuer is supposed to hand out end-user certificates with different serial numbers.

```python
from tno.mpc.communication import Pool

pool = Pool(key="path/to/own/keyfile", cert="path/to/own/certfile", ca_cert="path/to/cafile")
pool.add_http_server() # default port=443
pool.add_http_client("Client 1", "192.168.0.101", port=1234, cert="path/to/client/certfile")
```

Additional dependencies are required in order to load and compare certificates. These can be installed by installing this package with the `tls` extra, e.g. `pip install tno.mpc.communication[tls]`.

#### Adding clients

HTTP clients are identified by an address. The address can be an IP address, but hostnames are also supported. For example, when communicating between two docker containers on the same network, the address that is provided to `pool.add_http_client` can either be the IP address of the client container or the name of the client container.

### Sending, receiving messages

The library supports sending the following objects through the send and receive methods:

- strings
- byte strings
- integers
- floats
- enum (partially, see [Serializing `Enum`](#serializing-enum))
- (nested) lists/tuples/dictionaries/numpy arrays containing any of the above. Combinations of these as well.

Furthermore, types from several third party libraries are supported (note that the library must be installed for this to work):

- `bitarray` (class) from `bitarray` (library)
- various types from `gmpy2`
- `NDArray` from `numpy`
- `Dataframe` from `pandas` (requires `pyarrow`)

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
You should change this to `False` _only if you are exactly sure of what you are doing_.

```python
from tno.mpc.communication import RepetitionError, Serialization

try:
    Serialization.register_class(SomeClass, check_annotations=True)
except RepetitionError:
    pass
```

### Serializing `Enum`

The `Serialization` module can serialize an `Enum` member; however, only the value is serialized. The simplest way to work around this limitation is to convert the deserialized object into an `Enum` member:

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

Below is a very minimal example of how to use the library.
It consists of two instances, Alice and Bob, who greet each other.
Here, Alice runs on localhost and uses port 61001 for sending/receiving.
Bob also runs on localhost, but uses port 61002.

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
    asyncio.run(async_main())
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
    asyncio.run(async_main())
```

To run this example, run each of the files in a separate terminal window.
Note that if `alice.py` is started prior to `bob.py`, it will throw a `ClientConnectorError`.
Namely, Alice tries to send a message to port 61002, which has not been opened by Bob yet.
After starting `bob.py`, the error disappears.

The outputs in the two terminals will be the following:

```bash
>>> python bob.py
Hello Bob! This is Alice speaking.
```

```bash
>>> python alice.py
Hello back to you, Alice!
```

To get more information of what happens under the hood, you can import `logging` in both files and
add the line `logging.basicConfig(level=logging.INFO)` before `asyncio.run`. If you want to know even more, you can set the `level` to `logging.DEBUG`.

## Test fixtures

The `tno.mpc.communication` package exports several pytest fixtures as pytest plugins to facilitate the user in testing with pool objects. The fixtures take care of all configuration and clean-up of the pool objects so that you don't have to worry about that.

Usage:

```py
# test_my_module.py
import pytest
from typing import Callable
from tno.mpc.communication import Pool

def test_with_two_pools(http_pool_duo: tuple[Pool, Pool]) -> None:
    sender, receiver = http_pool_duo
    # ... your code

def test_with_three_pools(http_pool_trio: tuple[Pool, Pool, Pool]) -> None:
    alice, bob, charlie = http_pool_trio
    # ... your code

@pytest.mark.parameterize("n_players", (2, 3, 4))
def test_with_variable_pools(
    n_players: int,
    http_pool_group_factory: Callable[[int], tuple[Pool, ...]],
) -> None:
    pools = http_pool_group_factory(n_players)
    # ... your code
```

### Fixture scope

The scope of the fixtures can be set dynamically through the `--fixture-pool-scope` [option to pytest](https://docs.pytest.org/en/7.1.x/reference/reference.html#configuration-options). _Note that this will also change the scope of the global `event_loop` fixture that is provided by `pytest-asyncio`._ By default, in line with `pytest_asyncio`, the scope of all our fixtures is `"function"`. We advise to configure a larger scope (e.g. `"session"`, `"package"` or `"module"`) when possible to reduce test set-up and teardown time.

Our fixtures pass `True` to the `port_reuse` argument of `aiohttp.web.TCPSite`. Their [documentation](https://docs.aiohttp.org/en/stable/web_reference.html?highlight=reuse_port#aiohttp.web.TCPSite) states that this option is not supported on Windows (outside of WSL). If you experience any issues, please disable the plugin by adding `-p no:pytest_tno.tno.mpc.communication.pytest_pool_fixtures` to your pytest configuration. Note that without `port_reuse` the tests may crash, as the test may try to bind to ports which may not have been freed by the operating system. For more reliable testing, run the tests on a WSL / Linux platform.
