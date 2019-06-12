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
entParams = {'action':'query', 'list':'search', 'format':'json', 'srprop':'snippet|titlesnippet', 'srlimit':1}
# paramters to find a property
propParams = {'action':'query', 'list':'search', 'format':'json', 'srprop':'snippet|titlesnippet', 'srnamespace':'120', 'srlimit':5}
DEBUG = False				# debug is defaulted to false
TESTMODE = False 			# test mode is defaulted to false
ANSWERS = [] 				# list to keep track of all found answers
TOTAL = 0					# keeps track of how many questions are asked
CORRECT = 0					# keeps track of how many questions are answered correctly
TESTAMOUNT = 805			# max amount of questions that will be tested in test mode
CURRENTQUESTIONNUMBER = 0	# number of the question that is being answered right now
QUESTION_TYPE = ''

# class to store answers
# properties are:
#	number	: the number of the question
#	URL 	: the uri/url to the wikidatabase
# 	labels 	: list of labels (strings) of the answers
class Answer:
	def __init__(self, number, url, labels):
		self.number = number
		self.url = url
		self.labels = labels

	def show(self):
		print(self.number , "\t", self.url, end = "\t")
		for item in self.labels:
			print(item, end = "\t")
		print("")

#used to print output only if the debug is on
def log(s):
	if(DEBUG):
		print(s)
		


def printexamples():
  print("""
Example questions are:
1	What is the birthdate of Eminem?
2	From which album is Dancing Queen? 
3	What is the birth name of Dave Grohl? 
4	When was Lovely Day by Bill Withers released?
5	What are Michael Jackson's causes of death? 
6	What country is Kraftwerk from?
7	Did Mozart play on violin?
8	How many children does Chris Martin have?
9	In what genres does Taylor Swift perform?
10	Stewart Copeland was the drummer with which band?
""")

def convertSentence(text):
	sub = text
	
	# Remove the leading number and tabs/spaces of the sentence
	if not text[0].isalpha():
		sub = text.replace(text[0], "", 1)
	sub = sub.strip()
	
	# Case 1: String -> What be
	case1 = ["What is the name of", "What are the names of", "What is the title of",
			"What's the name of", "What's the title of"]
			
	case2 = ['What year']
			
	for string in case1:
		if string in sub:
			sub = sub.replace(string, "What be")
			
	for string in case2:
		if string in sub:
			sub = sub.replace(string, "When")

	return sub

#When given some input, it links it to the closest WikiData potential synonym
def fixer(string, QUESTION_TYPE):
	new_string = ''
	if (string == 'die' or string == 'pass') and QUESTION_TYPE != 'THING':
		new_string = 'death'
	elif (string == 'die' or string == 'pass') and QUESTION_TYPE == 'THING':
		new_string = 'cause of death'
	elif string == 'kill' and QUESTION_TYPE == 'TIME':
		new_string = 'death'
	elif string == 'take' and (QUESTION_TYPE == 'PLACE' or QUESTION_TYPE == 'TIME'):
		new_string = ''
	elif (string == 'break' or string == 'stop' or string == 'quit' or string == 'split') and QUESTION_TYPE == 'TIME':
		new_string = 'dissolution'
	elif string == 'start' and QUESTION_TYPE == 'TIME':
		new_string = 'start time' # work period (start) (P2031)
	elif string == 'start' and QUESTION_TYPE == 'THING':
		new_string = 'origin'
	elif (string == 'compose' or string == 'write') and QUESTION_TYPE == 'TIME':
		new_string = 'publication'
	elif string == 'release' or (string == 'publish' and (QUESTION_TYPE == 'TIME' or QUESTION_TYPE == 'PLACE' or QUESTION_TYPE == 'THING')):
		new_string = 'publication'
	elif string == 'educate' and QUESTION_TYPE == 'PLACE':
		new_string = 'P69' # educated at (P69)
	elif string == 'bear':
		new_string = 'birth'
	elif string == 'perform' and QUESTION_TYPE == 'THING':
		new_string = ''
	elif string == 'hold' and QUESTION_TYPE == 'PLACE':
		new_string = 'held '
	elif string == 'hold' and QUESTION_TYPE == 'TIME':
		new_string = 'start '
	elif string == 'hold' and QUESTION_TYPE == 'THING':
		new_string = ''
	elif string == 'live' and QUESTION_TYPE == 'PLACE':
		new_string = 'residence'
	elif string == 'marry':
		new_string = 'spouse'
	elif string == 'bury':
		new_string = 'burial'
	elif string == 'come' or string == 'originate':
		new_string = 'origin'
	elif string == 'sing':
		new_string = 'performer'
	elif string == 'found' and (QUESTION_TYPE == 'PLACE' or QUESTION_TYPE == 'TIME' or QUESTION_TYPE == 'THING'):
		new_string = 'foundation'
	elif (string == 'create' and QUESTION_TYPE == 'PERSON'):
		new_string = 'creator'
	elif string == 'form':
		new_string = 'formation'
	elif string.endswith('e'):
		new_string = string + 'r'
	elif string.endswith('n') and string != 'own':
		new_string = string + 'ner'
	else:
		new_string = string + 'er'
	return new_string

