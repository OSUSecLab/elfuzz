extern fn fuzz(data: &[u8]) -> bool;

//$main_begin$
#[macro_use]
extern crate afl;

use std::fs;
use std::env;

fn main() {
    fuzz!(|data: &[u8]| {fuzz(data);})
}
//$main_end$
