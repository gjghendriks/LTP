import spacy
import sys
import requests
import re
import copy
import csv
import platform
import os

# Load English tokenizer, tagger, parser, NER and word vectors
nlp = spacy.load("en")
url = 'https://www.wikidata.org/w/api.php' # URL for wikidata
# parameters to find an entity
entParams = {'action':'wbsearchentities', 'language':'en', 'format':'json', }		
# paramters to find a property
propParams = {'action':'wbsearchentities', 'language':'en', 'format':'json', 'type':'property'}
DEBUG = False		# debug is defaulted to false
TESTMODE = False 	# test mode is defaulted to false
ANSWERS = [] # list to keep track of all found answers
TOTAL = 0
CORRECT = 0

#class to store answers url and label together
class Answer:
	def __init__(self, item):
		for var in item :
			if(var == "item"):
				self.url = item[var]['value']
			elif(var == "itemLabel"):
				self.label = item[var]['value']

	def show(self):
		print(self.label , "\t\t" , self.url)


#used to print output only if the debug is on
def log(s):
	if(DEBUG):
		print(s)
		


def printexamples():
  print("""
Example questions are:
  What is the birth date of Dave Grohl?
  The birth date of Dave Grohl was when?
  What are the parts of guitar?
  What are the genres of tame impala?
  What is the birth name of Freddy mercury?
  What was the cause of death of Michael Jackson?
  What was the country of origin of intergalactic lovers?
  When was the date of death of mozart?
  What is the official website of Foals?
  What is the birth place of B. B. King?
""")

#When given some input, it links it to the closest WikiData potential synonym
def fixer(string):
	if string == 'die':
		new_string = 'death'
	elif string == 'release':
		new_string = 'publication'
	elif string == 'bear':
		new_string = 'birth'
	elif string == 'release':
		new_string = 'publication'
	elif string == 'marry':
		new_string = 'spouse'
	elif string == 'bury':
		new_string = 'burial'
	elif string.endswith('e'):
		new_string = string + 'r'
	else:
		new_string = string + 'er'
	return new_string

#Secondary version of analyze
def analyzeSecondary(result):
	k = ""
	
	for w in result:
		#Look for entities based on their main characteristics as the subjects of a sentence
		if w.pos_ == "PROPN" or ((w.ent_type_ == "PERSON" or w.ent_type_ == "ORG") and w.text != "'s"):
			subject=[]
			for d in w.subtree:
				if d.tag_ == "POS":
					continue
				subject.append(d.text)
	entParams['search'] = " ".join(subject)
	
	for w in result:
	
	# What is the X of Y// Who is the X of Y // When is the X of Y
	# What is X's Y // Who is X's Y // When is X's Y
		if w.lemma_ == 'when':
			k = 'date of '
		if w.lemma_ == 'where':
			k = 'place of '
		if w.pos_ == 'VERB':
			subject1=[]
			for d in w.subtree:
				if ((d.pos_ == 'NOUN' and d.nbor().tag_ == 'IN') or
					(d.pos_ == 'NOUN' and d.nbor(-1).tag_ == 'IN') or
					(d.pos_ == 'NOUN' and d.nbor().pos_ == 'NOUN') or
					(d.pos_ == 'NOUN' and d.nbor(-1).pos_ == 'NOUN') or
					(d.pos_ == 'NOUN' and d.nbor(-1).tag_ == 'POS') or
					(d.pos_ == 'NOUN' and d.nbor(-1).pos_ == 'ADJ') or
					(d.pos_ == 'ADJ')):
					subject1.append(d.lemma_)
				if d.tag_ == 'IN' and d.nbor().tag_ == 'NN':
					subject1.append(d.lemma_)
				if d.pos_ == 'VERB' and (d.lemma_ != 'be' and d.lemma_ != 'do'):
					subject1.append(k + fixer(d.lemma_))
	propParams['search'] = " ".join(subject1)
	
	
	# Searching for particular properties based on the query
	# (some properties need "special handling" with an if-statement,
	# since they can not be found via a simple search in the wikidata API):
	if propParams['search'] == "member":
		propParams['search'] = "has part"
	if propParams['search'] == "real name":
		propParams['search'] = "birth name"
	
	# Use the same method as before to find answers
	createQuery(entParams['search'] , propParams['search'] )
	



# creates and executes query
# for each entity and property it can find with the find function
def createQuery(ent, prop):
	ent = find(ent, entParams)
	prop = find(prop, propParams)
	if(ent and prop):
		for e in ent:
			for p in prop:
				query = "SELECT ?item ?itemLabel WHERE {wd:"+ str(e['id']) + " wdt:" + str(p['id']) + """ ?item.
				SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
				}"""
				log("\nGenerated following query: \n" + query)
				executeQuery(query)

#Checks for existing answers and returns 1 if there are duplicates and 0 if not
def answerExists(foundItem):
	for item in ANSWERS:
		for var in foundItem:
			if (var == "item") and (foundItem[var]['value'] == item.url):
				return 1
			elif (var == "itemLabel") and (foundItem[var]['value'] == item.label):
				return 1
			else:
				continue
	return 0
				

