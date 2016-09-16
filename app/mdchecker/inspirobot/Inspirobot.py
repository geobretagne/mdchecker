#!/usr/bin/env python
# -*- coding: utf-8 -*-

import urllib2
from owslib.csw import CatalogueServiceWeb
from owslib import fes
from lxml import etree
import os
import logging
import datetime
import dateutil.parser
import hashlib
import json
import shapefile

logging.basicConfig(level=logging.INFO)


### utility fn #######################################
def u(s):
    """
    decodes utf8
    """
    if isinstance(s, str):
        return s.decode('utf-8')
    elif isinstance(s, list):
        return [i.decode('utf-8') for i in s]


def xmlGetTextNodes(doc, xpath, namespaces):
    """
    shorthand to retrieve serialized text nodes matching a specific xpath
    """
    return ', '.join(doc.xpath(xpath, namespaces={
        'gmd':  u'http://www.isotc211.org/2005/gmd',
        'gco': u'http://www.isotc211.org/2005/gco'
    }))


def parse_string_for_max_date(dates_as_str):
    try:
        dates_python = []
        for date_str in dates_as_str.split(","):
            date_str = date_str.strip()
            if date_str != "":
                date_python = dateutil.parser.parse(date_str, ignoretz=True)
                dates_python.append(date_python)
        if len(dates_python) > 0:
            return max(dates_python)
    except:
        logging.error('date parsing error : ' +dates_as_str)
        return None

################################################


