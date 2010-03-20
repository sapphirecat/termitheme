all: import.py export.py

clean:
	touch rm-fodder.py
	rm *.py
	find . -name '*.py[co]' -exec rm '{}' \;

%.py: src/HEADER src/libtermitheme.py src/%.py
	cat $^ >$@
	chmod +x $@

.PHONY: all clean