# executes a query
def executeQuery(q):
	SPARQLurl = 'https://query.wikidata.org/sparql'
	log("\n\nexecuting query . . .\n\n")
	data = requests.get(SPARQLurl, params={'query': q, 'format': 'json'}).json()
	if(data):
		for item in data['results']['bindings']:
			if not answerExists(item):
				ANSWERS.append(Answer(item))
	else:
		print("Found no results to query\nPlease try again\n")


#finds the first corresponding wikidata entity or property
#TODO use named entitys here ?
def find(string, params):
	params['search'] = string
	json = requests.get(url,params).json()
	#log(json['search'])
	if(json['search']):
		ent = (json['search'])
		for e in ent:
			if('description' in ent):
				log("{}\t{}\t{}".format(e['id'], e['label'],e['description']))
			else:
				log("{}\t{}".format(e['id'], e['label']))
		return ent 
	else:
		log("Found no result in wikidata for '" + string +  "'")
		return False


#returns the subject in question
# not used atm
def findSubject(question):
	for w in question:
		if w.dep_ == "nsubj":
			subject=[]
			for d in w.subtree:
				subject.append(d.text)

	return subject

# finds the noun phrases in question
# merges them
# returns the doc
def findNounPhrases(question):
	newdoc = copy.deepcopy(question)
	for noun_phrase in list(newdoc.noun_chunks):
		noun_phrase.merge(noun_phrase.root.tag_, noun_phrase.root.lemma_, noun_phrase.root.ent_type_)
	return newdoc
	
# Gijs' version of the analyze
# tries to analyze the question and construct a query
def analyze(question):
	subj = ""
	prop = ""
	# for each word/token look for the nsubj and pobj
	for token in question:
		#log(token.text, "\t", token.lemma_, "\t", token.pos_, "\t", token.tag_, "\t", token.dep_, "\t\t", " head:\t", token.head)
		log(token.text + "\t" + token.dep_)
		if(token.dep_ == "nsubj" ):
			prop = token.text
		if(token.dep_ == "pobj"):
			subj = token.text

	log("\n\nFound subj:" + subj + " and prop:" + prop + '\n\n')

	# update tokens to capture whole compound noun phrases
	nounquestion = findNounPhrases(question)
	for token in nounquestion:
		log(token.text)
		# if token is a subj and found within broader token, then subj = token
		if(isinstance(subj, str) and re.search(subj, token.text)):
			log("broadend match for subj from\t" + subj + "\tto\t" + token.text)
			subj = token
		if(isinstance(prop, str) and re.search(prop, token.text)):
			log("broadend match for prop from\t" + prop + "\tto\t" + token.text)
			prop = token
		
	# append longer compounds to the property
	# when "of" is included, stop until the subject.
	for token in nounquestion:
		if(token.head.tag_ == "IN" and token.head.head == prop and token != subj):
			proptext = prop.text + " " + token.head.text + " " + token.text


	#try to remove the "the" from property text
	try:
		proptext
	except NameError:
		proptext = prop.text
		proptext = re.sub('(the|The)', '', proptext)
		createQuery(subj.text, proptext)
	else:
		proptext = re.sub('(the|The)', '', proptext)
		createQuery(subj.text, proptext)

	return


# check for flags
if(len(sys.argv) > 1):
	# turn on debug output by the -d flag
	if any("-d" in s for s in sys.argv):
		DEBUG = True
		print("Debug mode is on")
	else:
		print("Debug mode is off")
	# turn on test mode when -t flag is found
	# debug is turned off
	if any("-t" in s for s in sys.argv):
		TESTMODE = True
		DEBUG = False
		print("Testing with test set")



if(not TESTMODE):
	printexamples()
	# search for line/question
	for line in sys.stdin:
		text = line.rstrip()						# grab line
		doc = nlp(text)								#analyse question


		# Analyze syntax using Gijs' method
		analyze(doc)
		
		#Analyse using secondary method
		
		analyzeSecondary(doc)
	
		for item in ANSWERS:
			item.show()
		ANSWERS.clear()

#testmode
else:
	#read in the question file here depending on platform
	if(platform.system() == "Linux"):
		filename = """../resources/all_questions_and_answers.tsv"""
	else:
		filename = """..\\resources\\all_questions_and_answers.tsv"""
	with open(filename) as tsvfile:
		reader = reader = csv.reader(tsvfile, delimiter='\t')
		# file contains
		#	row[0]: Question
		#	row[1]: URI
		#	row[2]: Answer
		# 	row[..]: more answers (check with len(row))
		questionCount = 0
		for row in reader:
			questionCount += 1
			if(questionCount > 10):					# set amount of questions you want to test here
				break;
			question = row[0]
			URI = row[1]

			doc = nlp(question)
			analyze(doc)
			for item in ANSWERS:
				if(item.url == URI):
					print(questionCount, " was correct!")
					CORRECT += 1

			print(questionCount, "was incorrect!")
			TOTAL += 1

		print("From the ", str(TOTAL), " questions, ", CORRECT, " where correct.")