#Secondary version of analyze
def analyzeSecondary(result):
	log("Secondary analyze")
	k = ""
	entityString = ""
	propertyString = ""
	entity2String = ""
	subject = []
	subject1 = []
	
	entity = []
	property_ = []
	entity2 = []
	firstWord = result[0]
	lastWord = result[len(result)-2]


	#Look for entities based on their main characteristics in the sentence
	
	# PREPOSITION FIRST/LAST QUESTIONS
	if firstWord.dep_ == "prep" or lastWord.dep_ == "prep":
		QUESTION_TYPE = 'THING'
		
		# In/From which/what X is/do Y (VERB)?
		for w in result:
			if w.lemma_ == 'be' or w.lemma_ == 'do':
				for p in w.nbor(-1).subtree:
					if p.lemma_ != 'which' and p.lemma_ != 'what':
						property_.append(p.text)
				for e in w.nbor().subtree:
					if e.dep_ != 'VERB':
						entity.append(e.text)
		
		for w in result:
			if w.pos_ == 'NOUN' or w.pos_ == 'PROPN':
				if w.text not in entity and w.text not in property_:
					entity.append(w.text)
					
			if w.pos_ == 'VERB' and  w.lemma_ != 'be' and w.lemma_ != 'do':
				property_.append(fixer(w.lemma_, QUESTION_TYPE))
						
	
	# WHO QUESTIONS:
	if firstWord.lemma_ == "who":
		QUESTION_TYPE = 'PERSON'
		whoIsY = True
		noun_chunks = list(result.noun_chunks)
		
		# Who is Y?
		for chunk in noun_chunks:
			for word in chunk:
				if word.dep_ == 'poss' or word.dep_ == 'dobj' or (word.dep_ == 'attr' and word.nbor().dep_ == 'prep' and word.nbor(-1).dep_ == 'det'):
					whoIsY = False
				
		if whoIsY == True:
			for w in result:
				if w.pos_ == 'NOUN' or w.pos_ == 'PROPN':
					for e in w.subtree:
						if e.text not in entity and e.dep_ != 'case':
							entity.append(e.text)
		
		for w in result:
				
			# Who is the X (attr|nsubj) of Y (pobj)?
			if w.dep_ == 'pobj':
				for e in w.subtree:
					if e.text not in entity and e.dep_ != 'case':
						entity.append(e.text)
			
			# Who is Y's (poss) X (attr)?
			if w.dep_ == 'poss':
				for e in w.subtree:
					if e.text not in entity and e.text != "\'s" and e.text != "\'":
						entity.append(e.text)
						
			if ((w.dep_ == 'attr' or (w.dep_ == 'nsubj' and w.nbor().dep_ == 'prep')) and w.lemma_ != firstWord.lemma_):
				if w.text not in property_ and w.text not in entity:
					property_.append(w.text)
			
			
			# Who (VERB/ROOT) X (dobj/nsubj)?
			if (w.dep_ == 'dobj' or (w.dep_ == 'nsubj' and w.nbor().dep_ != 'prep') and w.lemma_ != firstWord.lemma_):
				for e in w.subtree:
					if e.text not in entity and e.dep_ != 'case':
						entity.append(e.text)
			
			if ((w.dep_ == 'ROOT' or w.dep_ == 'xcomp' or w.dep_ == 'acomp')  and (w.lemma_ != 'be')):
				if w.lemma_ not in property_:
					property_.append(fixer(w.lemma_, QUESTION_TYPE))
					

		# This will be the result of a "Who is Y" question?	
		if not property_:
			QUESTION_TYPE = 'DESCRIPTION'
			
		
	# WHAT/WHICH QUESTIONS:
	if firstWord.lemma_ == "what" or firstWord.lemma_ == "which":
		QUESTION_TYPE = 'THING'
		property_subtree = []
		entity_subtree = []
		number_of_chunks = 0
		whatIsY = True
		noun_chunks = list(result.noun_chunks)

		# What is Y?
		for chunk in noun_chunks:
			for word in chunk:
				if word.dep_ == 'poss' or word.dep_ == 'pobj' or word.dep_ == 'dobj':
					whatIsY = False
				
		if whatIsY == True:
			for chunk in noun_chunks:
				for word in chunk:
					if word.dep_ != 'det' and word.lemma_ != 'what' and word.lemma_ != 'which' and word.text not in entity and word.text not in property_:
						entity.append(word.text)
		
		for w in result:
			
			# What is the X (nsubj) of Y (PROPN)?
			if w.text == 'the':
				if w.head.dep_ == 'nsubj':
					property_subtree = w.head.subtree
	
			if (w.pos_ == 'PROPN' and w.dep_ != 'compound'):
				for e in w.subtree:
					if e.dep_ != 'prep' and e.text != "\'s" and e.text != "\'" and e.text not in entity:
						entity.append(e.text)

			# What is Y's (poss) X (nsubj)? (may not work for some bands)
			if (w.dep_ == 'poss'):
				for e in w.subtree:
					if e.text != "\'s" and e.text != "\'" and e.text not in entity:
						entity.append(e.text)
				for p in w.head.subtree:
					if p.dep_ != 'nmod' and p.pos_ != 'DET' and p.pos_ != 'PROPN' and p.text != "\'s" and p.text != "\'" and p.text not in property_ and p.text not in entity:
						property_.append(p.text)
						
			if (w.dep_ == 'nsubj' or w.dep_ == 'nsubjpass' or  w.dep_ == 'attr')  and w.pos_ == 'PROPN' and w.text not in property_:
				entity_subtree = w.subtree
									
			# What X (dobj) does Y(nsubj|PROPN) do? - e.g. What genres does Toto play?
			if w.dep_ == 'dobj' and w.pos_ != 'PROPN' and w.pos_ != 'DET':
				for p in w.subtree:
					if p.dep_ != 'det' and (p.text not in entity and p.text not in property_):
						property_.append(p.text)

		for e in entity_subtree:
			if e.dep_ != 'prep' and e.text not in entity:
				entity.append(e.text)

		for p in property_subtree:	
			if (((p.dep_ == 'nsubj' or
				p.dep_ == 'nsubjpass' or
				p.dep_ == 'compound' or
				p.dep_ == 'amod' or
				p.dep_ == 'pobj') and p.nbor().dep_ != 'appos' and p.text not in entity) and
				p.text not in property_ and p.text != firstWord.lemma_):
				property_.append(p.text)

		# This will be the result of a "What is Y" question?	
		if not property_:
			QUESTION_TYPE = 'DESCRIPTION'
	
	# WHEN QUESTIONS:
	if firstWord.lemma_ == "when":
		QUESTION_TYPE = 'TIME'
		date_of = 'date'
		for w in result:
			
			# When was X (nsubj/nsubjpass) VERB? - e.g. When was Eminem born?
			# When did X (nsubj) VERB? - e.g. When did Leslie Cheung die?
			if w.dep_ == 'nsubj' or w.dep_ == 'nsubjpass':
				for e in w.subtree:
					if e.pos_ != 'VERB' and e.dep_ != 'case' and e.dep_ != 'punct' and e.text not in entity and e.text not in property_:
						entity.append(e.text)
				if w.text not in entity and w.text not in property_:
					entity.append(w.text)
			
			# When was Y's X?
			if w.dep_ == 'poss' and w.lemma_ != '-PRON-':
				for e in w.subtree:
					if e.dep_ != 'case' and e.text not in entity and e.text not in property_:
						entity.append(e.text)
				for p in w.head.subtree:
					if p.dep_ != 'case' and p.text not in entity and p.text not in property_ and p.text not in date_of:
						if date_of not in property_:
							property_.append(date_of)
						property_.append(p.text)
			
			if w.pos_ == 'VERB' and w.dep_ != 'nsubj' and w.dep_ != 'xcomp' and (w.lemma_ != 'be' and w.lemma_ != 'do'):
				if date_of not in property_ and w.lemma_ != 'start':
					property_.append(date_of)
				property_.append(fixer(w.lemma_, QUESTION_TYPE))
				if w.head.text in property_ and w.head.text not in entity:
					property_.remove(w.head.text)
					entity.append(w.head.text)
			
			
		# When is the X (noun chunk 1) of Y (noun chunk 2)?
		# In this case the above statements result in an empty property list
		# Does not work for "When was the date of..." since this is not gramatically correct
		if not property_:
			entity = []
			noun_chunks = list(result.noun_chunks)
			
			for chunk in noun_chunks[0]:
				if chunk.dep_ != 'det':
					property_.append(date_of + ' ' + chunk.text)
			for chunk in noun_chunks[1]:
				entity.append(chunk.text)
				
	
	# WHERE QUESTIONS:
	if firstWord.lemma_ == "where":
		QUESTION_TYPE = 'PLACE'
		place_of = 'place'
		for w in result:
			
			# Where was X (nsubj/nsubjpass) VERB? - e.g. Where was Eminem born?
			# Where did X (nsubj) VERB? - e.g. Where did Leslie Cheung die?
			if w.dep_ == 'nsubj' or w.dep_ == 'nsubjpass':
				for e in w.subtree:
					if e.pos_ != 'VERB' and e.dep_ != 'case' and e.dep_ != 'det' and e.dep_ != 'punct' and e.text not in entity and e.text not in property_:
						entity.append(e.text)
				if w.text not in entity and w.text not in property_:
					entity.append(w.text)
			
			# Where is Y's X?
			if w.dep_ == 'poss' and w.lemma_ != '-PRON-':
				for e in w.subtree:
					if e.dep_ != 'case' and e.text not in entity and e.text not in property_:
						entity.append(e.text)
				for p in w.head.subtree:
					if p.dep_ != 'case' and p.text not in entity and p.text not in property_ and p.text not in place_of:
						if place_of not in property_:
							property_.append(place_of)
						property_.append(p.text)

			
			
		# Where is the X (noun chunk 1) of Y (noun chunk 2)?
		# In this case the above statements result in an empty property list
		# Does not work for "Where is the place of..." since this is not gramatically correct
		if not property_:
			entity = []
			counter = 0
			noun_chunks = list(result.noun_chunks)
			
			for i in noun_chunks:
				counter += 1
			
			if counter == 2:
				for chunk in noun_chunks[0]:
					if chunk.dep_ != 'det':
						property_.append(chunk.text)
				for chunk in noun_chunks[1]:
					entity.append(chunk.text)
	
	# HOW QUESTIONS:
	if firstWord.lemma_ == "how":
		number_of_chunks = 0
		noun_chunks = list(result.noun_chunks)
		
		for i in noun_chunks:
			#print("CHUNKS: ", i.text)
			number_of_chunks += 1
		
		# How did Y (noun chunk 1) VERB?
		if firstWord.nbor().lemma_ == 'do':
			QUESTION_TYPE = 'MANNER'
			manner_of = 'manner'
			for chunk in noun_chunks:
				for word in chunk:
					if word.dep_ != 'det' and word.text not in entity:
						entity.append(word.text)
	
			for w in result:
				if w.dep_ == 'ROOT' and (w.lemma_ != 'be' and w.lemma_ != 'do'):
					property_.append(manner_of)
					property_.append(fixer(w.text, QUESTION_TYPE))
					
		# How many X (noun chunk 1) does Y (noun chunk 2+) have?
		if firstWord.nbor().lemma_ == 'many':
			QUESTION_TYPE = 'NUMBER'
			
			for chunk in noun_chunks[0]:
				if chunk.dep_ != 'det' and chunk.dep_ != 'advmod' and chunk.dep_ != 'amod':
					property_.append(chunk.text)
			for chunk in noun_chunks[1:]:
				for word in chunk:
					if word.dep_ != 'det' and word.text not in entity:
						entity.append(word.text)
						
		# How Z (ADJ) is Y (noun chunk 1)?
		if firstWord.nbor().pos_ == 'ADJ' and firstWord.nbor().lemma_ != 'many' and firstWord.nbor().lemma_ != 'much':
			QUESTION_TYPE = 'QUALITY'
		
			for chunk in noun_chunks:
				for word in chunk:
					if word.dep_ != 'det' and word.text not in entity:
						entity.append(word.text)
		
			for w in result:
				if w.pos_ == 'ADJ':
					property_.append(w.text)
			
	
	# YES/NO QUESTIONS STARTING WITH IS/WAS or ARE/WERE:
	if firstWord.lemma_ == "be":
		
		# Is Y an X? # Is Y X? -e.g. Is Eminem a rapper? ---- Is Elvis dead?
		QUESTION_TYPE = 'YES_NO_PROPERTY' #dead, married etc
		for w in result:
			if w.dep_ == 'det':
				QUESTION_TYPE = 'YES_NO_A_Y' #a singer, a composer etc
			if w.dep_ == 'pobj':
				QUESTION_TYPE = 'YES_NO_TRIPLE' #a singer, a composer etc
			if w != result[0] and w != result[len(result)-1] and w != result[len(result)-2]:
				if w.text not in entity and w.dep_ != 'det':
					entity.append(w.text)
		
			if w.text not in entity:
				if w.lemma_ != 'be' and w.dep_ != 'det' and w.lemma_ != '?':
					property_.append(w.text)
		
					
		# Is Y the X of Z? -e.g. Is Justin Bieber the husband of Hailey Baldwin?
		if QUESTION_TYPE == 'YES_NO_TRIPLE':
			entity1_subtree = []
			property_subtree = []
			entity = []
			property_ = []
			for w in result:
				
				if (w.dep_ == "nsubj"):
					entity1_subtree = w.subtree
						
				if (w.dep_ == "appos"):
					property_subtree = w.subtree
							
				if (w.dep_ == "pobj"):
					for e2 in w.subtree:
						entity2.append(e2.text)
						
			for p in property_subtree:
				if ((p.text not in entity2) and (p.dep_ != 'det' and p.dep_ != 'prep')):
					property_.append(p.text)
				
			for e1 in entity1_subtree:
				if ((e1.text not in entity) and
					(e1.text not in entity2) and
					(e1.text not in property_) and
					(e1.dep_ != 'det' and e1.dep_ != 'prep' and e1.pos_ != 'VERB')):
					entity.append(e1.text)
		
	if firstWord.lemma_ == "do":
		
		# Die Y (nsubj) VERB X (pobj/dobj)? - e.g. Did Mozart play on violin?
		QUESTION_TYPE = 'DID_X_V_Y' #dead, married etc
		for w in result:
			if (w.dep_ == "nsubj"):
				for e in w.subtree:
					entity.append(e.text)
					
			if (w.dep_ == "pobj" or w.dep_ == "dobj"):
				for p in w.subtree:
					property_.append(p.text)
			
	entityString = " ".join(entity)
	propertyString = " ".join(property_)
	entity2String = " ".join(entity2)
	
	# Searching for particular properties based on the query
	# (some properties need "special handling" with an if-statement,
	# since they can not be found via a simple search in the wikidata API):
	if propertyString == "members":
		propertyString = "has part (P527)"
	if 'city ' in propertyString:
		propertyString = propertyString.replace('city', 'place')
	if propertyString == "place ":
		propertyString = "location (P276)"
	if propertyString == "tall":
		propertyString = "height"
	if "real name" in propertyString:
		propertyString = "birth name (P1477)"
	if propertyString == "university":
		propertyString = "educated at (P69)"
	if propertyString == "occupations":
		propertyString = "occupation (P106)"
	if "first name" in propertyString:
		propertyString = "given name (P735)"
	if 'home' in propertyString:
		propertyString = propertyString.replace('home', 'origin')
	if propertyString == "band" or propertyString == "bandss" or ("group" in propertyString) or propertyString == "album":
		propertyString = "(P463) (P361)" #member of (P463) & part of (P361)
	
	# Use the same method as before to find answers
	if (entityString and propertyString and not entity2String):
		if QUESTION_TYPE == 'NUMBER':
			createCountQuery(entityString, propertyString)
		elif QUESTION_TYPE == 'DID_X_V_Y':
			createYesNoQuery(entityString, propertyString, "")
		elif QUESTION_TYPE == 'YES_NO_A_Y':
			createYesNoQuery(entityString, propertyString, "")
		elif QUESTION_TYPE == 'YES_NO_PROPERTY':
			createYesNoQuery(entityString, "", propertyString)
		else:
			createQuery(entityString, propertyString)
	if (entityString and not propertyString and not entity2String):
		if QUESTION_TYPE == 'DESCRIPTION':
				createDescriptionQuery(entityString)
	if (entityString and propertyString and entity2String):
		if QUESTION_TYPE == 'YES_NO_TRIPLE':
			createYesNoQuery(entityString, propertyString, entity2String)
	else:
		log("Did not find entityString and propertyString")

