from konlpy.tag import Mecab
from pymongo import MongoClient

stop_word = dict()
DBname = "db20171640"
conn = MongoClient("localhost")
db = conn[DBname]
db.authenticate(DBname, DBname)

class Node:
    def __init__(self, item, parent):
        self.item = item
        self.num = 0
        self.fr = 0
        self.find = 0
        self.parent = parent
        self.child = []
        self.link = None

class item_Node:
    def __init__(self, item):
        self.item = item
        self.support = 0
        self.link = None

def printMenu():
    print("0. CopyData")
    print("1. Morph")
    print("2. print morphs")
    print("3. print wordset")
    print("4. frequent item set")
    print("5. association rule")

def make_stop_word():
    f = open("wordList.txt", "r")
    while True:
        line = f.readline()
        if not line:
            break
        stop_word[line.strip()] = True
    f.close()

def morphing(content):
    mecab = Mecab()
    morphList = []
    for word in mecab.nouns(content):
        if word not in stop_word:
            morphList.append(word)

    return morphList

def p0():
    col1 = db['news']
    col2 = db['news_freq']

    col2.drop()

    for doc in col1.find():
        contentDic = dict()
        for key in doc.keys():
            if key != "_id":
                contentDic[key] = doc[key]
        col2.insert(contentDic)

def p1():
    for doc in db['news_freq'].find():
        doc['morph'] = morphing(doc['content'])
        db['news_freq'].update({"_id": doc['_id']}, doc)

def p2():
    doc = db['news_freq'].find_one()
    for m in doc['morph']:
        print(m)

def p3():
    col1 = db['news_freq']
    col2 = db['news_wordset']
    col2.drop()
    for doc in col1.find():
        new_doc = dict()
        new_set = set()
        for w in doc['morph']:
            new_set.add(w)
        new_doc['word_set'] = list(new_set)
        new_doc['news_freq_id'] = doc['_id']
        col2.insert(new_doc)

def p4():
    doc = db['news_wordset'].find_one()
    for m in doc['word_set']:
        print(m)

def p5(length):
    ref = db['news_wordset']
    doc = db['candidate_L'+str(length)]
    doc.drop()
    min_sup = 0.04
    min = min_sup * ref.find().count()

    # item table
    item_table = []
    for d in ref.find():
        for w in d['word_set']:
            flag = 0
            for k in item_table:
                if k.item == w:
                    k.support += 1
                    flag = 1
                    break
            if flag == 0:
                newNode = item_Node(w)
                newNode.support += 1
                item_table.append(newNode)

   
    # sort item table
    item_table.sort(reverse=True, key = lambda obj:obj.support)
            
    # sort transaction
    trsc = []
    idx = 0
    for d in ref.find():
        trsc.append([])
        for t in item_table:
            if (t.item in d['word_set']) and (t.support >= min):
                trsc[idx].append(t.item)
        idx += 1

    # length = 1
    if length == 1:
        # create 'candidate_L1'
        for w in item_table:
            if w.support >= min:
                new_doc = {}
                new_doc['item_set'] = [w.item]
                new_doc['support'] = w.support
                doc.insert(new_doc)

    # length > 1
    else:
        global root;
        newNode = Node("root", None)
        root = newNode

        # construct FP-tree
        for n in trsc:
            subroot = root
            for w in n:
                exist = 0
                for c in subroot.child:
                    if w == c.item:
                        subroot = c
                        subroot.num += 1
                        exist = 1
                        break

                if exist == 0:
                    newNode = Node(w, subroot)
                    #newNode.parent = subroot
                    newNode.num += 1
                    subroot.child.append(newNode)
                    subroot = newNode
                    # linked list
                    for t in item_table:
                        if t.item == subroot.item:
                            if t.link == None:
                                t.link = subroot
                            else:
                                tmp = t.link
                                while tmp.link != None:
                                    tmp = tmp.link
                                tmp.link = subroot
                            break


        # construct conditional tree
        i = len(item_table) - 1
        while i >= 0:
            t = item_table[i]
            if t.support >= min:
                r = t.link
                while r != None:
                    r.fr = r.num
                    c = r
                    while c.parent.item != "root":
                        if c.parent.fr != 0:
                            c.parent.fr += c.fr
                            tmp = c.parent
                            while tmp.parent.item != "root":
                                tmp.parent.fr = tmp.fr
                                tmp = tmp.parent
                            break
                        else:
                            c.parent.fr = c.fr
                        c = c.parent
                    r = r.link

                # frequent item set
                freq = []
                # length = 2
                if length == 2:
                    idx = i - 1
                    while idx >= 0:
                        p = item_table[idx]
                        tmp = p.link
                        sum = 0
                        while tmp != None:
                            sum += tmp.fr
                            tmp = tmp.link

                        if sum >= min:
                            freq.append([p.item, t.item, sum])
                        idx -= 1

                    for inst in freq:
                        new_doc = {}
                        new_doc['item_set'] = [inst[0], inst[1]]
                        new_doc['support'] = inst[2]
                        doc.insert(new_doc)

                # length = 3
                if length == 3:
                    idx = i - 1
                    while idx >= 0:
                        p = item_table[idx]
                        tmp = p.link
                        sum = 0
                        while tmp != None:
                            sum += tmp.fr
                            tmp = tmp.link

                        if sum >= min:
                            if p.link.parent.item != "root":
                                freq.append([p.link.parent.item, p.item, t.item, sum])
                        idx -= 1

                    for inst in freq:
                        new_doc = {}
                        new_doc['item_set'] = [inst[0], inst[1], inst[2]]
                        new_doc['support'] = inst[3]
                        doc.insert(new_doc)

                r = t.link
                while r != None:
                    r.fr = r.num
                    c = r
                    while c.parent.item != "root":
                        c.parent.fr = 0
                        c = c.parent
                    r = r.link

            i -= 1



