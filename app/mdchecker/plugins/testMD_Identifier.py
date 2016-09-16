#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mdchecker.inspirobot import Inspirobot
import re


class MdUnitTestMdIdentifier(Inspirobot.MdUnitTest):
    """check MD_Identifier'"""
    def set(self):
        self.name = 'ID'
        self.abstract = u"MD_Identifier. " \
                        u"Vérifie sa présence et sa conformité à une expression régulière."
        self.xpath = {
            'MD_Identifier': u"/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/"
                             u"gmd:citation/gmd:CI_Citation/gmd:identifier/gmd:MD_Identifier/"
                             u"gmd:code/gco:CharacterString/text()"
        }
        self.re = {
            'MD_Identifier': r'^[A-Za-z0-9-_\.\/:\?=&]+$'
        }
    
    def test(self, md):
        rep = Inspirobot.MdUnitTestReport(self.name, self.abstract)
        md_identifier = md.xpath(self.xpath['MD_Identifier'], namespaces=self.cfg['ns'])
        if len(md_identifier) != 1:
            rep.addResult('error', u'nb de MD_Identifier incorrect : %s' % len(md_identifier))
        elif not(re.match(self.re['MD_Identifier'], md_identifier[0], re.I)):
            rep.addResult('warning', u'format MD_Identifier incorrect : %s' % md_identifier[0])
        else:
            rep.addResult('debug', u'MD_Identifier OK')
        self.addReport(rep)
