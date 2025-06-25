import logging
import secrets
from sys import argv
from time import time
from pydantic import BaseModel

import pyscrypt  # type: ignore
from tierkreis.worker import Worker


worker = Worker("cpu_worker")
logger = logging.getLogger(__name__)


class EncryptionResult(BaseModel):
    ciphertext: str
    time_taken: float


@worker.function()
def encrypt(plaintext: str, work_factor: int) -> EncryptionResult:
    start_time = time()
    salt = secrets.token_bytes(32)
    ciphertext = pyscrypt.hash(  # type:ignore
        password=plaintext.encode(), salt=salt, N=work_factor, r=1, p=1, dkLen=32
    )
    logger.error(ciphertext)
    time_taken = time() - start_time

    return EncryptionResult(ciphertext=str(ciphertext), time_taken=time_taken)


if __name__ == "__main__":
    worker.app(argv)
