from typing import BinaryIO

def preprocess(rng: BinaryIO, out: BinaryIO):
    rand_byte = rng.read(1)
    out.write(rand_byte + b'\n') # Use the random control flags of the fuzzer