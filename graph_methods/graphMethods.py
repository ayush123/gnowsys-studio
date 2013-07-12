import json
import networkx as nx
from networkx.readwrite import json_graph
from gstudio.models import *
from itertools import *
from gensim import corpora, models, similarities

#Silly function to get the node id of a node through it's title
def get_id(name):
	return Objecttype.objects.get(title=name).id 


'''
nx function to remove redundant edges in a transitive relation based network
'''
def tred(graph):
    A=nx.to_agraph(graph)
    I=A.tred(copy=true)
    new_graph=nx.from_agraph(I)
    return new_graph

'''
Check for shortest path (bidirectional) between two nodes
uses the nx implementation of Dijkstras
''' 
def min_path(name1, name2):
	G=json_graph.load(open("static/local_instance.json"))
	path=[]

	#check in both directions.
	try:
		path=nx.shortest_path(G,get_id(name1),get_id(name2))
	except:
		path=nx.shortest_path(G,get_id(name2),get_id(name1))
	return path


''' 
Returns shortest path to all nearest common ancestors
A simple iterative BFS call to expand frontiers of two nodes until they intersect
returns a list of tuples: [(ot1's minpath to ancestor i, ot2's minpath to ancestor i)]
'''
def nca(name1, name2):
	G=json_graph.load(open("static/local_instance.json"))	

	frontier1=[get_id(name1)]
	frontier2=[get_id(name2)]
	
	done=False
	while not done:
		#retrieve nodes in next BFS shell
		shell1=list(chain.from_iterable(G.predecessors(each) for each in frontier1))
		shell2=list(chain.from_iterable(G.predecessors(each) for each in frontier2))

		#no new nodes. End of the line
		if not shell1 and not shell2:
			return []
		
		frontier1+=shell1
		frontier2+=shell2
		intersect=set(frontier1)&set(frontier2)
	
		if intersect:
			done=True
			#print intersect

	return [(nx.shortest_path(G,ancestor,get_id(name1)),nx.shortest_path(G,ancestor,get_id(name2))) for ancestor in list(intersect)]

'''
Uses Gensim to find content similarity between two nodes
Uses a vector space model representation and computes cosine similarity
'''
def content_similarity(query, compare_to, content_field='content'):
	
	#load similarity data from local storage:
	index = similarities.MatrixSimilarity.load('static/local_index.index')
	dictionary = corpora.Dictionary.load('static/local_dict.dict')
	corpus = corpora.MmCorpus('static/local_corpus.mm')
	lsi=models.LsiModel.load('static/local_lsi.lsi')

	G=json_graph.load(open("static/local_instance.json"))
	#list all titles to generate top similar topics for debugging	
	titles=[title for title in [G.node[each_node]['title'] for each_node in G.nodes()]]

	#Gensim similarity computation
	query=G.node[get_id(query)][content_field]
	vec_bow = dictionary.doc2bow(query.lower().split())
	vec_lsi = lsi[vec_bow] # convert the query to LSI space
	sims = index[vec_lsi]

	#sort topics in descending order of similarity (debugging)
	
	sorted_sims = sorted(enumerate(sims), key=lambda item: -item[1])
	print "-----------------------------------------------------------------"
	for each in sorted_sims[0:15]:
		print str(each)+" --> "+titles[each[0]]
	print "-----------------------------------------------------------------"
	
	return sims[titles.index(compare_to)]


'''
Incomplete function to use parameters to generate an overall similarity score between nodes
Could be used to weight virtual edges between EVERY node and let it settle in equilibrium
This should cluster related topics into visually appealing domains

sim= [A*f1+B*f2+C*f3] (A,B,C: undecided weights)
f1: shortest_path/diameter (0--> incredibly similar)
f2: something with NCA (?)
f3: content similarity (1--> amazingly similar)
'''
def similarity(name1, name2,content_field='content'):
	G=json_graph.load(open("static/local_instance.json"))
	H=nx.DiGraph();
	path=nx.shortest_path(G,get_id(name1),get_id(name2))

	diameter=0
	with open("static/diameter.dat", "r") as f:
		diameter=float(f.read())

	f1=len(path)/float(diameter)
	print "minpath factor: %f"%f1


	nca_list=nca(name1,name2)
	#do something with the information
	#print "nca factor: %f"%f2

	f3=content_similarity(G.node[get_id(name1)][content_field], name2)
	print "content sim factor: %f"%f3

	#return A*f1+B*f2+C*f3

#----------------------------------------------------------------------------------------------

'''
Computes one extra level of a graph (either outgoing or incoming relations)
and returns the expanded graph
'''
def expand_graph(H, direction='in'):
	G=json_graph.load(open("static/local_instance.json"))

	#add predecessor or successor nodes depending on 'direction'
	frontier=[]
	if direction is 'out':
		frontier=list(chain.from_iterable(G.successors(each) for each in H.nodes()))
	elif direction is 'in':
		frontier=list(chain.from_iterable(G.predecessors(each) for each in H.nodes()))
	return nx.compose(H,G.subgraph(frontier+H.nodes()))


'''
Debug function to show NCA for the template
'''
def show_nca(name1, name2, levels=0):
	nca_list=nca(name1, name2)
	G=json_graph.load(open("static/local_instance.json"))
	H=nx.DiGraph()
	for each in nca_list:
		anc_path=nx.compose(color_path(each[0],'green'),color_path(each[1],'yellow'))
		H=nx.compose(H,anc_path)

	for i in range(levels):
		H=expand_graph(H)

	for each in nca_list:
		H.node[each[0][0]]['color']='red' #color the nca different

	data=json_graph.dumps(H)
	return data


'''
Debug function to color paths for the template
'''
def color_path(path, color):
	G=json_graph.load(open("static/local_instance.json"))
	H=G.subgraph(path)

	for each in zip(path,path[1:]):
		H.edge[each[0]][each[1]]['color']=color
		H.node[each[1]]['color']=color	
	H.node[path[0]]['color']=color

	return H


'''
Debug function to compute and color shortest paths for the template
'''
def show_min_path(name1, name2, levels=0):

	path=min_path(name1, name2)
	
	H=color_path(path,'blue')
	for i in range(levels):
		H=expand_graph(H)

	data=json_graph.dumps(H)
	return data

'''
Debug function to compute the neighborhood of a node up to a certain level for the template
'''
def concept_nbh(name, levels):
	G=json_graph.load(open("static/local_instance.json"))
	G=G.subgraph(get_id(name))
	
	#the user might not know his numbers very well
	try:
		levels=int(levels)
	except:
		levels=0

	for i in range(levels):
		G=expand_graph(G)

	data=json_graph.dumps(G)
	return data

def local_mega_graph():
	H=json_graph.load(open("static/local_instance.json"))
	data=json_graph.dumps(H)
	return data
