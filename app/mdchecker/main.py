#!/usr/bin/env python
# -*- coding: utf-8 -*-
import imp
import os
import io
import csv
import urllib
import json
import operator
import datetime
import logging

from flask import request
from flask import render_template
from flask import Response
from flask import url_for
from flask import redirect
from flask import abort
from flask import jsonify

from inspirobot import Inspirobot

from mdchecker import app
from mdchecker import db

from models.models import get_organisation_names_like
from models.models import UnitTestResult
from models.models import ResourceMd
from models.models import TestSession
from models.models import MdReport

logging.basicConfig(level=logging.INFO)


# default configuration
# and app.json.DIST into app.json for app config
#
cfg = {
    'proxy': '',
    "cats": [
        {
            "name": u"GéoBretagne",
            "cswurl": "http://geobretagne.fr/geonetwork/srv/fre/csw",
            "xmlurlprefix": "http://geobretagne.fr/geonetwork/srv/fre/xml_iso19139?uuid=",
            "viewurlprefix": "http://geobretagne.fr/geonetwork/apps/georchestra/?uuid="
        }
    ],

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
        "testDigitalTransferOptions.py",
        "testDefault.py"
    ],
    'mail_md': u"""la_metadonnee
%s%s
a_recu_un_score_de
%s/100
et_merite_votre_attention"""
}

# loads app file configuration, dumps a fresh one if missing
appfile = os.path.join(os.path.dirname(__file__), 'conf', 'app.json')
try:
    if not(os.path.isfile(appfile)):
        f = open(appfile, 'w')
        json.dump(cfg, f, indent=True)
        f.close()
    cfg.update(json.load(open(appfile)))
except Exception as e:
    app.logger.error(e)
    app.logger.error(u'cant read or write %s, using defaults' % appfile)

import pkgutil
path = os.path.join(os.path.dirname(__file__), u'plugins')
modules = list(pkgutil.walk_packages([path]))
module_names = [os.path.splitext(plugin)[0] for plugin in cfg['plugins']]

for module in modules:
    module_impoter = module[0]
    module_name = module[1]

    if module_name in module_names:
        try:
            module_loader = module_impoter.find_module(module_name)
            module_loader.load_module(module_name)
            module_names.remove(module_name)
            app.logger.info(u'module %s successfully loaded' % module_name)
        except:
            app.logger.error(u'module %s not loaded' % module_name)

if len(module_names) > 0:
    app.logger.error(u'The following plugins have not been found: %s' % module_names)

### utility fn #######################################


def u(s):
    """
    decodes utf8
    """
    if isinstance(s, unicode): 
        return s.encode('utf-8')
    if isinstance(s, str):
        return s.decode('utf-8')
    # fix this, item may be unicode
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


def getMdUnitTestsAsDict():
    unit_tests = getMdUnitTests()
    unit_tests_names = [unit_test.name for unit_test in unit_tests]
    return dict(zip(unit_tests_names, unit_tests))


def get_cat_with_name(cat_name):
    """
    Returns the catalogue dictionary described in cfg with the given name

    @param cat_name:    Name of the catalogue
    @return:            dict describing the catalogue
    """

    the_cat = None

    for cat in cfg["cats"]:
        if cat["name"] == cat_name:
            the_cat = cat
            break

    return the_cat


def get_cat_with_url(cat_url):
    """
    Returns the catalogue dictionary which url is given in parameter

    @param cat_url:     URL of the catalogue
    @return:            dict describing the catalogue
    """

    the_cat = None

    for cat in cfg["cats"]:
        if cat["cswurl"] == cat_url:
            the_cat = cat
            break

    return the_cat


def getArgsFromQuery(request):
    """
    parses and validates query arguments
    """
    args = {}

    # missing validation
    args['OrganisationName'] = request.args.get('OrganisationName', '')

    # missing validation
    args['anytext'] = request.args.get('anytext', '')

    if request.path == "/quick_test/":
        # missing validation
        args['format'] = request.args.get('format', '')

        # missing validation
        args['id'] = request.args.get('id', '')

        if request.args.get('sortby') in ['score', 'uuid', 'title', 'OrganisationName', 'date']:
            args['sortby'] = request.args.get('sortby')

        args['nextrecord'] = int(request.args.get('nextrecord', default=0, type=int))

        args['maxharvest'] = min(int(request.args.get(
            'maxharvest', default=cfg['maxharvest'], type=int)), cfg['maxmaxharvest'])

        args['cswurl'] = get_cat_with_name(request.args.get('cat', cfg["cats"][0]["name"]))["cswurl"]

    elif request.path == "/new_session/creation/":

        args['maxharvest'] = min(int(request.args.get(
            'maxharvest', default=cfg['maxharvest'], type=int)), cfg['maxmaxharvest'])

        args['cswurl'] = get_cat_with_name(request.args.get('cat', cfg["cats"][0]["name"]))["cswurl"]

    return args


