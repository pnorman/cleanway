import urllib2
import xml.etree.cElementTree as ElementTree
import sys
import StringIO
import codecs

from datetime import datetime

nodes = dict()
droppednodes = set()
droppedways = set()
ways = dict()
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
           if len(ways) >= 500:
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
        if self.element == 'node' and name == 'user' and attributes['severity'] == 'normal':
            droppednodes.add(self.id)
         
def clean_nodes(nds):
    get_status(nds)

    for node, attributes in nds.iteritems():
        if node not in droppednodes:
            out.write('<node')
            for k, v in attributes.iteritems():
                out.write(' {}="{}"'.format(k, v))
            out.write('/>\n')
            
def clean_ways(wys):
    get_way_status(wys)

    for way, (attributes,tags,nodes) in wys.iteritems():
        if way not in droppedways:
            out.write('<way')
            for k, v in attributes.iteritems():
                out.write(' {}="{}"'.format(k, v))
            out.write('>\n')
            
            for nd in nodes:
                if nd not in droppednodes:
                    out.write('<nd ref="{}" />\n'.format(nd))
                else:
                    print 'dropped {}'.format(nd)
            for k, v in tags.iteritems():
                out.write(u'<tag k="{}" v="{}" />\n'.format(k,v))
            out.write('</way>\n')
       
            
          
def get_status(nds):
    tofetch = []
    
    # Build a list of nodes to fetch
    for node, attributes in nds.iteritems():
        if attributes['version'] != '1' or int(attributes['uid']) < 286582:
            tofetch.append(node)
    if len(tofetch) > 0:
        url = 'http://wtfe.gryph.de/api/0.6/problems?nodes='
        for id in tofetch[0:-1]:
            url += '{},'.format(id)
        url += id
        content = urllib2.urlopen(url)
        content = StringIO.StringIO(content.read())
        handler=WTFEHandler()
        for event, elem in ElementTree.iterparse(content, events=('start', 'end')):
            if event == 'start':
                handler.startElement(elem.tag, elem.attrib)
            elif event == 'end':
                handler.endElement(elem.tag, elem.attrib)
                


def get_way_status(wys):          
    pass
                
if __name__ == "__main__":
    pass
    xml = open(sys.argv[1], 'r')
    out = codecs.open(sys.argv[2], encoding='utf-8', mode='w')
    
    out.write("<?xml version='1.0' encoding='UTF-8'?>\n")
    out.write('<osm version="0.6" generator="cleanway.py">\n')

    handler = OsmHandler()
    for event, elem in ElementTree.iterparse(xml, events=('start', 'end')):
        if event == 'start':
            handler.startElement(elem.tag, elem.attrib)
        elif event == 'end':
            handler.endElement(elem.tag, elem.attrib)
            
        if len(nodes) >= 500:
            clean_nodes(nodes)
            nodes.clear()
            
    clean_ways(ways)
    ways.clear()
    out.write('</osm>\n')                