class Inspirobot(object):
    """Inspirobot (c) geOrchestra project 2014
    
    tests and transactions against CSW (GeoNetwork) and OWS (GeoServer)
    to improve metadatas and capabilities qualities.
    """
    
    MANIFEST = 'MANIFEST.json'
    OUTPUTSCHEMA = "http://www.isotc211.org/2005/gmd"
    QUERYABLES = [
        'Operation',
        'Format',
        'OrganisationName',
        'Type',
        'ServiceType',
        'DistanceValue',
        'ResourceLanguage',
        'RevisionDate',
        'OperatesOn',
        'GeographicDescriptionCode',
        'AnyText',
        'Modified',
        'PublicationDate',
        'ResourceIdentifier',
        'ParentIdentifier',
        'Identifier',
        'CouplingType',
        'TopicCategory',
        'OperatesOnIdentifier',
        'ServiceTypeVersion',
        'TempExtent_end',
        'Subject',
        'CreationDate',
        'OperatesOnName',
        'Title',
        'DistanceUOM',
        'Denominator',
        'AlternateTitle',
        'Language',
        'TempExtent_begin',
        'HasSecurityConstraints',
        'KeywordType',
        'Abstract',
        'Relation',
        'AccessConstraints',
        'ResponsiblePartyRole',
        'OnlineResourceMimeType',
        'OnlineResourceType',
        'Lineage',
        'SpecificationDate',
        'ConditionApplyingToAccessAndUse',
        'SpecificationDateType',
        'MetadataPointOfContact',
        'Classification',
        'Date',
        'OtherConstraints',
        'Degree',
        'SpecificationTitle']
        
    cachepath = ''
    cswlist = {}
    
    def __init__(self, cachepath='cache'):
        """Reads the manifest files fom the cache and registers csw"""
        self.cachepath = cachepath
    
        for d in os.listdir(self.cachepath):
            cswpath = os.path.join(self.cachepath, d)
            manpath = os.path.join(cswpath, self.MANIFEST)
            if os.path.isfile(manpath):
                manifest = json.loads(open(manpath).read())
                self.cswlist[manifest['cswurl']] = manifest
                logging.info('%s %s md cached' % (manifest['cswurl'], len(os.listdir(cswpath))))

    def getQueryables(self):
        return self.QUERYABLES

    def setproxy(self, proxy):
        """Sets an outgoing http proxy"""
        if proxy:
            proxyHandler = urllib2.ProxyHandler({"http": proxy, "https": proxy})
            opener = urllib2.build_opener(proxyHandler)
            urllib2.install_opener(opener)
            logging.debug('%s outgoing proxy defined' % proxy)

    def u(self, s):
        """Converts string to unicode string"""
        return s.encode('utf-8') if bool(s) else ''

    def mdcache(self, cswurl, constraints=[], maxrecords=10, maxharvest=20):
        """Fills the cache from a csw"""
        
        # cache directory for this csw
        if cswurl in self.cswlist:
            cswsig = self.cswlist[cswurl]['cswsig']
            cswpath = os.path.join(self.cachepath, cswsig)
        else:
            cswsig = hashlib.md5(cswurl).hexdigest()
            logging.info('%s : new signature %s' % (cswurl, cswsig))
            cswpath = os.path.join(self.cachepath, cswsig)
            if not(os.path.isdir(cswpath)):
                os.makedirs(cswpath)
            logging.info('%s %s created' % (cswurl, cswpath))
            
        manifest = {
            'cswsig': cswsig,
            'cswurl': cswurl,
            'domains': {
                'organisationName': self.mdPropertyValues(cswurl, 'organisationName').values()[0],
                'Subject': self.mdPropertyValues(cswurl, 'Subject').values()[0]
            }
        }
        
        f = open(os.path.join(cswpath, self.MANIFEST), 'w')
        f.write(json.dumps(manifest))
        f.close()

        logging.info('loading max %s md from %s' % (maxharvest, cswurl))
        csw = CatalogueServiceWeb(cswurl, skip_caps=True)
        first = True
        nextrecord = 0
        count = 0

        while True:
            if not first:
                nextrecord = csw.results['nextrecord']

            if count + maxrecords > maxharvest:
                maxrecords = maxharvest - count

            csw.getrecords2(
                esn='full', constraints=constraints, startposition=nextrecord,
                maxrecords=maxrecords, outputschema=self.OUTPUTSCHEMA)

            if csw.results['matches'] == 0:
                logging.info('0 md found from %s' % cswurl)
                break
            else:
                first = False
                # fetch records
                for rec_id, rec in csw.records.iteritems():
                    count += 1
                    logging.info(str(int(float(count)/min(maxharvest, csw.results['matches'])*100))+'%')
                    filename = os.path.join(cswpath, rec_id)
                    os.path.join(filename)
                    f = open(filename, 'w')
                    f.write(rec.xml)
                    f.close()
            
                # break if no records, beyond maxrecords or matches
                if csw.results['nextrecord'] == 0 \
                        or csw.results['returned'] == 0 \
                        or csw.results['nextrecord'] > csw.results['matches'] \
                        or csw.results['nextrecord'] > maxharvest:
                    logging.info('%s md loaded from %s' % (count, cswurl))
                    break

        return cswpath

    def mdcount(self, cswurl, constraints=[], startrecord=0, maxharvest=10):
        """Queries the csw and count md matching constraints"""
        csw = CatalogueServiceWeb(cswurl, skip_caps=True)
        csw.getrecords2(
            esn='brief', constraints=constraints, startposition=startrecord, maxrecords=maxharvest, resulttype='hits')
        return csw.results

    def mdsearch(self, cswurl, esn='summary', constraints=[], startrecord=0, maxrecords=10, maxharvest=20):
        tstart = datetime.datetime.now()
        """Queries a csw to retrieve md ids matching constraints"""
        records = {}

        logging.info('searching max %s md from %s' % (maxharvest, cswurl))
        csw = CatalogueServiceWeb(cswurl, skip_caps=True)
        first = True
        nextrecord = startrecord
        count = 0

        while True:
            if not first:
                nextrecord = csw.results['nextrecord']

            if count + maxrecords > maxharvest:
                maxrecords = maxharvest - count     # retrieve exactly maxharvest md

            csw.getrecords2(
                esn=esn, constraints=constraints, startposition=nextrecord,
                maxrecords=maxrecords, outputschema=self.OUTPUTSCHEMA)

            if csw.results['matches'] == 0:
                logging.info('0 md found from %s' % cswurl)
                break
            else:
                first = False
                # fetch records
                for rec_id, rec in csw.records.iteritems():
                    count += 1
                    percent = int(float(count)/min(maxharvest, csw.results['matches'])*100)
                    logging.debug('%s%% %s' % (percent, rec_id))
                    records[rec_id] = rec

                # get out if no records or beyond maxrecords
                if csw.results['nextrecord'] == 0 \
                        or csw.results['returned'] == 0 \
                        or csw.results['nextrecord'] > csw.results['matches'] \
                        or csw.results['nextrecord'] > maxharvest:
                    d = (datetime.datetime.now() - tstart).total_seconds()
                    logging.info('%s md found from %s in %d s' % (count, cswurl, d))
                    break

        return records

    def mdToShape(self, records, path):
        """map the md extents in a shapefile"""
        if len(records) > 0:
            s = shapefile.Writer(shapefile.POLYGON)
            s.autoBalance = 1
            s.field('MDID', 'C', 255)
            s.field('FILEID', 'C', 255)
            s.field('ORG', 'C', 255)
            s.field('TITLE', 'C', 255)
            s.field('DATE', 'C', 255)
            for rec_id, rec in records.iteritems():
                try:
                    md = MD(rec.xml)
                    s.poly(parts=[[
                        [md.lonmin, md.latmin, md.lonmax, md.latmin],
                        [md.lonmax, md.latmin, md.lonmax, md.latmax],
                        [md.lonmax, md.latmax, md.lonmin, md.latmax],
                        [md.lonmin, md.latmax, md.lonmin, md.latmin],
                        [md.lonmin, md.latmin, md.lonmax, md.latmin]
                    ]], shapeType=shapefile.POLYGON)
                    s.record(self.u(md.MD_Identifier), self.u(md.fileIdentifier), self.u(md.OrganisationName),
                             self.u(md.title), u(md.date))
                except:
                    logging.error('error for md %s' % id)
            s.save(path)
            logging.info('%s contains %s md' % (path, len(records)))
        else:
            logging.info('no record found')

    def mdPropertyValues(self, cswurl, dname):
        """returns a value list for a property name"""
        csw = CatalogueServiceWeb(cswurl, skip_caps=True)
        csw.getdomain(dname, dtype='property')
        return csw.results

    def parseFilter(self, s):
        """translates inspirobot filter syntax into fes
        for example:
            'OrganisationName = DREAL Bretagne && Type = dataset || OrganisationName ~ DDTM 29 && Type = dataset'
        """
        filters = []
        for f_or in [x.split('&&') for x in s.split('||')]:
            andgroup = []
            for f_and in f_or:
                if '=' in f_and:
                    a = [s.strip() for s in f_and.split('=')]
                    andgroup.append(fes.PropertyIsEqualTo(propertyname=a[0], literal=a[1]))
                elif '~' in f_and:
                    a = [s.strip() for s in f_and.split('~')]
                    andgroup.append(fes.PropertyIsLike(propertyname=a[0], literal=a[1]))
            filters.append(andgroup)
        return filters
        
        