def doWeNeedToProcessRequest(request):
    return ('OrganisationName' in request.args or 'anytext' in request.args or
            'id' in request.args or 'format' in request.args)


class InspirobotWrapper(object):

    def __init__(self, test_params, unit_tests):

        self.md_records = None
        self.metadatas = None
        self.test_params = test_params
        self.unit_tests = unit_tests
        self.db = None
        self.constraints_str = None
        self.constraints_fes = None

        self.inspirobot = self.create_inspirobot_instance()
        self.build_inspirobot_constraints()

    def set_db(self, database):
        self.db = database

    def create_inspirobot_instance(self):
        cache_path = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir, u'cache'))
        inspirobot = Inspirobot.Inspirobot(cachepath=cache_path)
        if cfg.get('proxy', ''):
            inspirobot.setproxy(cfg['proxy'])
        return inspirobot

    def build_inspirobot_constraints(self):

        constraints_inspirobot = u"Type = dataset  && anytext = %(anytext)s" % self.test_params

        if self.test_params.get('OrganisationName', None) is not None:
            constraints_inspirobot += u" && OrganisationName = %(OrganisationName)s" % self.test_params

        if self.test_params.get('id', None) is not None:
            constraints_inspirobot += u" && Identifier = %(id)s" % self.test_params

        self.constraints_str = constraints_inspirobot
        self.constraints_fes = self.inspirobot.parseFilter(self.constraints_str)

    def run_unrecorded_tests(self):

        # get match count
        count = self.inspirobot.mdcount(
            self.test_params["cswurl"], constraints=self.constraints_fes,
            startrecord=self.test_params['nextrecord'],
            maxharvest=self.test_params['maxharvest'])

        # get metadatas
        self.md_records = self.inspirobot.mdsearch(
            self.test_params["cswurl"],
            esn='full',
            constraints=self.constraints_fes,
            startrecord=self.test_params['nextrecord'],
            maxrecords=cfg['maxrecords'],
            maxharvest=self.test_params['maxharvest']
        )

        self.run_tests_on_md_records()

        score = sum(md.score for md in self.metadatas) / max(len(self.metadatas), 1)

        # metadata order
        obsolete_date = datetime.datetime(1970,1,1)
        if self.test_params['sortby'] == 'score':
            self.metadatas.sort(key=operator.attrgetter('score'))
        elif self.test_params['sortby'] == 'uuid':
            self.metadatas.sort(key=operator.attrgetter('fileIdentifier'))
        elif self.test_params['sortby'] == 'title':
            self.metadatas.sort(key=operator.attrgetter('title'))
        elif self.test_params['sortby'] == 'OrganisationName':
            self.metadatas.sort(key=operator.attrgetter('OrganisationName'))
        elif self.test_params['sortby'] == 'date':
            self.metadatas.sort(key=lambda x: x.date or obsolete_date)

        return self.metadatas, count, score

    def run_and_record_tests(self, database):

        self.set_db(database)

        # get match count
        count = self.inspirobot.mdcount(
            self.test_params["cswurl"],
            constraints=self.constraints_fes,
            startrecord=0,
            maxharvest=1)

        # update maxharvest
        max_harvest = None
        if not ('maxharvest' in self.test_params and isinstance(self.test_params["maxharvest"], (int, long))):
            if isinstance(self.test_params["maxharvest"], (str, unicode)) and \
                    self.test_params["maxharvest"].strip().lower() == 'all':
                max_harvest = count["matches"]
            else:
                max_harvest = cfg["maxharvest"]
        elif self.test_params["maxharvest"] > count["matches"]:
            max_harvest = count["matches"]
        elif self.test_params["maxharvest"] == -1:
            max_harvest = count["matches"]
        elif self.test_params["maxharvest"] < 1:
            max_harvest = cfg["maxharvest"]
        else:
            max_harvest = self.test_params["maxharvest"]

        if count['matches'] == 0:
            max_harvest = 1

        # get metadata records
        self.md_records = self.inspirobot.mdsearch(
            self.test_params["cswurl"],
            esn='full',
            constraints=self.constraints_fes,
            startrecord=0,
            maxrecords=cfg['maxrecords'],
            maxharvest=max_harvest
        )

        new_session_id = self.run_tests_on_md_records(True)

        return new_session_id

    def run_tests_on_md_records(self, store_in_db=False):

        self.metadatas = []
        ts = None

        if store_in_db:
            # Test session db record
            ts = TestSession(
                cat_url=self.test_params["cswurl"],
                filter=self.constraints_str,
                date=datetime.datetime.utcnow(),
                max_harvest=self.test_params["maxharvest"]
            )
            self.db.session.add(ts)

        # run tests
        for rec_id, rec in self.md_records.iteritems():
            meta = Inspirobot.MD(rec.xml)
            meta.run(self.unit_tests)
            self.metadatas.append(meta)

            if store_in_db:
                # resource metadata db record
                # look for an existing metadata with the same cat_url and file_id
                md = ResourceMd.query.filter_by(
                    cat_url=self.test_params["cswurl"],
                    file_id=meta.fileIdentifier
                ).first()
                if md is None and meta.MD_Identifier.strip() != "":
                    md = ResourceMd.query.filter_by(
                        cat_url=self.test_params["cswurl"],
                        res_uri=meta.MD_Identifier
                    ).first()
                if md is None:
                    md = ResourceMd(
                        cat_url=self.test_params["cswurl"],
                        file_id=meta.fileIdentifier,
                        md_date=meta.md_date,
                        res_date=meta.date,
                        res_uri=meta.MD_Identifier,
                        res_title=meta.title,
                        res_abstract=meta.abstract,
                        res_organisation_name=meta.OrganisationName
                    )
                    self.db.session.add(md)
                else:
                    md.file_id = meta.fileIdentifier
                    md.md_date = meta.md_date
                    md.res_date = meta.date
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
                            md_report=mr,
                            test_name=report.name,
                            test_abstract=report.abstract,
                            test_result_level=result[0],
                            test_result_text=result[1]
                        )
                        db.session.add(unit_test_result)

        if store_in_db:
            db.session.commit()
            db.session.refresh(ts)
            return ts.id


