import urllib2
import xml.etree.cElementTree as ElementTree
from xml.sax.saxutils import quoteattr
import sys
import StringIO
import codecs
import os

from datetime import datetime

nodes = dict()
droppednodes = set()
droppedways = set()
ways = dict()
agreed = set()

CHUNK_SIZE = 500000
known_nodes = set()  # a list of known clean nodes.
known_ways = set()

# each way is ways[id]=(attributes, tags, nodes) where tags is a dict, nodes is a list and id is the way ID

done_nodes = False

class OsmHandler():
    def __init__(self):
        self.element = None
        self.id = None
        self.done_nodes = False
    def startElement(self, name, attributes):
        if name in ('node', 'way', 'relation'):
            self.element = name
            self.id = attributes['id']
        if name == 'node':
            nodes[self.id]=attributes
            
        if name == 'way':
            if not self.done_nodes:
                print "finishing nodes"
                clean_nodes(nodes)
                self.done_nodes = True
                nodes.clear()
            ways[self.id]=(attributes, {}, [])
       
    def endElement(self, name, attributes):
        if name in ('node', 'way', 'relation'):
            self.element = ''
            self.id = None

        if name == 'node':
            pass
        if self.element == 'way':
            if name == 'tag':
                ways[self.id][1][attributes['k']]=attributes['v']
            if name == 'nd':
                (ways[self.id][2]).append(attributes['ref'])
                
        if name == 'way':
           if len(ways) >= CHUNK_SIZE:
                clean_ways(ways)
                ways.clear()


class WTFEHandler():
    def __init__(self):
        self.element = ''
        self.id=''

    def startElement(self, name, attributes):
        if name in ('node', 'way', 'relation'):
            self.element = name
            self.id = attributes['id']

    def endElement(self, name, attributes):
        if name in ('node', 'way', 'relation'):
            self.element = ''
            self.tags = {}
        if self.element == 'node' and name == 'user' and attributes['severity'] == 'normal' and attributes['version'] == 'first':
            droppednodes.add(self.id)
        if self.element == 'way' and name == 'user' and attributes['severity'] == 'normal' and attributes['version'] == 'first':
            droppedways.add(self.id)
            
         
def clean_nodes(nds):

    fetched = False
    while not fetched:
        try:
            get_status(nds)
            fetched = True
        except urllib2.URLError:
            pass
    
    for node, attributes in nds.iteritems():
        if node not in droppednodes:
            out.write('<node')
            for k, v in attributes.iteritems():
                out.write(u' {}={}'.format(k, quoteattr(v)))
            out.write('/>\n')
            
    
            
def clean_ways(wys):
    fetched = False
    while not fetched:
        try:
            get_way_status(wys)
            fetched = True
        except urllib2.URLError:
            pass
       

    for way, (attributes,tags,nodes) in wys.iteritems():
        if way not in droppedways:
            out.write('<way')
            for k, v in attributes.iteritems():
                out.write(u' {}={}'.format(k, quoteattr(v)))
            out.write('>\n')
            
            for nd in nodes:
                if nd not in droppednodes:
                    out.write('<nd ref="{}" />\n'.format(nd))
            for k, v in tags.iteritems():
                out.write(u'<tag k={} v={} />\n'.format(quoteattr(k),quoteattr(v)))
            out.write('</way>\n')

def get_status(nds):
    tofetch = []
    
    # Build a list of nodes to fetch
    for node, attributes in nds.iteritems():
        if attributes['version'] == '1' and 'uid' in attributes and (int(attributes['uid']) < 286582 or 'uid' in agreed):
            pass
        else:
            if not node in known_nodes:
                tofetch.append(node)
    print 'Fetching {} of {} nodes.'.format(len(tofetch), len(nds))
    if len(tofetch) > 0:
        url = 'http://wtfe.gryph.de/api/0.6/problems'
        query = 'nodes='
        for id in tofetch[0:-1]:
            query += '{},'.format(id)
        query += tofetch[-1]
        content = urllib2.urlopen(url,query, timeout=60)
        content = StringIO.StringIO(content.read())
        handler=WTFEHandler()
        for event, elem in ElementTree.iterparse(content, events=('start', 'end')):
            if event == 'start':
                handler.startElement(elem.tag, elem.attrib)
            elif event == 'end':
                handler.endElement(elem.tag, elem.attrib)
        for id in tofetch:
            if id not in droppednodes:
                known_nodes.add(id)


