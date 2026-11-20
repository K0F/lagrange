CC ?= gcc
CFLAGS ?= -O2 -Wall -Wextra
PROC_DIR ?= /home/kof/src/processing.h

all: lagrange_constellation.svg

lagrange_constellation.svg: lagrange.py
	./lagrange.py svg --out lagrange_constellation.svg

test:
	./lagrange.py status
	./lagrange.py plot --dry-run

clean:
	rm -f lagrange_constellation.svg /tmp/lagrange_*.svg

.PHONY: all test clean
