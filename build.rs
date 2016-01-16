use std::fs;
use std::ffi::OsStr;
extern crate gcc;

fn main() {
    let mut cfg = gcc::Config::new();
    cfg.include("libvex-tob/VEX/pub")
       .include("libvex-tob/VEX/priv")
       //.opt_level(3)
       .debug(true);
    for filename in fs::read_dir("libvex-tob/VEX/priv").unwrap(){
        let filename = filename.unwrap().path();
        if filename.extension() == Some(&OsStr::new("c")) {
            cfg.file(filename);
        }
    }
    cfg.compile("libvex.a");
}
