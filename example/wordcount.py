# -*- coding: utf-8 -*-
"""
Created on Fri Mar 30 13:50:16 2018

@author: Okada
"""

def main():
    import sys
    import os
    import re
    
    input_file = sys.argv[1]
    output_file = sys.argv[2]
    
    if os.path.exists(os.path.dirname(output_file)) == False:
        os.makedirs(os.path.dirname(output_file))
        
    # read line and split word, next count up.
    p = re.compile(r'[^a-zA-Z0-9 ]')
    dic = {}
    for l in open(input_file).readlines():
        words = p.sub("", l).split(" ")
        for word in words:
            word = word.lower()
            if word == "":
                continue
            if word.isdigit():
                continue
            
            if word in dic.keys():
                dic[word] += 1
            else:
                dic[word] = 1
    
    # choise Top 100
    li = []
    vmax = max(dic.values())
    for key in sorted(dic.items(), key=lambda x: x[1], reverse=True):
        li.append((key[0], key[1], (vmax-key[1])))
        if len(li) >= 100:
            break
    
    # sort by count -> word
    li.sort(key=lambda x: [x[2], x[0]])
    fw = open(output_file, "w")
    for key in li:
        fw.write("%24s: %4d\n" % (key[0], key[1]))
    fw.close()

if __name__ == "__main__":
    main()

