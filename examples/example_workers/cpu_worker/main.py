import secrets
from sys import argv
from time import time
from pydantic import BaseModel

import pyscrypt  # type: ignore
from tierkreis.worker import Worker


worker = Worker("cpu_worker")


class EncryptionResult(BaseModel):
    ciphertext: bytes
    time_taken: float


@worker.function()
def encrypt(plaintext: str, work_factor: int) -> EncryptionResult:
    start_time = time()
    salt = secrets.token_bytes(32)
    ciphertext = pyscrypt.hash(  # type:ignore
        password=plaintext, salt=salt, N=work_factor, r=1, p=1, dkLen=32
    )
    time_taken = time() - start_time
    return EncryptionResult(ciphertext=ciphertext, time_taken=time_taken)


if __name__ == "__main__":
    worker.app(argv)
