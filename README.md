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
[here](https://docs.pet.tno.nl/mpc/communication/5.0.4).

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

Note: The package specifies several additional optional dependency groups:

Functionality:

- `pytest`: Required for utilizing this package's pytest fixtures (see also [Test fixtures](https://raw.githubusercontent.com/TNO-MPC/communication/main/#test-fixtures))
- `tls`: Required if SSL is needed

Serialization support for third-party types:

- `bitarray`: Adds support for sending `bitarray` types
- `gmpy`: Adds support for sending various `gmpy2` types
- `numpy`: Adds support for sending `numpy` types
- `pandas`: Adds support for sending `pandas` types
- `tests`: Includes all optional libraries required to run the full test suite
- `torch`: Adds support for sending `torch` types through [`safetensors`](https://huggingface.co/docs/safetensors/index), thereby avoiding `pickle`. Deserialized tensors are stored in CPU memory (the [`pytorch` docs](https://pytorch.org/docs/stable/generated/torch.Tensor.cuda.html#torch.Tensor.cuda) explain how to store a copy in CUDA memory).

See [Sending and receiving messages](https://raw.githubusercontent.com/TNO-MPC/communication/main/#sending-and-receiving-messages) for more
information on the supported third party types.

## Usage

The communication module uses `async` functions for sending and receiving. If you are familiar
with the async module, you can skip to the [Creating a `Pool`](https://raw.githubusercontent.com/TNO-MPC/communication/main/#creating-a-pool) section.

### Introduction to `asyncio`

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

### Creating a `Pool`

Let's assume you want to implement a protocol with two parties, and you want
to use the `tno.mpc.communication` for communication between the two parties.
Each party will need to create a `Pool`, configure a `Communicator`, and
register the other party to the `Pool` and `Communicator`.
Once configured, the `Pool` can be used for communication.

If you're just starting out, you can choose to use plain `HTTP` (insecure). If
you want to secure your traffic, configure SSL in order to use `HTTPS`.

<details open>
<summary><b>Pool using HTTP</b></summary>

The example below is from the perspective of our first party, called
Alice. Alice sets up a `HttpCommunicator`, which starts a HTTP server and
provides it to the `Pool`. Alice then adds Bob and Charlie by specifying how to
connect to their communicators.

```python
# We create a "communicator" which deals with implementing networking for Alice.
# Alice needs to provide some information to set it up, i.e. the ip-address and
# port to which she wants to bind (and to receive traffic on).
communicator = HttpCommunicator(addr="localhost", port=80) # Configure the HTTP server of Alice
# The Pool provides a simple interface for sending and receiving things
pool = Pool("Alice", communicator)
# We add a client called "Bob" and provide configuration to setup the connection to Bob
pool.add_client("Bob", HttpConnection(addr="123.4.56.78", port=80))
```

</details>

<details>
<summary><b>Pool using HTTPS</b></summary>

In order to use SSL, the communicator must be given an SSLContext for both its
"client" part (i.e. the context used while sending HTTP requests) and its
"server" part (i.e. the context used by the HTTP Server). Below an example is
given that shows how to configure both contexts.

```python
from tno.mpc.communication import create_ssl_context

ALICE_KEY = "./src/tno/mpc/communication/test/tls_certs/party_0.pem"
ALICE_CERT = "./src/tno/mpc/communication/test/tls_certs/party_0.crt"
BOB_CERT = "./src/tno/mpc/communication/test/tls_certs/party_1.crt"
CA_CERT = "./src/tno/mpc/communication/test/tls_certs/ca-root.crt"

# SSL Configuration of Alice
ssl_server_context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
ssl_server_context.load_cert_chain(certfile=ALICE_CERT, keyfile=ALICE_KEY)
ssl_server_context.load_verify_locations(cafile=CA_CERT)
ssl_server_context.check_hostname = False # Testing certificates will no have the correct hostname
ssl_server_context.verify_mode = ssl.CERT_REQUIRED # In order to require mutual TLS, this MUST be set

ssl_client_context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH) # The ssl_client_context is _used_ by the client _to authenticate the server_.
ssl_client_context.load_cert_chain(certfile=BOB_CERT, keyfile=BOB_KEY)
ssl_client_context.load_verify_locations(cafile=CA_CERT)
ssl_client_context.check_hostname = False

# Alice
communicator = HttpCommunicator(
    addr="localhost",
    port=80,
    ssl_server_context=ssl_server_context,
    ssl_client_context=ssl_client_context
)
pool = Pool("Alice", communicator)

# We add a client called "Bob" and provide configuration to setup the connection to Bob
pool.add_client(
    "Bob",
    HttpConnection(
        addr="123.4.56.78",
        port=80,
        cert=BOB_CERT,  # The public certificate of Bob
    ),
)
```

</details>

<details>
<summary><b>Explanation of Pool and Communicator</b></summary>

A `Pool` represents a generic communication network. It exposes a simple
interface for sending and receiving messages and objects to other parties. It
takes care of serialization (turning objects into bytes) and buffering messages.

A `Pool` uses a `Communicator` which is a generic communication layer. It
implements the actual networking code which sends and receives bytes over the
network.

The `tno.mpc.communication` module includes one `Communicator`, namely the
`HttpCommunicator` which implements the network layer using the HTTP
protocol. Every party serves an HTTP server to which other parties can send HTTP
POST requests to communicate.

</details>

### Lifecycle Management

The `Pool` object has a lifecycle that needs to be managed. More specifically,
the `Communicator` has a lifecycle, which is managed through the `Pool`.

After creating a `Pool`, but before using it, one must initialize the `Pool`:

```python
await pool.initialize()
```

This calls the `Communicator.initialize()` method, which does the required
setup, which will differ depending on the implementation.

After one is done with using the `Pool`, be sure to call `Pool.shutdown()`:

```python
await pool.shutdown()
```

This ensures that messages queues are empties and the open connections are
gracefully closed. Furthermore, the `Pool` will log a summary of all network
traffic for benchmarking purposes.

Tip: Instead of manually managing this lifecycle, you can also use a context
manager if this fits your use-case, like so

```python
async with pool:
    # Do stuff
```

This will automatically call `pool.initialize()` and `pool.shutdown()`.

### Sending and receiving messages

The library supports sending the following objects through the send and receive methods:

- strings
- byte strings
- integers
- floats
- enum (partially, see [Serializing `Enum`](https://raw.githubusercontent.com/TNO-MPC/communication/main/#serializing-enum))
- (nested) lists/tuples/dictionaries/numpy arrays containing any of the above. Combinations of these as well.

Furthermore, types from several third party libraries are supported (note that the library must be installed for this to work):

- `bitarray` (class) from `bitarray` (library)
- various types from `gmpy2`
- `NDArray` from `numpy`
  - Do note that due to limitations with the serialization library
    (ormsgpack), numpy arrays are deserialized as nested list.
- `Dataframe` from `pandas` (requires `pyarrow`)

Under the hood [`ormsgpack`](https://pypi.org/project/ormsgpack) is used, additional options can be activated using the `option` parameter (see, https://github.com/aviramha/ormsgpack#option).

The following code demonstrates how to use a `Pool` to send and receive
messages.

```python
# Client 0
await pool.send("Client 1", "Hello!") # Synchronous send message (blocking)
# Client 1
res = await pool.recv("Client 0") # Receive message synchronously (blocking)
```

### Custom Message IDs

It is possible to set custom message IDs when sending and receiving
messages. This not only helps in debugging, but it also of importance in any
program that is slightly non-trivial.

When the sending and receiving of messages is not strictly ordered (such as when
using `asyncio.gather`), the automatic message IDs are not sufficient to
determine which message is being replied to.

```python
# Client 0
await pool.send("Client 1", "Hello!", "id1")

# Client 1
res = await pool.recv("Client 0", "id1") # Will only return messages with `msg_id == "id1"`
```

### Custom serialization logic

It is also possible to define serialization logic in custom classes and load the logic into the commmunication module. An example is given below. We elaborate on the requirements for such classes after the example.

```python
from tno.mpc.communication.packers import (
    DeserializerOpts,
    SerializerOpts,
)

class SomeClass:
    def serialize(self, opts: SerializerOpts) -> dict[str, Any]:
        # serialization logic that returns a dictionary

    @staticmethod
    def deserialize(
        obj: dict[str, int], opts: SerializerOpts
    ) -> 'SomeClass':
        # deserialization logic that turns the dictionary produced
        # by serialize back into an object of type SomeClass
```

The class needs to contain a `serialize` method and a `deserialize` method. The type annotation is necessary and validated by the
communication module.
Next to this, the `opts` argument is also necessary to allow for nested (de)serialization that
makes use of additional options. Most implementers will only need to pass `opts` into `Serializer.transform_into_nonnative` if they delegate part of the deserialization logic to the `Serializer` (see e.g. `tno.mpc.communication.serializer_plugins.tuple.tuple_deserialize`) or they won't need to use `opts` at all.

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

from tno.mpc.communication import (
    Pool,
    HttpCommunicator,
)


async def async_main() -> None:
    # Create the pool for Alice and add Bob as client.
    communicator = HttpCommunicator(addr="localhost", port=61001)
    pool = Pool("Alice", communicator)
    pool.add_client("Bob", HttpConnection(addr="localhost", port=61002))

    with pool:
        # Alice sends a message to Bob and waits for a reply.
        # She prints the reply and shuts down the pool
        await pool.send("Bob", "Hello Bob! This is Alice speaking.")
        reply = await pool.recv("Bob")
        print(reply)


if __name__ == "__main__":
    asyncio.run(async_main())
```

`bob.py`

```python
import asyncio

from tno.mpc.communication import (
    Pool,
    HttpCommunicator,
)


async def async_main() -> None:
    # Create the pool for Bob and add Alice as client.
    communicator = HttpCommunicator(addr="localhost", port=61002)
    pool = Pool("Bob", communicator)
    pool.add_client("Alice", HttpConnection(addr="localhost", port=61001))

    async with pool:
        # Bob waits for a message from Alice and prints it.
        # He replies and shuts down his pool instance.
        message = await pool.recv("Alice")
        print(message)
        await pool.send("Alice", "Hello back to you, Alice!"))


if __name__ == "__main__":
    asyncio.run(async_main())
```

To run this example, run each of the files in a separate terminal window.
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

The `tno.mpc.communication[pytest]` package exports several pytest fixtures as pytest plugins to facilitate the user in testing with pool objects. The fixtures take care of all configuration and clean-up of the pool objects so that you don't have to worry about that.

For integration testing, you can use the `http_pool_*` fixtures which are
properly implemented using `HttpCommunicator` and thus perform networking.

```python
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

For most unit tests, it may suffice to use a mock implementation of a `Pool`
that works as expected but doesn't actually use networking. Because of this,
it's much faster. To use the mock pools, simply request `mock_pool_duo` instead
of `http_pool_duo` and `mock_pool_group_factory` instead of
`http_pool_group_factory`.

### Fixture scope

The scope of our fixtures defaults to the default fixture loop scope of `pytest-asyncio`, which can be set by configuring `asyncio_default_fixture_loop_scope`. Alternatively, our fixtures' scope can be set dynamically through the `--fixture-pool-scope` [option to pytest](https://docs.pytest.org/en/7.1.x/reference/reference.html#configuration-options). The scope provided through `--fixture-pool-scope` cannot be larger than the scope of `asyncio_default_fixture_loop_scope`.

_IMPORTANT: `pytest-asyncio` differentiates between two loop scopes: `asyncio_default_fixture_loop_scope` and `asyncio_default_fixture_loop_scope`. Both should have the same value for our fixtures to work properly!_

We advise to configure a larger scope (e.g. `"session"`, `"package"` or `"module"`) when possible to reduce test set-up and teardown time. Example `pyproject.toml` configuration:

```toml
[tool.pytest.ini_options]
asyncio_default_fixture_loop_scope = "session"
asyncio_default_test_loop_scope = "session"
```

## Migrating from v4 to v5

### Instantiation of `Pool`

The main change is the introduction of the `Communicator` through which the
networking is configured. The following example shows how to rewrite your
current code:

```python
# --+ Old +---------------------------------------------------------------------
pool = Pool()
pool.add_http_server(addr="localhost", port=61001)
pool.add_http_client("Bob", addr="localhost", port=61002)

# --+ New +---------------------------------------------------------------------
communicator = HttpCommunicator(addr="localhost", port=61001)
pool = Pool("Alice", communicator) # It is now required to specify a Pool's own name
pool.add_client("Bob", HttpConnection(addr="localhost", port=61002)) # Clients must be added before initialization
await pool.initialize() # It is now required to initialize a pool. We recommend using the contextmanager syntax instead (`async with pool`)
```

Furthermore, the `Pool.asend`, `Pool.arecv` and `Pool.async_broadcast` methods
have been removed, due to the problems that they caused and the complexity that
they introduce. Use the `async` methods `Pool.send`, `Pool.recv` and
`Pool.broadcast` methods instead.

### Asynchronous operations removed

The `Pool.asend`, `Pool.arecv` and `Pool.async_broadcast` methods have been
removed, as they were rarely used.

If you wish to reconstruct the behaviour of `Pool.asend`, you can do the
following:

```python
task = asyncio.create_task(Pool.send("Bob", "Hello!"))
```

Be sure to keep a reference to the task and properly await or cancel it before
shutting down the pool to avoid dangling coroutines.

### Serialization

The interface of `SupportsSerialization` has been slightly changed to provide
better typing.

```python
# --+ Old +---------------------------------------------------------------------
class SomeClass:
    def serialize(self, **kwargs: Any) -> dict[str, Any]: ...
    def deserialize(self, obj: dict[str, Any], **kwargs: Any) -> 'SomeClass': ...

# --+ New +---------------------------------------------------------------------
from tno.mpc.communication.packers.serialization import SerializerOpts, DeserializerOpts

class SomeClass:
    def serialize(self, opts: SerializerOpts) -> dict[str, Any]: ...

    @staticmethod
    def deserialize(obj: dict[str, int], opts: DeserializerOpts) -> 'SomeClass': ...
```

### Miscellaneous

- The extra dependency group `gmpy2` has renamed to `gmpy`.
