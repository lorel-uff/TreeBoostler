'''
   Functions to find best mapping from source to target domain
   Name:         mapping.py
   Author:       Rodrigo Azevedo
   Updated:      September 20, 2018
   License:      GPLv3
'''

import re
import copy
import random
import time

class KnowledgeGraph(object):
    def __init__(self):
        self.dataset = []
        self.settings = []
        self.sentences = []
        self.types = set()
        self.predicates = set()
        self.graph = self.Graph()

    # {'parent': ['person', 'person'] }
    def background(self, lines):
        '''Load background of a dataset'''
        st = {}
        for line in lines:
            m = re.search('^(\w+)\(([\w, +\-\#\`]+)*\).$', line)
            if m:
                relation = m.group(1)
                relation = re.sub('[+\-\#\` ]', '', relation)
                entities = m.group(2)
                entities = re.sub('[+\-\#\` ]', '', entities)
                entities = entities.split(',')
                st[relation] = entities
                for entity in entities:
                    self.types.add(entity)
        self.settings = st
    
    # [('parent', ['lidia','rodrigo'])]
    def facts(self, lines):
        '''Load facts of a dataset'''
        for line in lines:
            m = re.search('^(\w+)\(([\w, ]+)*\).$', line)
            if m:
                relation = m.group(1).replace(' ', '')
                entities = m.group(2).replace(' ', '').split(',')
                tupl = (relation, entities)
                if relation in self.settings:
                    self.dataset.append(tupl)
                    self.predicates.add(tupl[0])
                    type1 = self.settings[tupl[0]][0]
                    type2 = self.settings[tupl[0]][1] if len(tupl[1]) > 1 else self.settings[tupl[0]][0]
                    sub = type1 + '_' + tupl[1][0]
                    obj = type2 + '_' + tupl[1][1] if len(tupl[1]) > 1 else type2 + '_' + tupl[1][0]
                    self.graph.add_relation(sub, tupl[0], obj, True if len(tupl[1]) > 1 else False)
            
    def generate_sentences(self, max_depth=4, n_sentences=50000):
        '''Generate random paths from random nodes in graph'''
        self.sentences = []
        for i in range(n_sentences):
            node = self.graph.ids[random.randint(0, self.graph.n_nodes-1)] #self.graph.nodes[random.choice(list(self.graph.nodes))]
            clauses = {}
            sentence = []
            i_depth = 1
            while(i_depth < max_depth): #max_depth
                if node not in clauses:
                    clauses[node] = set()
                #edg = set(node.edges).difference(clauses[node])
                #if len(edg) == 0:
                #    break
                #edge = random.choice(list(edg))
                edg = node.edges
                if node.n_edges == 0:
                    break
                flag = False
                for k in range(10):
                    edge = edg[random.randint(0, node.n_edges-1)] #random.choice(list(edg))
                    if edge not in clauses[node]:
                        flag = True
                        break
                if not flag:
                    break
                if edge[1] not in clauses:
                    clauses[edge[1]] = set()
                clauses[node].add((edge[0], edge[1]))
                clauses[edge[1]].add((edge[0][1:] if edge[0][:1] == '_' else '_' + edge[0], node))
                sentence.append(str(edge[0]))
                #sentence.append(str(edge[1]))
                node = edge[1]
                i_depth += 1
            self.sentences.append(sentence)

    class Graph(object):
        '''Knowledge compilation into a graph'''
        def __init__(self):
            self.nodes = {}
            self.ids = {}
            self.n_nodes = 0
    
        def add_relation(self, subject, relation, object_, symmetry=True):
            if subject not in self.nodes:
                self.nodes[subject] = self.Node(subject)
                self.ids[self.n_nodes] = self.nodes[subject]
                self.n_nodes += 1
            if object_ not in self.nodes:
                self.nodes[object_] = self.Node(object_)
                self.ids[self.n_nodes] = self.nodes[object_]
                self.n_nodes += 1
            self.nodes[subject].add_edge(relation, self.nodes[object_], symmetry)
            
        class Node(object):
            def __init__(self, name):
                self.name = name
                self.edges = []
                self.n_edges = 0
            
            def add_edge(self, relation, node, symmetry=True):
                self._add_edge(relation, node)
                if symmetry:
                    node._add_edge('_'+relation, self)
            
            def _add_edge(self, relation, node):
                self.edges.append((relation, node))
                self.n_edges += 1
        
            def __str__(self):
                return str(self.name)
                
            def __hash__(self):
                return hash(self.name)
                
            def __eq__(self, other):
                return str(self) == str(other)

