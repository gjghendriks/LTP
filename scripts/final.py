import spacy
import sys
import requests
import re
import copy

# Load English tokenizer, tagger, parser, NER and word vectors
nlp = spacy.load("en_core_web_sm")
url = 'https://www.wikidata.org/w/api.php' # URL for wikidata
# parameters to find an entity
entParams = {'action':'wbsearchentities', 'language':'en', 'format':'json', }		
# paramters to find a property
propParams = {'action':'wbsearchentities', 'language':'en', 'format':'json', 'type':'property'}
DEBUG = False		# debug is defaulted to false
TESTMODE = False 	# test mode is defaulted to false
ANSWERS = [] # list to keep track of all found answers

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


# creates and executes query
# for each entity and property it can find with the find function
def createQuery(ent, prop):
	ent = find(ent, entParams)
	prop = find(prop, propParams)
	for e in ent:
		for p in prop:
			query = "SELECT ?item ?itemLabel WHERE {wd:"+ str(e['id']) + " wdt:" + str(p['id']) + """ ?item.
			SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
			}"""
			log("\nGenerated following query: \n" + query)
			executeQuery(query)

# executes a query
def executeQuery(q):
	SPARQLurl = 'https://query.wikidata.org/sparql'
	log("\n\nexecuting query . . .\n\n")
	data = requests.get(SPARQLurl, params={'query': q, 'format': 'json'}).json()
	if(data):
		for item in data['results']['bindings']:
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
		for item in ANSWERS:
			item.show()
		ANSWERS.clear()

#testmode
else:
	#read in the question file here
	pass