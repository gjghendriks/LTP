#!/usr/bin/python3
import sys
import requests
import re
import spacy
nlp = spacy.load('en')


					
url = 'https://www.wikidata.org/w/api.php'
url2 = 'https://query.wikidata.org/sparql'
		
def yield_item(query):
	data = requests.get(url = url2,
		params = {'query': query, 'format': 'json'}).json()
	new_list = []
	for item in data['results']['bindings']:
		for var in item :
			new_list.append(item[var]['value'])
	return new_list
	
def substitute(string):
	if string == 'die':
		new_string = 'death'
	elif string == 'release':
		new_string = 'publication'
	elif string == 'consist':
		new_string = 'member'
	elif string == 'occupy':
		new_string = 'occupation'
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

def main(argv):
	print("What is the date of birth of Ray Charles? / What is Ray Charles' birth date?",
		"Who are the members of Led Zeppelin? / Who does Led Zeppelin consist of?",
		"What is the date of death of Bob Dylan? / When did Bob Dylan die?",
		"Who is the father of Nancy Sinatra / Who is Nancy Sinatra's father?",
		"What is the birth name of Jay Z? / What is Jay Z's birth name?",
		"What is the place of birth of Dave Grohl ?/ Where was Dave Grohl born?",
		"Who is the spouse of Weird Al? / Who is Weird Al married to?",
		"What is the occupation of Andy Samberg? / How is Andy Samberg occupied?",
		"What is the place of burial of Jimi Hendrix? / Where was Jimi hendrix buried?",
		"What is the record label of Pink Floyd? / What is Pink Floyd's record label?")

	parameters = {'action':'wbsearchentities',
		'language':'en',
		'format':'json'}

	properties = {'action':'wbsearchentities',
		'language':'en',
		'format':'json'}
				
	for line in sys.stdin:
		mode = ""
		input = nlp(line)
		
		for i in input:
			if i.pos_ == "PROPN" or ((i.ent_type_ == "PERSON" or i.ent_type_ == "ORG") and i.text != "'s"):
				subject=[]
				for j in i.subtree:
					if j.tag_ == "POS":
						continue
					subject.append(j.text)
		parameters['search'] = " ".join(subject)
		
		for i in input:
			
			if i.lemma_ == 'when':
				mode = 'date_of_'
			if i.lemma_ == 'where':
				mode = 'place_of_'
			if i.pos_ == 'VERB':
				obj=[]
				for j in i.subtree:
					if ((j.pos_ == 'NOUN' and j.nbor().tag_ == 'IN') or
						(j.pos_ == 'NOUN' and j.nbor(-1).tag_ == 'IN') or
						(j.pos_ == 'NOUN' and j.nbor().pos_ == 'NOUN') or
						(j.pos_ == 'NOUN' and j.nbor(-1).pos_ == 'NOUN') or
						(j.pos_ == 'NOUN' and j.nbor(-1).tag_ == 'POS') or
						(j.pos_ == 'NOUN' and j.nbor(-1).pos_ == 'ADJ') or
						(j.pos_ == 'ADJ')):
						obj.append(j.lemma_)
					if j.tag_ == 'IN' and j.nbor().tag_ == 'NN':
						obj.append(j.lemma_)
					if j.pos_ == 'VERB' and (j.lemma_ != 'be' and j.lemma_ != 'do'):
						obj.append(mode + substitute(j.lemma_))
		properties['search'] = "_".join(obj)
		
		if properties['search'] == "member":
			properties['search'] = "has_part"
		if properties['search'] == "real_name":
			properties['search'] = "birth_name"
		prop_search_results = requests.get(url=url, params=properties).json()
		
		json = requests.get(url=url, params=parameters).json()
		
		if len(json['search']) == 0:
			print("Your search returned no results. Please try another question!")
		else:
			top_result = json['search'][0]
			prop_top_result = prop_search_results['search'][0]

			prop_query = '''
				SELECT ?wikidata_property_id WHERE {
					wd:''' + prop_top_result['id'] + ''' wdt:P1687 ?wikidata_property_id .

				SERVICE wikibase:label {
					bd:serviceParam wikibase:language "en" . 
				}
			}'''
			
			prop_id = requests.get(url = url2, params = {'query': prop_query, 'format': 'json'}).json()
			if len(prop_id['results']['bindings']) != 0:
				item = prop_id['results']['bindings'][0]
				for var in item :
					property_id = ('{}'.format(item[var]['value']))
				if "http" in property_id:
					property_id_proper = property_id.replace("http://www.wikidata.org/entity/", "")	

				query1 = '''
					SELECT ?''' + properties['search'] + ''' WHERE {
						wd:''' + top_result['id'] + ''' wdt:''' + property_id_proper + ''' ?''' + properties['search'] + '''.

					SERVICE wikibase:label {
						bd:serviceParam wikibase:language "en" . 
					}
				}'''
				
				a = yield_item(query1)
				if len(a) == 0:
					print("Your search returned no results. Please try another question!")
				query2 = ""
				b = ""
				for item in a:
					if "http" in item:
						query2 = '''
							SELECT ?''' + properties['search'] + '''Label WHERE {
								wd:''' + top_result['id'] + ''' wdt:''' + property_id_proper + ''' ?''' + properties['search'] + ''' .

							SERVICE wikibase:label {
								bd:serviceParam wikibase:language "en" . 
							}
						}'''
						b = yield_item(query2)
					else:
						print(item)
				for item in b:
					print(item)
			else:
				print("Your search returned no results. Please try another question!")

if __name__ == "__main__":
	main(sys.argv)