### metadata class ######################################


class MD:
    """
    metadata with unit test methods
    """
    def __init__(self, xml):
        self.namespaces = {
            'gmd':  u'http://www.isotc211.org/2005/gmd',
            'gco': u'http://www.isotc211.org/2005/gco'
        }
        self.bbox = []
        self.xml = xml
        self.md = etree.XML(u(xml))
        self.fileIdentifier = xmlGetTextNodes(
            self.md,
            '/gmd:MD_Metadata/gmd:fileIdentifier/gco:CharacterString/text()',
            self.namespaces)
        self.MD_Identifier = xmlGetTextNodes(
            self.md,
            '/gmd:MD_Metadata/gmd:identificationInfo/'
            'gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/'
            'gmd:identifier/gmd:MD_Identifier/gmd:code/gco:CharacterString/text()',
            self.namespaces)
        self.title = xmlGetTextNodes(
            self.md,
            '/gmd:MD_Metadata/gmd:identificationInfo/'
            'gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/'
            'gmd:title/gco:CharacterString/text()',
            self.namespaces)
        self.OrganisationName = xmlGetTextNodes(
            self.md,
            '/gmd:MD_Metadata/gmd:identificationInfo/'
            'gmd:MD_DataIdentification/gmd:pointOfContact/'
            'gmd:CI_ResponsibleParty/gmd:organisationName/gco:CharacterString/text()',
            self.namespaces)
        self.abstract = xmlGetTextNodes(
            self.md,
            '/gmd:MD_Metadata/gmd:identificationInfo/'
            'gmd:MD_DataIdentification/gmd:abstract/gco:CharacterString/text()',
            self.namespaces)

        # date or datetime ?
        dates_str = xmlGetTextNodes(
            self.md,
            '/gmd:MD_Metadata/gmd:identificationInfo/'
            'gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/'
            'gmd:date/gmd:CI_Date/gmd:date/gco:Date/text()',
            self.namespaces)
        datetimes_str = xmlGetTextNodes(
            self.md,
            '/gmd:MD_Metadata/gmd:identificationInfo/'
            'gmd:MD_DataIdentification/gmd:citation/gmd:CI_Citation/'
            'gmd:date/gmd:CI_Date/gmd:date/gco:DateTime/text()',
            self.namespaces)
        if dates_str != "":
            self.date = parse_string_for_max_date(dates_str)
        else:
            self.date = parse_string_for_max_date(datetimes_str)
        
        # seems always datetime
        md_dates_str = xmlGetTextNodes(
            self.md,
            '/gmd:MD_Metadata/gmd:dateStamp/'
            'gco:DateTime/text()',
            self.namespaces)
        self.md_date = parse_string_for_max_date(md_dates_str)
        self.contact = {
            'mails': self.md.xpath(
                '/gmd:MD_Metadata/gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/'
                'gmd:CI_Contact/gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString/text()',
                namespaces=self.namespaces)
        }
        self.reports = []
        self.score = 100
        try:
            self.lonmin = float(xmlGetTextNodes(
                self.md,
                '/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/'
                'gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/'
                'gmd:westBoundLongitude/gco:Decimal/text()',
                self.namespaces))
            self.lonmax = float(xmlGetTextNodes(
                self.md,
                '/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/'
                'gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/'
                'gmd:eastBoundLongitude/gco:Decimal/text()',
                self.namespaces))
            self.latmin = float(xmlGetTextNodes(
                self.md,
                '/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/'
                'gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/'
                'gmd:southBoundLatitude/gco:Decimal/text()',
                self.namespaces))
            self.latmax = float(xmlGetTextNodes(
                self.md,
                '/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/'
                'gmd:extent/gmd:EX_Extent/gmd:geographicElement/gmd:EX_GeographicBoundingBox/'
                'gmd:northBoundLatitude/gco:Decimal/text()',
                self.namespaces))
        except:
            self.lonmin = -180
            self.lonmax = 180
            self.latmin = -90
            self.latmax = 90
        
    def __repr__(self):
        return self.fileIdentifier
        
    def __str__(self):
        return self.fileIdentifier
        
    def getScore(self):
        score = 100
        for rep in self.reports:
            if rep.getLevel() == 'critical':
                score -= 100
            elif rep.getLevel() == 'error':
                score -= 25
            elif rep.getLevel() == 'warning':
                score -= 10
        return score
    
    def asDict(self):
        return {
            'fileIdentifier': self.fileIdentifier,
            'MD_Identifier': self.MD_Identifier,
            'md_date': self.md_date,
            'title': self.title,
            'OrganisationName': self.OrganisationName,
            'abstract': self.abstract,
            'date': self.date,
            'contact': self.contact,
            'reports': [rep.asDict(['warning', 'error', 'critical']) for rep in self.reports],
            'score': self.getScore(),
            'latmin': self.latmin,
            'latmax': self.latmax,
            'lonmin': self.lonmin,
            'lonmax': self.lonmax
        }
        
    def run(self, utests):
        for utest in utests:
            utest.run(self.md)
            results = utest.getReports()
            for rep in results:
                if rep.getLevel() == 'critical':
                    self.score -= 100
                elif rep.getLevel() == 'error':
                    self.score -= 25
                elif rep.getLevel() == 'warning':
                    self.score -= 10
                self.reports.append(rep)


