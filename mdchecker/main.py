#!/usr/bin/env python
# -*- coding: utf-8 -*-
import imp
import os
import urllib
import json
import operator
from flask import request
from flask import render_template
from flask import jsonify

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

    'maxrecords': 20,
    'maxharvest': 250,
    'maxmaxharvest': 2000,
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
    app.logger.error(u'cant read or write %s, using defaults'%appfile)

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
    args['format'] = request.args.get('format', '')
    
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


def runTests(args, mdUnitTests):
    """perform tests, return metadatas, count, score"""
    metadatas = []
    count = {'matches': 0, 'returned': 0}
    score = 0

    # inspirobot instance
    inspirobot = Inspirobot.Inspirobot()
    if cfg.get('proxy', ''):
        inspirobot.setproxy(cfg['proxy'])

    if args['OrganisationName'] or args['anytext'] or args['id'] or args['format'] == 'json':
        # owslib constraint
        constraintstr = u"Type = dataset  && anytext = %(anytext)s"%args
        if args['OrganisationName']:
            constraintstr += u" && OrganisationName = %(OrganisationName)s"%args
        if args['id']:
            constraintstr += u" && Identifier = %(id)s"%args
        constraints = inspirobot.parseFilter(constraintstr)

        # get match count
        count = inspirobot.mdcount(cfg['cswurl'], constraints=constraints, startrecord=args['nextrecord'], maxharvest=args['maxharvest'])

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
            meta = Inspirobot.MD(rec.xml)
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
        
        return metadatas, count, score


### routes ######################################
@app.route('/md/')
@app.route('/md/<id>')
@app.route('/md/<id>/<format>')
def byId(id='', format='html'):
    args = {
        'OrganisationName': '',
        'anytext': '',
        'maxharvest': cfg['maxharvest'],
        'sortby': cfg['sortby'],
        'nextrecord': 0,
        'id': id,
        'roles': [],
        'format': format
    }
    mdUnitTests = getMdUnitTests(cfg)
    metadatas, count, score = runTests(args, mdUnitTests)
    
    if args['format'] == 'json':
        return jsonify(
            matches =  count,
            score = score,
            metadatas = [md.asDict() for md in metadatas]
        )
    else:
        # paging for html
        pageUrls = [(n, getPermalink({'OrganisationName': args['OrganisationName'], 'nextrecord':n*args['maxharvest'], 'maxharvest':args['maxharvest']}))
            for n in range(1+count['matches'] //args['maxharvest'])
        ]
        return render_template('inspirobot.html', cfg=cfg, args=args, score=score, metas=metadatas, tests=mdUnitTests, count=count, pages=pageUrls)





@app.route("/")
def index():
    args = {
        'OrganisationName': '',
        'anytext': '',
        'maxharvest': cfg['maxharvest'],
        'sortby': cfg['sortby'],
        'nextrecord': 0,
        'id':'',
        'roles': [],
        'format': 'html'
    }
    mdUnitTests = getMdUnitTests(cfg)
    metadatas = []
    count = {'matches': 0, 'returned': 0}
    score = 0

    # querystring parser
    args.update(getArgsFromQuery(request))


    if args['OrganisationName'] or args['anytext'] or args['id'] or args['format'] == 'json':
        metadatas, count, score = runTests(args, mdUnitTests)



    if args['format'] == 'json':
        return jsonify(
            matches =  count,
            score = score,
            metadatas = [md.asDict() for md in metadatas]
        )
    else:
        # paging for html
        pageUrls = [(n, getPermalink({'OrganisationName': args['OrganisationName'], 'nextrecord':n*args['maxharvest'], 'maxharvest':args['maxharvest']}))
            for n in range(1+count['matches'] //args['maxharvest'])
        ]
        return render_template('inspirobot.html', cfg=cfg, args=args, score=score, metas=metadatas, tests=mdUnitTests, count=count, pages=pageUrls)


