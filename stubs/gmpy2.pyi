from __future__ import annotations

class mpz(int):
    def __new__(self, x: str | bytes | bytearray | int, base: int = ...) -> mpz: ...

class xmpz(int):
    def __new__(self, x: str | bytes | bytearray | int, base: int = ...) -> xmpz: ...

class mpq:
    def __new__(self, n: str | int, m: int = ..., base: int = ...) -> mpq: ...

class mpfr:
    def __new__(
        self, n: str | float, precision: int = ..., base: int = ...
    ) -> mpfr: ...

class mpc(complex):
    def __new__(
        self,
        c: str | complex | int | tuple[int, int],
        i: int = ...,
        precision: int = ...,
        base: int = ...,
    ) -> mpc: ...

def to_binary(a: xmpz | mpz | mpfr | mpq | mpc) -> bytes: ...
def from_binary(b: bytes) -> xmpz | mpz | mpfr | mpq | mpc: ...
