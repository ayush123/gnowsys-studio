import json
import networkx as nx
from networkx.readwrite import json_graph
from gstudio.models import *
from itertools import *
from nltk.corpus import *
from gensim import corpora, models, similarities
from testMethods import *
import re

'''
Estimate 'longest path length' as the diameter of the graph
Using built-in nx.diameter(graph).
'''
def computeDiameter():
	G=json_graph.load(open("static/local_instance.json"))
	diameter=0
	for g in nx.connected_component_subgraphs(G.to_undirected()):
		try:
			diameter= max(diameter,nx.diameter(g))
		except:
			pass

	with open("static/diameter.dat", "w") as f:
		f.write("%f"%diameter)
	
'''
Use content data for each node to train the Gensim corpus
Store all the data locally for future similarity calls
Refer to http://radimrehurek.com/gensim/tutorial.html for implementation details
'''
def trainCorpus(content_field='content'):
	G=json_graph.load(open("static/local_instance.json"))
	sentences=[]
	
	for each_node in G.nodes():
		sentences.append(G.node[each_node][content_field]) 

	#pre-process text: convert to lowercase, remove numbers/symbols, remove stopwords
	texts=[]
	for string in sentences:
		words = re.findall(r'[a-z]+', string.lower())
		imp_words = filter(lambda x: x not in stopwords.words('english'), words)
		texts.append(imp_words)

	dictionary = corpora.Dictionary(texts)
	corpus = [dictionary.doc2bow(text) for text in texts]
	lsi = models.LsiModel(corpus, id2word=dictionary, num_topics=100) #num_topics should be around 200 for a large corpus
	index = similarities.MatrixSimilarity(lsi[corpus]) # transform corpus to LSI space and index it
	
	#locally store computed information
	dictionary.save('static/local_dict.dict')
	corpora.MmCorpus.serialize('static/local_corpus.mm', corpus) 
	index.save('static/local_index.index')
	lsi.save('static/local_lsi.lsi')


'''
Generate the nx instance for a single node and its neighborhood
root: node to start at
edge_type: relationship used for edges (relevant for direction)
'''
def nbh_subgraph(root, edge_type):

	#returns the direction of the relationship. to_root needs to be updated for new types
	def edge_direction(edge_type):
		to_root=['prior_nodes','child_of'] #relationships that have a nbhr-->root edge
		if edge_type in to_root:
			return 'to_root'
		return 'from_root' #relationships that have a root-->nbhr edge

	G=nx.DiGraph()
	root_nbh=root.get_nbh 

	#add all directed edges (+implicitly add nodes to G)
	G.add_node(root.id)	
	for nhbr in root_nbh[edge_type]:
		if edge_direction(edge_type) is 'to_root':
			G.add_edge(nhbr.id,root.id)
		else:
			G.add_edge(root.id,nhbr.id)
		G.node[nhbr.id]['title']=nhbr.title

	#add all metadata (single fields need to be updated for all fields that are not lists)
	single_fields=['title','plural','content'] #add more depending on what get_nbh returns
	for field in root_nbh.keys():
		if field in single_fields:
			G.node[root.id][field]=root_nbh[field]
		else:
			G.node[root.id][field]=[node.id for node in root_nbh[field]]

	return G

'''
Create a local version of the nx graph using database calls and store it in .json format
Parallelize this in the future, it'll take forever with more data
'''
def generate_local_instance(edge_type='prior_nodes'):
	
	#massive database call. Iterate through this if the database gets too large
	objs=Objecttype.objects.all()
	G=nx.DiGraph()
	
	i=0
	#generate subgraphs for each node (along with metadata) and merge them    
	for each in objs:       
		sub_G=nbh_subgraph(each, edge_type)
		G.add_edges_from(sub_G.edges())
		G.add_nodes_from(zip(sub_G.node.keys(),sub_G.node.values()))        
		print i
		i=i+1

	#serialize data into json format and save locally
	g_json = json_graph.node_link_data(G) # node-link format to serialize
	json_graph.dump(g_json, open("static/local_instance.json",'w'))
	#return json_graph.dumps(g_json) 


