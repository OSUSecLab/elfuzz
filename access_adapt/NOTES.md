# Notes

When running on NSF ACCESS, after pulling the images, run

```bash
apptainer exec --no-mount bind-paths --cleanenv --writable-tmpfs elm_librsvg_24.09.sif bash
```

to enter the librsvg container. Then, run

```bash
cargo afl config --build
```

to rebuild the AFL++ runtime. Don't know why but otherwise you cannot run `cargo afl showmap`.

