all: import.py export.py

clean:
	rm *.py

%.py: src/HEADER src/theminator.py src/%.py
	cat $^ >$@
	chmod +x $@

.PHONY: all clean
