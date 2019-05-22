import spacy
import sys
import requests
import re

# Load English tokenizer, tagger, parser, NER and word vectors
nlp = spacy.load("en_core_web_sm")
url = 'https://www.wikidata.org/w/api.php'
entParams = {'action':'wbsearchentities', 'language':'en', 'format':'json', }
propParams = {'action':'wbsearchentities', 'language':'en', 'format':'json', 'type':'property'}


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
	ent = find(ent, entParams)['id']
	prop = find(prop, propParams)['id']
	query = "SELECT ?item ?itemLabel WHERE {wd:"+ str(ent) + " wdt:" + str(prop) + """ ?item.
	SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
	}"""
	print("\nGenerated following query: \n" + query)
	return query


def executeQuery(q):
	SPARQLurl = 'https://query.wikidata.org/sparql'
	print("\n\nexecuting query . . .\n\n")
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
	if(json['search']):
		ent = (json['search'][0])
		if('description' in ent):
			print("{}\t{}\t{}".format(ent['id'], ent['label'],ent['description']))
			return ent
		else:
			print("{}\t{}".format(ent['id'], ent['label']))
			return ent 
	else:
		print("Found no result in wikidata for '", string, "'")
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
	for noun_phrase in list(question.noun_chunks):
		noun_phrase.merge(noun_phrase.root.tag_, noun_phrase.root.lemma_, noun_phrase.root.ent_type_)
	return question

def analyze(question):
	

	for token in question:
		#print(token.text, "\t", token.lemma_, "\t", token.pos_, "\t", token.tag_, "\t", token.dep_, "\t\t", " head:\t", token.head)
		print(token.text, "\t", token.dep_)
		if(token.dep_ == "nsubj" ):
			prop = token.text
		if(token.dep_ == "pobj"):
			subj = token.text

	print("\n\nFound subj:", subj, " and prop:", prop,'\n\n')

	#update tokens to capture whole compound
	findNounPhrases(question)
	for token in question:
		print(token.text)
		if(isinstance(subj, str) and re.search(subj, token.text)):
			print("broadend match for subj from\t", subj, "\tto\t", token.text)
			subj = token
		if(isinstance(prop, str) and re.search(prop, token.text)):
			print("broadend match for prop from\t", prop,"\tto\t", token.text)
			prop = token
		

	for token in question:
		if(token.head.tag_ == "IN" and token.head.head == prop and token != subj):
			proptext = prop.text + " " + token.head.text + " " + token.text

	try:
		proptext
	except NameError:
		proptext = prop.text
		proptext = re.sub('(the|The)', '', proptext)
		executeQuery(createQuery(subj.text, proptext))
	else:
		proptext = re.sub('(the|The)', '', proptext)
		executeQuery(createQuery(subj.text, proptext))

	return


printexamples()


# search for line/question
for line in sys.stdin:
	text = line.rstrip()						# grab line
	doc = nlp(text)								#analyse question


	# Analyze syntax
	analyze(doc)

	# Find named entities, phrases and concepts
	#for entity in doc.ents:
	#	print(entity.text, entity.label_)