class mapping:
    def get_types(string):
        '''Get relation and its entities'''
        m = re.search('^(\w+)\(([\w, ]+)*\).$', string)
        if m:
            relation = m.group(1).replace(' ', '')
            entities = m.group(2).replace(' ', '').split(',')
            return (relation, entities)
        return None
        
    def find_pred(pred, preds):
        '''Find a predicate and its types given a predicate name'''
        for p in preds:
            m = re.search('^(\w+)\(([\w, ]+)*\).$', p)
            if m:
                relation = m.group(1).replace(' ', '')
                if relation == pred:
                    return p
        return None
    
    def invert(predicate):
        '''Get the inverse relation of a predicate'''
        if predicate[0] == '_':
            return predicate[1:]
        else:
            return '_' + predicate
    
    def map_set(mapping_dict, source):
        '''Maps a source set to a target set according to a given mapping'''
        mapped = set()
        for value in source:
            predicates = value.split()
            new_predicates = []
            for predicate in predicates:
                if predicate in mapping_dict:
                    new_predicates.append(mapping_dict[predicate])
                elif predicate[1:] in mapping_dict:
                    new_predicates.append(mapping.invert(mapping_dict[predicate[1:]]))
                else:
                    break
            if len(new_predicates) < 2:
                continue
            mapped.add(' '.join(new_predicates))
        return mapped
    
    def mapping_score(mapping_dict, source, target):
        '''Scores a possible mapping using Jaccard index'''
        mapped = mapping.map_set(mapping_dict, source)
        return len(mapped.intersection(target)) / len(mapped.union(target))        
    
    def is_compatible(source_args, target_args, typeCst):
        '''Determines if arguments mapping is compatible or not'''
        typeConstraints = copy.deepcopy(typeCst)
        if len(source_args) == len(target_args):
            for i in range(len(source_args)):
                if source_args[i] not in typeConstraints:
                    typeConstraints[source_args[i]] = target_args[i]
                else:
                    if typeConstraints[source_args[i]] != target_args[i]:
                        return (False, typeConstraints)
            return (True, typeConstraints)
        else:
            return (False, typeConstraints)
    
#    def get_pattern(pred):
#        '''Returns the type pattern'''
#        mapp = {}
#        count = 65
#        types = mapping.get_types(pred)
#        for j in range(len(types[1])):
#            if types[1][j] not in mapp:
#                mapp[types[1][j]] = chr(count)
#                count += 1
#            types[1][j] = mapp[types[1][j]]
#        joined = ''.join(types[1])
#        return joined
            
    def get_pattern(pred):
        '''Returns the type pattern'''
        types = mapping.get_types(pred)
        return len(types[1])
            
#    def get_max_patterns(preds):
#        '''Returns dictionary with number of predicates with the same type pattern'''
#        patterns = {}
#        for pred in preds:
#            joined = mapping.get_pattern(pred)
#            if joined not in patterns:
#                patterns[joined] = 1 # it includes Null mapping
#            patterns[joined] += 1
#        return patterns
        
    def get_max_patterns(preds):
        '''Returns dictionary with number of predicates with the same type pattern'''
        patterns = {}
        for pred in preds:
            joined = mapping.get_pattern(pred)
            if joined not in patterns:
                patterns[joined] = 0
            patterns[joined] += 1
        return patterns

