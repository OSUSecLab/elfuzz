# This file provides `generate_python3` to generate random Python 3 programs as inputs to a fuzzer. The fuzzer will then use the generated Python programs to fuzz CPython 3.
# The `generate_python3` function is the only part of the file that will be used. Please DO NOT DO NOT DO NOT DO NOT DO NOT ADD ANY OTHER FUNCTIONS or code blocks.
# We currently have a premitive version of `generate_python3 that may generate Python 3 programs that are gramatically/semantically incorrect or trivial. 
# You need to refine and repair it to gnerate DIVERSE DIVERSE DIVERSE AND SEMANTICALLY CORRECT Python 3 programs.
# Programmers who complete this task well will win a $1,000,000 award, but those who add functions other than `generate_python3` will have a $1,000 fine deducted from their wages.

from typing import BinaryIO
from io import TextIOBase

class WrappedTextWriter(TextIOBase):
    def __init__(self, binary_io: BinaryIO) -> None:
        self.__underlying = binary_io
    
    '''
    Write the text to the underlying binary stream after encoding it to UTF-8.
    '''
    def write_utf8(self, s: str) -> int:
        return self.__underlying.write(s.encode('utf-8'))
    
    '''
    Write the text to the underlying binary stream after encoding it to UTF-8 and appending a newline character.
    '''
    def write_utf8_line(self, s: str) -> int:
        return self.write_utf8(s + '\n')
    
    '''
    Write raw bytes to the underlying binary stream.
    '''
    def write(self, b: bytes) -> int:
        return self.__underlying.write(b)

class WrappedTextReader(TextIOBase):
    def __init__(self, binary_io: BinaryIO) -> None:
        self.__underlying = binary_io
    
    '''
    Directly read bytes from the underlying binary stream without decoding them.
    '''
    def read(self, size: int = -1) -> bytes:
        return self.__underlying.read(size)
    
    '''
    Read the specified number of characters from the underlying binary stream and decode them to UTF-8.
    We currently assume that all the characters are within the ASCII range.
    '''
    def read_utf8(self, char_count: int) -> str:
        b = bytes(map(lambda c: c % 0x80, self.__underlying.read(char_count)))
        return b.decode('utf-8')

''' 
Generate DIVERSE AND SEMANTICALLY CORRECT Python 3 programs and write it to `output`.
`rng` is a random number generator that can be used to make decisions during the generation process.
'''
def generate_python3(rng: BinaryIO, output: BinaryIO):
    # `wrapped_output` is a wrapper that allows writing text to the underlying binary output stream.
    # You should always write to `wrapped_output` instead of the raw `output`
    wrapped_output = WrappedTextWriter(output)
    
    # `wrapped_rng` is a wrapper that allows reading text from the underlying binary random number generator stream.
    # It provides the `read_utf8` method to read the specified number of characters and decode them to UTF-8, but
    # it also provides the `read` method to read raw bytes.
    wrapped_rng = WrappedTextReader(rng)
    
    random_len = int(wrapped_rng.read(1))
    random_text = wrapped_rng.read_utf8(random_len)
    wrapped_output.write_utf8(random_text)
    