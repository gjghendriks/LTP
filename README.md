# LTP

## Dependencies
The program needs spacy and the model en_core_web_md to be installed. Here is how:
```
pip install --user spacy
pip install --user link en_core_web_md
python -m spacy link en_core_web_md en
```

## Running the program
This program can be run with the following command
```
python .\scripts\combined.py
```

The program accepts questions on their own, but also accepts them in the required format. On Linux the program can be run like this:
```
python .\scripts\combined.py < text_questions.txt
```

## Command line options
```
	-d 		Turn on debug output
	-t		Turn on test mode
```
	
## About
This is a project for the course Language Technology Practical at the RuG.
George, Stratos and Gijs (s2410540)