# creates and executes query
# for each entity and property it can find with the find function
def createQuery(ent, prop):
	ent = find(ent, entParams)
	prop = find(prop, propParams)
	if(ent and prop):
		for e in ent:
			for p in prop:
				query = "SELECT ?item ?itemLabel WHERE {wd:"+ str(e['title']) + " wdt:" + str(p['title'].replace("Property:", '')) + """ ?item.
				SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
				}"""
				log("\nGenerated following query:")
				log(e['titlesnippet'])
				log(p['titlesnippet'])
				log(query)
				executeQuery(query, e['title'])

# Query used to count objects in properties -e.g Number of people in "Children" property
def createYesNoQuery(entity1, property1, entity2):
	if len(entity2) == 0:
		ent1 = find(entity1, entParams)
		prop1 = find(property1, entParams)
		if (ent1 and prop1):
			for e1 in ent1:
				for p1 in prop1:
					query = "ASK { wd:" + str(e1['title']) + "?property" + " wd:" + str(p1['title']) + " . }"
					executeYesNoQuery(query, e1['title'])
	if len(property1) == 0:
		ent1 = find(entity1, entParams)
		prop1 = find(entity2, propParams)
		if (ent1 and prop1):
			for e1 in ent1:
				for p1 in prop1:
					query = "ASK { wd:" + str(e1['title']) + " wdt:" + str(p1['title'].replace("Property:", '')) + " ?property . }"
					executeYesNoQuery(query, e1['title'])
	if len(entity2) > 0 and len(property1) > 0:
		ent1 = find(entity1, entParams)
		prop1 = find(property1, propParams)
		if not prop1:
			prop1 = find(property1, entParams)
		ent2 = find(entity2, entParams)
		if (ent1 and prop1 and ent2):
			for e1 in ent1:
				for p1 in prop1:
					for e2 in ent2:
						query = "ASK { wd:" + str(e1['title']) + " wdt:" + str(p1['title'].replace("Property:", '')) + " wd:" + str(e2['title']) + " . }"
						executeYesNoQuery(query, e1['title'])
						
