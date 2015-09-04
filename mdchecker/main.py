#!/usr/bin/env python
# -*- coding: utf-8 -*-
import imp
import re
import os
import urllib
import copy
import json
import operator
import logging
from collections import OrderedDict
from lxml import etree
from io import StringIO, BytesIO
from flask import Flask
from flask import request
from flask import Response
from flask import render_template

from inspirobot import Inspirobot
from mdchecker import app

# default configuration
# if you want to change this, copy server.cfg.DIST into server.cfg for werkzeug config
# and app.json.DIST into app.json for app config
#
cfg = {
    'proxy': '',
    'cswurl': 'http://geobretagne.fr/geonetwork/srv/fre/csw',
    'xmlurlprefix': 'http://geobretagne.fr/geonetwork/srv/fre/xml_iso19139?uuid=',
    'viewurlprefix': 'http://geobretagne.fr/geonetwork/apps/georchestra/?uuid=',

    'maxrecords': 2000,
    'maxharvest': 25,
    'maxmaxharvest': 250,
    'sortby': 'score',
    'ns': {
        'gmd':  u'http://www.isotc211.org/2005/gmd',
        'gco': u'http://www.isotc211.org/2005/gco'
    },
    "plugins": [
        "testSpatial.py",
        "testGenealogy.py",
        "testMD_Identifier.py",
        "testContact.py",
        "testLicence.py",
        "testInspireKeyword.py",
        "testDigitalTransferOptions.py"
    ],
    'mail_md': u"""la_metadonnee
%s%s
a_recu_un_score_de
%s/100
et_merite_votre_attention"""
}

# loads app file configuration, dumps a fresh one if missing
try:
    appfile = 'mdchecker/conf/app.json'
    if not(os.path.isfile(appfile)):
        f=open(appfile, 'w')
        json.dump(cfg, f, indent=True)
        f.close()
    cfg.update(json.load(open(appfile)))
except:
    app.logger.error(u'missing or bad app.json, using defaults')

# import plugins
for plugin in cfg['plugins']:
    path = os.path.join(u'mdchecker/plugins',plugin)
    if os.path.isfile(path):
        try:
            imp.load_source(plugin, path)
            app.logger.info(u'module %s successfully loaded'%plugin)
        except:
            app.logger.error(u'module %s not loaded'%plugin)

### utility fn #######################################

def u(s):
    """
    decodes utf8
    """
    if isinstance(s, str):
        return s.decode('utf-8')
    elif isinstance(s, list):
        return [i.decode('utf-8') for i in s]


def xmlGetTextNodes(doc, xpath):
    """
    shorthand to retrieve serialized text nodes matching a specific xpath
    """
    return ', '.join(doc.xpath(xpath, namespaces=cfg['ns']))
    
def getPermalink(args):
    """
    return a permalink for current arguments
    """
    escaped = {}
    for k, v in args.iteritems():
        if isinstance(v, unicode):
            escaped[k] = v.encode('utf8')
        else:
            escaped[k] = str(v)
    return '.?'+urllib.urlencode(escaped)
    
def getMdUnitTests(cfg):
    return [test(cfg) for test in Inspirobot.MdUnitTest.__subclasses__()]


def getArgsFromQuery(request):
    """
    parses and validates query arguments
    """
    args = {}
    
    # missing validation
    args['OrganisationName'] = request.args.get('OrganisationName', '')
    
    # missing validation
    args['anytext'] = request.args.get('anytext', '')
    
    args['maxharvest'] = min(int(request.args.get('maxharvest', default=cfg['maxharvest'], type=int)), cfg['maxmaxharvest'])
    args['nextrecord'] = int(request.args.get('nextrecord', default=0, type=int))

    if request.args.get('sortby') in ['score', 'uuid', 'title', 'OrganisationName', 'date']:
        args['sortby'] = request.args.get('sortby')
    
    # missing validation
    args['id'] = request.args.get('id', '')
    return args


### metadata class ######################################