### routes ######################################
@app.route('/md/')
@app.route('/md/<md_id>')
@app.route('/md/<md_id>/<format>')
def byId(md_id='', format='html'):
    args = {
        'OrganisationName': '',
        'anytext':          '',
        'maxharvest':       cfg['maxharvest'],
        'sortby':           cfg['sortby'],
        'nextrecord':       0,
        'id':               md_id,
        'roles':            [],
        'format':           format
    }
    mdUnitTests = getMdUnitTests()
    ins_wrapper = InspirobotWrapper(args, mdUnitTests)
    metadatas, count, score = ins_wrapper.run_unrecorded_tests()

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
        cat = get_cat_with_url(args["cswurl"])
        return render_template(
            'quick_test.html', cfg=cfg, cat=cat, args=args, score=score,
            metas=metadatas, tests=mdUnitTests, count=count, pages=pageUrls)


@app.route("/")
def index():
    return render_template('index.html', cfg=cfg)


@app.route("/quick_test/")
def quick_test():
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
    args.update(getArgsFromQuery(request))
    
    # bulk export
    if args['format'] in ['json', 'csv']:
        args['maxharvest'] = cfg['maxmaxharvest']

    if doWeNeedToProcessRequest(request):
        ins_wrapper = InspirobotWrapper(args, mdUnitTests)
        metadatas, count, score = ins_wrapper.run_unrecorded_tests()

    if args['format'] == 'json':
        return jsonify(
            matches=count,
            score=score,
            metadatas=[md.asDict() for md in metadatas]
        )
    elif args['format'] == 'csv':
            cat = get_cat_with_url(args["cswurl"])
            output = io.BytesIO()
            writer = csv.writer(output, dialect=csv.excel)
            writer.writerow( ('score', 'date', 'md_date', 'organisation', 'title','html', 'xml') )
            for md in metadatas:
                writer.writerow( (md.score, md.date, md.md_date, u(md.OrganisationName), u(md.title), cat["viewurlprefix"]+md.fileIdentifier, cat["xmlurlprefix"]+md.fileIdentifier) )
            return Response(output.getvalue(), mimetype='text/csv')
    else:
        cat = get_cat_with_url(args["cswurl"])

        # paging for html
        pageUrls = [(n, getPermalink({
            'cat': cat["name"],
            'OrganisationName': args['OrganisationName'],
            'anytext': args['anytext'],
            'nextrecord':n*args['maxharvest'],
            'maxharvest':args['maxharvest']}))
            for n in range(1+count['matches'] // args['maxharvest'])
        ]

        return render_template(
            'quick_test.html', cfg=cfg, cat=cat, args=args, score=score,
            metas=metadatas, count=count, pages=pageUrls)


@app.route("/new_session/")
def new_session():
    return render_template('new_session.html', cfg=cfg)


@app.route("/new_session/creation/")
def new_session_creation():

    args = {}
    args.update(getArgsFromQuery(request))

    mdUnitTests = getMdUnitTests()

    ins_wrapper = InspirobotWrapper(args, mdUnitTests)
    new_session_id = ins_wrapper.run_and_record_tests(db)

    if new_session_id is not None:
        return redirect(url_for("session_by_id", id=new_session_id))
    else:
        abort(500)


@app.route("/sessions/")
def session_list():

    sessions = TestSession.query.order_by(TestSession.date.desc())
    return object_list('session_list.html', sessions, cfg=cfg)


@app.route("/session/<id>/")
def session_by_id(id=None):

    session = TestSession.query.filter_by(
                id=id
            ).first()

    if session is None:
        abort(404)

    sort_by = "score"

    page = request.args.get('page')
    display = request.args.get('display')
    request_sort_by = request.args.get('sort_by')
    if request_sort_by:
        request_sort_by = request_sort_by.lower().strip()
        if request_sort_by in ("id", "title", "score", "organisation", "date"):
            sort_by = request_sort_by

    request_order = request.args.get('order')
    if request_order and request_order.lower().strip() == "desc":
        order = "desc"
    else:
        order = "asc"

    if sort_by == "id":
        if order == "asc":
            query = session.md_reports.join(ResourceMd).order_by("file_id")
        else:
            query = session.md_reports.join(ResourceMd).order_by("file_id desc")

    elif sort_by == "score":
        if order == "asc":
            query = session.md_reports.order_by(MdReport.score)
        else:
            query = session.md_reports.order_by(MdReport.score.desc())

    elif sort_by == "title":
        if order == "asc":
            query = session.md_reports.join(ResourceMd).order_by("res_title")
        else:
            query = session.md_reports.join(ResourceMd).order_by("res_title desc")

    elif sort_by == "organisation":
        if order == "asc":
            query = session.md_reports.join(ResourceMd).order_by("res_organisation_name")
        else:
            query = session.md_reports.join(ResourceMd).order_by("res_organisation_name desc")

    elif sort_by == "date":
        if order == "asc":
            query = session.md_reports.join(ResourceMd).order_by("md_date")
        else:
            query = session.md_reports.join(ResourceMd).order_by("md_date desc")

    cat = get_cat_with_url(session.cat_url)
    return object_list('session_id.html', query, cat=cat, cfg=cfg, session=session,
                       sort_by=sort_by, order=order, display=display, page=page)


@app.route("/test_description/")
def test_description():
    mdUnitTests = getMdUnitTests()

    return render_template('test_description.html', cfg=cfg, tests=mdUnitTests)


@app.route('/organisation_names/', methods=['GET'])
def organisation_names_autocomplete():
    q = request.args.get('q', '')
    results = get_organisation_names_like(q)
    return jsonify(results)


@app.errorhandler(404)
@app.errorhandler(500)
def page_not_found(e):
    return render_template("error.html", error=e)


def object_list(template_name, query, paginate_by=10, **context):
    page = request.args.get('page')
    if page and page.isdigit():
        page = int(page)
    else:
        page = 1

    object_list = query.paginate(page, paginate_by)
    return render_template(template_name, object_list=object_list, **context)