def createDescriptionQuery(ent):
	ent = find(ent, entParams)
	if (ent):
		for e in ent:
			query = "SELECT ?description WHERE { wd:" + str(e['title']) + """ schema:description ?description.
			FILTER ( lang(?description) = "en" )
			}"""
			log("\nGenerated following query:")
			log(e['titlesnippet'])
			executeQuery(query, e['title'])
			
def createCountQuery(ent, prop):
	ent = find(ent, entParams)
	prop = find(prop, propParams)
	if (ent and prop):
		for e in ent:
			for p in prop:
				query = "SELECT (COUNT(?item) AS ?count) WHERE {wd:"+ str(e['title']) + " wdt:" + str(p['title'].replace("Property:", '')) + """ ?item.
				SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
				}"""
				log("\nGenerated following query:")
				log(e['titlesnippet'])
				log(p['titlesnippet'])
				log(query)
				executeQuery(query, e['title'])
	
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
				if(var == "itemLabel" or var == "count"):
					log(item[var]['value'])
					answerList.append(item[var]['value'])
					
		# when all answers to one question are found
		# make Answer object and check if it does not exists yet
		a = Answer(CURRENTQUESTIONNUMBER, "http://www.wikidata.org/entity/" + str(entityID), answerList)
		
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

def executeYesNoQuery(q, entityID):
	SPARQLurl = 'https://query.wikidata.org/sparql'
	data = requests.get(SPARQLurl, params={'query': q, 'format': 'json'}).json()
	if(data):
		answerList = []
		if data['boolean']:
			answerList.append('yes')
		if not data['boolean']:
			answerList.append('no')
		#when all answers are found
		# make Answer object and check if it does not exists yet
		a = Answer(CURRENTQUESTIONNUMBER, "http://www.wikidata.org/entity/" + str(entityID), answerList)
		# Append the answer if it is not found yet
		# and only when an answer is found
		log(answerExists(a))
		log(answerList)
		if (not answerExists(a)) and  (answerList):
			log("answer appended")
			ANSWERS.append(a)
	else:
		print("Found no results to query\nPlease try again\n")


