#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mdchecker.inspirobot import Inspirobot


class MdUnitTestSpatial(Inspirobot.MdUnitTest):
    """check spatial descriptors"""
    def set(self):
        self.name = u'GEO'
        self.abstract = u"Descripteurs spatiaux. Vérifie si une résolution est fournie."
        self.xpath = {
            'denominator': '/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/'
                           'gmd:spatialResolution/gmd:MD_Resolution/gmd:equivalentScale/'
                           'gmd:MD_RepresentativeFraction/gmd:denominator/gco:Integer',
            'distance':    '/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/'
                           'gmd:spatialResolution/gmd:MD_Resolution/gmd:distance/'
                           'gco:Distance',
        }

    def test(self, md):
        rep = Inspirobot.MdUnitTestReport(self.name, self.abstract)
        node_den = md.xpath(self.xpath['denominator'], namespaces=self.cfg['ns'])
        node_dis = md.xpath(self.xpath['distance'], namespaces=self.cfg['ns'])

        if len(node_den) > 1:
            rep.addResult('error', u'Dénominateur fourni %s fois' % len(node_den))
            self.addReport(rep)

        if len(node_dis) > 1:
            rep.addResult('warning', u'Distance fournie %s fois' % len(node_dis))
            self.addReport(rep)

        if len(node_dis) > 0 and len(node_den) > 0:
            rep.addResult('error', u'Distance et résolution fournis simultanément')
            self.addReport(rep)

        if len(node_dis) == 0 and len(node_den) == 0:
            rep.addResult('warning', u'Aucune résolution fournie')
            self.addReport(rep)
