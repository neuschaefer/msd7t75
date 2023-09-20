# Flash modification recipes

Place your flash dump at `flash-dump.bin` and then just type `make` :-)

```
  flash-dump.bin                          original flash dump
    |   |    ../monitor/monitor.bin       monitor program
    |   |              v         |
    |   `---> flash-mon.bin      |        flash image with monitor as boot2
    |                            |
    |----> boot2-ecos.bin        v        original eCos-based boot2
    |         `----> boot2-ecos-mon.bin   eCos patched to jump into monitor instead of app
    v                  |
  flash-ecos-mon.bin <-'                  flash image with patched eCos
```
