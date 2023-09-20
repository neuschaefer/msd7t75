all: flash-mon.bin flash-ecos-mon.bin flash-ecos-mon-double.bin

../monitor/monitor.bin:
	+$(MAKE) -C ../monitor

monitor.bin: ../monitor/monitor.bin
	cp ../monitor/monitor.bin .

boot2-ecos.bin: flash-dump.bin
	../tools/extract-boot2.py $< $@

boot2-ecos-mon.bin: boot2-ecos.bin monitor.bin
	cp $< $@
	../tools/patch-ecos.py $@ monitor.bin

flash-mon.bin: flash-dump.bin monitor.bin
	cp $< $@
	@chmod +w $@
	../tools/inject-boot2.py $@ monitor.bin

flash-ecos-mon.bin: flash-dump.bin boot2-ecos-mon.bin
	cp $< $@
	@chmod +w $@
	../tools/inject-boot2.py $@ boot2-ecos-mon.bin

flash-ecos-mon-double.bin: flash-dump.bin boot2-ecos-mon.bin
	cp $< $@
	@chmod +w $@
	../tools/inject-boot2.py $@ boot2-ecos-mon.bin boot2-ecos-mon.bin

clean:
	rm -f monitor.bin boot2-ecos.bin boot2-ecos-mon.bin flash-mon.bin flash-ecos-mon.bin

.PHONY: clean
