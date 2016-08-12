#!/usr/bin/env python
# -*- coding: utf-8 -*-
import imp
import os
import urllib
import json
import operator
import datetime

from flask import request
from flask import render_template
from flask import jsonify

from inspirobot import Inspirobot

from mdchecker import app
from mdchecker import db

from models.models import UnitTestResult
from models.models import ResourceMd
from models.models import TestSession
from models.models import MdReport


# default configuration
# if you want to change this, copy server.cfg.DIST into server.cfg for werkzeug config
# and app.json.DIST into app.json for app config
#
cfg = {
    'proxy': '',
    'cswurl':        'http://geobretagne.fr/geonetwork/srv/fre/csw',
    'xmlurlprefix':  'http://geobretagne.fr/geonetwork/srv/fre/xml_iso19139?uuid=',
    'viewurlprefix': 'http://geobretagne.fr/geonetwork/apps/georchestra/?uuid=',

    'maxrecords':    20,
    'maxharvest':    250,
    'maxmaxharvest': 2000,
    'sortby':        'score',
    'ns': {
        'gmd': u'http://www.isotc211.org/2005/gmd',
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
appfile = 'mdchecker/conf/app.json'
try:
    if not(os.path.isfile(appfile)):
        f = open(appfile, 'w')
        json.dump(cfg, f, indent=True)
        f.close()
    cfg.update(json.load(open(appfile)))
except:
    app.logger.error(u'cant read or write %s, using defaults' % appfile)

# import plugins
for plugin in cfg['plugins']:
    path = os.path.join(u'mdchecker/plugins', plugin)
    if os.path.isfile(path):
        try:
            imp.load_source(plugin, path)
            app.logger.info(u'module %s successfully loaded' % plugin)
        except:
            app.logger.error(u'module %s not loaded' % plugin)

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


def getMdUnitTests():
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
    
    args['maxharvest'] = min(int(request.args.get(
        'maxharvest', default=cfg['maxharvest'], type=int)), cfg['maxmaxharvest'])
    args['nextrecord'] = int(request.args.get('nextrecord', default=0, type=int))

    if request.args.get('sortby') in ['score', 'uuid', 'title', 'OrganisationName', 'date']:
        args['sortby'] = request.args.get('sortby')
    
    # missing validation
    args['id'] = request.args.get('id', '')
    return args


def doWeNeedToProcessRequest(request):
    return (request.args.has_key('OrganisationName') or request.args.has_key('anytext') or
        request.args.has_key('id') or request.args.has_key('format'))


def runTests(args, mdUnitTests):
    """perform tests, return metadatas, count, score"""
    metadatas = []
    count = {'matches': 0, 'returned': 0}
    score = 0

    # inspirobot instance
    inspirobot = Inspirobot.Inspirobot()
    if cfg.get('proxy', ''):
        inspirobot.setproxy(cfg['proxy'])

    if args['anytext'].strip() == "":
        args['anytext'] = "*"

    if args['OrganisationName'].strip() == "":
        args['OrganisationName'] = "*"

    #do we still need this test?
    if args['OrganisationName'] or args['anytext'] or args['id'] or args['format'] == 'json':

        # owslib constraint
        constraintstr = u"Type = dataset  && anytext = %(anytext)s" % args
        if args['OrganisationName']:
            constraintstr += u" && OrganisationName = %(OrganisationName)s" % args
        if args['id']:
            constraintstr += u" && Identifier = %(id)s" % args
        constraints = inspirobot.parseFilter(constraintstr)

        # get match count
        count = inspirobot.mdcount(
            cfg['cswurl'], constraints=constraints, startrecord=args['nextrecord'], maxharvest=args['maxharvest'])

        # get metadatas
        records = inspirobot.mdsearch(
            cfg['cswurl'],
            esn='full',
            constraints=constraints,
            startrecord=args['nextrecord'],
            maxrecords=cfg['maxrecords'],
            maxharvest=args['maxharvest']
        )

        # Test session db record
        test_datetime = datetime.datetime.utcnow()
        ts = TestSession(
            cat_url=cfg['cswurl'],
            filter=constraintstr,
            date=datetime.datetime.utcnow()
        )
        db.session.add(ts)

        # run tests
        for rec_id, rec in records.iteritems():
            meta = Inspirobot.MD(rec.xml)
            meta.run(mdUnitTests)
            metadatas.append(meta)

            # resource metadata db record
            # look for an existing metadata with the same cat_url and file_id
            md = ResourceMd.query.filter_by(
                cat_url=cfg['cswurl'],
                file_id=meta.fileIdentifier
            ).first()
            if md is None and meta.MD_Identifier.strip() != "":
                md = ResourceMd.query.filter_by(
                    cat_url=cfg['cswurl'],
                    res_uri=meta.MD_Identifier
                ).first()
            if md is None:
                md = ResourceMd(
                    cat_url=cfg['cswurl'],
                    file_id=meta.fileIdentifier,
                    res_uri=meta.MD_Identifier,
                    res_title=meta.title,
                    res_abstract=meta.abstract,
                    res_organisation_name=meta.OrganisationName
                )
                db.session.add(md)
            else:
                md.file_id = meta.fileIdentifier
                md.res_uri = meta.MD_Identifier
                md.res_title = meta.title
                md.res_abstract = meta.abstract
                md.res_organisation_name = meta.OrganisationName

            # report for on medatada record and one test session in db
            mr = MdReport(
                test_session=ts,
                md=md,
                score=meta.score
            )
            db.session.add(mr)

            for report in meta.reports:

                for result in report.results:

                    # result of one unit test in db
                    unit_test_result = UnitTestResult(
                        md_report = mr,
                        test_id = report.name,
                        test_result_level = result[0],
                        test_result_text = result[1]
                    )
                    db.session.add(unit_test_result)
        db.session.commit()

        score = sum(md.score for md in metadatas) / max(len(metadatas), 1)
            
        # metadata order
        if args['sortby'] == 'score':
            metadatas.sort(key=operator.attrgetter('score'))
        elif args['sortby'] == 'uuid':
            metadatas.sort(key=operator.attrgetter('fileIdentifier'))
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
def byId(rec_id='', format='html'):
    args = {
        'OrganisationName': '',
        'anytext':          '',
        'maxharvest':       cfg['maxharvest'],
        'sortby':           cfg['sortby'],
        'nextrecord':       0,
        'id':               rec_id,
        'roles':            [],
        'format':           format
    }
    mdUnitTests = getMdUnitTests()
    metadatas, count, score = runTests(args, mdUnitTests)
    
    if args['format'] == 'json':
        return jsonify(
            matches=count,
            score=score,
            metadatas=[md.asDict() for md in metadatas]
        )
    else:
        # paging for html
        pageUrls = [(n, getPermalink({
            'OrganisationName': args['OrganisationName'],
            'nextrecord':n*args['maxharvest'],
            'maxharvest':args['maxharvest']}))
            for n in range(1+count['matches'] // args['maxharvest'])
        ]
        return render_template(
            'inspirobot.html', cfg=cfg, args=args, score=score,
            metas=metadatas, tests=mdUnitTests, count=count, pages=pageUrls)


@app.route("/")
def index():
    args = {
        'OrganisationName': '',
        'anytext':          '',
        'maxharvest':       cfg['maxharvest'],
        'sortby':           cfg['sortby'],
        'nextrecord':       0,
        'id':               '',
        'roles':            [],
        'format':           'html'
    }
    mdUnitTests = getMdUnitTests()
    metadatas = []
    count = {'matches': 0, 'returned': 0}
    score = 0

    # querystring parser
    request_args = getArgsFromQuery(request)
    args.update(getArgsFromQuery(request))

    if doWeNeedToProcessRequest(request):
        metadatas, count, score = runTests(args, mdUnitTests)
    # if args['OrganisationName'] or args['anytext'] or args['id'] or args['format'] == 'json':
    #     metadatas, count, score = runTests(args, mdUnitTests)

    if args['format'] == 'json':
        return jsonify(
            matches=count,
            score=score,
            metadatas=[md.asDict() for md in metadatas]
        )
    else:
        # paging for html
        pageUrls = [(n, getPermalink({
            'OrganisationName': args['OrganisationName'],
            'nextrecord':n*args['maxharvest'],
            'maxharvest':args['maxharvest']}))
            for n in range(1+count['matches'] // args['maxharvest'])
        ]

        return render_template(
            'inspirobot.html', cfg=cfg, args=args, score=score,
            metas=metadatas, count=count, pages=pageUrls)


@app.route("/session/")
def session_list():

    sessions = TestSession.query
    return object_list('session_list.html', sessions, cfg=cfg)


@app.route("/session/<id>/")
def session_by_id(id=None):

    session = TestSession.query.filter_by(
                id=id
            ).first()
    print(id)
    print(session)

    return render_template(
        'session_id.html', cfg=cfg, session=session)


@app.route("/tests/")
def test_description():
    mdUnitTests = getMdUnitTests()

    return render_template(
        'test_description.html', cfg=cfg, tests=mdUnitTests)


def object_list(template_name, query, paginate_by=10, **context):
    page = request.args.get('page')
    if page and page.isdigit():
        page = int(page)
    else:
        page = 1

    object_list = query.paginate(page, paginate_by)
    return render_template(template_name, object_list=object_list, **context)
