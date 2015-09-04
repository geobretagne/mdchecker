#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mdchecker.inspirobot import Inspirobot
import re

class MdUnitTestGenealogy(Inspirobot.MdUnitTest):
    """test genealogy'"""
    def set(self):
        self.name = u'LINEAGE'
        self.abstract = u"Généalogie. Vérifie la présence de généalogie avec une description dépassant 25 caractères."
        self.xpath = {
            'lineage': u"/gmd:MD_Metadata/gmd:dataQualityInfo/gmd:DQ_DataQuality/gmd:lineage/gmd:LI_Lineage/gmd:statement/gco:CharacterString/text()"
        }

    def test(self, md):
        rep = Inspirobot.MdUnitTestReport(self.name, self.abstract)
        node = md.xpath(self.xpath['lineage'], namespaces=self.cfg['ns'])
        if len(node)==1:
            if len(node[0])>25:
                rep.addResult('debug', node[0])
            else:
                rep.addResult('warning', u'généalogie trop courte : %s chars'%len(node[0]))
        else:
            rep.addResult('error', u'généalogie présente %s fois'%len(node))
        self.addReport(rep)
