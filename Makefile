DIRS=monitor

all: $(DIRS)

$(DIRS):
	+$(MAKE) -C $@

.PHONY: $(DIRS)
