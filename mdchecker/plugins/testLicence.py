#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mdchecker.inspirobot import Inspirobot


class MdUnitTestLicence(Inspirobot.MdUnitTest):
    """search for licence'"""
    def set(self):
        self.name = u'LIC'
        self.abstract = u"Licence et droits. Vérifie si le mot clef opendata est présent;" \
                        u"présence de contraintes légales; limitations d'usage dépassant 25 caractères."
        self.xpath = {
            'opendata': u"/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/"
                        u"gmd:descriptiveKeywords/gmd:MD_Keywords/gmd:keyword/"
                        u"gco:CharacterString[text()='données ouvertes']",
            'uselimitation': u"/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/"
                             u"gmd:resourceConstraints/gmd:MD_LegalConstraints/"
                             u"gmd:useLimitation/gco:CharacterString/text()",
            'restrictions': u"/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/"
                            u"gmd:resourceConstraints/gmd:MD_LegalConstraints/gmd:accessConstraints/"
                            u"gmd:MD_RestrictionCode/@codeListValue",
            'constraints': u"/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/"
                           u"gmd:resourceConstraints/gmd:MD_LegalConstraints/"
                           u"gmd:otherConstraints/gco:CharacterString[text()!=\"Pas de restriction d'accès public\"]"
        }
    
    def test(self, md):
        # limitations and restriction check
        rep2 = Inspirobot.MdUnitTestReport(self.name, self.abstract)
        uselimitation = md.xpath(self.xpath['uselimitation'], namespaces=self.cfg['ns'])
        restriction = md.xpath(self.xpath['restrictions'], namespaces=self.cfg['ns'])
        if len(uselimitation) > 0:
            rep2.setNameAbstract(u'LIMIT', u'useLimitation. Vérifie la longueur de ce champ.')
            if len(uselimitation[0]) > 25:
                rep2.addResult('debug', u'useLimitation : %s' % uselimitation[0])
            else: 
                rep2.addResult('debug', u'useLimitation < 25 char : %s' % uselimitation[0])
        else:
            rep2.setNameAbstract(u'LIC', u'Licence. Vérifie la présence de useLimitation.')
            rep2.addResult('error', u'useLimitation manquant')
        
        if len(restriction) > 0:
            rep2.addResult('debug', u'otherRestrictions : %s' % restriction[0])
        else:
            rep2.addResult('error', u'otherRestrictions manquant')
        self.addReport(rep2)

        # open licence check
        node_kwol = md.xpath(self.xpath['opendata'], namespaces=self.cfg['ns'])
        if len(node_kwol) == 1:
            rep1 = Inspirobot.MdUnitTestReport(self.name, self.abstract)
            rep1.setNameAbstract('OPEN', u'Données ouvertes. Recherche la présence du mot-clé.')
            rep1.addResult('info', u'keyword données ouvertes détecté')
            if len(md.xpath(self.xpath['constraints'], namespaces=self.cfg['ns'])) != 1:
                rep1.addResult('warning', u'otherConstraints incorrect')
            self.addReport(rep1)
