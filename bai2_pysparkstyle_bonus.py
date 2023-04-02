# -*- coding: utf-8 -*-
"""bai2-pysparkstyle-bonus

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1VjUdXRINTgwFkl-y-b9YD2Ocqg_HPrO5
"""

!pip install pyspark
!pip install -U -q PyDrive
!apt install openjdk-8-jdk-headless -qq
import os
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-8-op"

import os
os.environ["JAVA_HOME"] = "/usr/lib/jvm/java-8-openjdk-amd64"

from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
from google.colab import auth
from oauth2client.client import GoogleCredentials

# Authenticate and create the PyDrive client
auth.authenticate_user()
gauth = GoogleAuth()
gauth.credentials = GoogleCredentials.get_application_default()
drive = GoogleDrive(gauth)

from pyspark.sql import *
from pyspark.sql.functions import *
from pyspark import SparkContext
import pandas as pd

# create the Spark Session
spark = SparkSession.builder.getOrCreate()

# create the Spark Context
sc = spark.sparkContext

# YOUR
txt = spark.read.text('/content/drive/MyDrive/browsing.txt')

import re, sys, operator
from pyspark import SparkConf, SparkContext

lines = sc.textFile('/content/drive/MyDrive/browsing.txt')
baskets = lines.map(lambda l: l.split())
N = baskets.count()

#def uniq_helper(basket):
#    return len(set(basket)) != len(basket)
#uniq = baskets.map(uniq_helper).sum() # 3 baskets have repeated items

baskets = baskets.map(lambda b: sorted(set(b)))

# singles

def singles_helper(basket):
    ret = []
    for item in basket:
        ret.append((item, 1))
    return ret


singles_support = baskets.flatMap(singles_helper)
singles_support = singles_support.reduceByKey(operator.add)
singles_support = singles_support.filter(lambda x: x[1] >= 100)

singles_support_b = {}
for item, support in singles_support.collect():
    singles_support_b[item] = support

singles_support_b = sc.broadcast(singles_support_b)

# doubles

def doubles_helper(basket):
    singles = singles_support_b.value
    ret = []
    for i in range(len(basket)):
        if basket[i] in singles:
            for j in range(i):
                if basket[j] in singles:
                    ret.append(((basket[j], basket[i]), 1)) # basket is sorted
    return ret


doubles_support = baskets.flatMap(doubles_helper)
doubles_support = doubles_support.reduceByKey(operator.add)
doubles_support = doubles_support.filter(lambda x: x[1] >= 100)

def confidence_doubles_helper(double_support):
    double, support = double_support
    support = float(support)
    u, v = double
    singles = singles_support_b.value
    uv_conf = support / singles[u]
    vu_conf = support / singles[v]
    return (('%s -> %s' % (u, v), uv_conf),
            ('%s -> %s' % (v, u), vu_conf))


doubles_conf = doubles_support.flatMap(confidence_doubles_helper)
doubles_conf = doubles_conf.sortBy(lambda x: (-x[1], x[0]))

doubles_support_b = {}
for entry, support in doubles_support.collect():
    doubles_support_b[entry] = support

doubles_support_b = sc.broadcast(doubles_support_b)

# triples

def triples_helper(basket):
    doubles = doubles_support_b.value
    singles = singles_support_b.value
    ret = []
    for i in range(len(basket)):
        if basket[i] not in singles:
            continue
        for j in range(i):
            if basket[j] not in singles:
                continue
            if (basket[j], basket[i]) not in doubles:
                continue
            for k in range(j):
                if basket[k] not in singles:
                    continue
                if (basket[k], basket[j]) not in doubles:
                    continue
                if (basket[k], basket[i]) not in doubles:
                    continue
                ret.append(((basket[k], basket[j], basket[i]), 1))
    return ret


triples_support = baskets.flatMap(triples_helper)
triples_support = triples_support.reduceByKey(operator.add)
triples_support = triples_support.filter(lambda x: x[1] >= 100)

def confidence_triples_helper(triple_support):
    doubles = doubles_support_b.value
    triple, support = triple_support
    support = float(support)
    u, v, w = triple
    uv_w = support / doubles[u, v]
    uw_v = support / doubles[u, w]
    vw_u = support / doubles[v, w]
    return (('(%s, %s) -> %s' % (u, v, w), uv_w),
            ('(%s, %s) -> %s' % (u, w, v), uw_v),
            ('(%s, %s) -> %s' % (v, w, u), vw_u))


triples_conf = triples_support.flatMap(confidence_triples_helper)
triples_conf = triples_conf.sortBy(lambda x: (-x[1], x[0]))

with open('./bai2_homework1_.txt', 'w') as f:
    f.write(str(doubles_conf.take(5)))
    f.write('\n')
    f.write(str(triples_conf.take(5)))