#Checks if the answer is already found by a different analyze or a previous query
def answerExists(foundItem):
	# for each answer found so far
	for item in ANSWERS:
		# for each label within the answer 
		for iLabel in item.labels:
			for label in foundItem.labels:
				if (label == iLabel):
					log("Answer was already found, not adding it to ANSWERS")
					return 1
	return 0


# returns all corresponding wikidata entities or properties
# TODO use named entitys here ?
def find(string, params):
	params['srsearch'] = string
	json = requests.get(url,params).json()
	if(json['query']['search']):
		ent = (json['query']['search'])
		for e in ent:
			label = e['titlesnippet'].replace('<span class="searchmatch">', '').replace('</span>', '')
			if('snippet' in ent):
				log("{}\t{}\t{}".format(e['title'], label,e['snippet']))
			else:
				log("{}\t{}".format(e['title'], label))
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
			text = question
			# analyze each question
			# print amount of correct
			text = sanitizeInput(text)			# sanitize the input
			text = convertSentence(text)
			doc = nlp(text)
			analyze(doc, text)
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
					for answer in item.labels:
						if(answer == row[2]):
							CORRECT += 0.5

			print(questionCount, "cumalative score: ", CORRECT)
			TOTAL += 1

		print("From the ", str(TOTAL), " questions, ", CORRECT, " where correct.")
	
