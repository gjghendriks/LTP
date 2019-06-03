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
entParams = {'action':'wbsearchentities', 'language':'en', 'format':'json' }		
# paramters to find a property
propParams = {'action':'wbsearchentities', 'language':'en', 'format':'json', 'type':'property'}
DEBUG = False		# debug is defaulted to false
TESTMODE = False 	# test mode is defaulted to false
ANSWERS = [] 		# list to keep track of all found answers
TOTAL = 0			# keeps track of how many questions are asked
CORRECT = 0			# keeps track of how many questions are answered correctly
TESTAMOUNT = 805	# max amount of questions that will be tested in test mode

#class to store answers url and label together
class Answer:
	def __init__(self, labels, url):
		self.label = labels
		self.url = url

	def show(self):
		print(self.url, end = "\t")
		for item in self.label:
			print(item, end = "\t")
		print("")
		


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
	elif string == 'come':
		new_string = 'origin'
	elif string == 'found':
		new_string = 'foundation'
	elif string.endswith('e'):
		new_string = string + 'r'
	else:
		new_string = string + 'er'
	return new_string

#Secondary version of analyze
def analyzeSecondary(result):
	log("Secondary analyze")
	k = ""
	entityString = ""
	propertyString = ""
	subject = []
	subject1 = []
	ignorable_adjectives = ['many', 'long']
	
	if result[0].lemma_ == "be" or result[0].lemma_ == "do":
			yesNoQuery = True

	#Look for entities based on their main characteristics as the subjects of a sentence
	for w in result:
		if ((w.pos_ == "PROPN" or
			# What are the parts of a guitar? (guitar = pobj)
			(w.dep_ == "pobj" and w.nbor().pos_ != 'PROPN' and w.pos_ != "ADV" and w.pos_ != "PRON" and (w.nbor().tag_ != 'IN' and w.nbor(-1).tag_ != 'IN')) or
			# How many strings does a violin have? (violin = nsubj)
			(w.dep_ == "nsubj" and w.nbor().pos_ != 'PROPN' and w.pos_ != "PRON" and w.pos_ != "DET" and (w.nbor().tag_ != 'IN' and w.nbor(-1).tag_ != 'IN' and w.nbor(-1).pos_ != 'NOUN' and w.nbor(-1).pos_ != 'ADJ')) or
			(w.ent_type_ == "PERSON" or w.ent_type_ == "ORG" or w.ent_type_ == "WORK_OF_ART")) and w.tag_ != "POS"):
			subject.append(w.text)
	entityString = " ".join(subject)

	
	#Look for property
	for d in result:	
	# What is the X of Y// Who is the X of Y // When is the X of Y
	# What is X's Y // Who is X's Y // When is X's Y
		if d.lemma_ == 'when':
			k = 'date of '
		if d.lemma_ == 'where':
			k = 'place of '

		if (d.lemma_ == 'how' and d.nbor().lemma_ == 'many'):
			k = 'number of '
		if (d.lemma_ == 'how' and d.nbor().lemma_ == 'long'):
			subject1.append('duration')

		if (d.text != entityString):
			if ((d.pos_ == 'NOUN' and d.nbor().tag_ == 'IN') or
				(d.pos_ == 'NOUN' and d.nbor(-1).tag_ == 'IN') or
				(d.pos_ == 'NOUN' and d.nbor().pos_ == 'NOUN') or
				(d.pos_ == 'NOUN' and d.nbor(-1).pos_ == 'NOUN') or
				(d.pos_ == 'NOUN' and d.nbor(-1).tag_ == 'POS') or
				(d.pos_ == 'NOUN' and d.nbor(-1).pos_ == 'ADJ') or
				(d.tag_ == 'IN' and d.nbor().tag_ == 'NN' and d.nbor().text != entityString) or
				(d.pos_ == 'ADJ' and d.lemma_ not in ignorable_adjectives and d.text not in entityString)):
					if d.text not in k:
						subject1.append(k + d.text)
			if d.dep_ == 'ROOT' and (d.lemma_ != 'be' and d.lemma_ != 'do' and d.lemma_ != 'have'):
				subject1.append(k + fixer(d.lemma_))
	propertyString = " ".join(subject1)
	
	
	# Searching for particular properties based on the query
	# (some properties need "special handling" with an if-statement,
	# since they can not be found via a simple search in the wikidata API):
	if propertyString == "members":
		propertyString = "has part"
	if propertyString == "real name":
		propertyString = "birth name"
	
	# If an entity was mistakenly fethced in the property string
	# find it, fetch it and fix the property string
	if not entityString:
		tempEntity = nlp(propertyString)
		for word in tempEntity:
			if word.dep_ == 'ROOT':
				entityString = word.text
	
	# If a property was mistakenly fethced in the entity string
	# find it, fetch it and fix the entity string
	if not propertyString:
		tempProperty = nlp(entityString)
		for word in tempProperty:
			if word.pos_ == ('NOUN' or 'PROPN') and word.dep_ != 'ROOT':
				propertyString = word.text
	
	if entityString in propertyString:
		propertyString = propertyString.replace(entityString, '')
		
	if propertyString in entityString:
		entityString = entityString.replace(propertyString, '')
	
	# Use the same method as before to find answers
	if (entityString and propertyString):
		createQuery(entityString, propertyString)
	else:
		log("Did not find entityString and propertyString")
	