def p6(length):
    doc = db['candidate_L1']
    ref = db['candidate_L'+str(length)]
    min_conf = 0.8

    # length = 2
    if length == 2:
        for w in ref.find():
            item1 = w['item_set'][0]
            item2 = w['item_set'][1] 
            num = w['support']

            alpha = 0
            beta = 0
            for r in doc.find():
                comp = r['item_set'][0]
                if item1 == comp:
                    alpha = r['support']
                    break

            for r in doc.find():
                comp = r['item_set'][0]
                if item2 == comp:
                    beta = r['support']
                    break

            if alpha != 0:
               if num / alpha >= min_conf:
                    print (item1+' => '+item2+'\t'+str(num/alpha))
            if beta != 0:
                if num / beta >= min_conf:
                    print (item2+' => '+item1+'\t'+str(num/beta))
    # length = 3
    elif length == 3:
        doc2 = db['candidate_L2']
        for w in ref.find():
            item1 = w['item_set'][0]
            item2 = w['item_set'][1]
            item3 = w['item_set'][2]
            num = w['support']
                      
            a1 = 0
            a2 = 0 
            a3 = 0
            for r1 in doc.find():
                comp = r1['item_set'][0]
                if item1 == comp:
                    a1 = r1['support']
                    break

            for r1 in doc.find():
                comp = r1['item_set'][0]
                if item2 == comp:
                    a2 = r1['support']
                    break
                
            for r1 in doc.find():
                comp = r1['item_set'][0]
                if item3 == comp:
                    a3 = r1['support']
                    break

            if a1 != 0:
                if num / a1 >= min_conf:
                    print(item1+' => '+item2+', '+item3+'\t'+str(num/a1))
            if a2 != 0:
                if num / a2 >= min_conf:
                    print(item2+' => '+item3+', '+item1+'\t'+str(num/a2))
            if a3 != 0:
                if num / a3 >= min_conf:
                    print(item3+' =>'+item1+', '+item2+'\t'+str(num/a3))

            L2_list = []
            for d in doc2.find():
                L2_list.append(d['item_set'] + [d['support']])

            for l in L2_list:
                if (l[0] == item1 and l[1] == item2) or (l[0] == item2 and l[1] == item1):
                    if num / l[2] >= min_conf:
                        print(item1+", "+item2+" => "+item3+"\t"+str(num/l[2]))
                    break

            for l in L2_list:
                if (l[0] == item1 and l[1] == item3) or (l[0] == item3 and l[1] == item1):
                    if num / l[2] >= min_conf:
                        print(item3+", "+item1+" => "+item2+"\t"+str(num/l[2]))
                    break


            for l in L2_list:
                if (l[0] == item2 and l[1] == item3) or (l[0] == item3 and l[1] == item2):
                    if num / l[2] >= min_conf:
                        print(item2+", "+item3+" => "+item1+"\t"+str(num/l[2]))
                    break



if __name__ == "__main__":
    make_stop_word()
    printMenu()
    selector = int(input())
    if selector == 0:
        p0()
    elif selector == 1:
        p1()
        p3()
    elif selector == 2:
        p2()
    elif selector == 3:
        p4()
    elif selector == 4:
        print("input length of the frequent item:")
        length = int(input())
        p5(length)
    elif selector == 5:
        print("input length of the frequent item:")
        length = int(input())
        p6(length)