class MD:
    """
    metadata with unit test methods
    """
    def __init__(self, xml):
        self.xml = xml
        self.md = etree.parse(StringIO(u(xml)))
        self.fileIdentifier = xmlGetTextNodes(self.md, '/gmd:MD_Metadata/gmd:fileIdentifier/gco:CharacterString/text()')
        self.MD_Identifier = xmlGetTextNodes(self.md, '/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()')
        self.title = xmlGetTextNodes(self.md, '/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/gmd:title/gco:CharacterString/text()')
        self.OrganisationName = xmlGetTextNodes(self.md, '/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/gmd:pointOfContact/gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString/text()')
        self.abstract = xmlGetTextNodes(self.md, '/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/gmd:abstract/gco:CharacterString/text()')
        self.date = xmlGetTextNodes(self.md, '/gmd:MD_Metadata/gmd:dateStamp/gco:DateTime/text()').split('-')[0]
        self.contact = {
            'mails': self.md.xpath('/gmd:MD_Metadata/gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString/text()', namespaces=cfg['ns'])
        }
        self.reports = []
        self.score = 100

    def __repr__(self):
        return self.fileIdentifier
        
    def __str__(self):
        return self.fileIdentifier
        
    def getScore(self):
        score = 100
        for rep in self.reports:
            if rep.getLevel() == 'critical':
                score = score - 100
            elif rep.getLevel() == 'error':
                score = score - 25
            elif rep.getLevel() == 'warning':
                score = score - 10
        return score
    
    def asDict(self):
        return {
            'fileIdentifier': self.fileIdentifier,
            'MD_Identifier': self.MD_Identifier,
            'title': self.title,
            'OrganisationName': self.OrganisationName,
            'abstract': self.abstract,
            'date': self.date,
            'contact': self.contact,
            'reports': [rep.asDict(['warning', 'error', 'critical']) for rep in self.reports],
            'score': self.getScore()
        }
        
    def run(self, utests):
        for utest in utests:
            utest.run(self.md)
            results = utest.getReports()
            for rep in results:
                if rep.getLevel() == 'critical':
                    self.score = self.score - 100
                elif rep.getLevel() == 'error':
                     self.score =  self.score - 25
                elif rep.getLevel() == 'warning':
                     self.score =  self.score - 10
                self.reports.append(rep)
                
    def getMailtoQS(self):
        return urllib.urlencode({
            'subject': ('[inspirobot][%s/100]-%s'%(self.getScore(),self.title)).encode('utf-8'),
            'body': cfg["mail_md"]%(cfg['viewurlprefix'],self.fileIdentifier,self.score)
        })

### end class ######################################





@app.route("/")
def index():
    args = {
        'OrganisationName': '',
        'anytext': '',
        'maxharvest': cfg['maxharvest'],
        'sortby': cfg['sortby'],
        'nextrecord': 0,
        'id':'',
        'roles': []
    }
    mdUnitTests = getMdUnitTests(cfg)
    metadatas = []
    count = {'matches': 0, 'returned': 0}
    score = 0
    pageUrls = []

    # querystring parser
    args.update(getArgsFromQuery(request))

    # inspirobot instance
    inspirobot = Inspirobot.Inspirobot()
    if cfg.get('proxy', ''):
        inspirobot.setproxy(cfg['proxy'])

    if args['OrganisationName'] or args['anytext'] or args['id']:
        # owslib constraint
        constraintstr = u"Type = dataset  && anytext = %(anytext)s"%args
        if args['OrganisationName']:
            constraintstr += u" && OrganisationName = %(OrganisationName)s"%args
        if args['id']:
            constraintstr += u" && Identifier = %(id)s"%args
        constraints = inspirobot.parseFilter(constraintstr)
        
        # get match count
        count = inspirobot.mdcount(cfg['cswurl'], constraints=constraints)
        
        # get metadatas
        records =  inspirobot.mdsearch(
            cfg['cswurl'],
            esn='full',
            constraints=constraints,
            startrecord=args['nextrecord'],
            maxrecords=cfg['maxrecords'],
            maxharvest=args['maxharvest']
        )
        
        # run tests
        for id,rec in records.iteritems():
            meta = MD(rec.xml)
            meta.run(mdUnitTests)
            metadatas.append(meta)
            
        score = sum(md.score for md in metadatas) / max(len(metadatas),1)
            
        # metadata order
        if args['sortby'] == 'score':
            metadatas.sort(key=operator.attrgetter('score'))
        elif args['sortby'] == 'uuid':
            metadatas.sort( key=operator.attrgetter('fileIdentifier'))
        elif args['sortby'] == 'title':
            metadatas.sort(key=operator.attrgetter('title'))
        elif args['sortby'] == 'OrganisationName':
            metadatas.sort(key=operator.attrgetter('OrganisationName'))
        elif args['sortby'] == 'date':
            metadatas.sort(key=operator.attrgetter('date'))

        # paging
        pageUrls = [(n, getPermalink({'OrganisationName': args['OrganisationName'], 'nextrecord':n*args['maxharvest'], 'maxharvest':args['maxharvest']}))
            for n in range(1+count['matches'] //args['maxharvest'])
        ]
    
    return render_template('inspirobot.html', cfg=cfg, args=args, score=score, metas=metadatas, tests=mdUnitTests, count=count, pages=pageUrls)