#    def get_max_mappings(srcPreds, tarPreds):
#        '''Returns max possible mappings considering only type pattern'''
#        tarPatterns = mapping.get_max_patterns(tarPreds)
#        ret = 1
#        for pred in srcPreds:
#            p = mapping.get_pattern(pred)
#            if p in tarPatterns:
#                ret *= tarPatterns[p]
#        return ret
            
    def get_max_mappings(srcPreds, tarPreds):
        '''Returns max possible mappings considering only type pattern'''
        tarPatterns = mapping.get_max_patterns(tarPreds)
        ret = 1
        for pred in srcPreds:
            p = mapping.get_pattern(pred)
            if p in tarPatterns:
                ret *= (tarPatterns[p]+1) # it includes null mapping
        return ret

    def mapping(srcPreds, tarPreds, forceHead=None, predsMapping={}, typeConstraints={}, i=None):
        '''Generate all possible mappings that are type consistent'''
        result = []
        if len(predsMapping):
            result += mapping.mapping_recursive(srcPreds, tarPreds, predsMapping, typeConstraints, i, forceHead=forceHead)
        else:
            result += mapping.mapping_recursive(srcPreds, tarPreds, {}, {}, 0, forceHead=forceHead)
        return result
    
    def mapping_recursive(srcPreds, tarPreds, predsMapping, typeConstraints, i, forceHead=None):
        '''Recursive function for generating possible mappings'''
        if i >= len(srcPreds):
            return [(predsMapping, typeConstraints)]
        else:
            srcPred = srcPreds[i]
            src = mapping.get_types(srcPred)
            rets = []
            # mapping to None
            if i > 0: # or not mapped_flag:
                newPredsMapping = copy.deepcopy(predsMapping)
                newTypeConstraints = copy.deepcopy(typeConstraints)
                rets += mapping.mapping_recursive(srcPreds, tarPreds, newPredsMapping, newTypeConstraints, i+1)
            #mapped_flag = False
            # make source head clause maps to a target head clause (or inverse)
            tPreds = tarPreds if i > 0 or not forceHead else [forceHead]
            for tarPred in tPreds:
                tar = mapping.get_types(tarPred)
                # avoid multiple mapping to target predicate (recursion)
                targetPred = mapping.get_types(srcPreds[0])
                if targetPred[0] not in predsMapping or tar[0] != predsMapping[targetPred[0]].replace('_', ''): 
                    isCompatible = mapping.is_compatible(src[1], tar[1], typeConstraints)
                    if isCompatible[0]:
                        #mapped_flag = True
                        newPredsMapping = copy.deepcopy(predsMapping)
                        newPredsMapping[src[0]] = tar[0]
                        newTypeConstraints = isCompatible[1]
                        rets += mapping.mapping_recursive(srcPreds, tarPreds, newPredsMapping, newTypeConstraints, i+1)
                    if len(tar[1]) > 1:
                        isCompatible = mapping.is_compatible(src[1], tar[1][::-1], typeConstraints)
                        if isCompatible[0]:
                            #mapped_flag = True
                            newPredsMapping = copy.deepcopy(predsMapping)
                            newPredsMapping[src[0]] = '_' + tar[0]
                            newTypeConstraints = isCompatible[1]
                            rets += mapping.mapping_recursive(srcPreds, tarPreds, newPredsMapping, newTypeConstraints, i+1)
            return rets
        
    def get_best(sPreds, tPreds, srcFacts, tarFacts, n_sentences=50000, forceHead=None, threshold=10**7):
        '''Return best mapping found given source and target predicates and facts'''
        srcPreds = sPreds
        tarPreds = mapping.clean_preds(tPreds)
        start_time = time.time()
        results = {}
        source = KnowledgeGraph()
        source.background(srcPreds)
        source.facts(srcFacts)
        target = KnowledgeGraph()
        target.background(tarPreds)
        target.facts(tarFacts)
        results['Knowledge compiling time'] = time.time() - start_time
        new_start = time.time()
        source.generate_sentences(max_depth=4, n_sentences=n_sentences)
        target.generate_sentences(max_depth=4, n_sentences=n_sentences)
        source_sentences = set([' '.join(i) for i in source.sentences if len(i) > 1])
        target_sentences = set([' '.join(i) for i in target.sentences if len(i) > 1])
        results['Generating paths time'] = time.time() - new_start
        new_start = time.time()
        best = -1
        best_mapping_size = 0
        best_mapping = None
        fHead = None if not forceHead else mapping.find_pred(forceHead, tarPreds)
        start = 0
        end = len(srcPreds)
        bestPredsMapping = {}
        bestTypeConstraints = {}
        n_mappings = []
        mappings_end = []
        results['Max mapping'] = mapping.get_max_mappings(srcPreds, tarPreds)
        while start < len(srcPreds):
            max_mappings = mapping.get_max_mappings(srcPreds[start:end], tarPreds)
            while max_mappings > threshold:
                end -= 1
                max_mappings = mapping.get_max_mappings(srcPreds[start:end], tarPreds)
            mappings_end.append(end - start)
            possible_mappings = mapping.mapping(srcPreds[0:end], tarPreds, forceHead=fHead, predsMapping=bestPredsMapping, typeConstraints=bestTypeConstraints, i=start)
            for possible_item in possible_mappings:
                mapping_dict = possible_item[0]
                type_constraints = possible_item[1]
                score = mapping.mapping_score(mapping_dict, source_sentences, target_sentences)
                #scores.append((score, mapping_dict))
                if score > best or len(mapping_dict) > best_mapping_size:
                    best = score
                    best_mapping_size = len(mapping_dict)
                    best_mapping = mapping_dict
                    bestPredsMapping = mapping_dict
                    bestTypeConstraints = type_constraints
            # return None if incompatible forceHead is defined
            #if not len(possible_mappings):
                #return ({}, None)
            start = end
            end = len(srcPreds)
            n_mappings.append(len(possible_mappings))
        results['Generating mappings time'] = time.time() - new_start
        if not len(possible_mappings):
            return ({}, None)
        new_start = time.time()
        results['Possible mappings'] = n_mappings
        results['Numbers preds mapping'] = mappings_end
        #scores = []
        #scores = sorted(scores, key=lambda tup: tup[0], reverse=True)
        #print(scores)
        #print('Best Score: %s, Mapping: %s' % (best, best_mapping))
        results['Finding best mapping'] = time.time() - new_start
        results['Total time'] = time.time() - start_time
        mapd = []
        unaries = []
        for srcPred in srcPreds:
            s = mapping.get_types(srcPred)
            if len(s[1]) == 1:
                unaries.append(s[0])
        for key, value in best_mapping.items():
            if key in unaries:
                string = key + '(A) -> ' + value + '(A)'
            else:
                string = key + '(A,B) -> ' + (value if value[0] != '_' else value[1:]) + ('(A,B)' if value[0] != '_' else '(B,A)')
            mapd.append(string)
        return (mapd, results)
        
    def get_preds(structured, p):
        '''Returns all predicates presented in boosted trees in order of nodes and trees'''
        modes = mapping.clean_preds(p)
        pattern = '([a-zA-Z_0-9]*)\s*\(([a-zA-Z_0-9,\\s]*)\)'
        m = re.findall(pattern, structured[0][0])
        if m:
            preds_selected = set()
            preds = []
            target = m[0][0]
            for struct in structured:
                for node in struct[1].values():
                    n = re.findall(pattern, node)
                    if n:
                        for p in n:
                            if p[0] != target and p[0] not in preds_selected:
                                preds.append(p[0])
                                preds_selected.add(p[0])
            preds_modes = {}
            target_mode = None
            for line in modes:
                m = re.search('^(\w+)\(([\w, +\-\#\`]+)*\).$', line)
                if m:
                    relation = m.group(1)
                    relation = re.sub('[+\-\#\` ]', '', relation)
                    entities = m.group(2)
                    entities = re.sub('[+\-\#\` ]', '', entities)
                    if relation == target:
                        target_mode = relation + '(' + entities + ').'
                    if relation in preds_selected:
                        preds_modes[relation] = '(' + entities + ').'
            for i in range(len(preds)):
                preds[i] = preds[i] + preds_modes[preds[i]]
            return [target_mode] + preds
            
    def clean_preds(preds):
        '''Clean +/- from modes'''
        ret = set()
        for line in preds:
            m = re.search('^(\w+)\(([\w, +\-\#\`]+)*\).$', line)
            if m:
                relation = m.group(1)
                relation = re.sub('[+\-\#\` ]', '', relation)
                entities = m.group(2)
                entities = re.sub('[+\-\#\` ]', '', entities)
                ret.add(relation + '(' + entities + ').')
        return list(ret)
