from typing import BinaryIO

def preprocess(rng: BinaryIO, out: BinaryIO):
    out.write(b'\x02' + rng.read(1))