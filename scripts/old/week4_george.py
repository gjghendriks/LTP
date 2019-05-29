#!/usr/bin/python3
import sys
import requests
import re
import spacy
nlp = spacy.load('en')

#Example questions ("what/who is/are/were/was (the) X of Y ?"):
example_queries = ["What is the official website of Pink Floyd? -> What is Pink Floyd's official website?",
					"Who is the father of Miley Cyrus? -> Who is Miley Cyrus's father?",
					"What is the place of birth of Freddie Mercury? -> Where was Freddie Mercury born? -> What is Freddie Mercury's place of birth?",
					"What is the date of birth of Elvis Presley? -> When was Elvis Presley born? -> When is Elvis Presley's birth date?",
					"What is the birth name of Eminem? -> What is Eminem's birth name?",
					"What is the date of death of Michael Jackson? -> When did Michael Jackson die?",
					"Who is the composer of Bohemian Rhapsody? -> Who composed Bohemian Rhapsody?",
					"What is the place of burial of Mozart? -> Where is Mozart buried?",
					"Who is the spouse of Justin Bieber? -> Who is Justin Bieber's spouse? -> Who is Justin Bieber married to?",
					"What is the record label of Scorpions? -> What is Scorpion's record label"]
					
url = 'https://www.wikidata.org/w/api.php'
url2 = 'https://query.wikidata.org/sparql'
DEBUG = False;

def log(s):
	if(DEBUG):
		print(s)

# Function for printing the example questions
def print_example_queries():
	for item in example_queries:
		print(item)
		
# Function that performs a search in the wikidata API
def find_answer(query):
	data = requests.get(url = url2,
		params = {'query': query, 'format': 'json'}).json()
	new_list = []
	for item in data['results']['bindings']:
		#print(item)
		for var in item :
			new_list.append(item[var]['value'])
	return new_list

# Finds the first corresponding wikidata entity or property
# TODO use named entitys here
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

# Main program	
def main(argv):
	print("Example questions:")
	print_example_queries()

	entities = {'action':'wbsearchentities',
			'language':'en',
			'format':'json'}
			
	props = {'action':'wbsearchentities',
			'language':'en',
			'format':'json',
			'type': 'property'}

	
				
	for line in sys.stdin:
		result = nlp(line)
		k = ""
		
		for w in result:
			if w.pos_ == "PROPN" or ((w.ent_type_ == "PERSON" or w.ent_type_ == "ORG") and w.text != "'s"):
				subject=[]
				for d in w.subtree:
					if d.tag_ == "POS":
						continue
					subject.append(d.text)
		entities['search'] = " ".join(subject)
		
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
		props['search'] = " ".join(subject1)
		
		
		# Searching for particular properties based on the query
		# (some properties need "special handling" with an if-statement,
		# since they can not be found via a simple search in the wikidata API):
		if props['search'] == "member":
			props['search'] = "has part"
		if props['search'] == "real name":
			props['search'] = "birth name"
		prop_search_results = requests.get(url=url, params=props).json()
		
		# Searching for particular entities based on the query:
		entities_search_results = requests.get(url=url, params=entities).json()
		
		# If no entities are found return error message, else return the
		# top entity and property results provided by the wikidata API:
		if len(entities_search_results['search']) == 0:
			print("The query returned no results. Please try again!")
		else:
			top_result = entities_search_results['search'][0]
			prop_top_result = prop_search_results['search'][0]
			
			# Once we have the property's P-code, we are ready to make
			# a query about the user's specific input question:
			query1 = '''
				SELECT ?itemLabel''' + ''' WHERE {
					wd:''' + top_result['id'] + ''' wdt:''' + prop_top_result['id'] + ''' ?item''' + '''.

				SERVICE wikibase:label {
					bd:serviceParam wikibase:language "en" . 
				}
			}'''
			
			a = find_answer(query1)
			if len(a) == 0:
				print("The query returned no results. Please try again!")

			for item in a:
				print(item)


if __name__ == "__main__":
	main(sys.argv)
	
	
	
#Named entities:
#result=nlp('Where wes Beyonce born?')
#for ent in result.ents:
#	if ent.label_ == 'PERSON':
#		print(ent.lemma_)
