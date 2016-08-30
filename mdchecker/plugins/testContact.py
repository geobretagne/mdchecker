#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mdchecker.inspirobot import Inspirobot
import re


class MdUnitTestContact(Inspirobot.MdUnitTest):
    """test mail address for md author and data provider"""
    def set(self):
        self.name = u'MAIL'
        self.abstract = u'Email. Vérifie que les contacts pour la ressource et pour les métadonnées comprennent ' \
                        u'chacun une adresse mail bien formée.'
        self.xpath = {
            'mailResponsibleParty': u"/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/"
                                    u"gmd:pointOfContact/gmd:CI_ResponsibleParty/"
                                    u"gmd:contactInfo/gmd:CI_Contact/gmd:address/gmd:CI_Address/"
                                    u"gmd:electronicMailAddress/gco:CharacterString/text()",
            'mailMDContact': u"/gmd:MD_Metadata/gmd:contact/gmd:CI_ResponsibleParty/gmd:contactInfo/gmd:CI_Contact/"
                             u"gmd:address/gmd:CI_Address/gmd:electronicMailAddress/gco:CharacterString/text()"
        }
        self.re = {
            'mail': r"[a-z0-9!#$%&'*+/=?^_`{|}~-]+"
                    r"(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*@"
                    r"(?:[a-z0-9](?:[a-z0-9-]*[a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?"
        }

    def test(self, md):
        rep = Inspirobot.MdUnitTestReport(self.name, self.abstract)
        # responsible party
        noderp = md.xpath(self.xpath['mailResponsibleParty'], namespaces=self.cfg['ns'])
        nodect = md.xpath(self.xpath['mailMDContact'], namespaces=self.cfg['ns'])
        if len(noderp) > 0:
            if re.match(self.re['mail'], noderp[0], re.I):
                rep.addResult('debug', u'partie responsable %s' % noderp[0])
            else:
                rep.addResult('error', u'mail contact pour la ressource mal formé : %s' % noderp[0])
        else:
            rep.addResult('error', u'mail contact pour la ressource manquant')

        if len(nodect) > 0:
            if re.match(self.re['mail'], nodect[0], re.I):
                rep.addResult('debug', u'contact %s' % nodect[0])
            else:
                rep.addResult('error', u'mail contact pour les métadonnées mal formé : %s' % nodect[0])
        else:
            rep.addResult('error', u'mail contact pour les métadonnées manquant')
        self.addReport(rep)
