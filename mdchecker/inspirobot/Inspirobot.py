#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import urllib2
import base64
from owslib.csw import CatalogueServiceWeb
from owslib import fes
import os
import logging
import datetime
import hashlib
import json
import shapefile
import re

logging.basicConfig(level=logging.INFO)

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
        #
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
                logging.info('%s %s md cached'%(manifest['cswurl'], len(os.listdir(cswpath))))

    def getQueryables(self):
        return self.QUERYABLES

    def setproxy(self, proxy):
        """Sets an outgoing http proxy"""
        if proxy:
            proxyHandler = urllib2.ProxyHandler({"http" : proxy, "https": proxy})
            opener = urllib2.build_opener(proxyHandler)
            urllib2.install_opener(opener)
            logging.debug('%s outgoing proxy defined'%proxy)


    def u(self, s):
        """Converts string to unicode string"""
        return s.encode('utf-8') if bool(s) else ''


    def mdcache(self, cswurl, constraints=[], maxrecords=10, maxharvest=20):
        """Fills the cache from a csw"""
        
        # cache directory for this csw
        cswpath = ''
        cswsig = ''
        if self.cswlist.has_key(cswurl):
            cswsig = self.cswlist[cswurl]['cswsig']
            cswpath = os.path.join(self.cachepath, cswsig)
        else:
            cswsig = hashlib.md5(cswurl).hexdigest()
            logging.info('%s : new signature %s'%(cswurl, cswsig))
            cswpath = os.path.join(self.cachepath, cswsig)
            if not(os.path.isdir(cswpath)):
                os.makedirs(cswpath)
            logging.info('%s %s created'%(cswurl, cswpath))
            
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
        
        
        logging.info('loading max %s md from %s'%(maxharvest, cswurl))
        csw = CatalogueServiceWeb(cswurl, skip_caps=True)
        first = True
        more = True
        nextrecord = 0
        count = 0
        while more:
            if not(first):
                nextrecord = csw.results['nextrecord']
            if count+maxrecords > maxharvest:
                maxrecords = maxharvest - count
            csw.getrecords2(esn='full', constraints=constraints, startposition=nextrecord, maxrecords=maxrecords, outputschema=self.OUTPUTSCHEMA)
            if csw.results['matches']==0:
                logging.info('0 md found from %s'%cswurl)
                more = False
                break
            else:
                first = False
                # fetch records
                for id, rec in csw.records.iteritems():
                    count += 1
                    logging.info(str(int(float(count)/min(maxharvest, csw.results['matches'])*100))+'%')
                    filename = os.path.join(cswpath, id)
                    os.path.join(filename)
                    f=open(filename, 'w')
                    f.write(rec.xml)
                    f.close()
            
                # break if no records, beyond maxrecords or matches
                if csw.results['nextrecord'] == 0 \
                    or csw.results['returned'] == 0 \
                    or csw.results['nextrecord'] > csw.results['matches'] \
                    or csw.results['nextrecord'] > maxharvest:
                    more = False
                    logging.info('%s md loaded from %s'%(count, cswurl))
        return cswpath


    def mdcount(self, cswurl, constraints=[]):
        """Queries the csw and count md matching constraints"""
        csw = CatalogueServiceWeb(cswurl, skip_caps=True)
        csw.getrecords2(esn='brief', constraints=constraints)
        return csw.results
        


    def mdsearch(self, cswurl, esn='summary', constraints=[], startrecord=0, maxrecords=10, maxharvest=20):
        tstart = datetime.datetime.now()
        """Queries a csw to retrieve md ids matching constraints"""
        records = {}
        logging.info('searching max %s md from %s'%(maxharvest, cswurl))
        csw = CatalogueServiceWeb(cswurl, skip_caps=True)
        first = True
        more = True
        nextrecord = startrecord
        count = 0
        while more:
            if not(first):
                nextrecord = csw.results['nextrecord']
            if count+maxrecords > maxharvest:
                maxrecords = maxharvest - count # retrieve exactly maxharvest md
            csw.getrecords2(esn=esn, constraints=constraints, startposition=nextrecord, maxrecords=maxrecords, outputschema=self.OUTPUTSCHEMA)
            if csw.results['matches']==0:
                logging.info('0 md found from %s'%cswurl)
                more = False
                break
            else:

                first = False
                # fetch records
                for id, rec in csw.records.iteritems():
                    count += 1
                    percent = int(float(count)/min(maxharvest, csw.results['matches'])*100)
                    logging.debug('%s%% %s'%(percent, id))
                    records[id] = rec

                # get out if no records or beyond maxrecords
                if csw.results['nextrecord'] == 0 \
                    or csw.results['returned'] == 0 \
                    or csw.results['nextrecord'] > csw.results['matches'] \
                    or csw.results['nextrecord'] > maxharvest:
                    more = False
                    d = (datetime.datetime.now() - tstart).total_seconds()
                    logging.info('%s md found from %s in %d s'%(count, cswurl, d))
        return records


    def md2shp(self, records, path):
        """map the md extents in a shapefile"""
        if len(records)>0:
            s = shapefile.Writer(shapefile.POLYGON)
            s.autoBalance = 1
            s.field('ID', 'C', 50)
            s.field('TYPE', 'C', 20)
            s.field('TITLE', 'C', 255)
            for id, rec in records.iteritems():
                try:
                    if rec.hasattr(bbox):
                        xmin, ymin = float(rec.bbox.minx), float(rec.bbox.miny)
                        xmax, ymax = float(rec.bbox.maxx), float(rec.bbox.maxy)
                        s.poly(parts=[[
                            [xmin,ymin,xmax,ymin],
                            [xmax,ymin,xmax,ymax],
                            [xmax,ymax,xmin,ymax],
                            [xmin,ymax,xmin,ymin],
                            [xmin,ymin,xmax,ymin]
                        ]], shapeType=shapefile.POLYGON)
                        s.record(self.u(id), self.u(rec.type), self.u(rec.title))
                    else:
                        pass
                except:
                    print("error")
            s.save(path)
            logging.info('%s contains %s md'%(path, len(records)))
        else:
            logging.info('no record found')

    def mdPropertyValues(self, cswurl, dname):
        """returns a value list for a property name"""
        csw = CatalogueServiceWeb(cswurl, skip_caps=True)
        csw.getdomain(dname, dtype='property')
        return csw.results


    def parseFilter(self, s):
        """translates inspirobot filter syntax into fes
        
        for example : 'OrganisationName = DREAL Bretagne && Type = dataset || OrganisationName ~ DDTM 29 && Type = dataset'
        """
        filters = []
        for f_or in [x.split('&&') for x in s.split('||')]:
            andgroup = []
            for f_and in f_or:
                if '=' in f_and:
                    a = [s.strip() for s in f_and.split('=')]
                    andgroup.append(fes.PropertyIsEqualTo(propertyname=a[0], literal=a[1]))
                elif ('~') in f_and:
                    a = [s.strip() for s in f_and.split('~')]
                    andgroup.append(fes.PropertyIsLike(propertyname=a[0], literal=a[1]))
            filters.append(andgroup)
        return filters


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
    
    def asDict(self, levels = ['debug', 'info', 'warning', 'error', 'critical']):
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
        return "level=%s %s"%(self.getLevel(), self.results)




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
