import secrets
from sys import argv
from time import time
from typing import NamedTuple

from tierkreis.controller.data.models import portmapping
import pyscrypt  # type: ignore
from tierkreis import Worker

worker = Worker("auth_worker")


@portmapping
class EncryptionResult(NamedTuple):
    ciphertext: str
    time_taken: float


@worker.task()
def encrypt(plaintext: str, work_factor: int) -> EncryptionResult:
    start_time = time()
    salt = secrets.token_bytes(32)
    ciphertext = pyscrypt.hash(  # type:ignore
        password=plaintext.encode(), salt=salt, N=work_factor, r=1, p=1, dkLen=32
    )
    time_taken = time() - start_time

    return EncryptionResult(ciphertext=str(ciphertext), time_taken=time_taken)


if __name__ == "__main__":
    worker.app(argv)
