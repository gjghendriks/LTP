import spacy
import sys
import requests
import re
import copy

# Load English tokenizer, tagger, parser, NER and word vectors
nlp = spacy.load("en_core_web_sm")
url = 'https://www.wikidata.org/w/api.php'
entParams = {'action':'wbsearchentities', 'language':'en', 'format':'json', }
propParams = {'action':'wbsearchentities', 'language':'en', 'format':'json', 'type':'property'}
DEBUG = False;


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


def executeQuery(q):
	SPARQLurl = 'https://query.wikidata.org/sparql'
	log("\n\nexecuting query . . .\n\n")
	data = requests.get(SPARQLurl, params={'query': q, 'format': 'json'}).json()
	if(data):
		for item in data['results']['bindings']:
			for var in item :
				print('{}\t{}'.format(var,item[var]['value']))
	else:
		print("Found no results to query\nPlease try again\n")


#finds the first corresponding wikidata entity or property
#TODO use named entitys here
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
		log("Found no result in wikidata for '" + string+  "'")
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
# returns the doc
def findNounPhrases(question):
	newdoc = copy.deepcopy(question)
	for noun_phrase in list(newdoc.noun_chunks):
		noun_phrase.merge(noun_phrase.root.tag_, noun_phrase.root.lemma_, noun_phrase.root.ent_type_)
	return newdoc

def analyze(question):	

	for token in question:
		#log(token.text, "\t", token.lemma_, "\t", token.pos_, "\t", token.tag_, "\t", token.dep_, "\t\t", " head:\t", token.head)
		log(token.text + "\t" + token.dep_)
		if(token.dep_ == "nsubj" ):
			prop = token.text
		if(token.dep_ == "pobj"):
			subj = token.text

	log("\n\nFound subj:" + subj + " and prop:" + prop + '\n\n')

	#update tokens to capture whole compound
	nounquestion = findNounPhrases(question)
	for token in nounquestion:
		log(token.text)
		if(isinstance(subj, str) and re.search(subj, token.text)):
			log("broadend match for subj from\t" + subj + "\tto\t" + token.text)
			subj = token
		if(isinstance(prop, str) and re.search(prop, token.text)):
			log("broadend match for prop from\t" + prop + "\tto\t" + token.text)
			prop = token
		

	for token in nounquestion:
		if(token.head.tag_ == "IN" and token.head.head == prop and token != subj):
			proptext = prop.text + " " + token.head.text + " " + token.text

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


# turn on debug output by the -d flag
if(len(sys.argv) > 1):
	if any("-d" in s for s in sys.argv):
		DEBUG = True
		print("Debug mode is on")
	else:
		print("Debug mode is off")
	if any("-t" in s for s in sys.argv):
		print("Testing with test set")
		#todo implement this george.



printexamples()



# search for line/question
for line in sys.stdin:
	text = line.rstrip()						# grab line
	doc = nlp(text)								#analyse question


	# Analyze syntax using Gijs' method
	analyze(doc)



