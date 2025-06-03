from typing import BinaryIO

def preprocess(rng: BinaryIO, out: BinaryIO):
    out.write(rng.read(4))