# creates and executes query
# for each entity and property it can find with the find function
# create a query and execute said query
def createQuery(ent, prop):
	ent = find(ent, entParams)
	prop = find(prop, propParams)
	if(ent and prop):
		for e in ent:
			for p in prop:
				query = "SELECT ?item ?itemLabel WHERE {wd:"+ str(e['id']) + " wdt:" + str(p['id']) + """ ?item.
				SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
				}"""
				log("\nGenerated following query:")
				log(e['label'])
				log(p['label'])
				log(query)
				executeQuery(query, e['id'])
	
# executes a query
def executeQuery(q, entityID):
	#define url
	SPARQLurl = 'https://query.wikidata.org/sparql'
	log("\nexecuting query . . .\n")
	# retrieve data in json
	data = requests.get(SPARQLurl, params={'query': q, 'format': 'json'}).json()
	# if data is retrieved
	if(data):
		answerList = [] 
		log("data length is = " + str(len(data)))
		# for each answer, append in the answerList
		for item in data['results']['bindings']:
			for var in item:
				if(var == "itemLabel"):
					log(item[var]['value'])
					answerList.append(item[var]['value'])
					
		# when all answers to one question are found
		# make Answer object and check if it does not exists yet
		a = Answer(answerList, "http://www.wikidata.org/entity/" + str(entityID))
		
		# Append the answer if it is not found yet
		# and only when an answer is found
		log(answerExists(a))
		log(answerList)
		if (not answerExists(a)) and  (answerList):
			log("answer appended")
			ANSWERS.append(a)
			
	#no data retrieved, print error
	else:
		print("Found no results to query\nPlease try again\n")

#Checks if the answer is already found by a different analyze or a previous query
def answerExists(foundItem):
	# for each answer found so far
	for item in ANSWERS:
		# for each label within the answer 
		for iAnswer in item.label:
			for answer in foundItem.label:
				if (answer == iAnswer):
					log("Answer was already found, not adding it to ANSWERS")
					return 1
	return 0


# returns all corresponding wikidata entities or properties
# TODO use named entitys here ?
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
def findSubject(question):
	for w in question:
		if w.dep_ == "nsubj":
			subject=[]
			for d in w.subtree:
				subject.append(d.text)

	return subject

# finds the noun phrases in question
# merges them
# returns new doc
def findNounPhrases(text):
	log("Finding noun phrases")
	newdoc = nlp(text)	# make a new doc
	for noun_phrase in list(newdoc.noun_chunks):
		noun_phrase.merge(noun_phrase.root.tag_, noun_phrase.root.lemma_, noun_phrase.root.ent_type_)
	return newdoc
	