class MdUnitTestReport(object):
    """metadata test results"""
    def __init__(self, name='', abstract='', url=''):
        self.levels = ['debug', 'info', 'warning', 'error', 'critical']
        self.shortlevels = [s[0] for s in self.levels]
        self.name = name
        self.abstract = abstract
        self.url = url
        self.results = []
        self.maxlevel = 0

    def addResult(self, level, description):
        """appends a UnitTestResult to the report"""
        try:
            i = self.shortlevels.index(level.lower()[0])
        except:
            i = 1
        self.maxlevel = max(self.maxlevel, i)
        self.results.append((self.levels[i], description))
    
    def setNameAbstract(self, name, abstract=''):
        self.name = name
        self.abstract = abstract
    
    def setUrl(self, url):
        """sets an URL for the test"""
        self.url = url
        
    def getUrl(self):
        if self.url:
            return self.url
        else:
            return '#'
    
    def asDict(self, levels=['debug', 'info', 'warning', 'error', 'critical']):
        return {
            "name": self.name,
            "results": filter(lambda x: x[0] in levels, self.results)
        }
    
    def getLevel(self):
        """returns the test 'worst' level (info, warning...)"""
        return self.levels[self.maxlevel]
        
    def getResults(self):
        return self.results

    def __repr__(self):
        return str(self.results)
        
    def __str__(self):
        return "level=%s %s" % (self.getLevel(), self.results)


class MdUnitTest(object):
    """generic MdUnitTest class to be extended"""
    def __init__(self, cfg):
        self.cfg = cfg
        self.name = u'dummy check name'
        self.abstract = u'dummy check abstract'
        self.xpath = {}
        self.re = {}
        self.values = {}
        self.reports = []
        self.set()

    def __repr__(self):
        return self.name

    def clearReports(self):
        self.reports = []
        
    def addReport(self, res):
        self.reports.append(res)
        
    def set(self):
        """
        sample dummy test init
        replace this 
        """
        pass
        
    def test(self, md):
        """
        sample dummy test run
        replace this 
        """
        res = MdUnitTestReport(self.name, self.abstract)
        self.addReport(res)

    def run(self, md):
        self.clearReports()
        self.test(md)
        return self.reports
    
    def getReports(self):
        return self.reports

    __set = set
    __run = run
