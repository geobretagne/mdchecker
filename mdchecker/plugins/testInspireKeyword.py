#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mdchecker.inspirobot import Inspirobot


class MdUnitTestInspireKeyword(Inspirobot.MdUnitTest):
    """search for a single INSPIRE keyword'"""
    def set(self):
        self.name = u'INSPIRE'
        self.abstract = u"""Valide le mot-clef INSPIRE s'il est présent."""
        self.xpath = {
            'inspire': u"/gmd:MD_Metadata/gmd:identificationInfo/gmd:MD_DataIdentification/"
                       u"gmd:descriptiveKeywords/gmd:MD_Keywords[gmd:thesaurusName/gmd:CI_Citation/"
                       u"gmd:title/gco:CharacterString/text()='GEMET - INSPIRE themes, version 1.0']",
            'subKeyword': u"gmd:keyword/gco:CharacterString/text()[contains('TX AL MA', State)]"
        }
        self.values = {
            'inspireKw': [
                u"Référentiel de coordonnées",
                u"Système de maillage géographique",
                u"Dénominations géographiques",
                u"Unités administratives",
                u"Adresses",
                u"Parcelles cadastrales",
                u"Réseaux de transport",
                u"Hydrographie",
                u"Sites protégés",
                u"Altitude",
                u"Occupation des terres",
                u"Ortho-imagerie",
                u"Géologie",
                u"Unités statistiques",
                u"Bâtiments",
                u"Sols",
                u"Usage des sols",
                u"Santé et sécurité des personnes",
                u"Services d'utilité publique et services publics",
                u"Installations de suivi environnemental",
                u"Lieux de production et sites industriels",
                u"Installation agricoles et aquacoles",
                u"Répartition de la population - Démographie",
                u"Zones de gestion, de restriction ou de réglementation et unités de déclaration",
                u"Unités de déclaration",
                u"Zones à risque naturel",
                u"Conditions atmosphériques",
                u"Caractéristiques géographiques météorologiques",
                u"Caractéristiques. géographiques océanographiques",
                u"Régions maritimes",
                u"Régions biogéographiques",
                u"Habitats et biotopes",
                u"Répartition des espèces",
                u"Sources d'énergie",
                u"Ressources minérales"
            ]
        }
    
    def test(self, md):
        rep = Inspirobot.MdUnitTestReport(self.name, self.abstract)
        node = md.xpath(self.xpath['inspire'], namespaces=self.cfg['ns'])
        if len(node) > 1:
            rep.addResult('warning', u'mot-clés INSPIRE utilisés %s fois' % len(node))
            self.addReport(rep)
        elif len(node) == 1:
            kw = node[0].xpath(self.xpath['subKeyword'], namespaces=self.cfg['ns'])[0]
            if kw in self.values['inspireKw']:
                rep.addResult('info', u'INSPIRE/%s' % kw)
            else:
                rep.addResult('warning', u'INSPIRE/%s incorrect' % kw)
            self.addReport(rep)
        # 0 is not an error