def get_way_status(wys):          
    tofetch = []
    
    # Build a list of nodes to fetch
    for way, (attributes, tags, _) in wys.iteritems():
        if attributes['version'] == '1' and 'uid' in attributes and (int(attributes['uid']) < 286582 or 'uid' in agreed):
            pass # easier than complicated de morgans
        else:
            if 'odbl' in tags and tags['odbl'] == 'clean':
                pass
            elif not way in known_ways:
                tofetch.append(way)
            
    print 'Fetching {} ways'.format(len(tofetch))
    if len(tofetch) > 0:
        url = 'http://wtfe.gryph.de/api/0.6/problems'
        query = 'ways='
        for id in tofetch[0:-1]:
            query += '{},'.format(id)
        query += tofetch[-1]
        content = urllib2.urlopen(url,query, timeout=60)
        content = StringIO.StringIO(content.read())
        handler=WTFEHandler()
        for event, elem in ElementTree.iterparse(content, events=('start', 'end')):
            if event == 'start':
                handler.startElement(elem.tag, elem.attrib)
            elif event == 'end':
                handler.endElement(elem.tag, elem.attrib)    
                
        for id in tofetch:
            if id not in droppednodes:
                known_ways.add(id)

if __name__ == "__main__":

    # requires the output of curl http://planet.openstreetmap.org/users_agreed/users_agreed.txt | tail -n +3 > users_agreed.txt
    with open(os.path.realpath(os.path.dirname(sys.argv[0])) + '/users_agreed.txt', mode='r') as f: 
        for line in f: 
            try:
                agreed.add(str(int(line)))
            except ValueError:
                pass
    
    with open(os.path.realpath(os.path.dirname(sys.argv[0])) + '/known_nodes.txt', mode='r') as f:
        for line in f:
            try:
                known_nodes.add(str(int(line)))
            except ValueError:
                pass
                
    with open(os.path.realpath(os.path.dirname(sys.argv[0])) + '/known_ways.txt', mode='r') as f:
        for line in f:
            try:
                known_ways.add(str(int(line)))
            except ValueError:
                pass
    
    
    xml = open(sys.argv[1], 'r')
    out = codecs.open(sys.argv[2], encoding='utf-8', mode='w')
    
    out.write("<?xml version='1.0' encoding='UTF-8'?>\n")
    out.write('<osm version="0.6" generator="cleanway.py">\n')

    handler = OsmHandler()
    context = ElementTree.iterparse(xml, events=('start', 'end'))
    context = iter(context)
    event, root = context.next()
    
    for event, elem in context:
        if event == 'start':
            handler.startElement(elem.tag, elem.attrib)
        elif event == 'end':
            handler.endElement(elem.tag, elem.attrib)
            elem.clear()
            root.clear()
            
        if len(nodes) >= CHUNK_SIZE:
            clean_nodes(nodes)
            nodes.clear()
            
    clean_ways(ways)
    ways.clear()
    out.write('</osm>\n')   

    with open(os.path.realpath(os.path.dirname(sys.argv[0])) + '/known_nodes.txt', mode='w') as f:
        for id in known_nodes:
            f.write('{}\n'.format(id))
            
    with open(os.path.realpath(os.path.dirname(sys.argv[0])) + '/known_ways.txt', mode='w') as f:
        for id in known_ways:
            f.write('{}\n'.format(id))            