# function for sanitizing the input given
# also indexes the question number
def sanitizeInput(line):

	# try to detect number and tab
	m = re.search("^(\d)*\t", line, re.IGNORECASE)
	log(m)
	if m:
		# detected expression in line, so set current question number
		global CURRENTQUESTIONNUMBER
		CURRENTQUESTIONNUMBER = int(m.group(0))
		log("CURRENTQUESTIONNUMBER = " + str(CURRENTQUESTIONNUMBER))
		# also need to remove pattern from the line
		line = re.sub("^(\d)*\t", "", line, re.IGNORECASE)
		log(line)

	# add ? if this is not at the end of the line.
	# this is done to prevent errors.
	if(not line.endswith("?")):
		log("appending question mark at the end of question")
		line += "?"	

	return line


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
	questionNumber = ''
	printexamples()
	# search for line/question
	for line in sys.stdin:
		
		if not line[0].isalpha():
			questionNumber = line[0]
		
		text = line.rstrip()				# grab line
		text = sanitizeInput(text)			# sanitize the input
		text = convertSentence(text)
		doc = nlp(text)						# make a doc from question
		
		# only grab input that is longer than 1 words
		# this is done to prevent errors
		if(len(doc) > 2):
			
			#Analyse using secondary method
			analyzeSecondary(doc)
			
			# found no answers
			if(not ANSWERS):
				print(CURRENTQUESTIONNUMBER,"\tFound no answer(s) to the question you asked, sorry!");
			else:
				# print each answer
				for item in ANSWERS[:1]:
					item.show()
				#clean up
				ANSWERS.clear()
		else:
			print("Question is too short")

#testmode
else:
	testmode()