# Gijs' version of the analyze
# tries to analyze the question using nsubj and pobj
# then sends the property- and subject strings to createQuery
def analyze(question, text):
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
	# found no nsubj and pobj so break out of analyze
	if(not (subj and prop)):
		log("Did not find subj and prop")
		return

	# update tokens to capture whole compound noun phrases
	# instead of only one word
	nounquestion = findNounPhrases(text)
	for token in nounquestion:
		log(token.text)
		# if token is a subj and found within broader token, then subj = token
		if(isinstance(subj, str) and re.search(subj, token.text)):
			log("broadend match for subj from\t" + subj + "\tto\t" + token.text)
			subj = token
		# if token is a prop and found within a broader token, then prop = token
		if(isinstance(prop, str) and re.search(prop, token.text)):
			log("broadend match for prop from\t" + prop + "\tto\t" + token.text)
			prop = token
		
	# append longer compounds to the property
	# when "of" is included, stop until the subject.
	for token in nounquestion:
		if(token.head.tag_ == "IN" and token.head.head == prop and token != subj):
			proptext = prop.text + " " + token.head.text + " " + token.text
			log("property has now become " + proptext)


	# remove the "the" from property text
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

# Function used to run the test mode
def testmode():
	# read in the question file here depending on platform
	if(platform.system() == "Linux"):
		filename = """../resources/all_questions_and_answers.tsv"""
	else:
		filename = """resources\\all_questions_and_answers.tsv"""
		#open file
	with open(filename) as tsvfile:
		reader = reader = csv.reader(tsvfile, delimiter='\t')
		# file contains
		#	row[0]: Question
		#	row[1]: URI
		#	row[2]: Answer
		# 	row[..]: more answers (check with len(row))
		questionCount = 0		# keep track of amount of questions answered so far
		# for each question/row
		for row in reader:
			questionCount += 1
			if(questionCount > int(TESTAMOUNT)):
				#stop if we have reached the test amount
				break;
			question = row[0]
			URI = row[1]
			
			# analyze each question
			# print amount of correct
			doc = nlp(question)
			analyze(doc, question)
			analyzeSecondary(doc)
			# keep tract of recall and precision
			global CORRECT
			global TOTAL
			for item in ANSWERS:
				score = 0;
				#check if URI is the same
				if(item.url == URI):
					CORRECT += 0.5
					# check if the first answer is the same
					for answer in item.label:
						if(answer == row[2]):
							CORRECT += 0.5

			print(questionCount, "cumalative score: ", CORRECT)
			TOTAL += 1

		print("From the ", str(TOTAL), " questions, ", CORRECT, " where correct.")
	

####################

# check for flags
if(len(sys.argv) > 1):
	# turn on debug output with the -d flag
	if any("-d" in s for s in sys.argv):
		DEBUG = True
		print("Debug mode is on")
	else:
		print("Debug mode is off")
	# turn on test mode when -t flag is found
	# debug is turned off in test mode
	if any("-t" in s for s in sys.argv):
		TESTMODE = True
		DEBUG = False
		# if a number is given after the -t flag, set that to be the max test questions
		# else defaulted to max
		if(len(sys.argv) >= 3):
			TESTAMOUNT = sys.argv[sys.argv.index("-t") + 1]
		print("Testing mode is on")


# In normal mode
if(not TESTMODE):
	printexamples()
	# search for line/question
	for line in sys.stdin:
		text = line.rstrip()				# grab line
		doc = nlp(text)						# make a doc from question

		# only grab input that is longer than 1 words
		# this is done to prevent errors
		if(len(doc) > 1):
			# Analyze syntax using Gijs' method
			analyze(doc, text)
			
			#Analyse using secondary method
			analyzeSecondary(doc)
		
			# print each answer
			for item in ANSWERS:
				item.show()
			#clean up
			ANSWERS.clear()
		else:
			print("Question is too short")

#testmode
else:
	testmode()
