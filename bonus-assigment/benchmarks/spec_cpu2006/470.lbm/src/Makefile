
SOURCES= lbm.c main.c

CC=arm-linux-gnueabihf-gcc
CFLAGS=-O0
COMP_FLAGS=-DSPEC_CPU -DNDEBUG -static

all: $(SOURCES)
	$(CC) $(COMP_FLAGS) $(SOURCES) $(CFLAGS) -o speclibm -lm



