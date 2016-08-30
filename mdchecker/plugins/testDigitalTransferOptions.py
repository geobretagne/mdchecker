#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mdchecker.inspirobot import Inspirobot
import re


class MdUnitTestDigitalTransferOptions(Inspirobot.MdUnitTest):
    """
    check digital transfer option declarations correctness for INSPIRE
    returns an array of MdUnitTestReport
    """
    def set(self):
        self.name = u'DTO'
        self.abstract = u"""Vérification des options de transfert numérique.
        On examine les différents protocoles proposés et on vérifie que les URLs sont bien formées.
        On vérifie qu'il existe au moins un service de visualisation et un de téléchargement.
        Attention, les URLs ne sont pas résolues et les services non mentionnés dans la MD ne sont pas recherchés.
        """
        self.xpath = {
            'DTO_OnlineResource': '/gmd:MD_Metadata/gmd:distributionInfo/gmd:MD_Distribution/gmd:transferOptions/'
                                  'gmd:MD_DigitalTransferOptions/gmd:onLine/gmd:CI_OnlineResource',
            'protocol': './gmd:protocol/gco:CharacterString/text()',
            'URL': './gmd:linkage/gmd:URL/text()',
            'layername': './gmd:name/gco:CharacterString/text()',
            'featuretype': './gmd:name/gco:CharacterString/text()'
        }
        self.re = {
            'WMSCapabilities': r'http.*\bservice=wms&request=getcapabilities{1}\b',
            'WFSCapabilities': r'http.*\bservice=wfs&request=getcapabilities{1}\b',
            'WCSCapabilities': r'http.*\bservice=wcs&request=getcapabilities{1}\b',
            'url': r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        }
    
    def test(self, md):
        view = False
        download = False
        
        # iterates over digital transfert options
        for olnode in md.xpath(self.xpath['DTO_OnlineResource'], namespaces=self.cfg['ns']):
            protocol = olnode.xpath(self.xpath['protocol'], namespaces=self.cfg['ns'])
            uri = olnode.xpath(self.xpath['URL'], namespaces=self.cfg['ns'])
            # results in our test results class
            rep = Inspirobot.MdUnitTestReport('DTO', u'Vérification digitalTransferOption')
            if protocol and uri:
                rep.setUrl(uri[0])
                # DTO WMS
                if protocol[0] == 'OGC:WMS':
                    rep.setNameAbstract('WMS', u'WMS. Vérifie le renseignement des liens WMS.')
                    if re.match(self.re['WMSCapabilities'], uri[0], re.I) and re.match(self.re['url'], uri[0]):
                        rep.addResult('debug', u'getCapabilities trouvé')
                        layername = olnode.xpath(self.xpath['layername'], namespaces=self.cfg['ns'])
                        if len(layername) == 1:
                            rep.addResult('debug', u'layername trouvé : %s' % layername[0])
                            view = True
                        else:
                            rep.addResult('error', u'layername non trouvé')
                    elif re.match(self.re['url'], uri[0]):
                        rep.addResult('warn', u'getCapabilities suspect : %s' % rep.url)
                    else:
                        rep.addResult('error', u'getCapabilities n\'est pas une URL : %s' % rep.url)
                # DTO WFS
                elif protocol[0] == 'OGC:WFS':
                    rep.setNameAbstract('WFS', u'WFS. Vérifie le renseignement des liens WFS.')
                    if re.match(self.re['WFSCapabilities'], uri[0], re.I) and re.match(self.re['url'], uri[0]):
                        rep.addResult('debug', u'getCapabilities trouvé')
                        featuretype = olnode.xpath(self.xpath['featuretype'], namespaces=self.cfg['ns'])
                        if len(featuretype) == 1:
                            rep.addResult('debug', u'featuretype trouvé : %s' % featuretype[0])
                            download = True
                        else:
                            rep.addResult('error', u'featuretype non trouvé')
                    else:
                        rep.addResult('warning', u'getCapabilities suspect : %s' % rep.url)
                # DTO WCS
                elif protocol[0] == 'OGC:WCS':
                    rep.setNameAbstract('WCS', u'WCS. Vérifie le renseignement des liens WCS.')
                    if re.match(self.re['WCSCapabilities'], uri[0], re.I) and re.match(self.re['url'], uri[0]):
                        rep.addResult('debug', u'getCapabilities trouvé')
                        download = True
                    else:
                        rep.addResult('warn', u'getCapabilities suspect : %s' % rep.url)
                # DTO download
                elif protocol[0] == 'WWW:DOWNLOAD-1.0-http--download':
                    if re.match(self.re['url'], uri[0]):
                        rep.setNameAbstract(u'DL', u'Vérifie la conformité des liens de téléchargement')
                        rep.addResult('debug', u'URL téléchargement trouvée')
                        download = True
                    else:
                        rep.addResult('error', 'mauvaise URL : %s' % rep.url)
                # DTO web
                elif protocol[0] == 'WWW:LINK-1.0-http--link':
                    rep.setNameAbstract('WWW', u'Vérifie la conformité des liens vers des pages web')
                    if re.match(self.re['url'], uri[0]):
                        rep.addResult('debug', u'URL trouvée')
                    else:
                        rep.addResult('error', u'mauvaise URL : %s' % rep.url)
                # DTO unknown
                else:
                    rep.setNameAbstract(u'WW?', u'Vérifie la conformité des autres URL')
                    if re.match(self.re['url'], uri[0]):
                        rep.addResult('debug', u'URL trouvée')
                    else:
                        rep.addResult('error', u'mauvaise URL : %s' % rep.url)
            else:
                rep.addResult('warning', u'protocole manquant')
            self.addReport(rep)
            
        rep = Inspirobot.MdUnitTestReport('view', u"Vérifie la présence d'un service de visualisation")
        if view:
            rep.addResult('info', u'service visualisation trouvé')
        else:
            rep.addResult('error', u'service visualisation non trouvé')
        self.addReport(rep)
        rep = Inspirobot.MdUnitTestReport('download', u"Vérifie la présence d'un service de téléchargement")
        if download:
            rep.addResult('info', u'service téléchargement trouvé')
        else:
            rep.addResult('error', u'service téléchargement non trouvé')
        self.addReport(rep)
